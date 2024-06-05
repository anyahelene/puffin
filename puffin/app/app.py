import base36
import yaml
import logging.config
import logging
import os
import sys
from puffin.db import database
from puffin.gitlab.users import GitlabConnection
from puffin.canvas.users import CanvasConnection
from puffin.util.errors import ErrorResponse
from puffin.app import view_projects
from os.path import dirname, abspath, join, isabs
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from werkzeug.security import safe_join
from requests import HTTPError
import gitlab
from flask_wtf import CSRFProtect, FlaskForm
from flask_login import login_required, current_user
from flask import Blueprint, Flask, flash, abort, g, has_request_context, url_for, render_template, request, send_file, send_from_directory, make_response, session, Response
import json
from datetime import datetime
from .proxy_fix import ProxyFix
minimal_init = 'alembic' in sys.argv[0]
    
if not minimal_init:
    print('\n\n\n\n------------------------------------------------------------------------\n\n')

APP_PATH = dirname(dirname(dirname(abspath(__file__))))


class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
            record.log_ref = g.log_ref
        else:
            record.url = ''
            record.remote_addr = ''
            record.log_ref = ''
        record.user = current_user.email if current_user else ''

        return super().format(record)


LOGGING = {'version': 1,
           'formatters': {
               'app': {
                   'format': '%(levelname)-7s: .%(module)s – %(message)s'
               },
               'simple': {
                   'format': '%(levelname)-7s: %(name)s – %(message)s'
               },
               'app_request': {
                   '()': RequestFormatter,
                   'format': '%(levelname)-7s %(asctime)s [%(log_ref)-6s] .%(module)s %(user)s %(url)s\n|    %(message)s\n'
               },
               'request': {
                   '()': RequestFormatter,
                   'format': '%(levelname)-7s %(asctime)s [%(log_ref)-6s] %(name)s %(user)s %(url)s\n|    %(message)s\n'
               }

           },
           'handlers': {
               'app_console': {
                   'class': 'logging.StreamHandler', 'level': 'DEBUG',
                   'formatter': 'app', 'stream': 'ext://sys.stderr'
               },
               'console': {
                   'class': 'logging.StreamHandler', 'level': 'INFO',
                   'formatter': 'simple', 'stream': 'ext://sys.stderr'
               },
               'app_file': {
                   'class': 'logging.FileHandler', 'level': 'DEBUG',
                   'formatter': 'app_request', 'filename': 'applog.log'
               },
               'file': {
                   'class': 'logging.FileHandler', 'level': 'INFO',
                   'formatter': 'request', 'filename': 'applog.log'
               }
           },
           'loggers': {
               'puffin': {'level': 'DEBUG', 'handlers': ['app_console', 'app_file'], 'propagate': False},
               'root': {'level': 'WARNING', 'handlers': ['console', 'file']}
           },
           }


root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
# _fileHandler = logging.FileHandler(join(APP_PATH, "applog.log"), 'w')
# _fileHandler.setLevel(logging.DEBUG)
# _streamHandler = logging.StreamHandler()
# root_logger.addHandler(_fileHandler)
# werkzeug_logger = logging.getLogger('werkzeug')
# werkzeug_logger.addHandler(_fileHandler)
# root_logger.addHandler(_streamHandler)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# werkzeug_logger.info('WERKZEUG LOGGER')
# Start app


def create_app(config_only = False):
    app = Flask('puffin')
    # app.secret_key = 'mY s3kritz'
    app.config.from_object('puffin.app.default_settings')
    app.config['APP_PATH'] = APP_PATH
    app.config['APP_WEBROOT'] = 'dist/webroot/'
    app.config['SITE_TITLE'] = 'Puffin'
    app.config.from_pyfile(join(APP_PATH, 'secrets'))

    if not isabs(app.config['APP_WEBROOT']):
        app.config['APP_WEBROOT'] = join(
            app.config['APP_PATH'], app.config['APP_WEBROOT'])
    app.template_folder = join(app.config['APP_WEBROOT'], 'templates')
    app.static_folder = app.config['APP_WEBROOT']

   
    bp = Blueprint('app', __name__,
                   url_prefix=app.config.get('APP_PREFIX', '/'))

    if minimal_init:
        return app, bp
 
    print(f'Starting {app.name}...')
    print(f'Prefix: {bp.url_prefix}')
    print(
        f'Paths: APP_PATH={app.config["APP_PATH"]} APP_WEBROOT={app.config["APP_PATH"]}')
    print(f'\troot={app.root_path}, instance={app.instance_path}')
    print(f'\tstatic={app.static_folder}, template={app.template_folder}')
    if app.config.get('TRUST_X_REAL_IP', False):
        app.wsgi_app = ProxyFix(app.wsgi_app)
    
    CSRFProtect(app)
    CanvasConnection(app)
    GitlabConnection(app)

    database.configure(app)
    from . import login, view_courses, view_users
    login.init(app, bp)
    view_users.init(app, bp)
    view_courses.init(app, bp)
    view_projects.init(app, bp)
    database.init(app)

    return app, bp


