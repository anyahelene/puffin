from flask.json.tag import TaggedJSONSerializer
import logging, random
from io import StringIO
import csv
from puffin.canvas.users import CanvasConnection
from wtforms import (
    StringField,
    SelectField,
    SubmitField,
    validators,
    IntegerField,
    DateTimeField,
    ValidationError,
    SelectMultipleField,
    BooleanField,
)
from flask_wtf import FlaskForm
from puffin.util.util import *
from puffin.util.errors import ErrorResponse
from puffin.gitlab.users import GitlabConnection
from simpleeval import simple_eval
from sqlalchemy.orm import aliased
from sqlalchemy.exc import IntegrityError
from sqlalchemy import alias, and_, or_, select, column
from puffin.db.database import db_session as db
from puffin.db.model_util import (
    check_group_membership,
    check_unique,
    new_id,
    get_or_define,
    update_from_uib,
    update_groups_from_uib,
)
from puffin.db.model_views import CourseUser, UserAccount
from datetime import datetime, timezone
import os
import posixpath
from flask import Blueprint, Flask, current_app, request, session, url_for, make_response
from flask_login import login_required, current_user as current_user_proxy
from gitlab import GitlabOperationError
from slugify import slugify
from puffin.db.model_tables import (
    Account,
    AuditLog,
    JoinModel,
    LastSync,
    Project,
    User,
    Enrollment,
    Course,
    Group,
    Membership,
    PRIVILEGED_ROLES
)
current_user: User = current_user_proxy

logger = logging.getLogger(__name__)

bp = Blueprint("courses", __name__, url_prefix="/courses")


def init(app: Flask, parent: Blueprint):
    (parent or app).register_blueprint(bp)


def get_course(course_id_or_slug):
    course_id_or_slug = intify(course_id_or_slug)
    if isinstance(course_id_or_slug, int):
        where = Course.external_id == course_id_or_slug
    elif isinstance(course_id_or_slug, str):
        where = Course.slug == course_id_or_slug
    if current_user.is_admin:
        return db.execute(select(Course).where(where)).scalar_one_or_none()
    else:
        return db.execute(
            select(Course).where(
                where,
                Enrollment.course_id == Course.id,
                Enrollment.user_id == current_user.id,
            )
        ).scalar_one_or_none()


def get_course_or_fail(course_id_or_slug):
    course = get_course(course_id_or_slug)
    if course == None:
        raise ErrorResponse(
            "No such accessible course", course_id_or_slug, status_code=404
        )
    return course


def get_group(course, group_id_or_slug, privileged = False):
    group_id_or_slug = intify(group_id_or_slug)
    if isinstance(group_id_or_slug, int):
        where = and_(Group.id == group_id_or_slug, Group.course_id == course.id)
    elif isinstance(group_id_or_slug, str):
        where = and_(Group.slug == group_id_or_slug, Group.course_id == course.id)

    if privileged or is_privileged(current_user, course):
        return db.execute(select(Group).where(where)).scalar_one_or_none()
    else:
        return db.execute(
            select(Group).where(
                where, Membership.group_id == Group.id, Membership.join_model != JoinModel.REMOVED, Membership.user_id == current_user.id
            )
        ).scalar_one_or_none()


def get_group_or_fail(course, group_id_or_slug, privileged = False):
    group = get_group(course, group_id_or_slug, privileged)
    if group == None:
        raise ErrorResponse(
            "No such accessible group", group_id_or_slug, status_code=404
        )
    return group


def is_privileged(user, course):
    if user.is_admin:
        return True
    en = current_user.enrollment(course)
    if not en:
        return False
    return en.role in PRIVILEGED_ROLES


@bp.get("/")
@login_required
def courses():
    if current_user.is_admin:
        courses = db.execute(select(Course).order_by(
            Course.name)).scalars().all()
    else:
        subq = (
            select(Enrollment)
            .where(Enrollment.course_id == Course.id, Enrollment.user == current_user)
            .exists()
        )
        courses = (
            db.execute(select(Course).where(subq).order_by(
                Course.name)).scalars().all()
        )

    return [c.to_result(is_privileged(current_user, c)) for c in courses]


@bp.get("/<course_spec>/")
@login_required
def course(course_spec):
    course = get_course(course_spec)
    if request.args.get("from_canvas") == "true":
        if not current_user.is_admin:  # TODO?
            raise ErrorResponse("Access denied", status_code=403)
        cc: CanvasConnection = current_app.extensions["puffin_canvas_connection"]
        if current_user.is_admin and course_spec.isdigit():
            return cc.clean_course(cc.get_course(course_spec))
        elif course:
            en = current_user.enrollment(course)
            if current_user.is_admin or en.role in ["admin", "ta", "teacher"]:
                return cc.clean_course(cc.get_course(course.external_id))
        raise ErrorResponse("Access denied", status_code=403)
    else:
        course = get_course_or_fail(course_spec)
        return course.to_result(is_privileged(current_user, course))


