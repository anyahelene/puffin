from gitlab import Gitlab, GitlabGetError
from gitlab.v4.objects import Project, User as GitlabUser, Group as GitlabGroup
from sqlalchemy import select
from puffin.db.database import db_session as db
from puffin.db.model import providers, User as PuffinUser, Account, define_gitlab_account
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class GitlabConnection:
    def __init__(self, url, token):
        self.gl = Gitlab(url=url, private_token=token)

    
    def project_members(self, project: Project | GitlabGroup | str | int, indirect=False) -> list[PuffinUser]:
        p = self.get_project_or_group(project)
        if indirect:
            members = p.members_all.list(iterator=True)
        else:
            members = p.members.list(iterator=True)

        return [self.map_gitlab_user(u) for u in members]

    def map_gitlab_user(self, user : GitlabUser) -> PuffinUser:
        puffin_user = db.execute(select(PuffinUser).where(Account.user_id == PuffinUser.id,
            Account.provider_id == providers['git.app.uib.no'],
            Account.ref_id == user.get_id())).scalar_one_or_none()
        print("Trying to map gitlab user:", user.username, "→", puffin_user.lastname if puffin_user else None)
        return puffin_user

    def get_project_or_group(self, name_or_id: Project | GitlabGroup | str | int) -> Project | GitlabGroup:
        if isinstance(name_or_id, int) or isinstance(name_or_id, str):
            try:
                return self.gl.projects.get(name_or_id)
            except GitlabGetError:
                return self.gl.groups.get(name_or_id)
        if isinstance(name_or_id, Project) or isinstance(name_or_id, GitlabGroup):
            return name_or_id
        else:
            raise ValueError(f"Not a project: {name_or_id}")

    def get_project(self, project: Project | str | int) -> Project:
        if isinstance(project, int) or isinstance(project, str):
            project = self.gl.projects.get(project)
            if project == None:
                self.gl.namespaces.g
        if isinstance(project, Project):
            return project
        else:
            raise ValueError(f"Not a project: {project}")


    def find_gitlab_account(self, user:PuffinUser) -> Account:
        name = f'{user.lastname}, {user.firstname}'
        (first_firstname,*more_firstnames) = user.firstname.split()
        acc = user.account(providers['git.app.uib.no']) 
        if acc == None:
            username=user.email.replace('@uib.no','').replace('@student.uib.no','')
            users = self.gl.users.list(username = username)
            logger.debug('Searching with username=%s: %s', username, users)
            gituser:GitlabUser = None
            if len(users) == 1:
                gituser = users[0]
            else:
                username = user.account(providers['uib']).username
                logger.debug('Searching with username=%s: %s', username, users)
                more_users = self.gl.users.list(username=username)
                if len(more_users) == 1:
                    gituser = more_users[0]
                else:
                    username = f'{first_firstname}.{user.lastname}'
                    logger.debug('Searching with username=%s: %s', username, users)
                    more_users = self.gl.users.list(username=username)
                    if len(more_users) == 1:
                        gituser = more_users[0]

            if gituser:
                acc = define_gitlab_account(user, gituser.username, gituser.id, gituser.name, commit=True)
                logger.info("Defined gitlab account: %s", acc)
            elif len(users) == 0:
                if 'uib.no' in user.email:
                    logger.warn("Missing GitLab user – maybe not registered yet? %s", user)
                else:
                    logger.warn("Missing GitLab user: %s", user)
            else:
                logger.warn("Ambiguous GitLab user: %s: %s", user, users)
        return acc
