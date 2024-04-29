from datetime import datetime, timezone
import os
import posixpath
from flask import Blueprint, Flask, current_app, request, session
from flask_login import login_required, current_user
from gitlab import GitlabOperationError
from slugify import slugify
from puffin.db.model_tables import Account, AuditLog, JoinModel, LastSync, Project, User, Enrollment, Course, Group, Membership
from puffin.db.model_views import CourseUser, UserAccount
from puffin.db.model_util import check_group_membership, new_id, get_or_define, update_from_uib, update_groups_from_uib
from puffin.db.database import db_session as db
from sqlalchemy import alias, and_, or_, select, column
from simpleeval import simple_eval
from puffin.gitlab.users import GitlabConnection
from .errors import ErrorResponse
from puffin.util.util import *
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, validators, IntegerField, DateTimeField, ValidationError
from puffin.canvas.users import CanvasConnection
import logging
from flask.json.tag import TaggedJSONSerializer
logger = logging.getLogger(__name__)

bp = Blueprint('courses', __name__, url_prefix='/courses')



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
        return db.execute(select(Course).where(where, Enrollment.course_id ==
                                               Course.id, Enrollment.user == current_user)).scalar_one_or_none()


def get_course_or_fail(course_id_or_slug):
    course = get_course(course_id_or_slug)
    if course == None:
        raise ErrorResponse('No such accessible course',
                            course_id_or_slug, status_code=404)
    return course


@bp.get('/')
@login_required
def courses():
    if current_user.is_admin:
        courses = db.execute(select(Course).order_by(
            Course.name)).scalars().all()
    else:
        subq = select(Enrollment).where(Enrollment.course_id ==
                                        Course.id, Enrollment.user == current_user).exists()
        courses = db.execute(select(Course).where(
            subq).order_by(Course.name)).scalars().all()

    return [c.to_json() for c in courses]


@bp.get('/<course_spec>/')
@login_required
def course(course_spec):
    course = get_course(course_spec)
    if request.args.get('from_canvas') == 'true':
        cc: CanvasConnection = current_app.extensions['puffin_canvas_connection']
        if current_user.is_admin and course_spec.isdigit():
            return cc.clean_course(cc.get_course(course_spec))
        elif course:
            en = current_user.enrollment(course)
            if current_user.is_admin or en.role in ['admin', 'ta', 'teacher']:
                return cc.clean_course(cc.get_course(course.external_id))
        raise ErrorResponse('Access denied', status_code=403)
    else:
        return get_course_or_fail(course_spec).to_json()

class EditCourseForm(FlaskForm):
    name = StringField(
        'Course name', [validators.regexp(VALID_DISPLAY_NAME_REGEX)])
    slug = StringField('Slug', [validators.regexp(VALID_SLUG_REGEX)])
    canvas_id = IntegerField('Canvas id')
    gitlab_path = StringField('Gitlab path', [validators.regexp(VALID_SLUG_PATH_OR_EMPTY_REGEX)])
    gitlab_student_path = StringField('Gitlab student path', [validators.regexp(VALID_SLUG_PATH_OR_EMPTY_REGEX)])
    expiry_date = StringField('Expiry Date')

@bp.route('/<course_spec>/',methods=['PUT','POST'])
@login_required
def new_course(course_spec):
    course = get_course(course_spec)
    print(request.form)
    form = EditCourseForm()
    for (k,v) in form._fields.items():
        print(k,v,v.raw_data,v.data)
    changes = []
    if not form.is_submitted():
        raise ErrorResponse('Bad request', status_code=400)
    if not course:
        if not form.canvas_id.validate(form):
            raise ErrorResponse('Bad request', status_code=400)
        if current_user.is_admin:
            changes = changes + _create_course(int(course_spec))
            course = get_course(course_spec)

    if course:
        en = current_user.enrollment(course)
        if current_user.is_admin or en.role in ['admin', 'ta', 'teacher']:
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
            raise ErrorResponse('Access denied', status_code=403)
        if current_user.is_admin or en.role in ['admin', 'teacher']:
            newData = course.json_data.copy()
            for key in Course.info['data']:
                if getattr(form, key,None) and getattr(form,key).validate(form):
                    newData[key] = getattr(form, key).data
            if newData != course.json_data:
                course.json_data = newData
        print(db.dirty)
        for obj in db.dirty:
            changes.append((obj.__tablename__, obj.id))
        db.commit()
    return changes