class EditCourseForm(FlaskForm):
    name = StringField(
        "Course name", [validators.regexp(VALID_DISPLAY_NAME_REGEX)])
    slug = StringField("Slug", [validators.regexp(VALID_SLUG_REGEX)])
    canvas_id = IntegerField("Canvas id")
    gitlab_path = StringField(
        "Gitlab path", [validators.regexp(VALID_SLUG_PATH_OR_EMPTY_REGEX)]
    )
    gitlab_student_path = StringField(
        "Gitlab student path", [validators.regexp(
            VALID_SLUG_PATH_OR_EMPTY_REGEX)]
    )
    expiry_date = StringField("Expiry Date")


@bp.route("/<course_spec>/", methods=["PUT", "POST"])
@login_required
def new_course(course_spec):
    if not current_user.is_admin:  # TODO?
        raise ErrorResponse("Access denied", status_code=403)

    course = get_course(course_spec)
    print(request.form)
    form = EditCourseForm()
    for k, v in form._fields.items():
        print(k, v, v.raw_data, v.data)
    changes = []
    if not form.is_submitted():
        raise ErrorResponse("Bad request", status_code=400)
    if not course:
        if not form.canvas_id.validate(form):
            raise ErrorResponse("Bad request", status_code=400)
        if current_user.is_admin:
            changes = changes + _create_course(int(course_spec))
            course = get_course(course_spec)

    if course:
        en = current_user.enrollment(course)
        if current_user.is_admin or en.role in ["admin", "ta", "teacher"]:
            if form.name.validate(form):
                course.name = form.name.data
            if form.slug.validate(form):
                course.slug = form.slug.data
            elif form.name.validate(form):
                course.slug = slugify(form.name.data)
            d = decode_date(form.expiry_date.data)
            if d:
                course.expiry_date = d
        else:
            raise ErrorResponse("Access denied", status_code=403)
        if current_user.is_admin or en.role in ["admin", "teacher"]:
            newData = course.json_data.copy()
            for key in Course.info["data"]:
                if getattr(form, key, None) and getattr(form, key).validate(form):
                    newData[key] = getattr(form, key).data
            if newData != course.json_data:
                course.json_data = newData
        print(db.dirty)
        for obj in db.dirty:
            changes.append((obj.__tablename__, obj.id))
        db.commit()
    return changes


@bp.post("/<course_spec>/sync")
@login_required
def course_sync(course_spec):
    course = get_course_or_fail(course_spec)
    if is_privileged(current_user, course):
        return _sync_course(course)
    else:
        raise ErrorResponse("Access denied", status_code=403)


def _create_course(course_id: int):
    cc: CanvasConnection = current_app.extensions["puffin_canvas_connection"]

    canvas_course = cc.get_course(course_id)

    course, created = get_or_define(
        db,
        Course,
        {"slug": canvas_course["sis_course_id"]},
        {
            "name": canvas_course["name"],
            "external_id": canvas_course["id"],
            "expiry_date": canvas_course["end_at"],
        },
    )

    db.commit()
    return _sync_course(course)


def _sync_course(course: Course):
    result = course.to_json()
    canvas_accs = 0
    gitlab_accs = 0
    sync_time = now()
    result["changes"] = changes = []

    print("\n\n\n\n")
    logger.info("sync_course: %s, %s, %s", course, request.args, request.form)

    if request.args.get("sync_canvas") or request.form.get("sync_canvas"):
        cc: CanvasConnection = current_app.extensions["puffin_canvas_connection"]
        userlist = cc.get_users(course.external_id)
        for row in userlist:
            acc = update_from_uib(
                db, row, course, changes=changes, sync_time=sync_time)
            if acc:
                canvas_accs += 1
        result["num_canvas_users"] = canvas_accs

    if request.args.get("sync_canvas_groups") or request.form.get("sync_canvas_groups"):
        course_groups_sync(course.external_id)
    if request.args.get("sync_gitlab") or request.form.get("sync_gitlab"):
        gc: GitlabConnection = current_app.extensions["puffin_gitlab_connection"]
        for user in (
            db.execute(
                select(User).where(
                    Enrollment.user_id == User.id, Enrollment.course_id == course.id
                )
            )
            .scalars()
            .all()
        ):
            acc = gc.find_gitlab_account(db, user, sync_time=sync_time)
            if acc:
                gitlab_accs += 1
        result["num_gitlab_users"] = gitlab_accs

    return changes


