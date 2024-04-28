#! /usr/bin/python

import csv
from pprint import pformat
import re
import time
import gitlab
import sys
from gitlab import Gitlab, GitlabError
from gitlab.exceptions import GitlabGetError
from gitlab.v4.objects import User, CurrentUser, Project, Group

import logging
logger = logging.getLogger(__name__)

logger.info('hello!')

TOKEN = open('../uib-git.api_token').read().strip()

STATUS_BADGE_LINK_URL = 'https://git.app.uib.no/%{project_path}/-/pipelines/latest'
STATUS_BADGE_IMAGE_URL = 'https://git.app.uib.no/%{project_path}/badges/%{default_branch}/pipeline.svg'

CI_CONFIG_PATH = '.gitlab-ci.yml@ii/inf222/v23/assignments/test-runner'
DEFAULT_ACCESS_LEVEL = gitlab.const.DEVELOPER_ACCESS

FATAL_ERRORS = [gitlab.GitlabBanError, gitlab.GitlabAuthenticationError]
# Set these to 'disabled' to disabled the feature,
# 'enabled' to enable (for everyone with access – makes no sense for private project), or
# 'private' to enable only for project members
FEATURE_ACCESS = {
    'analytics_access_level': 'disabled',
    'builds_access_level': 'enabled',
    'container_registry_access_level': 'disabled',
    'environments_access_level': 'disabled',
    'feature_flags_access_level': 'disabled',
    'forking_access_level': 'enabled',
    'infrastructure_access_level': 'disabled',
    'merge_requests_access_level': 'enabled',
    'monitor_access_level': 'disabled',
    'pages_access_level': 'disabled',
    'releases_access_level': 'disabled',
    'repository_access_level': 'private',
    'security_and_compliance_access_level': 'disabled',
    'snippets_access_level': 'private',
    'wiki_access_level': 'disabled',
    #    'requirements_access_level': 'disabled',
}
REPO_SUB_FEATURES = ['merge_requests_access_level',
                     'builds_access_level', 'forking_access_level']
DEFAULT_PROJECT_CONFIG = {
    'visibility': gitlab.const.VISIBILITY_PRIVATE,
    'ci_config_path': CI_CONFIG_PATH,
    'auto_cancel_pending_pipelines': 'enabled',
    'auto_devops_enabled': False,
    'lfs_enabled': False,
    'packages_enabled': False,
    'request_access_enabled': False,
    'service_desk_enabled': False,
    'shared_runners_enabled': False,
    #    'group_runners_enabled': True,
    'keep_latest_artifact': True,
    'build_git_strategy': 'fetch',
    'autoclose_referenced_issues': True,
    'build_timeout': 600
}


