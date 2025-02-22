import logging
from typing import Any

from flask import Flask, current_app
from sqlalchemy import select

from puffin.util.apicalls import ApiConnection



logger = logging.getLogger(__name__)



class SonarConnection(ApiConnection):

    def __init__(
        self, app_or_base_url: Flask | str | None = None, token: str | None = None
    ):
        if isinstance(app_or_base_url, Flask):
            app = app_or_base_url
            app.extensions["puffin_sonarqube_connection"] = self
            base_url = None
        else:
            app = current_app
            base_url = app_or_base_url
        if app:
            base_url = base_url or app.config.get("SONARQUBE_BASE_URL")
            token = token or app.config.get("SONARQUBE_SECRET_TOKEN")

        super().__init__(base_url or '', token or '')

        self.__groups : dict[str,Any] = {}
        self.__users = {}
        self.__projects = {}



    def load_groups(self):
        gs : list[dict[str,Any]] = self.get_single('api/v2/authorizations/groups', {}).get('groups', [])
        for g in gs:
            self.__groups[g['name']] = g
        return gs
    
    def load_projects(self):
        # TODO: use pagination
        ps : list[dict[str,Any]] = self.get_single('api/v2/dop-translation/project-bindings', {}).get('projectBindings', [])
        for p in ps:
            self.__projects[p['projectKey']] = p
        return ps


    def group(self, name:str):
        if len(self.__groups) == 0:
            self.load_groups()
        
        return self.__groups.get(name)
    
    def get_or_create_group(self, name:str, desc:str = ""):
        grp = self.group(name)

        if grp == None:
            grp = self.post('api/v2/authorizations/groups', {'name':name, 'desc':desc})
            self.__groups[name] = grp

        return grp




