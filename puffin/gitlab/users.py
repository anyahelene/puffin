from datetime import datetime
from typing import Iterable
from flask import Flask, current_app
from gitlab import Gitlab, GitlabGetError
from gitlab.v4.objects import (
    Project,
    User as GitlabUser,
    Group as GitlabGroup,
    GroupMergeRequest,
    ProjectMergeRequest,
)
import sqlalchemy as sa
from puffin.db.model_tables import LastSync, User as PuffinUser, Account
from puffin.db.model_util import define_gitlab_account
import logging
import threading

logger = logging.getLogger(__name__)


class GitlabConnection:  
    def __init__(self, app_or_url, token=None):
        if isinstance(app_or_url, Flask):
            app = app_or_url
            app.extensions["puffin_gitlab_connection"] = self
            base_url = None
        else:
            app = current_app
            base_url = app_or_url
        if app:
            base_url = base_url or app.config.get("GITLAB_BASE_URL")
            token = token or app.config.get("GITLAB_SECRET_TOKEN")
        self.base_url = base_url
        self.token = token
        self.thread_local = threading.local()
        self.thread_local.gl = None

    @property
    def gl(self) -> Gitlab:
        if getattr(self.thread_local, "gl", None) == None:
            self.thread_local.gl = Gitlab(url=self.base_url, private_token=self.token)
        return self.thread_local.gl

    def project_members(
        self,
        session: sa.orm.Session,
        project: Project | GitlabGroup | str | int,
        indirect=True,
    ) -> list[PuffinUser]:
        return self.project_members_incl_unmapped(session, project, indirect)[0]
    
    def project_members_incl_unmapped(
        self,
        session: sa.orm.Session,
        project: Project | GitlabGroup | str | int,
        indirect=True,
    ) -> tuple[list[PuffinUser], list[str]]:
        p = self.get_project_or_group(project)
        ml = p.members_all if indirect else p.members
        members: Iterable[GitlabUser] = ml.list(iterator=True) # type:ignore
        result = [(self.map_gitlab_user(session, u), u) for u in members]
        return (
            [pu for (pu, gu) in result if pu],
            [gu.username for (pu, gu) in result if not pu],
        )

    def map_gitlab_user(self, session: sa.orm.Session, user: GitlabUser) -> PuffinUser:
        puffin_user = session.execute(
            sa.select(PuffinUser).where(
                Account.user_id == PuffinUser.id,
                Account.provider_name == "gitlab",
                Account.external_id == user.get_id(),
            )
        ).scalar_one_or_none()
        print(
            "Trying to map gitlab user:",
            user.username,
            "→",
            puffin_user.lastname if puffin_user else None,
        )
        return puffin_user

    def get_project_or_group(
        self, name_or_id: Project | GitlabGroup | str | int
    ) -> Project | GitlabGroup:
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
                self.gl.namespaces.g  # type:ignore
        if isinstance(project, Project):
            return project
        else:
            raise ValueError(f"Not a project: {project}")

    def get_user(self, user_id: int) -> dict:
        try:
            user = self.gl.users.get(user_id)
            return user.asdict()
        except:
            return None # type:ignore 

    def find_gitlab_account(
        self,
        session: sa.orm.Session,
        user: PuffinUser,
        verify=False,
        sync_time: datetime = None, # type:ignore
        gitusername: str = None, # type:ignore
    ) -> Account:
        name = f"{user.lastname}, {user.firstname}"
        (first_firstname, *more_firstnames) = user.firstname.split()
        acc = user.account("gitlab")
        gituser: GitlabUser = None # type:ignore
        if acc == None:
            username = gitusername or user.email.replace("@uib.no", "").replace(
                "@student.uib.no", ""
            )
            users = self.gl.users.list(username=username)
            logger.debug("Searching with username=%s: %s", username, users)
            if len(users) == 1:
                gituser = users[0] # type:ignore
            else:
                username = user.account("canvas").username # type:ignore
                logger.debug("Searching with username=%s: %s", username, users)
                more_users = self.gl.users.list(username=username)
                if len(more_users) == 1:
                    gituser = more_users[0] # type:ignore
                else:
                    username = f"{first_firstname}.{user.lastname}"
                    logger.debug("Searching with username=%s: %s", username, users)
                    more_users = self.gl.users.list(username=username)
                    if len(more_users) == 1:
                        gituser = more_users[0]  # type:ignore

            if gituser:
                acc = define_gitlab_account(
                    session,
                    user,
                    gituser.username,
                    gituser.id,
                    gituser.name,
                    sync_time=sync_time,
                )
                logger.info("Defined gitlab account: %s", acc)
            elif len(users) == 0:
                if "uib.no" in user.email:
                    logger.warn(
                        "Missing GitLab user – maybe not registered yet? %s", user
                    )
                else:
                    logger.warn("Missing GitLab user: %s", user)
            else:
                logger.warn("Ambiguous GitLab user: %s: %s", user, users)
        elif verify:
            gituser = self.gl.users.get(acc.external_id)  # type:ignore
            if gituser:
                if gituser.username != acc.username:
                    logger.error(
                        "GitLab user %d: expected username %s, was %s for user %s",
                        acc.external_id,
                        acc.username,
                        gituser.username,
                        user,
                    )
                    acc.username = gituser.username
                    session.add(acc)
            else:
                logger.error(
                    "GitLab user %d doesn't exist: account=%s, user=%s",
                    acc.external_id,
                    acc,
                    user,
                )
                session.delete(acc)
                acc = None
            if sync_time and acc:
                LastSync.set_sync(session, acc, sync_time)
        return acc  # type:ignore

    def group_mergerequest_to_project_mergerequest(
        self, gmreq: GroupMergeRequest
    ) -> ProjectMergeRequest:
        return self.gl.projects.get(gmreq.project_id).mergerequests.get(gmreq.iid)
