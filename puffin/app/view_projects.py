from flask import Blueprint, Flask, current_app, request
from flask_login import login_required, current_user
from gitlab import GitlabGetError
from puffin.db.model_tables import Account, Enrollment, User
from puffin.db.database import db_session as db
from sqlalchemy import select,and_

from puffin.gitlab.users import GitlabConnection
from puffin.util.errors import ErrorResponse
from puffin.util.util import *
import logging
logger = logging.getLogger(__name__)

bp = Blueprint('projects', __name__, url_prefix='/projects')
def init(app:Flask, parent: Blueprint):
    (parent or app).register_blueprint(bp)

@bp.get('/gitlab/')
@login_required
def search_gitlab_project() -> Any:
    gc : GitlabConnection = current_app.extensions['puffin_gitlab_connection']
    if not current_user.is_admin:
         return ('Access denied', 403)
    try:
        search = request.args.get('search')
        if search:
            return gc.gl.search('projects', search, list_all=True)
        else:
            raise ErrorResponse('Missing parameter', 401)
    except GitlabGetError as e:
            return {'status':'error', 'message':e.error_message}


@bp.get('/gitlab/<path:path>')
@login_required
def get_gitlab_project(path) -> Any:
    user : User = current_user  # type: ignore
    gitlab_acc = user.account('gitlab')
    external_id = gitlab_acc and gitlab_acc.external_id or 0

    if type(path) == str:
        path = path.strip('/')

    if (gitlab_acc and gitlab_acc.external_id) or user.is_admin:   
        gc : GitlabConnection = current_app.extensions['puffin_gitlab_connection']
        try:
            project = gc.gl.projects.get(path)
            if user.is_admin or project.members_all.get(external_id).access_level >= 30:
                print(project.asdict())
                return project.asdict()
            else:
                raise ErrorResponse('Access denied', status_code=403)
        except GitlabGetError as e:
            raise ErrorResponse('Not found', status_code=404)

@bp.get('/gitlab_group/<path:path>')
@login_required
def get_gitlab_group(path) -> Any:
    user : User = current_user  # type: ignore
    gitlab_acc = user.account('gitlab')
    external_id = gitlab_acc and gitlab_acc.external_id or 0
    if type(path) == str:
        if path.startswith(current_app.config.get('GITLAB_BASE_URL','')):
            path = path[len(current_app.config.get('GITLAB_BASE_URL','')):]
        path = path.strip('/')
    if user.is_admin or external_id:   
        gc : GitlabConnection = current_app.extensions['puffin_gitlab_connection']
        try:
            group = gc.gl.groups.get(path, with_projects=False)
            if user.is_admin or group.members_all.get(external_id).access_level >= 30:
                return group.asdict()
            else:
                raise ErrorResponse('Access denied', status_code=403)
        except GitlabGetError as e:
            logger.error(e)
            raise ErrorResponse('Not found', status_code=404)
