#! /usr/bin/python3

from flask import Flask, current_app
import requests
import re
import logging

from slugify import slugify
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
from puffin.app.errors import ErrorResponse

class CanvasConnection:

    def __init__(self, app_or_base_url:str = None, token:str = None):
        if isinstance(app_or_base_url, Flask):
            app = app_or_base_url
            app.extensions['puffin_canvas_connection'] = self
            base_url = None
        else:
            app = current_app
            base_url = app_or_base_url
        if app:
            base_url = base_url or app.config.get('CANVAS_BASE_URL')
            token = token or app.config.get('CANVAS_SECRET_TOKEN')
        self.token = token
        self.base_url = base_url
        self.terms = {}

    def get_single(self, endpoint, params={}, headers={}, ignore_fail=False):
        headers['Authorization'] = f'Bearer {self.token}'

        req = requests.get(f'{self.base_url}{endpoint}', params=params, headers=headers)
        if req.ok:
            return req.json()
        elif ignore_fail:
            return None
        else:
            logger.error(f'Request failed: {self.base_url}{endpoint} {req.status_code} {req.reason}')
            raise ErrorResponse(f'Request failed: {req.reason}', endpoint, status_code=req.status_code)

    def get_paginated(self, endpoint, params={}, headers={}, ignore_fail=False):
        headers['Authorization'] = f'Bearer {self.token}'
        results = []
        endpoint = f'{self.base_url}{endpoint}'
        while endpoint != None:
            req = requests.get(endpoint, params=params, headers=headers)
            if req.ok:
                results = results + req.json()
                if 'next' in req.links:
                        endpoint = req.links['next']['url']
                else:
                        endpoint = None
                params = None
            elif ignore_fail:
                return None
            else:
                logger.error(f'Request failed: {endpoint} {req.status_code} {req.reason}')
                raise ErrorResponse(f'Request failed: {req.reason}', endpoint, status_code=req.status_code)
        return results

    def get_user_courses(self, userid='self'):
        return self.get_paginated(f'users/{userid}/courses')

    def get_profile(self, userid):
        return self.get_single(f'users/{userid}/profile')

    def get_users_raw(self, course):
        params = {'include[]' : ['email','avatar_url','enrollments','locale','effective_locale'],
                'per_page' : '200'}
        return self.get_paginated(f'courses/{course}/users', params)


    def get_sections_raw(self, course):
        params = {'include[]' : ['students'],
                'per_page' : '200'}
        return self.get_paginated(f'courses/{course}/sections', params)


    def get_course(self, course):
        return self.get_single(f'courses/{course}/')

    def get_term(self, root, term_id, ignore_fail=False):
        result = self.terms.get((root, term_id))
        if not result:
            result = self.get_single(f'accounts/{root}/terms/{term_id}', ignore_fail=ignore_fail)
            mo = re.match(r'^(\w).*(\d\d)$', result.get('name',''))
            if mo:
                result['term_slug'] = f'{mo.group(1).lower()}{mo.group(2)}'
            else:
                result['term_slug'] = slugify(result['name'])
            self.terms[(root,term_id)] = result
        return result

    def get_users(self, course):
        jsonUsers = self.get_users_raw(course)
        users = []
        
        for u in jsonUsers:
                kind = ""
                enrollments = u.get('enrollments', [])
                #print()
                #print(user)
                for e in enrollments:
                        #print(" * ", e)
                        u['role'] = e.get('role', e.get('kind', ""))
                        if e['type'] == "StudentEnrollment" and kind in [""]:
                                kind = "student"
                        elif e['type'] == "TaEnrollment" and kind in ["", "student"]:
                                kind = "ta"
                        elif e['type'] == "TeacherEnrollment" and kind in ["", "student"]:
                                kind = "teacher"
        
                if kind != "":
                        u['kind'] = kind
                        users.append(u)
        return users