@bp.get("/<course_spec>/users/")
@login_required
def course_users(course_spec):
    course = get_course_or_fail(course_spec)

    if not is_privileged(current_user, course):
        alias = aliased(Membership)
        # find all the groups the user is a member of
        subq = select(Group.id).where(Group.course_id == course.id, 
                                   alias.group_id == Group.id,
                                   alias.user_id == current_user.id,)
        # select users who are in one or more of those groups
        where = [or_(select(Membership.user_id).where(Membership.user_id == CourseUser.id,
                                                      Membership.__table__.c.group_id.in_(subq)).exists(),
                     CourseUser.id == current_user.id)]
    else:
        where = []

    result = []
    if request.args.get("accounts", False) or request.form.get("accounts", False):
        query = (select(CourseUser, UserAccount)
            .where(CourseUser.course_id == course.id, CourseUser.id == UserAccount.id, *where)
            .order_by((CourseUser.role == "student").desc(), CourseUser.lastname))
        #print('query', query)
        users = db.execute(query).all()
        logger.info("users: found %s records", len(users))
        for u, a in users:
            u = u.to_result(is_privileged(current_user, course))
            u.update(a.to_result(is_privileged(current_user, course)))
            u["_type"] = "course_user,user_account"
            result.append(u)
    else:
        users = (
            db.execute(
                select(User, CourseUser)
                .where(CourseUser.course_id == course.id, User.id == CourseUser.id, *where)
                .order_by((CourseUser.role == "student").desc(), CourseUser.lastname)
            )
            .all()
        )

        logger.info("users: found %s records", len(users))
        if request.args.get("details") or request.form.get("details"):
            result = [__user_details(u, course) for (u,cu) in users]
        else:
            users = [cu for (u,cu) in users]
            result = [u.to_result(is_privileged(current_user, course))
                    for u in users]
        
    if request.args.get("csv") or request.form.get("csv") or request.accept_mimetypes.best_match(['application/json', 'text/html', 'text/csv']) == 'text/csv':
        response = make_response()
        for entry in result:
            entry['sortable_name'] = f'{entry.get("lastname")}, {entry.get("firstname")}'
            groups = entry.get('groups')
            if groups != None:
                entry['section'] = ','.join([g['group_slug'] for g in groups if g['kind'] == 'section' and g['role'] == 'student'])
                entry['team'] = ','.join([g['group_slug'] for g in groups if g['kind'] == 'team' and g['role'] == 'student'])
                if is_privileged(current_user, course):
                    entry['review_team'] = ','.join([g['group_slug'] for g in groups if g['kind'] == 'team' and g['role'] == 'reviewer'])
                del entry['groups']
            for k in ['is_admin', 'locale', 'expiry_date', 'key']:
                if k in entry:
                    del entry[k]
        with StringIO() as f:
            fieldnames = [n  for n in result[0].keys() if not n.startswith('_')]
            w = csv.DictWriter(f, fieldnames,extrasaction = 'ignore', dialect='excel')
            w.writeheader()
            w.writerows(result)
            print('CSV: ', f.getvalue())
            print(result[0].keys())
            response.content_type = 'text/csv'
            response.charset = 'utf-8'
            response.data = f.getvalue()
            response.headers.add('Content-Disposition', f'attachment; filename="{course.slug}_users.csv"')
            print('response', response)
            return response
        
        
    return result


def __user_details(user: User, course: Course):
    obj = user.to_json()
    obj["role"] = user.enrollment(course).role
    obj["groups"] = [
        {"group_id": m.group.id, "group_slug": m.group.slug, "role": m.role, "kind":g.kind, "joined" : m.join_model.name}
        for (m,g) in db.execute(select(Membership,Group).where(Membership.user_id == user.id,
                                                               Membership.group_id == Group.id, 
                                                               Group.course_id == course.id,
                                                               Membership.join_model != JoinModel.REMOVED)).all()
    ]
    if not obj.get("locale") and current_app.config.get("DEFAULT_LOCALE"):
        obj["locale"] = current_app.config.get("DEFAULT_LOCALE")
    canvas_account = user.account("canvas")
    if canvas_account:
        obj["canvas_id"] = canvas_account.external_id
        obj["canvas_username"] = canvas_account.username
    gitlab_account = user.account("gitlab")
    if gitlab_account:
        obj["gitlab_id"] = gitlab_account.external_id
        obj["gitlab_username"] = gitlab_account.username
    return obj


