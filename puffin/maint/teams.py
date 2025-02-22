from datetime import datetime, date, timedelta
import logging
from slugify import slugify
from sqlalchemy import select
from puffin.app.app import app
from puffin.canvas.assignments import CanvasSubmission
from puffin.canvas.lib import CanvasConnection
from puffin.gitlab.users import GitlabConnection
from puffin.db.database import init, db_session
from puffin.db.model_tables import Assignment, Enrollment, Group, User, Account, Course
from puffin.db.model_util import update_from_uib, get_or_define
from puffin.maint.sonarqube import SonarConnection
from gitlab import Gitlab, GitlabGetError
from gitlab.v4.objects import (
    Project as GitlabProject,
    User as GitlabUser,
    Group as GitlabGroup,
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    init(app)

gc: GitlabConnection = app.extensions["puffin_gitlab_connection"]
sqc: SonarConnection = app.extensions["puffin_sonarqube_connection"]
gl = gc.gl
cc: CanvasConnection = app.extensions["puffin_canvas_connection"]


class ProjectTeam:
    team: Group
    last_activity: datetime
    worked: bool
    submission: CanvasSubmission | None

    def __init__(self, g: Group):
        self.refresh()
        self.team = g
        self.__sq_project = None  # type: ignore
        self.sq_group = {}
        self.last_activity = None  # type: ignore
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
    def project_id(self):
        return self.team.json_data.get("project_id")

    @property
    def project_path(self):
        return self.team.json_data.get("project_path")

    @property
    def project(self) -> GitlabProject:
        if not self.__full_project__ and self.project_id:
            self.__full_project__ = gl.projects.get(self.project_id, simple=True)
        return self.__full_project__

    @property
    def lazy_project(self):
        if not (self.__full_project__ or self.__lazy_project__) and self.project_id:
            self.__lazy_project__ = gl.projects.get(self.project_id, lazy=True)
        return self.__full_project__ or self.__lazy_project__

    @property
    def pipelines(self):
        return self.lazy_project and self.lazy_project.pipelines

    @property
    def pipeline_status(self) -> str | None:
        if self.__pipeline_status__ == None and self.pipelines:
            try:
                self.__pipeline_status__ = self.pipelines.get("latest").status
            except:
                self.__pipeline_status__ = "na"
        return self.__pipeline_status__

    @property
    def sq_project(self) -> dict |None:
        return self.get_sq_project()
    
    def get_sq_project(self, binding_id = None) -> dict | None:
        if not self.__sq_project and self.team.json_data.get("sonarqube_binding"):
            sq = self.team.json_data["sonarqube_binding"]
            self.__sq_project = sqc.get_single(
                f'/api/v2/dop-translation/project-bindings/{sq["id"]}'
            )
            print(sq, self.__sq_project, sq == self.__sq_project)
        elif not self.__sq_project and binding_id:
            self.__sq_project = sqc.get_single(
                f'/api/v2/dop-translation/project-bindings/{binding_id}'
            )
            del self.team.json_data['sonarqube']
            self.team.json_data["sonarqube_binding"] = self.__sq_project
            db_session.add(self.team)
            db_session.commit()
        return self.__sq_project

    def ensure_sonarqube_setup(self):
        if not self.sq_project:
            logger.info('generating sonarqube project for %s', self.team.name)
            self.create_sonarqube_project()
        else:
            self.set_sonarqube_permissions()
        
        if not self.team.json_data.get("sonarqube_analysis_token"):
            logger.info('generating token for %s', self.team.name)
            self.generate_token()
        
        self.set_cicd_config()

    def create_sonarqube_project(self) -> dict | None:
        if self.sq_project:
            return self.sq_project
        params = {}
        params["projectKey"] = slugify(self.project_path, separator="_")
        params["projectName"] = self.project.name
        params["devOpsPlatformSettingId"] = gitlabDop["id"]
        params["repositoryIdentifier"] = self.project.id
        params["monorepo"] = "false"
        result = sqc.post("/api/v2/dop-translation/bound-projects", params, debug=True)
        print(result)
        self.__sq_project = sqc.get_single(
            f'/api/v2/dop-translation/project-bindings/{result["bindingId"]}'
        )
        self.team.json_data["sonarqube"] = self.__sq_project
        db_session.add(self.team)
        db_session.commit()
        self.set_sonarqube_permissions()
        return self.__sq_project

    def generate_token(self):
        if self.sq_project and self.project:
            params = {}
            params["name"] = f'Analyze "{self.project.name}'
            params["type"] = "PROJECT_ANALYSIS_TOKEN"
            params["projectKey"] = self.sq_project["projectKey"]
            params["expirationDate"] = (date.today() + timedelta(365)).isoformat()
            token_result = sqc.post("/api/user_tokens/generate", params, use_form=True)
            self.set_gitlab_project_variable(
                "SONAR_TOKEN",
                token_result.get("token"),
                masked_and_hidden=True,
                protected=True,
                raw=True,
            )
            del token_result["token"]
            self.team.json_data["sonarqube_analysis_token"] = token_result
            db_session.add(self.team)
            db_session.commit()
            return token_result

    def revoke_token(self):
        if self.sq_project:
            params = {}
            params["name"] = f'Analyze "{self.project.name}'
            token_result = sqc.post("/api/user_tokens/revoke", params, use_form=True)
            del self.team.json_data["sonarqube_analysis_token"]
            db_session.add(self.team)
            db_session.commit()
            self.delete_gitlab_project_variable("SONAR_TOKEN")
            return token_result

    def set_cicd_config(self):
        if self.sq_project and self.project:
            self.set_gitlab_project_variable(
                "SONAR_PROJECT_KEY", self.sq_project["projectKey"], raw=True
            )
            self.project.ci_default_git_depth = 0
            self.project.ci_config_path = 'proj_gitlab-ci.yml@inf112/25v/devops'
            self.project.save()

    def set_sonarqube_permissions(self):
        sqp = self.sq_project
        if sqp:
            params = {}
            params["groupName"] = self.sq_group["name"]
            # params['projectId'] = sqp['projectId']
            params["projectKey"] = sqp["projectKey"]
            for perm in "issueadmin,codeviewer,securityhotspotadmin,scan,user".split(
                ","
            ):  # , admin
                params["permission"] = perm
                perm_result = sqc.post(
                    "api/permissions/add_group", params, use_form=True
                )
            return perm_result

    def set_gitlab_project_variable(self, key, value, **kwargs):
        try:
            var = self.project.variables.get(key)
            var.value = value
            var.save()
        except:
            try:
                kwargs["key"] = key
                kwargs["value"] = value
                var = self.project.variables.create(kwargs)
            except:
                logger.error("failed to set variable %s", key)
        return var


    def delete_gitlab_project_variable(self, key):
        try:
            self.project.variables.delete(key)
        except:
            pass

# gitlab access key:
# api/alm_integrations/set_pat?almSetting=INF112-25v-proj&pat=pp9fY9QH_Mw8Fuszeftq&username=


def make_team_groups():
    for team in teams:
        group_slug = team.project_path
        if group_slug:
            team.sq_group = sqc.get_or_create_group(group_slug)


# /api/v2/dop-translation/bound-projects


def setup():
    global course, teams, gitlabDop

    course = db_session.get(Course, 3159)
    teams = [
        ProjectTeam(group)
        for group in db_session.execute(
            select(Group).where(Group.kind == "team", Group.course == course)
        )
        .scalars()
        .all()
    ]

    make_team_groups()
    gitlabDop = [
        dop
        for dop in sqc.get_single("/api/v2/dop-translation/dop-settings")["dopSettings"]
        if dop["url"].strip("/").startswith(gc.base_url.strip("/"))
    ][0]

def all_configure():
    for team in teams:
        logger.info('ensuring sonarqube setup for %s', team.team.name)
        team.ensure_sonarqube_setup()

def all_start_pipelines():
    for team in teams:
        logger.info('creating pipeline for %s, branch %s', team.project.name, team.project.default_branch)
        team.project.pipelines.create({'ref':team.project.default_branch})


