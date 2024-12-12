import csv
from datetime import datetime
import sys
from gitlab import Gitlab, GitlabGetError
from gitlab.v4.objects  import Project as GitlabProject, User as GitlabUser, Group as GitlabGroup
from slugify import slugify
from sqlalchemy import select
from puffin.canvas.assignments import CanvasAssignment, CanvasSubmission
from puffin.db.database import init, db_session
from puffin.db.model_tables import  Assignment, Enrollment, User, Account, Course
from puffin.db.model_util import update_from_uib, get_or_define
from puffin.app.app import app
from puffin.canvas.canvas import CanvasConnection
from puffin.app.view_users import get_user, get_user_or_fail
import gitlab
import re
from puffin.db.model_views import CourseUser, FullUser, UserAccount
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
    
def get_all_assignment_projects(group_id) -> list[GitlabProject]:
    group = gl.groups.get(group_id)
    return group.projects.list(all=True) # type: ignore

def get_all_course_users(course_id):
    return db_session.execute(select(User,Enrollment,Account).where(User.id == Enrollment.user_id, Enrollment.course_id == course_id, Account.user_id == User.id, Account.provider_name == 'gitlab')).all()

def create_projects_pipelines(ps : list[GitlabProject]):
    for p in ps:
        print(p.name)
        p.pipelines.create({'ref':'main'})

def delete_project_pipelines(p : GitlabProject):
    print(p.name, end=': ')
    if not hasattr(p, 'pipelines'):
        p = gl.projects.get(p.id)
    for pl in p.pipelines.list(iterator=True):
        print(f'{pl.id}({pl.status})', end=' ')
        pl.delete()
    print()


class Submission:
    user : User
    enrollment: Enrollment
    project : GitlabProject
    gitlab: Account
    canvas: Account
    last_activity : datetime
    worked : bool
    submission : CanvasSubmission|None

    def __init__(self):
        self.refresh()
        self.user = None
        self.enrollment = None
        self.project = None
        self.gitlab = None
        self.canvas = None
        self.last_activity = None
        self.worked = False
        self.submission = None

    def __repr__(self):
        return repr(self.__dict__)

    def refresh(self):
        self.__full_project__ = None
        self.__lazy_project__ = None
        self.__pipeline_status__ = None
        return self

    @property
    def full_project(self) -> GitlabProject:
        if not self.__full_project__:
            self.__full_project__ = gl.projects.get(self.project.id, simple = True)
        return self.__full_project__

    @property
    def lazy_project(self):
        if not (self.__full_project__ or self.__lazy_project__):
            self.__lazy_project__ = gl.projects.get(self.project.id, lazy = True)
        return self.__full_project__ or self.__lazy_project__

    @property
    def pipelines(self):
        return self.lazy_project and self.lazy_project.pipelines

    @property
    def pipeline_status(self) -> str|None:
        if self.__pipeline_status__ == None:
            try:
                self.__pipeline_status__ = self.pipelines.get('latest').status
            except:
                self.__pipeline_status__ = 'na'
        return self.__pipeline_status__
    
def get_all_course_user_projects(course_id, projects : list[GitlabProject], canvas_subs : list[CanvasSubmission] = []):
    users = db_session.execute(select(User,Enrollment,Account).where(User.id == Enrollment.user_id, Enrollment.course_id == course_id, Enrollment.role == 'student', Account.user_id == User.id, Account.provider_name == 'gitlab')).all()
    projectsByUser = {p.path.split('_',1)[0]:p for p in projects}
    submissionsByUser = {s.user_id:s for s in canvas_subs}
    submissions = []
    for (u,enr,acc) in users:
        if acc.username:
            sub = Submission()
            sub.user = u
            sub.enrollment = enr
            sub.gitlab = acc
            sub.canvas = u.account('canvas')
            sub.project = projectsByUser.get(acc.username)
            sub.submission = submissionsByUser.get(sub.canvas.external_id or 0)
            if sub.project:
                sub.last_activity = datetime.fromisoformat(sub.project.last_activity_at)
                diff = datetime.fromisoformat(sub.project.created_at) - sub.last_activity
                sub.worked = abs(diff.total_seconds()) > 60
                submissions.append(sub)
                del projectsByUser[acc.username]
            else:
                print('no project found for', u.email)
        else:
            print('no gitlab username', u.email)
    print('leftover projects:', projectsByUser)
    submissions.sort(key = lambda s: (s.user.lastname.casefold(),s.user.firstname.casefold()))
    for (i,s) in enumerate(submissions):
        s.id = i
    return submissions