@bp.get("/<course_spec>/users/<user_id>")
@login_required
def course_user(course_spec, user_id):
    course = get_course_or_fail(course_spec)
    if user_id.isdigit():
        user_id = int(user_id)
    elif user_id == "self":
        user_id = current_user.id

    if not is_privileged(current_user, course) and user_id != current_user.id:
        raise ErrorResponse("Access denied", status_code=403)

    if type(user_id) == int:
        u = db.execute(
            select(User)
            .join(User.enrollments)
            .filter_by(course=course, user_id=user_id)
            .order_by(User.lastname)
        ).scalar_one()
        return __user_details(u, course)
    else:
        raise ErrorResponse("Not found", status_code=404)


@bp.get("/<course_spec>/groups/")
@bp.get("/<course_spec>/teams/")
@login_required
def get_course_groups(course_spec):
    course = get_course_or_fail(course_spec)
    priv = is_privileged(current_user, course)

    if not priv:
        # restrict to groups the user is a member of
        where = []  # Membership.group_id == Group.id, Membership.user_id == current_user.id, Membership.join_model != JoinModel.REMOVED]
    else:
        where = []

    if request.path.endswith('teams/'):
        where.append(Group.kind == 'team')
    # TODO: add other filters

    groups = (
        db.execute(
            select(Group).where(Group.course_id ==
                                course.id, *where).order_by(Group.name)
        )
        .scalars()
        .all()
    )
    logger.info("groups: found %s records", len(groups))

    return [g.to_result(priv or current_user.is_member(g)) for g in groups]


@bp.get("/<course_spec>/memberships/")
@login_required
def get_course_memberships(course_spec):
    course = get_course_or_fail(course_spec)
    if not is_privileged(current_user, course):
        membership_alias = aliased(Membership)
        where = [Membership.group_id == membership_alias.group_id,
                 membership_alias.user_id == current_user.id, 
                 Membership.join_model != JoinModel.REMOVED,
                 or_(Membership.role != 'reviewer', Membership.user_id == current_user.id)] # TODO
    else:
        where = [Membership.join_model != JoinModel.REMOVED]
    members = (
        db.execute(
            select(Membership).where(
                Membership.group_id == Group.id, Group.course_id == course.id,
                *where
            )
        )
        .scalars()
        .all()
    )
    logger.info("memberships: found %s records", len(members))

    return [m.to_json() for m in members]

# e.g.: {"name":"Microissant","slug":"microissant", "join_model":"AUTO", "join_source":"gitlab(33690, students_only=True)", "kind":"team"}


@bp.post("/<course_spec>/teams/")
@bp.post("/<course_spec>/groups/<int:group_id>/teams/")
@login_required
def create_course_team(course_spec, group_id=None):
    course = get_course_or_fail(course_spec)
    if not is_privileged(current_user, course):
        raise ErrorResponse('access denied', status_code=403)

    parent_id = (
        db.execute(select(Group).filter_by(
            course=course, id=group_id)).scalar_one().id
        if group_id
        else None
    )

    form = CreateTeamForm()

    if not form.slug.data:
        form.slug.data = slugify(form.name.data)
    print(
        f'Received form: {"invalid" if not form.validate() else "valid"} {form.form_errors} {form.errors}'
    )
    print(
        request.form,
        form.meta.csrf_class,
        form.meta.csrf_field_name,
        request.headers.get("X-CSRFToken"),
    )
    if form.validate():
        join_source = f"gitlab({form.project_id.data})"

        check_unique(
            db,
            Group,
            "Team already exists",
            ("slug", Group.slug == form.slug.data),
            ("project", Group.join_source == join_source),
        )
        obj = Group(
            id=new_id(db, Group),
            name=form.name.data,
            slug=form.slug.data,
            course_id=course.id,
            kind="team",
            join_model=JoinModel.AUTO,
            external_id=form.canvas_id.data,
            parent_id=parent_id,
            join_source=join_source,
            json_data={
                "project_path": form.project_path.data,
                "project_name": form.project_name.data,
                "project_id": form.project_id.data,
            },
        )
        logger.info("group object: %s", obj)

        try:
            db.add(obj)
            db.commit()
        except IntegrityError as e:
            logger.error("Failed to add team: %s %s",
                         type(e), e.orig, exc_info=True)
            return {
                "status": "error",
                "code": 400,
                "message": "Team already exists",
            }, 400
        return obj.to_json()
    else:
        raise ErrorResponse("Invalid request form",
                            status_code=400, errors=form.errors)


class CreateGroupForm(FlaskForm):
    name = StringField(
        "Group name", [validators.regexp(VALID_DISPLAY_NAME_REGEX)])
    kind = StringField(
        "Group kind", [validators.regexp(VALID_DISPLAY_NAME_REGEX)])
    join_model = SelectField(
        "Joining",
        choices=[(x.name, x.value.capitalize()) for x in JoinModel],
        default=JoinModel.RESTRICTED.name,
    )
    join_source = StringField("Auto-join Source")
    slug = StringField("Slug", [validators.regexp(VALID_SLUG_REGEX)])
    submit = SubmitField("Submit")


