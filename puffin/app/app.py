import json
from flask import Flask, abort, render_template, request, send_file, send_from_directory, make_response, session
from flask_login import login_required, current_user
from flask_wtf import CSRFProtect, FlaskForm
from werkzeug.security import safe_join
from puffin.db.database import init_db, db_session as db
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy import select
from .errors import ErrorResponse
from puffin import settings
import os
import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

APP_PATH = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

# Start app


def create_app():
    app = Flask(__name__,
                template_folder=os.path.join(APP_PATH, 'templates/'),
                static_folder=os.path.join(APP_PATH, 'dist/webroot/'))
    app.secret_key = 'mY s3kritz'
    app.config.from_object('puffin.app.default_settings')
    app.config.from_pyfile(os.path.join(APP_PATH, 'secrets'))
    CSRFProtect(app)
    app.config.update(

        SQLALCHEMY_DATABASE_URI=settings.DB_URL
    )
    from . import login, view_courses, view_users
    login.init(app)
    view_users.init(app)
    view_courses.init(app)

    return app


app = create_app()

init_db()
print(app.config)

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
    db.remove()


#@app.errorhandler(ErrorResponse)
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