def submit_projects(subs:list[Submission]):
    for s in subs:
        submit_project(s)

def submit_project(sub:Submission):
    if not sub.submission:
        print("no canvas submission for", sub.user.email)
        return
    if not sub.worked:
        print("no work done for", sub.user.email)
        return
    if sub.submission.submission_type != 'online_url' or sub.submission.url != sub.project.web_url:
        sub.submission.submit('online_url', url = sub.project.web_url)
    pass

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


def print_student_list(subs):
    for s in subs:
        if s.enrollment.role == 'student':
            print(s.gitlab.username)

def print_submission_list(subs, filename = None, pipeline=False):
    def doit(f):
        for s in subs:
            if s.enrollment.role == 'student' and s.worked:
                if pipeline:
                    status = gl.projects.get(s.project.id, lazy=True).pipelines.get('latest').status
                    print(f'{status:8s} {s.user.lastname + ", " + s.user.firstname:40s}: {s.project.web_url}', file=f)
                else:
                    print(f'{s.user.lastname + ", " + s.user.firstname:40s}: {s.project.web_url}', file=f)
    if filename:
        with open(filename, 'w') as f:
            doit(f)
    else:
        doit(sys.stdout)

def doit_inf226_23h():
    global subs, peers
    subs = get_submissions(42576, 76979)
    peers = get_peer_reviews(42576, 76979)
    set_peer_review_settings(subs,peers)

def doit_inf214_24h_1():
    global subs1, projects1, canvas_submissions1, asgn1
    course = cc.course(48837)
    projects1 = get_all_assignment_projects(48521)
    asgn1 = course.get_assignment(95608)
    canvas_submissions1 = asgn1.get_submissions()
    subs1 = get_all_course_user_projects(2712, projects1, canvas_submissions1)
    submit_projects(subs1)
    print_submission_list(subs1, datetime.now().strftime('all-oblig-1-projects_%Y-%m-%d.txt'))

subs1:list[Submission] = []
projects1:list[GitlabProject] = []
worked1:list[GitlabProject] = []
canvas_submissions1:list[CanvasSubmission] = []
asgn1:CanvasAssignment|None = None
subs2:list[Submission] = []
projects2:list[GitlabProject] = []
worked2:list[GitlabProject] = []
canvas_submissions2:list[CanvasSubmission] = []
asgn2:CanvasAssignment|None = None

def doit_inf214_24h_2():
    global subs2, projects2, canvas_submissions2, asgn2
    course = cc.course(48837)
    projects2 = get_all_assignment_projects(49374)
    asgn2 = course.get_assignment(96088)
    canvas_submissions2 = asgn2.get_submissions()
    subs2 = get_all_course_user_projects(2712, projects2, canvas_submissions2)
    submit_projects(subs2)
    print_submission_list(subs2, datetime.now().strftime('all-oblig-2-projects_%Y-%m-%d.txt'))

def get_worked_projects(ss):
    global worked
    worked = [gc.gl.projects.get(p.project.id) for p in ss if p.worked]
    return worked

gc : GitlabConnection = app.extensions['puffin_gitlab_connection']
gl = gc.gl
cc : CanvasConnection = app.extensions['puffin_canvas_connection']
