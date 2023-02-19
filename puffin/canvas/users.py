#! /usr/bin/python3

import requests
import csv
import sys

class CanvasConnection:

    def __init__(self, base_url, token):
        self.token = token
        self.base_url = base_url

    def get_single(self, endpoint, params={}, headers={}):
        headers['Authorization'] = f'Bearer {self.token}'

        req = requests.get(f'{self.base_url}{endpoint}', params=params, headers=headers)
        if req.ok:
            return req.json()

    def get_paginated(self, endpoint, params={}, headers={}):
        headers['Authorization'] = f'Bearer {self.token}'
        results = []
        while url != None:
            req = requests.get(f'{self.base_url}{endpoint}', params=params, headers=headers)
            if req.ok:
                results = results + req.json()
                if 'next' in req.links:
                        url = req.links['next']['url']
                else:
                        url = None
                params = None
        return results


    def get_profile(self, userid):
        return self.get_single(f'users/{userid}/profile')

    def get_users_raw(self, course):
        params = {'include[]' : ['email','avatar_url','enrollments'],
                'per_page' : '200'}
        return self.get_paginated(f'course/{course}/users', params)


    def get_sections_raw(self, course):
        params = {'include[]' : ['students'],
                'per_page' : '200'}
        return self.get_paginated(f'course/{course}/sections', params)


    def get_users(self, course):
        jsonUsers = self.get_users_raw(course)
        users = []
        
        for u in jsonUsers:
                user = {}
                for k in ['sortable_name', 'name', 'login_id', 'email', 'id', 'avatar_url']:
                        if k in u:
                                user[k] = u[k]
                        else:
                                user[k] = ""
                if False:
                    for k in u:
                        user[k] = u[k]
                kind = ""
                enrollments = u.get('enrollments', [])
                #print()
                #print(user)
                for e in enrollments:
                        #print(" * ", e)
                        user['role'] = e.get('role', e.get('kind', ""))
                        if e['type'] == "StudentEnrollment" and kind in [""]:
                                kind = "student"
                        elif e['type'] == "TaEnrollment" and kind in ["", "student"]:
                                kind = "ta"
                        elif e['type'] == "TeacherEnrollment" and kind in ["", "student"]:
                                kind = "teacher"
        
                if kind != "":
                        user['kind'] = kind
                        users.append(user)
        return users