app, app_bp = create_app()

app.logger.info('APP LOGGER')


@app.context_processor
def extra_template_context():
    import posixpath
    def static_url_for(path: str):
        if '/' in path:
            return url_for('app.static', path=path)
        elif path.endswith('.css'):
            return url_for('app.static_css', path=path) 
        elif path.endswith('.js'):
            return url_for('app.static_js', path=path)
        else:
            return url_for('app.static_img', path=path)  
             
    def static(path: str, relativize=False):
        if relativize:
            return posixpath.relpath(static_url_for(path), start=posixpath.dirname(request.path)+'/')
        else:
            return static_url_for(path)

    return dict(static=static)


@app.shell_context_processor
def shell_setup():
    from sqlalchemy import select, alias, and_, or_, column, join, literal, literal_column, all_, any_, label, outerjoin
    import sqlalchemy as sa
    from puffin.db import model_tables, model_util, model_views, database
    from puffin.db.model_tables import User, Account, Course, Enrollment, Membership, Group, JoinModel, LogType, Id, Project
    from puffin.db.model_views import CourseUser, UserAccount, FullUser
    from importlib import reload
    db = database.db_session

    return locals().copy()


class HeartbeatForm(FlaskForm):

    @property
    def current_token(self):
        return self._fields['csrf_token'].current_token


@app_bp.get("/heartbeat")
def heartbeat():
    form = HeartbeatForm()
    return {"status": "ok", "csrf_token": form.current_token}

#################################################################################################

# Static content – this could also be served directly by the web server


@app_bp.route('favicon.ico')
def favicon_ico():
    return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app_bp.route('/favicon.png')
def favicon_png():
    return send_from_directory(app.static_folder, 'favicon.png', mimetype='image/png')


@app_bp.route('/index.html')
@app_bp.route('/')
def index_html():
    return render_template('index.html', title=app.config.get('SITE_TITLE', ''))
    # return send_from_directory(app.static_folder, 'index.html', mimetype='text/html')


@app_bp.route('/static/js/<path>')
def static_js(path: str):
    return send_from_directory(app.static_folder, request.path[1:])


@app_bp.route('/static/img/<path>')
def static_img(path: str):
    return send_from_directory(app.static_folder, request.path[1:])


@app_bp.route('/static/css/<path>')
def static_css(path: str):
    return send_from_directory(app.static_folder, request.path[1:])


#################################################################################################

@app.before_request
def before_request():
    #print(request.max_content_length, request.max_form_memory_size, request.max_forwards)
    request.max_form_memory_size = 65536
    #request.max_content_length = 65536
    #request.max_form_parts = 0

    print('********** BEFORE REQUEST', request.remote_addr, repr(request.base_url))
    g.log_ref = base36.dumps(
        int(datetime.timestamp(datetime.now())*1000) & 0x7fffffff)
    # print("request.args: ", request.args)
    print("current_user: ", current_user,
          'real user:', session.get('real_user'))
    # print("session: ", session)

@app.after_request
def after_request(response:Response):
    print('after requset', current_user)
    if current_user:
        response.headers.add('X-User', getattr(current_user, "email", None))
    return response
    
@app.teardown_appcontext
def shutdown_session(exception=None):
    print("shutdown_session")
    database.db_session.remove()


# @app.errorhandler(Exception)
# def handle_404(e:Exception):
#    print(request.url, request.path, request.full_path)
#    raise e

@app.errorhandler(ErrorResponse)
def handle_exception(e: ErrorResponse):
    """Return JSON for errors."""
    # start with the correct headers and status code from the error
    response = make_response()
    # replace the body with JSON
    response.data = json.dumps(e.to_dict())
    response.status_code = e.status_code
    response.content_type = "application/json"
    logger.error(f'{e.status_code} {e.to_dict()}')
    return response


@app.errorhandler(SQLAlchemyError)
def handle_exception(e: SQLAlchemyError):
    """Return JSON for errors."""
    error = {
        'status': 'error',
        'exception': type(e).__name__,
        'status_code': 400,
        'message': str(e),
        'args': []
    }
    if isinstance(e, NoResultFound):
        error['status_code'] = 404
        error['message'] = 'Not found'
    response = make_response()
    # replace the body with JSON
    response.data = json.dumps(error)
    response.status_code = error['status_code']
    response.content_type = "application/json"
    return response


@app.errorhandler(gitlab.exceptions.GitlabAuthenticationError)
def handle_gitlab_auth_error(e: gitlab.exceptions.GitlabAuthenticationError):
    error = {
        'status': 'error',
        'exception': type(e).__name__,
        'status_code': e.response_code,
        'message': f'GitLab authentication error: {e}',
        'args': []
    }
    response = make_response()
    # replace the body with JSON
    response.data = json.dumps(error)
    response.status_code = error['status_code']
    response.content_type = "application/json"
    return response


app.register_blueprint(app_bp)