@bp.post('/<course_spec>/sync')
@login_required
def course_sync(course_spec):
    course = get_course(course_spec)
    en = current_user.enrollment(course)
    if current_user.is_admin or en.role in ['admin', 'ta', 'teacher']:
        return _sync_course(get_course_or_fail(course_spec))
    else:
        raise ErrorResponse('Access denied', status_code=403)


def _create_course(course_id: int):
    cc: CanvasConnection = current_app.extensions['puffin_canvas_connection']

    canvas_course = cc.get_course(course_id)

    course, created = get_or_define(db, Course, {'slug': canvas_course['sis_course_id']},  {
        'name': canvas_course['name'],
        'external_id': canvas_course['id'],
        'expiry_date': canvas_course['end_at']
    })

    db.commit()
    return _sync_course(course)


def _sync_course(course: Course):
    result = course.to_json()
    canvas_accs = 0
    gitlab_accs = 0
    sync_time = now()
    result['changes'] = changes = []

    print('\n\n\n\n')
    logger.info('sync_course: %s, %s, %s', course, request.args, request.form)

    if request.args.get('sync_canvas') or request.form.get('sync_canvas'):
        cc: CanvasConnection = current_app.extensions['puffin_canvas_connection']
        userlist = cc.get_users(course.external_id)
        for row in userlist:
            acc = update_from_uib(
                db, row, course, changes=changes, sync_time=sync_time)
            if acc:
                canvas_accs += 1
        result['num_canvas_users'] = canvas_accs

    if request.args.get('sync_canvas_groups') or request.form.get('sync_canvas_groups'):
        course_groups_sync(course.external_id)
    if request.args.get('sync_gitlab') or request.form.get('sync_gitlab'):
        gc: GitlabConnection = current_app.extensions['puffin_gitlab_connection']
        for user in db.execute(select(User).where(Enrollment.user_id == User.id,
                                                  Enrollment.course_id == course.id)).scalars().all():
            acc = gc.find_gitlab_account(db, user, sync_time=sync_time)
            if acc:
                gitlab_accs += 1
        result['num_gitlab_users'] = gitlab_accs

    return changes


@bp.get('/<course_spec>/users/')
@login_required
def course_users(course_spec):
    course = get_course_or_fail(course_spec)

    result = []
    if request.args.get('accounts', False) or request.form.get('accounts', False):
        users = db.execute(select(CourseUser, UserAccount)
                           .where(CourseUser.course_id == course.id, CourseUser.id == UserAccount.id)
                           .order_by((CourseUser.role == 'student').desc(), CourseUser.lastname)).all()
        for u, a in users:
            u = u.to_json()
            u.update(a.to_json())
            u['_type'] = 'course_user,user_account'
            result.append(u)
    else:
        users = db.execute(select(CourseUser)
                           .where(CourseUser.course_id == course.id)
                           .order_by((CourseUser.role == 'student').desc(), CourseUser.lastname)).scalars().all()
        result = [u.to_json() for u in users]
    return result


def __user_details(user: User, course: Course):
    obj = user.to_json()
    obj['role'] = user.enrollment(course).role
    obj['groups'] = [{'group_id': m.group.id, 'group_slug': m.group.slug,
                      'role': m.role} for m in user.membership(course)]
    if not obj.get('locale') and current_app.config.get('DEFAULT_LOCALE'):
        obj['locale'] = current_app.config.get('DEFAULT_LOCALE')
    canvas_account = user.account('uib.no')
    if canvas_account:
        obj['canvas_id'] = canvas_account.external_id
    gitlab_account = user.account('git.app.uib.no')
    if gitlab_account:
        obj['gitlab_id'] = gitlab_account.external_id
        obj['gitlab_username'] = gitlab_account.username
    return obj


