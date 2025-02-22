from datetime import datetime
from http import HTTPStatus
from typing import Any
from flask import Blueprint, Config, Flask, abort, current_app, flash, g, jsonify, make_response, redirect, render_template, request, session, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_wtf import CSRFProtect, FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from puffin.util.errors import ErrorResponse
from puffin.db.model_tables import Course, Enrollment, Group, JoinModel, Membership, User,Account
from puffin.db.database import db_session
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash
from authlib.integrations.flask_client import OAuth
import logging
from puffin.db.model_util import define_gitlab_account
from puffin.gitlab.users import GitlabConnection

from puffin.util.util import now

_logger = logging.getLogger(__name__)

class LoginForm(FlaskForm):
    username = StringField('Username')
    password = PasswordField('Password')
    submit = SubmitField('Submit')

bp = Blueprint('login', __name__, url_prefix='/login')
login_manager : Any = LoginManager()
oauth = OAuth()
app_config : Config
def init(app:Flask, parent:Blueprint):
    (parent or app).register_blueprint(bp)
    login_manager.init_app(app)
    login_manager.id_attribute = 'get_id'
    login_manager.login_view = "app.login.login"
    oauth.init_app(app)
    global gitlab_oauth, app_config
    app_config = app.config
    gitlab_oauth = oauth.register('gitlab',
                                  server_metadata_url=app.config['GITLAB_BASE_URL'] + '.well-known/openid-configuration',
                                  client_kwargs={'scope':'openid profile email'})
    #_logger.debug("/login init: %s\n\t%s", oauth._clients, gitlab_oauth.__dict__)


@bp.route('/', methods=['GET', 'POST'])
def login():
    allow_gitlab = gitlab_oauth != None
    next_page = request.args.get('next_page')
    _logger.info("/login[%s]: next_page=%s", g.log_ref, next_page)
    if app_config.get('LOGIN_ALLOW_PASSWORD', True):
        form = LoginForm()
        if form.is_submitted():
            _logger.info('/login/login[%s]: Received form: %s form_errors=%s errors=%s form=%s', g.log_ref, "invalid" if not form.validate() else "valid", form.form_errors, form.errors, request.form)
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data
            u = db_session.execute(select(User).where(User.email==username)).scalar_one_or_none()

            _logger.info('/login/login[%s]: Found user: %s', g.log_ref, u)
            if u and u.password and password and check_password_hash(u.password, password):
                if not u.is_expired:
                    _logger.info('/login/login[%s]: Logged in successfully, redirecting to %s', g.log_ref, url_for('app.index_html'))
                    #session.clear()
                    login_user(u)
                    session['real_user'] = u.id
                    session['login_ref'] = g.log_ref
                    flash('Logged in successfully')
                    return redirect(url_for('app.index_html'))
                else:
                    error = "Account expired – contact administrators"
            else:
                error = "Wrong username or password"

            _logger.error("/login/login error: %s", error)
            flash(error + f'(ref: {g.log_ref})')

        return render_template('./login.html', form=form, title=f"Login – {app_config.get('SITE_TITLE', '')}", allow_password=True, allow_gitlab=allow_gitlab, next_page=next_page)
    else:
        return render_template('./login.html', title=f"Login – {app_config.get('SITE_TITLE', '')}", allow_password=False, allow_gitlab=allow_gitlab, next_page=next_page)



@bp.route('/gitlab')
def login_gitlab():
    session['next_page'] = request.args.get('next_page')
    redirect_uri = url_for('app.login.authorize_gitlab', _external=True)
    _logger.info("/login/gitlab[%s]: redirect_uri=%s, next_page=%s", g.log_ref, redirect_uri, request.args.get('next_page'))
    r= oauth.gitlab.authorize_redirect(redirect_uri) # type: ignore
    #for k,v in gitlab_oauth.__dict__.items():
    #    print(k, v)
    return r

@bp.route('/logout')
def logout_gitlab():
    print(session)
    logout_user()
    print(session)
    
    return "logged out"
    #oauth.gitlab.revoke_token('https://git.app.uib.no/oauth/revoke', session['log_ref'])


@bp.route('/sudone')
@login_required
def sudone():
    _logger.info("/login/sudone[%s]: real=%s, id=%s",  g.log_ref, repr(session.get('real_user')), repr(current_user.id))
    real_user = session.get('real_user')

    if real_user != None and real_user != current_user.id:
        u = db_session.execute(select(User).where(User.id==real_user)).scalar_one_or_none()
        _logger.info("/login/sudone[%s]: returning to user %s",  g.log_ref, u)
        if u:
            login_user(u)
            flash(f"Returned to real user {u.email}")
        else:
            flash(f"Didn't find real user", category="error")
    return redirect(url_for('app.index_html'))
    
