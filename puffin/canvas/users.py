#! /usr/bin/python3

import csv
import json
import os
from flask import Flask, current_app
import requests
import re
import logging

from slugify import slugify
logger = logging.getLogger(__name__)
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
   
    def post(self, endpoint, params={}, headers={}, ignore_fail=False):
        headers['Authorization'] = f'Bearer {self.token}'

        req = requests.post(f'{self.base_url}{endpoint}', json=params, headers=headers)
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
        params = {'include[]' : ['email','avatar_url','enrollments','locale','effective_locale','test_student'],
                'per_page' : '200'}
        return self.get_paginated(f'courses/{course}/users', params)


    def get_sections_raw(self, course):
        params = {'include[]' : ['students'],
                'per_page' : '200'}
        return self.get_paginated(f'courses/{course}/sections', params)


    def get_peer_reviews(self, course, assignment):
        return self.get_paginated(f'courses/{course}/assignments/{assignment}/peer_reviews')
 
    def get_submissions(self, course, assignment):
        return self.get_paginated(f'courses/{course}/assignments/{assignment}/submissions')
    
    def get_course(self, course):
        return self.get_single(f'courses/{course}/')
    
    def clean_course(self, course):
        if not course:
             return None
        result = {}
        if course['root_account_id'] and course['enrollment_term_id']:
            term = self.get_term(
                course['root_account_id'], course['enrollment_term_id'], ignore_fail=True)
            if term:
                course['start_at'] = course['start_at'] or term['start_at']
                course['end_at'] = course['end_at'] or term['end_at']
                result['term'] = term['name']
                result['term_slug'] = term['term_slug']
        if result['term_slug']:
             result['slug'] = f"{course['course_code'].lower()}-{term['term_slug']}"
        for k in ['id', 'course_code', 'name', 'workflow_state', 'start_at', 'end_at', 'locale','sis_course_id','time_zone' ]:
            if k in course:
                result[k] = course[k]
        if len(course['enrollments']) > 0 and course['enrollments'][0]['type'] != 'teacher':
            return None
        return result
    
    def get_term(self, root, term_id, ignore_fail=False):
        result = self.terms.get((root, term_id))
        if not result:
            result = self.get_single(f'accounts/{root}/terms/{term_id}', ignore_fail=ignore_fail)
            mo = re.match(r'^(\w).*(\d\d)$', result.get('name',''))
            if mo:
                result['term_slug'] = f'{mo.group(2)}{mo.group(1).lower()}'
            else:
                result['term_slug'] = slugify(result['name'])
            self.terms[(root,term_id)] = result
        return result

    def get_users(self, course):
        jsonUsers = self.get_users_raw(course)
        users = []
        
        for u in jsonUsers:
                role = ""
                specific_role = ""
                enrollments = u.get('enrollments', [])
                print('\n')
                print(u['name'])
                for e in enrollments:
                        print(" * ", e['enrollment_state'], e['type'], e['role'])
                        if e['type'] == "StudentEnrollment" and role in [""]:
                                role = "student"
                                specific_role = e['role']
                        elif e['type'] == "TaEnrollment" and role in ["", "student"]:
                                role = "ta"
                                specific_role = e['role']
                        elif e['type'] == "TeacherEnrollment" and role in ["", "ta", "student"]:
                                role = "teacher"
                                specific_role = e['role']
                        elif e['type'] == "Administrasjon" and role in ["", "ta", "student"]:
                                role = "admin"
                                specific_role = e['role']
                        
                if role != "":
                    if role.startswith('Admin'):
                         role = 'admin'
                    u['role'] = role
                    u['canvas_role'] = specific_role or role
                    print('→', role, specific_role)        
                    users.append(u)
        #try:
        fields = 'sortable_name,name,login_id,email,id,avatar_url,role,canvas_role'.split(',')
        with open(os.path.join(current_app.config['APP_PATH'], 'last_canvas_sync.csv'), 'w') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(users)
        #except:
        #     pass
                  
        return users