@bp.get('/<course_spec>/users/<user_id>')
@login_required
def course_user(course_spec, user_id):
    course = get_course_or_fail(course_spec)
    if user_id.isdigit():
        user_id = int(user_id)
    elif user_id == 'self':
        user_id = current_user.id
    if type(user_id) == int:
        u = db.execute(select(User).join(User.enrollments).filter_by(
            course=course, user_id=user_id).order_by(User.lastname)).scalar_one()
        return __user_details(u, course)
    else:
        raise ErrorResponse('Not found', status_code=404)


@bp.get('/<course_spec>/groups/')
@login_required
def get_course_groups(course_spec):
    course = get_course_or_fail(course_spec)
    groups = db.execute(select(Group).where(
        Group.course_id == course.id).order_by(Group.name)).scalars().all()

    return [g.to_json() for g in groups]


@bp.get('/<course_spec>/memberships/')
@login_required
def get_course_memberships(course_spec):
    course = get_course_or_fail(course_spec)
    members = db.execute(select(Membership).where(
        Membership.group_id == Group.id, Group.course_id == course.id)).scalars().all()
    return [m.to_json() for m in members]

# e.g.: {"name":"Microissant","slug":"microissant", "join_model":"AUTO", "join_source":"gitlab(33690, students_only=True)", "kind":"team"}


class CreateGroupForm(FlaskForm):
    name = StringField(
        'Group name', [validators.regexp(VALID_DISPLAY_NAME_REGEX)])
    kind = StringField(
        'Group kind', [validators.regexp(VALID_DISPLAY_NAME_REGEX)])
    join_model = SelectField('Joining',
                             choices=[(x.name, x.value.capitalize()) for x in JoinModel], default=JoinModel.RESTRICTED.name)
    join_source = StringField('Auto-join Source')
    slug = StringField('Slug', [validators.regexp(VALID_SLUG_REGEX)])
    submit = SubmitField('Submit')


@bp.post('/<course_spec>/groups/')
# @bp.get('/<course_spec>/groups/form')
@bp.post('/<course_spec>/groups/<int:group_id>/groups/')
# @bp.get('/<course_spec>/groups/<int:group_id>/groups/form')
@login_required
def create_course_group(course_spec, group_id=None):
    print(request.headers, session.items())

    course = get_course_or_fail(course_spec)
    parent = db.execute(select(Group).filter_by(
        course=course, parent_id=group_id)).scalar_one() if group_id else None
    print(request, request.is_json, request.content_type)

    obj = Group(id=new_id(db, Group), course=course, external_id=None)
    form = CreateGroupForm()
    print(form._fields)
    if form.is_submitted():
        print({'course': course.id, 'parent': group_id, 'name': form.name.data,
              'slug': form.slug.data, 'kind': form.kind.data, 'join_model': form.join_model.data})
        if not form.slug.data:
            form.slug.data = slugify(form.name.data)
        print(
            f'Received form: {"invalid" if not form.validate() else "valid"} {form.form_errors} {form.errors}')
        print(request.form, obj, form.meta.csrf_class,
              form.meta.csrf_field_name, request.headers.get('X-CSRFToken'))
        if form.validate():
            form.populate_obj(obj)
            logger.info('group object: %s', obj)
            if parent:
                obj.parent = parent
            db.add(obj)
            db.commit()
            return obj.to_json()
        else:
            return {'status': 'error', 'code': 400, 'message': 'Invalid request form', 'errors': form.errors}, 400
    return {'status': 'error', 'code': 400, 'message': 'Missing data', 'errors': []}, 400


@bp.get('/<course_spec>/groups/<group_spec>')
@login_required
def course_group(course_spec, group_spec):
    course = get_course_or_fail(course_spec)
    group_spec = intify(group_spec)
    if isinstance(group_spec, int):
        group = db.execute(select(Group).where(
            Group.course_id == course.id, Group.id == group_spec)).scalar_one_or_none()
    else:
        group = db.execute(select(Group).where(
            Group.course_id == course.id, Group.slug == group_spec)).scalar_one_or_none()
    if group == None:
        raise ErrorResponse('No such group', group_spec, status_code=404)
    return group.to_json()