class CreateTeamForm(FlaskForm):
    name = StringField(
        "Team name", [validators.regexp(VALID_DISPLAY_NAME_REGEX)])
    project_path = StringField(
        "Team project", [validators.regexp(VALID_SLUG_PATH_REGEX)]
    )
    project_id = IntegerField("Team project id")
    project_name = StringField("Team project name")
    canvas_id = IntegerField("Canvas group id")
    slug = StringField("Slug", [validators.regexp(VALID_SLUG_REGEX)])
    submit = SubmitField("Submit")


@bp.get("/<course_spec>/teams/reviews/assign/<int:user_id>")
@login_required
def team_project_review_get_assigned(course_spec, user_id = None):
    course = get_course_or_fail(course_spec)
    user_id = user_id if is_privileged(current_user, course) and user_id != None else current_user.id
    
    assigned = db.execute(select(Group).where(Membership.user_id == user_id,
                                              Membership.role == 'reviewer',
                                              Membership.group_id == Group.id)).scalars().all()
    
    return [t.to_result(True) for t in assigned]

@bp.post("/<course_spec>/teams/reviews/assign/<int:user_id>")
@login_required
def team_project_review_assign(course_spec, user_id = None):
    course = get_course_or_fail(course_spec)
    user_id = user_id if is_privileged(current_user, course) and user_id != None else current_user.id
    user : User = db.get(User, user_id)
    #if is_privileged(current_user, course):
    #    raise ErrorResponse('Manual review assignment not implemented yet')

    already_assigned = db.execute(select(Group).where(Membership.user_id == user_id, Membership.role == 'reviewer', Membership.group_id == Group.id)).scalars().all()
    if len(already_assigned) != 0:
        raise ErrorResponse(f'You are already assigned as reviewer for {", ".join([repr(g.name) for g in already_assigned])}')
    
    user_teams = [m.group_id for m in user.memberships]
    print('user_teams', user_teams)
    teams:list = db.execute(select(Group).where(Group.course_id == course.id,
                                                Group.kind == 'team',
                                                )).scalars().all()
    reviewers = db.execute(select(Membership).where(Membership.group_id == Group.id,
                                                  Group.course_id == course.id,
                                                  Membership.role == 'reviewer',
                                                  Group.kind == 'team')).scalars().all()
    team_reviewers = {team.id:[] for team in teams}
    for r in reviewers:
        team_reviewers[r.group_id].append(r.user_id)
    least = min([len(l) for l in team_reviewers.values()])
    eligible_teams = [t for t in teams if len(team_reviewers[t.id]) == least and t.id not in user_teams]
    if len(eligible_teams) > 0:
        team : Group = random.choice(eligible_teams)
        print('teams', least,sorted([t.id for t in eligible_teams]), team_reviewers)
        print('picked team', team.id)
        print('reviewers', list(reviewers))
        n_reviewers = len(team_reviewers[team.id])
        logger.info('Reviewer assignment sanity check: %s, %d=%d', team.memberships, least, n_reviewers)
        if user_id in [m.group_id for m in team.memberships] or n_reviewers != least:
            logger.error('Reviewer assignment sanity check: %s, %s=%s', team.memberships, least, n_reviewers)
            raise ErrorResponse('bug in reviewer assigment!')
        membership, created = get_or_define(db, Membership, {'group_id': team.id, 'user_id': user.id},
                                                {'role': 'reviewer', 'join_model': JoinModel.CLOSED})
        db.add(membership)
        db.commit()
        return team.to_json()
    
    raise ErrorResponse('No suitable team project found')


@bp.post("/<course_spec>/teams/check_uploads")
@login_required
def team_check_uploads(course_spec):
    course = get_course_or_fail(course_spec)

    if not is_privileged(current_user, course):
        raise ErrorResponse('access denied', status_code=403)

    teams = db.execute(select(Group).where(Group.course_id == course.id, Group.kind == 'team')).scalars().all()
    
    for t in teams:
        if 'share' not in t.json_data:
            t.json_data['share'] = {}
            
        #path = url_for('app.courses.team_get_file', course_spec=course_spec, path=f'{t.slug}.jar')
        name = f'{t.slug}.jar'
        print(name, os.path.join(current_app.config['APP_DOWNLOAD_DIR'], f'{t.slug}.jar'))
        if os.path.exists(os.path.join(current_app.config['APP_DOWNLOAD_DIR'], f'{t.slug}.jar')):
            t.json_data['share']['jar_file'] = name
            t.json_data['share']['share_jar'] = True
            db.add(t)
        #path = url_for('app.courses.team_get_file', course_spec=course_spec, path=f'{t.slug}.zip')
        name = f'{t.slug}.zip'
        if os.path.exists(os.path.join(current_app.config['APP_DOWNLOAD_DIR'], f'{t.slug}.zip')):
            t.json_data['share']['src_file'] = name
            t.json_data['share']['share_src'] = False
            db.add(t)
    db.commit()
    return {}