@bp.route('/sudo/<username>')
@login_required
def sudo(username: str = ""):
    _logger.info("/login/sudo[%s]: real=%d, id=%s",  g.log_ref, repr(session.get('real_user')), repr(current_user.id))

    if not current_user.is_admin:
        abort(403)
    else:
        u = db_session.execute(select(User).where(User.email==username)).scalar_one_or_none()
        if u:
            login_user(u, force=True)
            _logger.info("/login/sudo[%s]: switched to %s", g.log_ref, u.email)
            flash(f"Switched to user {u.email}")
        else:
            flash(f"Didn't find user", category="error")
        return redirect(url_for('app.index_html'))   

def define_gitlab_from_gitlab_userinfo(user, external_id, userinfo, profile):
    _logger.warn('OpenID Connect login – defining GitLab account %s:\n\tuser: %s\n\tuserinfo: %s\n\tprofile: %s',
                 external_id, user, userinfo, profile)
    acc = define_gitlab_account(db_session, user, profile.username, external_id, profile.name)
    acc.last_login = now()
    acc.avatar_url = profile['avatar_url']
    acc.email_verified = userinfo.get('email_verified', False)
    db_session.commit()
    return acc

@bp.route('/gitlab/callback')
def authorize_gitlab():
    token = oauth.gitlab.authorize_access_token() # type: ignore
    _logger.info('/login/authorize_gitlab[%s]: token %s', g.log_ref, token)
    userinfo = token['userinfo']
    _logger.info('/login/authorize_gitlab[%s]: OpenID Connect callback userinfo: %s', g.log_ref,  userinfo)
    next_page = session.get('next_page')
    del session['next_page']
    
    # do something with the token and profile
    userid = int(userinfo['sub'])
    uacc = db_session.execute(select(User,Account).where(User.id==Account.user_id,Account.external_id==userid, Account.provider_name=='gitlab')).one_or_none()
    gc : GitlabConnection = current_app.extensions['puffin_gitlab_connection']
    #resp = oauth.gitlab.get(f'{current_app.config["GITLAB_BASE_URL"]}/api/v4/user', token=token)
    #resp.raise_for_status()
    #profile = resp.json()
    _logger.info('/login/authorize_gitlab[%s]: OpenID Connect login - account %s', g.log_ref, uacc)
    redirect_url = url_for('app.index_html')
    if next_page:
        _logger.info('/login/authorize_gitlab[%s]: next_page=%s', g.log_ref, next_page)
        if next_page == '/sonarqube':
            redirect_url = '/sonarqube'

    if uacc: # user exists, connected to this GitLab account
        acc : Account = uacc.Account
        user : User = uacc.User
        if not user.is_expired:
            _logger.info('/login/authorize_gitlab[%s]: logged in successfully, redirecting to %s', g.log_ref, redirect_url)
            #session.clear()
            login_user(user)
            session['real_user'] = user.id
            session['login_ref'] = g.log_ref
            acc.last_login = now()
            acc.email_verified = userinfo.get('email_verified', False)
            db_session.commit()
            flash('Logged in successfully')
            return redirect(redirect_url)
        else:
            error = "Account expired – contact administrators"
            _logger.error('/login/authorize_gitlab[%s]: Error: %s', g.log_ref, error)
            flash(error + f'(ref: {g.log_ref})')
            return redirect('/')

    profile = gc.get_user(userid)
    _logger.info('/login/authorize_gitlab[%s]: Profile: %s', g.log_ref, profile)
    if not profile:
        error = f'Failed to retrieve information about {userid}. Please ask a TA for assistance. Sorry!'


    if current_user: # user is logged in, we're connecting to the GitLab account
        _logger.warn('/login/authorize_gitlab[%s]: OpenID Connect login – no account, current user %s, profile data %s', g.log_ref, current_user, profile)

        acc = define_gitlab_from_gitlab_userinfo(current_user, userid, userinfo, profile)

        flash(f'Successfully connected to your GitLab account {acc.username}! (ref: {g.log_ref})')
        return redirect(url_for('app.index_html'))
    else:
        email_user = db_session.execute(select(User).where(User.email == userinfo['email'])).scalar_one_or_none()
        if email_user and email_user.account('gitlab'):
            # user exists with this email address, but different GitLab account
            error = f'User with email {userinfo["email"]} already exists with a GitLab account'
        elif email_user:
            # user exists, not connected to GitLab
            acc = define_gitlab_from_gitlab_userinfo(email_user, userid, userinfo, profile)
            login_user(email_user)
            session['real_user'] = email_user.id
            session['login_ref'] = g.log_ref
            flash(f'Successfully logged in and connected to your GitLab account {acc.username}! (ref: {g.log_ref})')
            return redirect(url_for('app.index_html'))
        else:
            error = f'No user found corresponding to your GitLab account {userinfo['email']}. Please as a TA for assistance. Sorry!'

    _logger.error('/login/authorize_gitlab[%s]: Error: %s', g.log_ref, error)
    flash(error+ f' (ref: {g.log_ref})')
    return redirect(url_for('app.login.login'))
            