class AssignmentFork:
    def __init__(self, assignment: Project | str | int, test_project: Project | str = None, gitlab_config: dict = None, access_level: int = DEFAULT_ACCESS_LEVEL, gitlab: gitlab.Gitlab = None, gitlab_token=TOKEN):
        self.gl = Gitlab(url='https://git.app.uib.no/',
                         private_token=gitlab_token) if gitlab == None else gitlab
        if self.gl.user == None and TOKEN != None and not TOKEN.isspace():
            self.gl.auth()
        self.assignment = self.get_project(assignment)
        self.changelog: list = []
        self.errors = []
        self.access_level = access_level
        self.namespace = self.assignment.namespace
        self.group = self.gl.groups.get(self.namespace['id']) if self.namespace['kind'] == 'group' else None
        self.variables = {'ASSIGNMENT': self.assignment.path}
        test_path = self.__find_test_project(test_project)
        if test_path != None:
            self.variables['TEST_PROJECT_NAME'] = test_path
        config = FEATURE_ACCESS.copy()
        config.update(DEFAULT_PROJECT_CONFIG)
        if gitlab_config != None:
            config.update(gitlab_config)
        for key in REPO_SUB_FEATURES:
            if config['repository_access_level'] == 'private' and config[key] == 'enabled':
                config[key] = 'private'
            if config['repository_access_level'] == 'disabled':
                config[key] = 'disabled'
        self.gitlab_config = config
        self.commit = True

    def __find_test_project(self, test_project) -> str:
        if isinstance(test_project, Project):
            self.test_project = test_project
            return test_project.path

        try:
            var: str = test_project if isinstance(
                test_project, str) else self.assignment.variables.get('TEST_PROJECT_NAME').value
        except GitlabGetError:
            var = f"{self.assignment.path_with_namespace}-tests"  # fallback
        if '/' not in var and '$PROJECT_PATH' not in var:
            var = f"{self.namespace['full_path']}/{var}"  # looks unqualified
        if '$' in var:  # a variable we can't expand
            self.test_project = var
            return var
        else:
            try:
                self.test_project = self.get_project(var)
                return self.test_project.path_with_namespace
            except GitlabGetError:
                self.errors.append(('test project not found', var))
                return None

    def check_membership(self, resource: Project | Group, user: User | CurrentUser | int):
        user_id = getattr(user, 'id', user)
        #logger.debug('checking membership for %s %s %s', user, resource, user_id)
        try:
            membership = resource.members.get(user_id)
            if membership.access_level != gitlab.const.OWNER_ACCESS and membership.access_level != self.access_level:
                print(
                    f'Correcting member level for {self.get_user_name(user)} on {resource.name}: {membership.access_level} → {self.access_level}')
                membership.access_level = self.access_level
                if self.commit:
                    membership.save()
                self.__change('set_user', resource, user=user, access_level=self.access_level)
            # TODO: check active and expiry
        except GitlabGetError:
            try:
                # maybe user is member through group?
                resource.members_all.get(user_id)
            except GitlabGetError:
                print(
                    f'Adding user {self.get_user_name(user)} to {resource.name}: 0 → {self.access_level}')
                if self.commit:
                    resource.members.create(
                        {'user_id': user_id, 'access_level': self.access_level})
                self.__change('add_user', resource, user=user, access_level=self.access_level)

    def check_push_access(self, project):
        branch = project.default_branch

        def protect():
            payload = {'name': branch, 'push_access_level': self.access_level,
                       'merge_access_level': self.access_level, 'allow_force_push': False}
            print(
                f'Setting branch permissions for {project.name} to {self.access_level}')
            if self.commit:
                project.protectedbranches.create(payload)
            self.__change('protect_branch', project, branch=branch, access_level=self.access_level)

        try:
            prot = project.protectedbranches.get(project.default_branch)
            if all([lvl['access_level'] != self.access_level for lvl in prot.push_access_levels]) \
                    or all([lvl['access_level'] != self.access_level for lvl in prot.merge_access_levels]):
                if self.commit:
                    prot.delete()
                protect()
        except GitlabGetError:
            protect()

    def __change(self, what:str, object:Project|User|Group, **changes):
        change = {what:object}
        change.update(changes)
        self.changelog.append(change)

    def __failed(self, e:GitlabError, subject=None):
        self._last_error = e
        self.__change('failed', subject, error_message=e.error_message, response_code=e.response_code, response_body=e.response_body)
        self.errors.append((e.error_message, subject, e))

    def check_pushes(self,  user: User | CurrentUser | str | int, count_commits=False, override_project_username = None):
        try:
            user = self.get_user(user)
            proj =  self.__check_user_project(user, details = False,override_project_username=override_project_username)
            fetches = proj.additionalstatistics.get().fetches['total']

            events = proj.events.list(action='pushed',iterator=True)
            if count_commits:
                commits = 0
                for event in events:
                    if event.author_id == user.id:
                        commits = commits + event.push_data['commit_count']
                if commits > 0:
                    print(f'pushed:  {user.name} ({commits} commits, {fetches} fetches)')
                    return proj
                else:
                    print(f'no_push: {user.name} ({commits} commits, {fetches} fetches)')
            else:
                for event in events:
                    if event.author_id == user.id:
                        print(f'pushed:  {user.name} ({fetches} fetches)')
                        return proj
                print(f'no_push: {user.name} ({fetches} fetches)')
        except gitlab.GitlabError as e:
            self.__failed(e, user)

    def make_merge_request(self,  user: User | CurrentUser | str | int, title = 'Updates/fixes', labels=['upstream'], details = False, override_project_username = None):
        try:
            user = self.get_user(user)
            proj =  self.__check_user_project(user, details,override_project_username)
            req = {'source_branch': self.assignment.default_branch,
                   'target_branch': proj.default_branch,
                    'title': title,
                    'target_project_id': proj.id,
                    'labels':labels,
                    'assignee_id': user.id
                }
            if self.commit:
                mr = self.assignment.mergerequests.create(req)
                self.__change('merge_request',proj, source=self.assignment, result=mr.web_url)
                print(mr.references['full'], '– created:', mr.web_url)
                time.sleep(2)
            return proj
        except gitlab.GitlabError as e:
            if proj and e.response_code == 409:
                print(proj.path_with_namespace, '– merge request already exists')
                return proj
            else:
                self.__failed(e, user)

    def get_merge_requests(self, state = 'opened', has_conflicts:bool = None):
        if self.group:
            mreqs = self.group.mergerequests.list(source_branch=self.assignment.default_branch, source_project_id=self.assignment.id, state=state, view='simple', iterator=True)
            mreqs = [self.gl.projects.get(mr.project_id).mergerequests.get(mr.iid) for mr in mreqs]
        else:
            forks = [self.gl.projects.get(f.id) for f in self.assignment.forks.list(iterator=True)]
            mreqs = []
            for fork in forks:
                mreqs.extend(fork.mergerequests.list(source_branch=self.assignment.default_branch, source_project_id=self.assignment.id, state=state, iterator=True))

        if has_conflicts != None:
            mreqs = [mr for mr in mreqs if mr.has_conflicts == has_conflicts]
        return mreqs
    
    def check_variables(self, project: Project):
        vars = self.variables.copy()
        changes = {}
        for var in project.variables.list(iterator=True):
            if var.key in vars:
                if var.value != vars[var.key]:
                    var.value = vars[var.key]
                    if self.commit:
                        var.save()
                    changes[var.key] = var.value
                del vars[var.key]
            if len(vars) == 0:
                break
        for key in vars:
            if self.commit:
                project.variables.create({'key': key, 'value': vars[key]})
            changes[key] = vars[key]
        if len(changes) > 0:
            self.__change('variables', project, **changes)

    def check_badges(self, project: Project):
        for badge in project.badges.list(iterator=True):
            if badge.image_url == STATUS_BADGE_IMAGE_URL:
                if badge.link_url != STATUS_BADGE_LINK_URL:
                    badge.link_url = STATUS_BADGE_LINK_URL
                    if self.commit:
                        badge.save()
                    self.__change('set_badge_link', project)
                return
        project.badges.create(
            {'image_url': STATUS_BADGE_IMAGE_URL, 'link_url': STATUS_BADGE_LINK_URL})
        self.__change('add_badge', project)

    def check_project_setup(self, user: User | CurrentUser, project: Project, config: dict):
        for key in config:
            if getattr(project, key) != config[key]:
                setattr(project, key, config[key])
                self.__change('set_attr', project, **{key: config[key]})

        if self.commit and project._get_updated_data() != None:
            project.save()

        if project.id != self.assignment.id \
                and not (hasattr(project, 'forked_from_project') or project.forked_from_project['id'] != self.assignment.id):
            logger.info(
                f'Updating fork relationship: {project.name} ← {self.assignment.name}')
            if self.commit:
                project.create_fork_relation(self.assignment.id)
            self.__change('set_fork', project, source=self.assignment)

        self.check_push_access(project)
        self.check_variables(project)
        self.check_badges(project)

        if user != None:
            self.check_membership(project, user)

    def check_assignment(self):
        try:
            self.check_project_setup(
                None, self.assignment, self.gitlab_config.copy())
        except gitlab.GitlabError as e:
            self.__failed(e, self.assignment)

    def check_user_project(self, user: User | CurrentUser | str | int, details = False, override_project_username = None):
        try:
            return self.__check_user_project(self.get_user(user), details,override_project_username)
        except gitlab.GitlabError as e:
            self.__failed(e, user)

    def __check_user_project(self, user: User | CurrentUser, details:bool, override_project_username:str|None):
        config = self.gitlab_config.copy()

        try:
            config['name'] = f'{user.username} – {self.assignment.name}'
            project_slug = f'{override_project_username or user.username}_{self.assignment.path}'
            self._last_user = user
            self._last_project = project = self.gl.projects.get(
                f'{self.namespace["full_path"]}/{project_slug}')
            logger.debug('Found project %s for user %s', project.path_with_namespace, user.username)
        except GitlabGetError:
            details = True
            url = self.assignment.ssh_url_to_repo.replace(
                f'/{self.assignment.path}.git', f'/{project_slug}.git')
            desc = self.assignment.description
            desc = re.sub(r'\r?\n\r?\n.*$', '', desc, re.DOTALL)
            if desc != '' and not desc.isspace():
                desc = desc + '\n\n'
            logger.info(
                f'Creating fork of {self.assignment.name} for {user.username}: {self.namespace["full_path"]}/{project_slug}')
            if self.commit:
                self._last_fork = self.assignment.forks.create({
                    'namespace_id': self.namespace['id'],
                    'path': project_slug,
                    'name': config['name'],
                    'visibility': config['visibility'],
                    'description': f'{desc}{self.assignment.name} for {user.name}\n\n*Clone →* `git clone {url} {self.assignment.path}`'
                })
                time.sleep(1)
            if self.commit:
                self._last_project = project = self.gl.projects.get(self._last_fork.id)
            else:
                project = None
            self.__change('add_fork', project,source=self.assignment)
        if project != None and details:
            self.check_project_setup(user, project, config)
        return project

    def get_user(self, user: User | CurrentUser | str | int) -> User | CurrentUser:
        if isinstance(user, int):
            user = self.gl.users.get(user)
        elif isinstance(user, str):
            user, = self.gl.users.list(username=user)
        return user

    def get_user_name(self, user: User | CurrentUser | str | int) -> str:
        if isinstance(user, int):
            return str(user)
        elif isinstance(user, User) or isinstance(user, CurrentUser):
            return user.username
        return user

    def get_project(self, project: Project | str | int) -> Project:
        if isinstance(project, int) or isinstance(project, str):
            project = self.gl.projects.get(project)
        if isinstance(project, Project):
            return project
        else:
            raise ValueError(f"Not a project: {project}")