@bp.get("/<course_spec>/teams/<group_spec>/files/<path>")
@login_required
def team_get_file(course_spec, group_spec, path):
    course = get_course_or_fail(course_spec)
    group = get_group_or_fail(course, group_spec, True)
    
    logger.info('Get file: user=%s file=%s', current_user.email, path)
    share_file = None
    mime_type = None
    if path == f'{group.slug}.jar':
        share_file = 'share_jar'
        mime_type = 'application/java-archive'
    elif path == f'{group.slug}.zip':
        share_file = 'share_src'
        mime_type = 'application/zip'
        
    def has_access():
        if is_privileged(current_user, course):
            logger.info('Get file: has access due to privilege')
            return True
        if db.execute(select(Membership.id).where(Membership.group_id == group.id, Membership.user_id == current_user.id,
                                        Membership.join_model != JoinModel.REMOVED)).first() != None:
            logger.info('Get file: has access due to group membership')
            return True
        if group.json_data.get('share', {}).get(share_file, False):
            logger.info('Get file: has access due to sharing')
            return True
    
    if not share_file:
        raise ErrorResponse('file not found', status_code=404)
    if has_access():
        response = make_response()
        response.mimetype = mime_type
        response.headers.add('X-Accel-Redirect', os.path.join(current_app.config.get('APP_PREFIX', '/'), '_internal/downloads', path))
        response.cache_control.private = True
        #response.headers.add('Cache-Control', 'private')
        print(response.headers)
        return response
    else:
        raise ErrorResponse('access denied', status_code=403)
        
class PutTeamForm(FlaskForm):
    share_src = BooleanField("Share source code")
    share_jar = BooleanField("Share JAR file")
    
@bp.put("/<course_spec>/teams/<group_spec>/share")
@login_required
def team_put(course_spec, group_spec):
    course = get_course_or_fail(course_spec)
    group = get_group_or_fail(course, group_spec)

    if group.kind != 'team':
        raise ErrorResponse('not a team')
    form = PutTeamForm()
    
    if form.validate():
        if 'share' not in group.json_data:
            group.json_data['share'] = {}
        if form.share_jar.data != None:
            group.json_data['share']['share_jar'] = not not form.share_jar.data
        if form.share_src.data != None:
            group.json_data['share']['share_src'] = not not form.share_src.data
        # trigger update
        group.json_data['share'] = group.json_data['share'].copy()
        db.add(group)
        db.commit()
        return group.to_json()
    else:
        return {
            "status": "error",
            "code": 400,
            "message": "Invalid request form",
            "errors": form.errors,
        }, 400
    
class PutFileForm(FlaskForm):
    allow_read = SelectMultipleField(
        "Allow read",
        choices=['admin','self','group','course','all'],
    )
    allow_write = SelectMultipleField(
        "Allow write",
        choices=['admin','self','group','course','all'],
    )
  

@bp.put("/<course_spec>/teams/<group_spec>/files/<path>")
@login_required
def team_put_file_TODO(course_spec, group_spec, path):
    course = get_course_or_fail(course_spec)
    group = get_group_or_fail(course, group_spec)

    if not is_privileged(current_user, course):
        raise ErrorResponse('access denied', status_code=403)
    form = PutFileForm()
    print('team_put_file', form._fields, form.allow_read.data, form.allow_write.data)
    
    return {'status':'ok', 'allow_read':allow_read, 'allow_write':allow_write, 'json_data':group.json_data}
 
