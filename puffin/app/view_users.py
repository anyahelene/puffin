from flask import Blueprint, Flask
from flask_login import login_required, current_user
from puffin.db.model import Account, Enrollment, User
from puffin.db.database import db_session as db
from sqlalchemy import select,and_
from .errors import ErrorResponse
from puffin.util.util import *
import logging
logger = logging.getLogger(__name__)

bp = Blueprint('users', __name__, url_prefix='/users')
def init(app:Flask):
    app.register_blueprint(bp)

def get_user(user_id_or_name):
    user_id_or_name = intify(user_id_or_name)
    if current_user.is_admin and isinstance(user_id_or_name, int):
        return db.get(user_id_or_name)
    elif isinstance(user_id_or_name, int):
        where = User.id == user_id_or_name
    elif isinstance(user_id_or_name, str):
        where = and_(User.id == Account.user_id, Account.username == user_id_or_name)
    if current_user.is_admin:
        return db.execute(select(User).where(where)).scalar_one_or_none()
    else:
        return db.execute(select(User).where(where, User.id == current_user.id)).scalar_one_or_none()
def get_user_or_fail(user_id_or_name):
    user = get_user(user_id_or_name)
    if user == None:
        raise ErrorResponse('No such accessible user',
                            user_id_or_name, status_code=404)
    return user

@bp.route('/', methods=['GET'])
@login_required
def users():
    # with Session() as db:
    if current_user.is_admin:
        users = db.execute(select(User).order_by(
            User.lastname)).scalars().all()
        return [u.to_json() for u in users]
    else:
        return [current_user.to_json()]


@bp.route('/<user_spec>/', methods=['GET'])
@login_required
def user(user_spec):
    user = get_user_or_fail(user_spec)
    return user.to_json()

@bp.route('/<user_spec>/courses', methods=['GET'])
@login_required
def user_courses(user_spec):
    user = get_user_or_fail(user_spec)
    return [en.course.to_json() for en in user.enrollments]


@bp.route('/<user_spec>/groups', methods=['GET'])
@login_required
def user_groups(user_spec):
    user = get_user_or_fail(user_spec)
    return [en.group.to_json() for en in user.memberships]
