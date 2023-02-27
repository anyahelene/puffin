import json
from flask import Flask, abort, render_template, request, send_file, send_from_directory, make_response, session
from flask_login import login_required, current_user
from flask_wtf import CSRFProtect, FlaskForm
from werkzeug.security import safe_join
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy import select
from .errors import ErrorResponse
from puffin import settings
from puffin.canvas.users import CanvasConnection
from puffin.gitlab.users import GitlabConnection
from puffin.db import database
import os
import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

APP_PATH = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

# Start app


def create_app():
    app = Flask('puffin',
                template_folder=os.path.join(APP_PATH, 'templates/'),
                static_folder=os.path.join(APP_PATH, 'dist/webroot/'))
    app.secret_key = 'mY s3kritz'
    app.config.from_object('puffin.app.default_settings')
    app.config.from_pyfile(os.path.join(APP_PATH, 'secrets'))
    print(f'Starting {app.name}... Paths: root={app.root_path}, instance={app.instance_path}, static={app.static_folder}, template={app.template_folder}')
    CSRFProtect(app)
    CanvasConnection(app)
    GitlabConnection(app)
    app.config.update(

        SQLALCHEMY_DATABASE_URI=settings.DB_URL
    )
    from . import login, view_courses, view_users
    login.init(app)
    view_users.init(app)
    view_courses.init(app)
    database.init(app)

    return app


app = create_app()

print(app.config)

@app.shell_context_processor
def shell_setup():
    from sqlalchemy import select, alias, and_, or_, column, join, literal, literal_column, all_, any_, label, outerjoin
    from puffin.db import model, database
    from puffin.db.model import User, Account, Course, Enrollment, Membership, Group, Provider, JoinModel, LogType, Id, CourseUser, UserAccount
    from puffin.db.views import view
    from importlib import reload
    db = database.db_session

    return locals().copy()

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
    return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/favicon.png')
def favicon_png():
    return send_from_directory(app.static_folder, 'favicon.png', mimetype='image/png')


@app.route('/')
@app.route('/index.html')
def index_html():
    return send_from_directory(app.static_folder, 'index.html', mimetype='text/html')

@app.route('/js/<path>')
@app.route('/style/<path>')
@app.route('/assets/<path>')
@app.route('/css/<path>')
def static_js(path:str):
    return send_from_directory(app.static_folder, request.path[1:])

#################################################################################################


@app.teardown_appcontext
def shutdown_session(exception=None):
    print("shutdown_session")
    database.db_session.remove()


@app.errorhandler(ErrorResponse)
def handle_exception(e: ErrorResponse):
    """Return JSON for errors."""
    # start with the correct headers and status code from the error
    response = make_response()
    # replace the body with JSON
    response.data = json.dumps(e.to_dict())
    response.status_code = e.status_code
    response.content_type = "application/json"
    logger.error(f'{e.status_code} {response.data}')
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