@bp.post("/<course_spec>/groups/")
# @bp.get('/<course_spec>/groups/form')
@bp.post("/<course_spec>/groups/<int:group_id>/groups/")
# @bp.get('/<course_spec>/groups/<int:group_id>/groups/form')
@login_required
def create_course_group(course_spec, group_id=None):
    course = get_course_or_fail(course_spec)

    if not is_privileged(current_user, course):
        raise ErrorResponse('access denied', status_code=403)

    parent = (
        db.execute(
            select(Group).filter_by(course=course, parent_id=group_id)
        ).scalar_one()
        if group_id
        else None
    )
    print(request, request.is_json, request.content_type)

    obj = Group(id=new_id(db, Group), course=course, external_id=None)
    form = CreateGroupForm()
    print(form._fields)
    if form.is_submitted():
        print(
            {
                "course": course.id,
                "parent": group_id,
                "name": form.name.data,
                "slug": form.slug.data,
                "kind": form.kind.data,
                "join_model": form.join_model.data,
            }
        )
        if not form.slug.data:
            form.slug.data = slugify(form.name.data)
        print(
            f'Received form: {"invalid" if not form.validate() else "valid"} {form.form_errors} {form.errors}'
        )
        print(
            request.form,
            obj,
            form.meta.csrf_class,
            form.meta.csrf_field_name,
            request.headers.get("X-CSRFToken"),
        )
        if form.validate():
            form.populate_obj(obj)
            logger.info("group object: %s", obj)
            if parent:
                obj.parent = parent
            db.add(obj)
            db.commit()
            return obj.to_json()
        else:
            return {
                "status": "error",
                "code": 400,
                "message": "Invalid request form",
                "errors": form.errors,
            }, 400
    return {
        "status": "error",
        "code": 400,
        "message": "Missing data",
        "errors": [],
    }, 400


@bp.get("/<course_spec>/groups/<group_spec>")
@login_required
def course_group(course_spec, group_spec):
    course = get_course_or_fail(course_spec)  # limited to members or privilege
    # limited to members or privilege
    group = get_group_or_fail(course, group_spec)

    return group.to_json()


@bp.get("/<course_spec>/groups/<group_spec>/users/")
@login_required
def course_group_users(course_spec, group_spec):
    result = []
    course = get_course_or_fail(course_spec)  # limited to members or privilege
    # limited to members or privilege
    group = get_group_or_fail(course, group_spec)

    if request.args.get("details", "false") == "true" and is_privileged(current_user, course):
        for m in group.memberships:
            if m.join_model != JoinModel.REMOVED:
                u = m.user.to_json()
                u["role"] = m.role
                result.append(u)
    else:
        result = [m.to_json()
                  for m in group.memberships if m.join_model != JoinModel.REMOVED]
    logger.info("group users: found %s records", len(result))
    return result


@bp.post("/<course_spec>/groups/<group_spec>/sync")
@login_required
def course_groups_sync_one(course_spec, group_spec):
    log = []
    course = get_course_or_fail(course_spec)
    group = get_group_or_fail(course, group_spec)
    token = request.form.get("token")

    if not is_privileged(current_user, course):
        raise ErrorResponse("Access denied", status_code=403)

    sync_time = now()
    lastlog = db.execute(select(AuditLog).order_by(
        AuditLog.id.desc())).scalar()

    if not group.join_source:
        raise ErrorResponse("no join source configured",
                            group, status_code=200)

    def gitlab_sync(project: str, students_only=True):
        gc: GitlabConnection = current_app.extensions["puffin_gitlab_connection"]
        (members, unmapped) = gc.project_members_incl_unmapped(db, project)
        logger.info("gitlab_sync(%s,%s)", project, members)
        # TODO: auto-remove members when they're removed from project
        for m in members:
            logger.info(
                "check_group_membership(%s,%s,%s)", course.slug, group.slug, m
            )
            if m != None:
                check_group_membership(
                    db,
                    course,
                    group,
                    m,
                    students_only=students_only,
                    join=JoinModel.AUTO,
                    sync_time=sync_time,
                )
        old_unmapped = group.json_data.get('unmapped', [])
        if old_unmapped != unmapped:
            group.json_data['unmapped'] = unmapped
            db.add(group)
            db.commit()
        if len(unmapped) > 0:
            raise ErrorResponse("user not found", unmapped)

    def canvas_sync(*args, **kwargs):
        pass

    simple_eval(
        group.join_source,
        functions={
            "gitlab": gitlab_sync,
            "canvas_sections": canvas_sync,
            "canvas_groups": canvas_sync,
        },
        names={"COURSE_ID": course.id},
    )
    LastSync.set_sync(db, group, sync_time)
    if lastlog != None:
        log = (
            db.execute(select(AuditLog).where(AuditLog.id > lastlog.id))
            .scalars()
            .all()
        )
    else:
        log = db.execute(select(AuditLog)).scalars().all()
    log = [l.to_json() for l in log if l.table_name in ["group", "membership"]]
    print("AFTERLOG:", log)
    return log


@bp.post("/<course_spec>/groups/sync")
@login_required
def course_groups_sync(course_spec):
    changes = []
    course = get_course_or_fail(course_spec)

    if not is_privileged(current_user, course):
        raise ErrorResponse("Access denied", status_code=403)

    sync_time = now()
    cc: CanvasConnection = current_app.extensions["puffin_canvas_connection"]
    sections = cc.get_sections_raw(course.external_id)
    for row in sections:
        logger.info("section: %s", row)
        update_groups_from_uib(
            db, row, course, changes=changes, sync_time=sync_time
        )
    return changes


