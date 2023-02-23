from flask import Blueprint, Flask, current_app, request, session
from flask_login import login_required, current_user
from slugify import slugify
from puffin.db import model
from puffin.db.model import AuditLog, JoinModel, User, Enrollment, Course, Group, Membership, VALID_DISPLAY_NAME_REGEX, VALID_SLUG_REGEX
from puffin.db.database import db_session as db
from sqlalchemy import or_, select
from simpleeval import simple_eval
from puffin.gitlab.users import GitlabConnection
from .errors import ErrorResponse
from puffin.util.util import *
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, validators, IntegerField, ValidationError
from puffin.canvas.users import CanvasConnection
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

bp = Blueprint('courses', __name__, url_prefix='/courses')


def init(app: Flask):
    app.register_blueprint(bp)


def get_course(course_id_or_slug):
    course_id_or_slug = intify(course_id_or_slug)
    if isinstance(course_id_or_slug, int):
        where = Course.id == course_id_or_slug
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


@bp.route('/', methods=['GET'])
@login_required
def courses():
    subq = select(Enrollment).where(Enrollment.course_id ==
                                    Course.id, Enrollment.user == current_user).exists()
    courses = db.execute(select(Course).where(
        subq).order_by(Course.name)).scalars().all()

    return [c.to_json() for c in courses]


@bp.route('/<course_spec>/', methods=['GET'])
@login_required
def course(course_spec):
    return get_course_or_fail(course_spec).to_json()


@bp.post('/<course_spec>/sync')
def course_sync(course_spec):
    log = []
    course = get_course_or_fail(course_spec)
    token = request.form.get('token')

    en = current_user.enrollment(course)
    if current_user.is_admin or en.role in ['admin', 'ta', 'teacher']:
        # TODO: track changes in a better way
        lastlog = db.execute(select(AuditLog).order_by(
            AuditLog.id.desc())).scalar()
        print('lastlog:', lastlog.to_json())

        if request.args.get('sync_canvas'):
            cc = CanvasConnection(
                current_app.config['CANVAS_BASE_URL'], token or current_app.config['CANVAS_SECRET_TOKEN'])
            userlist = cc.get_users(course.id)
            for row in userlist:
                model.update_from_uib(db, row, course)

        if request.args.get('sync_gitlab'):        
            gc = GitlabConnection(
                current_app.config['GITLAB_BASE_URL'], token or current_app.config['GITLAB_SECRET_TOKEN'])
            for user in db.execute(select(User).where(Enrollment.user_id == User.id,
                Enrollment.course_id == course.id)).scalars().all():
                gc.find_gitlab_account(user)

        if lastlog != None:
            log = db.execute(select(AuditLog).where(
                AuditLog.id > lastlog.id)).scalars().all()
        else:
            log = db.execute(select(AuditLog)).scalars().all()
        log = [l.to_json() for l in log if l.table_name in [
            'user', 'account', 'enrollment']]
        print('AFTERLOG:', log)
        return log
    else:
        raise ErrorResponse('Access denied', status_code=403)


@bp.route('/<course_spec>/users/', methods=['GET'])
@login_required
def course_users(course_spec):
    course = get_course_or_fail(course_spec)
    users = db.execute(select(User).join(User.enrollments).filter_by(
        course=course).order_by(User.lastname)).scalars().all()
    if request.args.get('details', 'false') == 'true':
        return [__user_details(u, course) for u in users]
    else:
        return [u.id for u in users]


def __user_details(user: User, course: Course):
    obj = user.to_json()
    obj['role'] = user.enrollment(course).role
    obj['groups'] = [{'group_id': m.group.id, 'group_slug': m.group.slug,
                      'role': m.role} for m in user.membership(course)]
    canvas_account = user.account('uib.no')
    if canvas_account:
        obj['canvas_id'] = canvas_account.ref_id
    gitlab_account = user.account('git.app.uib.no')
    if gitlab_account:
        obj['gitlab_id'] = gitlab_account.ref_id
        obj['gitlab_username'] = gitlab_account.username
    return obj


@bp.route('/<course_spec>/users/<int:user_id>', methods=['GET'])
@login_required
def course_user(course_spec, user_id):
    course = get_course_or_fail(course_spec)

    u = db.execute(select(User).join(User.enrollments).filter_by(
        course=course, user_id=user_id).order_by(User.lastname)).scalar_one()
    return __user_details(u, course)


