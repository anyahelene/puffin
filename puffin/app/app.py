import json
from flask import Flask, abort, render_template, request, send_from_directory, make_response, session
from flask_login import login_required, current_user
from flask_wtf import CSRFProtect, FlaskForm
from slugify import slugify
import logging
from puffin.db.model import CreateGroupForm, Course, Account, User, Enrollment, Group
from puffin.db.database import init_db, db_session as db
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy import select
from .errors import ErrorResponse
from puffin import settings
import os

APP_PATH = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

# Start app


def create_app():
    app = Flask(__name__,
                template_folder=os.path.join(APP_PATH, 'templates/'),
                static_folder=os.path.join(APP_PATH, 'static/'))
    app.secret_key = 'mY s3kritz'
    CSRFProtect(app)
    app.config.update(
        SESSION_COOKIE_NAME='pf_session',
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SQLALCHEMY_DATABASE_URI=settings.DB_URL
    )
    from . import login
    login.init(app)

    return app


app = create_app()

init_db()
print(app.config)


def get_course_or_fail(course_id_or_slug):
    if isinstance(course_id_or_slug, str) and course_id_or_slug.isnumeric():
        course_id_or_slug = int(course_id_or_slug)
    if isinstance(course_id_or_slug, int):
        where = Course.id == course_id_or_slug
    elif isinstance(course_id_or_slug, str):
        where = Course.slug == course_id_or_slug
    else:
        raise ErrorResponse('Bad request parameter', course_id_or_slug)
    if current_user.is_admin:
        course = db.execute(select(Course).where(where)).scalar_one_or_none()
    else:
        course = db.execute(select(Course).where(where, Enrollment.course_id ==
                            Course.id, Enrollment.user == current_user)).scalar_one_or_none()
    if course == None:
        raise ErrorResponse('No such accessible course',
                            course_id_or_slug, status_code=404)
    return course


@app.route('/users/', methods=['GET'])
@login_required
def users():
    # with Session() as db:
    if current_user.is_admin:
        users = db.execute(select(User).order_by(
            User.lastname)).scalars().all()
        return [u.to_json() for u in users]
    else:
        return [current_user.to_json()]


@app.route('/users/<int:user_spec>', methods=['GET'])
@login_required
def user(user_spec: int):
    user = db.get(User, int(user_spec))
    if current_user.is_admin:
        if user:
            return user.to_json()
        else:
            raise ErrorResponse('User not found', status_code=404)
    elif user and user.id == current_user.id:
        return current_user.to_json()
    else:
        raise ErrorResponse('Forbidden', status_code=403)


@app.route('/courses/', methods=['GET'])
@login_required
def courses():
    subq = select(Enrollment).where(Enrollment.course_id ==
                                    Course.id, Enrollment.user == current_user).exists()
    courses = db.execute(select(Course).where(
        subq).order_by(Course.name)).scalars().all()

    return [c.to_json() for c in courses]


@app.route('/courses/<course_spec>', methods=['GET'])
@login_required
def course(course_spec):
    return get_course_or_fail(course_spec).to_json()


@app.route('/courses/<course_spec>/users/', methods=['GET'])
@login_required
def course_users(course_spec):
    result = []
    course = get_course_or_fail(course_spec)

    for u in db.execute(select(User).join(User.enrollments).filter_by(course=course).order_by(User.lastname)).scalars().all():
        result.append(__user_details(u, course))
    return result


def __user_details(user:User, course:Course):
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


@app.route('/courses/<course_spec>/users/<int:user_id>', methods=['GET'])
@login_required
def course_user(course_spec, user_id):
    course = get_course_or_fail(course_spec)

    u = db.execute(select(User).join(User.enrollments).filter_by(
        course=course, user_id=user_id).order_by(User.lastname)).scalar_one()
    return __user_details(u, course)


@app.route('/courses/<course_spec>/groups/', methods=['GET'])
@login_required
def get_course_groups(course_spec):
    course = get_course_or_fail(course_spec)

    return [g.to_json() for g in db.execute(select(Group).filter_by(course=course).group_by(Group.kind, Group.parent_id).order_by(Group.name)).scalars().all()]


@app.post('/courses/<course_spec>/groups/')
@app.get('/courses/<course_spec>/groups/form')
@app.post('/courses/<course_spec>/groups/<int:group_id>/groups/')
@app.get('/courses/<course_spec>/groups/<int:group_id>/groups/form')
@login_required
def create_course_group(course_spec, group_id=None):
    # TODO: check that user has access
    print(request.headers, session.items())
    db = db

    # with Session() as db:
    course = get_course_or_fail(course_spec)
    parent = db.execute(select(Group).filter_by(
        course=course, parent_id=group_id)).scalar_one() if group_id else None
    print(request, request.is_json, request.content_type)
    # if request.is_json:
    #   json = request.get_json()
    #    print("json data:", json)
    #    form = CreateGroupForm.from_json(json)
    #form.csrf_token.data = json['csrf_token']
    #    print(form.csrf_token.data, json.get('csrf_token'), form.meta.csrf_secret)
    # else:
    obj = Group(course=course, external_id='')
    form = CreateGroupForm()
    print(form._fields)
    if form.is_submitted():
        if not form.slug.data:
            form.slug.data = slugify(form.name.data)
        print(
            f'Received form: {"invalid" if not form.validate() else "valid"} {form.form_errors} {form.errors}')
        print(request.form, obj, form.meta.csrf_class,
              form.meta.csrf_field_name, request.headers.get('X-CSRFToken'))
        print({'course': course.id, 'parent': group_id, 'name': form.name.data,
              'slug': form.slug.data, 'kind': form.kind.data, 'join_model': form.join_model.data})
        if form.validate():
            form.populate_obj(obj)
            if parent:
                obj.parent = parent
            db.add(obj)
            db.commit()
            return obj.to_json()
        else:
            return {'status': 'error', 'code': 400, 'message': 'Invalid request form', 'errors': form.errors}, 400
    return render_template('./login.html', form=form)


class HeartbeatForm(FlaskForm):

    @property
    def current_token(self):
        return self._fields['csrf_token'].current_token


@app.get("/heartbeat")
def heartbeat():
    form = HeartbeatForm()
    return {"status": "ok", "csrf_token": form.current_token}

#################################################################################################

# Static content – this could also be served directly by the web server


@app.route('/favicon.ico')
def favicon_ico():
    return send_from_directory(app.root_path, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/favicon.png')
def favicon_png():
    return send_from_directory(app.root_path, 'favicon.png', mimetype='image/png')


@app.route('/')
@app.route('/index.html')
def index_html():
    return send_from_directory(app.root_path, 'index.html', mimetype='text/html')

#################################################################################################


@app.teardown_appcontext
def shutdown_session(exception=None):
    print("shutdown_session")
    db.remove()


@app.errorhandler(ErrorResponse)
def handle_exception(e: ErrorResponse):
    """Return JSON for errors."""
    # start with the correct headers and status code from the error
    response = make_response()
    # replace the body with JSON
    response.data = json.dumps(e.to_dict())
    response.status_code = e.status_code
    response.content_type = "application/json"
    return response


@app.errorhandler(SQLAlchemyError)
def handle_exception(e: SQLAlchemyError):
    """Return JSON for errors."""
    error = {
        'status': type(e).__name__,
        'code': 400,
        'message': str(e),
        'args': []
    }
    if isinstance(e, NoResultFound):
        error['code'] = 404
        error['message'] = 'Not found'
    response = make_response()
    # replace the body with JSON
    response.data = json.dumps(error)
    response.status_code = error['code']
    response.content_type = "application/json"
    return response