@bp.get('/<course_spec>/groups/<group_spec>/users/')
@login_required
def course_group_users(course_spec, group_spec):
    result = []
    course = get_course_or_fail(course_spec)
    group_spec = intify(group_spec)
    if isinstance(group_spec, int):
        group = db.execute(select(Group).where(
            Group.course_id == course.id, Group.id == group_spec)).scalar_one_or_none()
    else:
        group = db.execute(select(Group).where(
            Group.course_id == course.id, Group.slug == group_spec)).scalar_one_or_none()
    if group == None:
        raise ErrorResponse('Not such group', group_spec, status_code=404)

    print(request.args.get('details', 'false'))
    if request.args.get('details', 'false') == 'true':
        result = []
        for m in group.memberships:
            u = m.user.to_json()
            u['role'] = m.role
            result.append(u)
        return result
    else:
        return [m.to_json() for m in group.memberships]


@bp.post('/<course_spec>/groups/<group_spec>/sync')
@login_required
def course_groups_sync_one(course_spec, group_spec):
    log = []
    course = get_course_or_fail(course_spec)
    token = request.form.get('token')
    group_spec = intify(group_spec)

    en = current_user.enrollment(course)
    print(course, group_spec, en)
    if current_user.is_admin or en.role in ['admin', 'ta', 'teacher']:
        sync_time = now()
        lastlog = db.execute(select(AuditLog).order_by(
            AuditLog.id.desc())).scalar()
        group = db.execute(select(Group).where(Group.course_id == course.id, or_(
            Group.id == group_spec, Group.slug == group_spec))).scalar_one()
        print('sync group:', group)
        if not group.join_source:
            raise ErrorResponse('no join source configured',
                                group, status_code=200)

        def gitlab_sync(project: str, students_only=True):
            gc: GitlabConnection = current_app.extensions['puffin_gitlab_connection']
            members = gc.project_members(db, project)
            logger.info('gitlab_sync(%s,%s)', project, members)
            # TODO: auto-remove members when they're removed from project
            for m in members:
                logger.info('check_group_membership(%s,%s,%s)',
                            course.slug, group.slug, m)
                if m != None:
                    check_group_membership(
                        db, course,  group, m, students_only=students_only, join=JoinModel.AUTO, sync_time=sync_time)

        def canvas_sync(*args, **kwargs):
            pass

        simple_eval(group.join_source, functions={
                    'gitlab': gitlab_sync,
                    'canvas_sections': canvas_sync,
                    'canvas_groups': canvas_sync
                    }, names={'COURSE_ID': course.id})
        LastSync.set_sync(db, group, sync_time)
        if lastlog != None:
            log = db.execute(select(AuditLog).where(
                AuditLog.id > lastlog.id)).scalars().all()
        else:
            log = db.execute(select(AuditLog)).scalars().all()
        log = [l.to_json()
               for l in log if l.table_name in ['group', 'membership']]
        print('AFTERLOG:', log)
        return log
    else:
        raise ErrorResponse('Access denied', status_code=403)


@bp.post('/<course_spec>/groups/sync')
@login_required
def course_groups_sync(course_spec):
    changes = []
    course = get_course_or_fail(course_spec)

    en = current_user.enrollment(course)
    if current_user.is_admin or en.role in ['admin', 'ta', 'teacher']:
        sync_time = now()
        cc: CanvasConnection = current_app.extensions['puffin_canvas_connection']
        sections = cc.get_sections_raw(course.external_id)
        for row in sections:
            logger.info('section: %s', row)
            update_groups_from_uib(
                db, row, course, changes=changes, sync_time=sync_time)
        return changes
    else:
        raise ErrorResponse('Access denied', status_code=403)