if __name__ == '__main__':
    args = sys.argv[1:]
    file = None
    assignment = None
    details = False
    merge = False
    check_push = False
    skip = 0
    while len(args) > 0:
        if args[0] == '-f':
            file = args[1]
            print('Students file:', file)
            args = args[2:]
        elif args[0] == '-a':
            assignment = args[1]
            print('Assignment:', assignment)
            args = args[2:]
        elif args[0] == '-d':
            print('Details enabled!')
            details = True
            args = args[1:]
        elif args[0] == '-s':
            skip = int(args[1])
            print('Skipping', skip)
            args = args[2:]
        elif args[0] == '-m':
            merge = True
            print('Making merge requests')
            args = args[1:]
        elif args[0] == '-P':
            check_push = True
            print('Checking pushes')
            args = args[1:]
        else:
            raise ValueError(args[0])

    projects : list[tuple[str, Project|None]] = []
    if file == None:
        print("Missing input file")
    elif assignment == None:
        print("Missing assignment")
    else:
        assignment = AssignmentFork(assignment)
        print(assignment.assignment.name_with_namespace)
        try:
            with open('students.csv', 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                n = 0
                for row in reader:
                    if row['gitid'].isdigit():
                        if n >= skip:
                            if merge:
                                proj = assignment.make_merge_request(int(row['gitid']), details, row.get('gitoverride'))
                            elif check_push:
                                proj = assignment.check_pushes(int(row['gitid']), count_commits=True, override_project_username=row.get('gitoverride'))
                            else:
                                proj = assignment.check_user_project(int(row['gitid']), details, row.get('gitoverride'))
                            projects.append((row.get('gitoverride') or row['gituser'], proj))
                            if details:
                                time.sleep(1)
                            else:
                                time.sleep(0.01)
                    n = n + 1
                with open('project-links.txt', 'w') as f:
                    for u,p in projects:
                        if p:
                            f.write(f'{u} {p.ssh_url_to_repo}\n')
        finally:
            with open('changes.txt', 'w') as f:
                f.write(pformat(assignment.changelog, sort_dicts=False))
            with open('errors.txt', 'w') as f:
                f.write(pformat(assignment.errors, sort_dicts=False))