# This method is called whenever the login manager needs to get
# the User object for a given user id
@login_manager.user_loader
def user_loader(user_id):
    user = db_session.get(User, int(user_id))
    return user

@login_manager.unauthorized_handler
def handle_needs_login():
    login_url = url_for('app.login.login', next_page=request.endpoint)
    if request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json':
        return jsonify({'status':'error', 'message':'Login required', 'login_required':True, 'login_url': login_url, 'log_ref' : g.log_ref})
    else:
        return redirect(login_url)


# This method is called to get a User object based on a request,
# for example, if using an api key or authentication token rather
# than getting the user name the standard way (from the session cookie)
@login_manager.request_loader
def request_loader(request):
    # Even though this HTTP header is primarily used for *authentication*
    # rather than *authorization*, it's still called "Authorization".
    auth = request.headers.get('Authorization')

    # If there is not Authorization header, do nothing, and the login
    # manager will deal with it (i.e., by redirecting to a login page)
    if not auth:
        return

    (auth_scheme, auth_params) = auth.split(maxsplit=1)
    auth_scheme = auth_scheme.casefold()
    if auth_scheme == 'bearer': # Bearer auth contains an access token;
        # an 'access token' is a unique string that both identifies
        # and authenticates a user, so no username is provided (unless
        # you encode it in the token – see JWT (JSON Web Token), which
        # encodes credentials and (possibly) authorization info)
        _logger.warning("/login/request_loader: Bearer auth not supported: %s %s", g.log_ref, auth_params)
        #return
        raise ErrorResponse('Not supported', 404)

    # For other authentication schemes, see
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication

    # If we failed to find a valid Authorized header or valid credentials, fail
    # with "401 Unauthorized" and a list of valid authentication schemes
    # (The presence of the Authorized header probably means we're talking to
    # a program and not a user in a browser, so we should send a proper
    # error message rather than redirect to the login page.)
    # (If an authenticated user doesn't have authorization to view a page,
    # Flask will send a "403 Forbidden" response, so think of
    # "Unauthorized" as "Unauthenticated" and "Forbidden" as "Unauthorized")
    abort(HTTPStatus.UNAUTHORIZED)

@bp.route("/auth/<name>/")
@bp.route("/auth/<name>/<path:path>")
def auth_helper(name: str, path : str = ''):
    if not current_user or not current_user.is_authenticated:
        abort(HTTPStatus.UNAUTHORIZED)


    if name == 'sonarqube':
        user : User = current_user # type: ignore
        account : Account|None = user.account('gitlab')
        if account == None:
            abort(HTTPStatus.FORBIDDEN)

        response = make_response()
        response.headers.add('X-Forwarded-Login', account.username)
        response.headers.add('X-Forwarded-Name', user.firstname + ' ' + user.lastname)
        response.headers.add('X-Forwarded-Email', user.email)
        response.headers.add('Cache-Control', 'private, max-age: 300, must-revalidate')
        groups = []
        for (course_id, slug, json_data, role) in db_session.execute(select(Course.id, Course.slug, Course.json_data, Enrollment.role).where(Course.id == Enrollment.course_id, Enrollment.user_id == user.id, Enrollment.join_model != JoinModel.REMOVED)).all():
            gitlab_path = json_data.get('gitlab_path')
            print(course_id, slug, json_data, role, gitlab_path)
            if not gitlab_path or not role:
                continue
            groups.append(f'{gitlab_path}/{role}s')
            groups.append(f'{slug}_{role}s')
            if role == 'teacher' or role == 'ta':
                groups.append(f'{gitlab_path}/proj')

            for team in db_session.execute(select(Group).where(Group.id == Membership.group_id, Group.kind == 'team', Group.course_id == course_id, Membership.user_id == user.id, Membership.join_model != JoinModel.REMOVED)).scalars().all():
                proj = team.json_data.get('project_path')
                if proj and proj.startswith(gitlab_path):
                    groups.append(proj)
        if len(groups) == 0:
            abort(HTTPStatus.FORBIDDEN)
        response.headers.add('X-Forwarded-Groups', ','.join(groups))
        print(request.headers, response.headers)
        return response
    else:
        abort(HTTPStatus.NOT_FOUND)