@bp.route('/<course_spec>/groups/', methods=['GET'])
@login_required
def get_course_groups(course_spec):
    course = get_course_or_fail(course_spec)

    return [g.to_json() for g in db.execute(select(Group).where(Group.course_id == course.id).order_by(Group.name)).scalars().all()]



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

    obj = Group(course=course, external_id='')
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
            if parent:
                obj.parent = parent
            db.add(obj)
            db.commit()
            return obj.to_json()
        else:
            return {'status': 'error', 'code': 400, 'message': 'Invalid request form', 'errors': form.errors}, 400
    return {'status': 'error', 'code': 400, 'message': 'Missing data', 'errors': []}, 400


@bp.route('/<course_spec>/groups/<group_spec>', methods=['GET'])
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


@bp.route('/<course_spec>/groups/<group_spec>/users/', methods=['GET'])
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


@bp.route('/<course_spec>/groups/<group_spec>/sync', methods=['POST'])
@login_required
def course_groups_sync_one(course_spec, group_spec):
    log = []
    course = get_course_or_fail(course_spec)
    token = request.form.get('token')
    group_spec = intify(group_spec)

    en = current_user.enrollment(course)
    print(course, group_spec, en)
    if current_user.is_admin or en.role in ['admin', 'ta', 'teacher']:
        lastlog = db.execute(select(AuditLog).order_by(
            AuditLog.id.desc())).scalar()
        group = db.execute(select(Group).where(Group.course_id == course.id, or_(
            Group.id == group_spec, Group.slug == group_spec))).scalar_one()
        print('sync group:', group)
        if not group.join_source:
            raise ErrorResponse('no join source configured',
                                group, status_code=200)

        def gitlab_sync(project: str, students_only=True):
            gc = GitlabConnection(
                current_app.config['GITLAB_BASE_URL'], token or current_app.config['GITLAB_SECRET_TOKEN'])
            members = gc.project_members(project)
            # TODO: auto-remove members when they're removed from project
            for m in members:
                logger.info('check_group_membership(%s,%s,%s)', course.slug, group.slug, m)
                if m != None:
                    model.check_group_membership(
                        db, course,  group, m, students_only=students_only, join=JoinModel.AUTO)

        def canvas_sync(*args, **kwargs):
            pass

        simple_eval(group.join_source, functions={
                    'gitlab': gitlab_sync, 
                    'canvas_sections': canvas_sync, 
                    'canvas_groups': canvas_sync
                    }, names={'COURSE_ID': course.id})

        if lastlog != None:
            log = db.execute(select(AuditLog).where(
                AuditLog.id > lastlog.id)).scalars().all()
        else:
            log = db.execute(select(AuditLog)).scalars().all()
        log = [l.to_json()
               for l in log if l.table_name in ['subgroup', 'membership']]
        print('AFTERLOG:', log)
        return log
    else:
        raise ErrorResponse('Access denied', status_code=403)


@bp.post('/<course_spec>/groups/sync')
def course_groups_sync(course_spec):
    log = []
    course = get_course_or_fail(course_spec)
    print()
    token = request.form.get('token')

    en = current_user.enrollment(course)
    if current_user.is_admin or en.role in ['admin', 'ta', 'teacher']:
        lastlog = db.execute(select(AuditLog).order_by(
            AuditLog.id.desc())).scalar()
        print('lastlog:', lastlog.to_json())
        cc = CanvasConnection(
            current_app.config['CANVAS_BASE_URL'], token or current_app.config['CANVAS_SECRET_TOKEN'])
        sections = cc.get_sections_raw(course.id)
        for row in sections:
            model.update_groups_from_uib(db, row, course)
        if lastlog != None:
            log = db.execute(select(AuditLog).where(
                AuditLog.id > lastlog.id)).scalars().all()
        else:
            log = db.execute(select(AuditLog)).scalars().all()
        log = [l.to_json()
               for l in log if l.table_name in ['subgroup', 'membership']]
        print('AFTERLOG:', log)
        return log
    else:
        raise ErrorResponse('Access denied', status_code=403)
