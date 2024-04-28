from datetime import datetime
import json
from flask import Blueprint, Flask, abort, g, has_request_context, render_template, request, send_file, send_from_directory, make_response, session
from flask_login import login_required, current_user
from flask_wtf import CSRFProtect, FlaskForm
import gitlab
from requests import HTTPError
from werkzeug.security import safe_join
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy import select
from os.path import dirname, abspath, join
from puffin.app import view_projects
from .errors import ErrorResponse
from puffin import settings
from puffin.canvas.users import CanvasConnection
from puffin.gitlab.users import GitlabConnection
from puffin.db import database
import os
import logging
import logging.config
import yaml
import base36

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


print(LOGGING)
logging.config.dictConfig(LOGGING)

root_logger = logging.getLogger()
# root_logger.setLevel(logging.DEBUG)
#_fileHandler = logging.FileHandler(join(APP_PATH, "applog.log"), 'w')
# _fileHandler.setLevel(logging.DEBUG)
#_streamHandler = logging.StreamHandler()
# root_logger.addHandler(_fileHandler)
#werkzeug_logger = logging.getLogger('werkzeug')
# werkzeug_logger.addHandler(_fileHandler)
# root_logger.addHandler(_streamHandler)
logger = logging.getLogger(__name__)
print('\n\n\n', __name__, root_logger.name, logger.name, '\n\n\n')
root_logger.warning('ROOT LOGGER')
logger.info('LOGGER')
#werkzeug_logger.info('WERKZEUG LOGGER')
# Start app


def create_app():
    app = Flask('puffin',
                template_folder=os.path.join(APP_PATH, 'dist/webroot/'),
                static_folder=os.path.join(APP_PATH, 'dist/webroot/'))
    #app.secret_key = 'mY s3kritz'
    app.config.from_object('puffin.app.default_settings')
    app.config.from_pyfile(os.path.join(APP_PATH, 'secrets'))
    app.config['APP_PATH'] = APP_PATH

    bp = Blueprint('app', __name__, url_prefix=app.config.get('APP_PREFIX', '/'))
    
    print(f'Starting {app.name}... prefix={bp.url_prefix} Paths: root={app.root_path}, instance={app.instance_path}, static={app.static_folder}, template={app.template_folder}')
    CSRFProtect(app)
    CanvasConnection(app)
    GitlabConnection(app)
    app.config.update(

        SQLALCHEMY_DATABASE_URI=settings.DB_URL
    )
    from . import login, view_courses, view_users
    login.init(app, bp)
    view_users.init(app, bp)
    view_courses.init(app, bp)
    view_projects.init(app, bp)
    database.init(app)

    return app, bp


app, app_bp = create_app()

app.logger.info('APP LOGGER')


@app.shell_context_processor
def shell_setup():
    from sqlalchemy import select, alias, and_, or_, column, join, literal, literal_column, all_, any_, label, outerjoin
    import sqlalchemy as sa
    from puffin.db import model_tables, model_util, model_views, database
    from puffin.db.model_tables import User, Account, Course, Enrollment, Membership, Group, JoinModel, LogType, Id
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

@app_bp.route('/')
@app_bp.route('/index.html')
def index_html():
    return render_template('index.html')
    #return send_from_directory(app.static_folder, 'index.html', mimetype='text/html')


@app_bp.route('/js/<path>')
@app_bp.route('/style/<path>')
@app_bp.route('/assets/<path>')
@app_bp.route('/css/<path>')
def static_js(path: str):
    return send_from_directory(app.static_folder, request.path[1:])


#################################################################################################

@app.before_request
def before_request():
    g.log_ref = base36.dumps(int(datetime.timestamp(datetime.now())*1000) & 0x7fffffff)
    print("request.args: ", request.args)
    print("current_user: ", current_user)
    print("session: ", session)

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

@app.errorhandler(gitlab.exceptions.GitlabAuthenticationError)
def handle_gitlab_auth_error(e:gitlab.exceptions.GitlabAuthenticationError):
    error = {
        'status':type(e).__name__,
        'code':e.response_code,
        'message':f'GitLab authentication error: {e}',
        'args':[]
    }
    response = make_response()
    # replace the body with JSON
    response.data = json.dumps(error)
    response.status_code = error['code']
    response.content_type = "application/json"
    return response


app.register_blueprint(app_bp)