@bp.get('/canvas')
@login_required
def canvas_courses():
    cc: CanvasConnection = current_app.extensions['puffin_canvas_connection']
    print(cc)
    if current_user.is_admin:
        courses = cc.get_user_courses()

        courses = [cc.clean_course(c) for c in courses]
        ser = TaggedJSONSerializer()
        print(ser.dumps(courses))
        return [x for x in courses if x != None]
    else:
        raise ErrorResponse('Access denied', status_code=403)

def normalize_project_path(path:str|int, course:Course):
    root = course.json_data.get('gitlab_path')
    if not root:
        raise ErrorResponse(
            'No gitlab path configured for course', status_code=404)
    if path.isdigit():
        return (None,None,int(path))

    path = path.strip('/')
    if not path.startswith(root):
        path = posixpath.join(root, path)

    ns,name = posixpath.split(path)
    return ns, name, None

@bp.get('/<course_spec>/gitlab/<path:path>')
@login_required
def get_gitlab_project(course_spec, path):
    user : User = current_user
    if current_user.is_admin and request.args.get('sudo'):
        user = db.get(User, int(request.args['sudo']))
    course = get_course_or_fail(course_spec)

    gitlab_acc = user.account('gitlab')
    en = user.enrollment(course)
    if (gitlab_acc and gitlab_acc.external_id and en.role in ['admin', 'ta', 'teacher']) or user.is_admin: 
        ns, name, id = normalize_project_path(path, course)
        proj = db.execute(select(Project).where(or_(Project.gitlab_id == id,
                                             and_(Project.namespace_slug == ns,
                                                  Project.slug == name)))).scalar_one_or_none()
        if not proj:
            gc: GitlabConnection = current_app.extensions['puffin_gitlab_connection']
            try:
                gl_proj = gc.gl.projects.get(id if id else posixpath.join(ns,name))
                if not (user.is_admin or gl_proj.members_all.get(gitlab_acc.external_id).access_level >= 30):
                    raise ErrorResponse('Access denied', status_code=403)
            except GitlabOperationError as e:
                raise ErrorResponse('Not found', status_code=404)
            ns, name = posixpath.split(gl_proj.path_with_namespace)
            if not ns.startswith(course.json_data['gitlab_path']):  
                raise ErrorResponse('Project is outside course namespace', status_code=404)
            proj, created = get_or_define(db, Project, {
                'gitlab_id':gl_proj.id,
                'namespace_slug':ns,
                'slug':name},{
                'name':gl_proj.name,
                'description':gl_proj.description,
                'course_id':course.id,
                'owner_id':course.id,
                'owner_kind':'course',
            })
            db.commit()

        if proj.owner_id == course.id and proj.owner_kind == 'course':
            return proj.to_json()
        else:
            raise ErrorResponse("Project does not belong to this course", status_code=404)
    raise ErrorResponse('Access denied', status_code=403)
        
@bp.get('/<course_spec>/gitlab_group/<path:path>')
@login_required
def get_gitlab_group(course_spec, path):
    user : User = current_user
    if current_user.is_admin and request.args.get('sudo'):
        user = db.get(User, int(request.args['sudo']))
    course = get_course_or_fail(course_spec)

    if type(path) == str:
         path = path.strip('/')

    gitlab_acc = user.account('gitlab')
    en = user.enrollment(course)
    if (gitlab_acc and gitlab_acc.external_id and en.role in ['admin', 'ta', 'teacher']) or user.is_admin: 
        root = course.json_data.get('gitlab_path')
        if not root:
            raise ErrorResponse(
                'No gitlab path configured for course', status_code=404)
        gc: GitlabConnection = current_app.extensions['puffin_gitlab_connection']
        try:
            group = gc.gl.groups.get(path, with_projects=False).asdict() if path.startswith(
                root) or path.isdigit() else gc.gl.group.get(os.path.join(root, path), with_projects=False)
            if user.is_admin or group.members_all.get(gitlab_acc.external_id).access_level >= 30:
                return group.asdict()
            else:
                raise ErrorResponse('Access denied', status_code=403)
        except GitlabOperationError as e:
            raise ErrorResponse('Not found', status_code=404)
