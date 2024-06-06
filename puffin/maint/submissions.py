import csv
from gitlab import Gitlab, GitlabGetError
from gitlab.v4.objects  import Project as GitlabProject, User as GitlabUser
from slugify import slugify
from sqlalchemy import select
from puffin.db.database import init, db_session
from puffin.db.model_tables import  Assignment, User, Account, Course
from puffin.db.model_util import update_from_uib, get_or_define
from puffin.app.app import app
from puffin.canvas.canvas import CanvasConnection
from puffin.app.view_users import get_user, get_user_or_fail
import gitlab
import re
from puffin.gitlab.users import GitlabConnection

from puffin.util.util import intify 

def url_to_project_path(url):
    if url != None:
        url = re.sub('^https://git.app.uib.no/', '', url)
        url = re.sub('/-/.*$','',url)
        url = re.sub('\\.git$','',url)
        url = re.sub('/+$','',url)
    return url

if __name__ == '__main__':
    init(app)

def get_user(user_id_or_name):
    user_id_or_name = intify(user_id_or_name)
    return db_session.execute(select(User).where(User.id == Account.user_id, Account.external_id == user_id_or_name)).scalar_one_or_none()

def get_gitlab_username(user_or_id):
    if not type(user_or_id) is User:
        user_or_id = get_user(user_or_id)
        if not user_or_id:
            return None
    gitlab_account = user_or_id.account('gitlab')
    if gitlab_account:
        return gitlab_account.username
    else:
        return None
    
def autofill_submissions(subs):
    for sub in subs:
        if sub['submitted_at'] and not sub['url']:
            gituser = get_gitlab_username(sub['user_id'])
            if gituser:
                sub['url'] = f'https://git.app.uib.no/inf226/23h/assignment-2/{gituser}_headbook'
                print('found url: ', sub['url'])
            else:
                print('gitlab user not found:', sub)

def check_membership(resource: GitlabProject, user : User, access_level : int):
    account : Account = user.account('gitlab') # type: ignore
    user_id = account.external_id
    user_name =account.username
    #logger.debug('checking membership for %s %s %s', user, resource, user_id)
    try:
        membership = resource.members.get(user_id) # type: ignore
        if membership.access_level < access_level:
            print(
                f'Correcting member level for {user_name} on {resource.name}: {membership.access_level} → {access_level}')
            membership.access_level = access_level
            membership.save()
        # TODO: check active and expiry
    except GitlabGetError:
        try:
            # maybe user is member through group?
            resource.members_all.get(user_id) # type: ignore
        except GitlabGetError:
            print(
                f'Adding user {user_name} to {resource.name}: 0 → {access_level}')
            resource.members.create(
                    {'user_id': user_id, 'access_level': access_level})

def set_peer_review_settings(subs, peers):
    gl : Gitlab = app.extensions['puffin_gitlab_connection'].gl
    autofill_submissions(subs)
    peers = {peer['user_id'] : peer for peer in peers}
    for sub in subs:
        if sub['submitted_at']:
            user_git = get_gitlab_username(sub['user_id'])
            peer = peers.get(sub['user_id'])
            if not peer:
                print('No peer reviewer assigned:', user_git, sub)
                continue
            url = url_to_project_path(sub['url'])
            assessor = get_user(peer['assessor_id'])
            if not assessor:
                print('no assessor:', sub)
                continue
            print(sub['user_id'], user_git, assessor.account('gitlab').username, assessor.account('gitlab').external_id, url) # type:ignore
            if not assessor.account('gitlab'):
                print('no gitlab account:', user_git, assessor)
                continue
            if url and url.startswith('inf226/23h'):
                proj = gl.projects.get(url)
                check_membership(proj, assessor, gitlab.const.REPORTER_ACCESS) # type:ignore
            else:
                print('no project link:', sub)

def get_submissions(course, assignment):
    cc : CanvasConnection = app.extensions['puffin_canvas_connection']
    return cc.get_submissions(course, assignment) # type:ignore

def get_peer_reviews(course, assignment):
    cc : CanvasConnection = app.extensions['puffin_canvas_connection']
    return cc.get_peer_reviews(course, assignment) # type:ignore


def doit():
    global subs, peers
    subs = get_submissions(42576, 76979)
    peers = get_peer_reviews(42576, 76979)
    set_peer_review_settings(subs,peers)

gc : GitlabConnection = app.extensions['puffin_gitlab_connection']
gl = gc.gl
cc : CanvasConnection = app.extensions['puffin_canvas_connection']
