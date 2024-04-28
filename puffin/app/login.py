from datetime import datetime
from flask import Blueprint, Flask, abort, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for
from flask_login import LoginManager, current_user, login_required, login_user
from flask_wtf import CSRFProtect, FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from puffin.db.model_tables import User,Account
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
login_manager = LoginManager()
oauth = OAuth()
def init(app:Flask, parent:Blueprint):
    (parent or app).register_blueprint(bp)
    login_manager.init_app(app)
    login_manager.id_attribute = 'get_id'
    login_manager.login_view = "app.login.login"
    oauth.init_app(app)
    global gitlab_oauth
    gitlab_oauth = oauth.register('gitlab',
                                  server_metadata_url=app.config['GITLAB_BASE_URL'] + '.well-known/openid-configuration',
                                  client_kwargs={'scope':'openid profile email'})
    print(oauth._clients, gitlab_oauth.__dict__)
    for k,v in gitlab_oauth.__dict__.items():
        print(k, v)

@bp.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.is_submitted():
        print(f'Received form: {"invalid" if not form.validate() else "valid"} {form.form_errors} {form.errors}')
        print(request.form)
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        u = db_session.execute(select(User).where(User.email==username)).scalar_one_or_none()

        print('found user:', u)
        if u and u.password and check_password_hash(u.password, password):
            if not u.is_expired:
                print('logged in successfully, redirecting to', url_for('app.index_html'))
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

        print('Error:', error)
        flash(error + f'(ref: {g.log_ref})')

    return render_template('./login.html', form=form)


@bp.route('/gitlab')
def login_gitlab():
    redirect_uri = url_for('app.login.authorize_gitlab', _external=True)
    print('login_gitlab: uri', redirect_uri)
    r= oauth.gitlab.authorize_redirect(redirect_uri)
    for k,v in gitlab_oauth.__dict__.items():
        print(k, v)
    return r

@bp.route('/logout')
def logout_gitlab():
    oauth.gitlab.revoke_token('https://git.app.uib.no/oauth/revoke', session['log_ref'])


@bp.route('/sudone')
@login_required
def sudone():
    print("sudone", repr(session.get('real_user')), repr(current_user.id))
    real_user = session.get('real_user')

    if real_user != None and real_user != current_user.id:
        u = db_session.execute(select(User).where(User.id==real_user)).scalar_one_or_none()
        print("returning to user ", u)
        if u:
            login_user(u)
            flash(f"Returned to real user {u.email}")
        else:
            flash(f"Didn't find real user", category="error")
    return redirect(url_for('app.index_html'))
    
@bp.route('/sudo/<username>')
@login_required
def sudo(username: str = ""):
    print("sudo", repr(session.get('real_user')), repr(current_user.id))

    if not current_user.is_admin:
        abort(403)
    else:
        u = db_session.execute(select(User).where(User.email==username)).scalar_one_or_none()
        if u:
            login_user(u, force=True)
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
    token = oauth.gitlab.authorize_access_token()
    _logger.info('authorize_gitlab: token %s', token)
    userinfo = token['userinfo']
    _logger.info('OpenID Connect callback userinfo: %s', userinfo)
    # do something with the token and profile
    userid = int(userinfo['sub'])
    uacc = db_session.execute(select(User,Account).where(User.id==Account.user_id,Account.external_id==userid, Account.provider_name=='gitlab')).one_or_none()
    gc : GitlabConnection = current_app.extensions['puffin_gitlab_connection']
    #resp = oauth.gitlab.get(f'{current_app.config["GITLAB_BASE_URL"]}/api/v4/user', token=token)
    #resp.raise_for_status()
    #profile = resp.json()
    _logger.info('OpenID Connect login - account %s', uacc)
    if uacc:
        acc : Account = uacc.Account
        user : User = uacc.User
        if not user.is_expired:
            _logger.info('logged in successfully, redirecting to %s', url_for('app.index_html'))
            #session.clear()
            login_user(user)
            session['real_user'] = user.id
            session['login_ref'] = g.log_ref
            acc.last_login = now()
            acc.email_verified = userinfo.get('email_verified', False)
            db_session.commit()
            flash('Logged in successfully')
            return redirect(url_for('app.index_html'))
        else:
            error = "Account expired – contact administrators"
            _logger.error('Error: %s', error)
            flash(error + f'(ref: {g.log_ref})')
            return redirect('/')

    profile = gc.get_user(userid)
    _logger.info('Profile: %s', profile)
    if not profile:
        error = f'Failed to retrieve information about {acc.username}. Please ask a TA for assistance. Sorry!'


    if current_user: # user is logged in, we're connecting to the GitLab account
        _logger.warn('OpenID Connect login – no account, current user %s, profile data %s', current_user, profile)

        acc = define_gitlab_from_gitlab_userinfo(current_user, userid, userinfo, profile)

        flash(f'Successfully connected to your GitLab account {acc.username}!')
        return redirect(url_for('app.index_html'))
    else:
        user = db_session.execute(select(User).where(User.email == userinfo['email'])).one_or_none()
        if user and user.account['gitlab']:
            error = f'User with email {userinfo["email"]} already exists with a GitLab account'
        elif user:
            acc = define_gitlab_from_gitlab_userinfo(user, userid, userinfo, profile)
            login_user(user)
            session['real_user'] = user.id
            session['login_ref'] = g.log_ref
            flash(f'Successfully logged in and connected to your GitLab account {acc.username}!')
            return redirect(url_for('app.index_html'))
        else:
            error = f'No user found corresponding to your GitLab account {acc.username}. Please as a TA for assistance. Sorry!'

    _logger.error('Error: %s', error)
    flash(error+ f'(ref: {g.log_ref})')
    return redirect(url_for('app.index_html'))
            
# This method is called whenever the login manager needs to get
# the User object for a given user id
@login_manager.user_loader
def user_loader(user_id):
    user = db_session.get(User, int(user_id))
    print('user_loader', user)
    return user

@login_manager.unauthorized_handler
def handle_needs_login():
    login_url = url_for('app.login.login', next_page=request.endpoint)
    if request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json':
        return jsonify({'status':'error', 'message':'Login required', 'login_required':True, 'login_url': login_url})
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
    if auth_scheme == 'basic':  # Basic auth has username:password in base64
        (uid,passwd) = b64decode(auth_params.encode(errors='ignore')).decode(errors='ignore').split(':', maxsplit=1)
        print(f'Basic auth: {uid}:{passwd}')
        u = users.get(uid)
        if u: # and check_password(u.password, passwd):
            return user_loader(uid)
    elif auth_scheme == 'bearer': # Bearer auth contains an access token;
        # an 'access token' is a unique string that both identifies
        # and authenticates a user, so no username is provided (unless
        # you encode it in the token – see JWT (JSON Web Token), which
        # encodes credentials and (possibly) authorization info)
        print(f'Bearer auth: {auth_params}')
        for uid in users:
            if users[uid].get('token') == auth_params:
                return user_loader(uid)
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
    abort(HTTPStatus.UNAUTHORIZED, www_authenticate = WWWAuthenticate('Basic realm=inf226, Bearer'))
