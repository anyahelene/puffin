from flask import Blueprint, Flask, flash, redirect, render_template, request, session, url_for
from flask_login import LoginManager, login_user
from flask_wtf import CSRFProtect, FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from puffin.db.model import User,Account
from puffin.db.database import db_session
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

class LoginForm(FlaskForm):
    username = StringField('Username')
    password = PasswordField('Password')
    submit = SubmitField('Submit')

bp = Blueprint('login', __name__, url_prefix='/login')
login_manager = LoginManager()

def init(app:Flask):
    app.register_blueprint(bp)
    login_manager.init_app(app)
    login_manager.id_attribute = 'get_id'
    login_manager.login_view = "login.login"


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
                print('logged in successfully, redirecting to', url_for('index_html'))
                #session.clear()
                login_user(u)
                flash('Logged in successfully')
                return redirect(url_for('index_html'))
            else:
                error = "Account expired – contact administrators"
        else:
            error = "Wrong username or password"

        print('Error:', error)
        flash(error)

    return render_template('./login.html', form=form)

# This method is called whenever the login manager needs to get
# the User object for a given user id
@login_manager.user_loader
def user_loader(user_id):
    print('user_loader')
    user = db_session.get(User, int(user_id))
    print('user_loader', user)
    return user


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