@bp.get("/canvas")
@login_required
def canvas_courses():
    if not current_user.is_admin:
        raise ErrorResponse("Access denied", status_code=403)

    cc: CanvasConnection = current_app.extensions["puffin_canvas_connection"]
    print(cc)
    courses = cc.get_user_courses()

    courses = [cc.clean_course(c) for c in courses]
    ser = TaggedJSONSerializer()
    print(ser.dumps(courses))
    return [x for x in courses if x != None]


def normalize_project_path(path: str | int, course: Course):
    root = course.json_data.get("gitlab_path")
    if not root:
        raise ErrorResponse(
            "No gitlab path configured for course", status_code=404)
    if path.isdigit():
        return (None, None, int(path))

    path = path.strip("/")
    if not path.startswith(root):
        path = posixpath.join(root, path)

    ns, name = posixpath.split(path)
    return ns, name, None


@bp.get("/<course_spec>/gitlab/<path:path>")
@login_required
def get_gitlab_project(course_spec, path):
    if not current_user.is_admin:  # TODO?
        raise ErrorResponse("Access denied", status_code=403)

    user: User = current_user
    if current_user.is_admin and request.args.get("sudo"):
        user = db.get(User, int(request.args["sudo"]))
    course = get_course_or_fail(course_spec)

    gitlab_acc = user.account("gitlab")
    en = user.enrollment(course)
    if (
        gitlab_acc and gitlab_acc.external_id and en.role in [
            "admin", "ta", "teacher"]
    ) or user.is_admin:
        ns, name, id = normalize_project_path(path, course)
        proj = db.execute(
            select(Project).where(
                or_(
                    Project.gitlab_id == id,
                    and_(Project.namespace_slug == ns, Project.slug == name),
                )
            )
        ).scalar_one_or_none()
        if not proj:
            gc: GitlabConnection = current_app.extensions["puffin_gitlab_connection"]
            try:
                gl_proj = gc.gl.projects.get(
                    id if id else posixpath.join(ns, name))
                if not (
                    user.is_admin
                    or gl_proj.members_all.get(gitlab_acc.external_id).access_level
                    >= 30
                ):
                    raise ErrorResponse("Access denied", status_code=403)
            except GitlabOperationError as e:
                raise ErrorResponse("Not found", status_code=404)
            ns, name = posixpath.split(gl_proj.path_with_namespace)
            if not ns.startswith(course.json_data["gitlab_path"]):
                raise ErrorResponse(
                    "Project is outside course namespace", status_code=404
                )
            proj, created = get_or_define(
                db,
                Project,
                {"gitlab_id": gl_proj.id, "namespace_slug": ns, "slug": name},
                {
                    "name": gl_proj.name,
                    "description": gl_proj.description,
                    "course_id": course.id,
                    "owner_id": course.id,
                    "owner_kind": "course",
                },
            )
            db.commit()

        if proj.owner_id == course.id and proj.owner_kind == "course":
            return proj.to_json()
        else:
            raise ErrorResponse(
                "Project does not belong to this course", status_code=404
            )
    raise ErrorResponse("Access denied", status_code=403)


@bp.get("/<course_spec>/gitlab_group/<path:path>")
@login_required
def get_gitlab_group(course_spec, path):
    if not current_user.is_admin:  # TODO?
        raise ErrorResponse("Access denied", status_code=403)

    user: User = current_user
    if current_user.is_admin and request.args.get("sudo"):
        user = db.get(User, int(request.args["sudo"]))
    course = get_course_or_fail(course_spec)

    if type(path) == str:
        path = path.strip("/")

    gitlab_acc = user.account("gitlab")
    en = user.enrollment(course)
    if (
        gitlab_acc and gitlab_acc.external_id and en.role in [
            "admin", "ta", "teacher"]
    ) or user.is_admin:
        root = course.json_data.get("gitlab_path")
        if not root:
            raise ErrorResponse(
                "No gitlab path configured for course", status_code=404)
        gc: GitlabConnection = current_app.extensions["puffin_gitlab_connection"]
        try:
            group = (
                gc.gl.groups.get(path, with_projects=False).asdict()
                if path.startswith(root) or path.isdigit()
                else gc.gl.group.get(os.path.join(root, path), with_projects=False)
            )
            if (
                user.is_admin
                or group.members_all.get(gitlab_acc.external_id).access_level >= 30
            ):
                return group.asdict()
            else:
                raise ErrorResponse("Access denied", status_code=403)
        except GitlabOperationError as e:
            raise ErrorResponse("Not found", status_code=404)
