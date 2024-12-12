from collections import UserDict
from flask import current_app
from typing import Any, Iterable, Self, Annotated
import csv
import os
from flask import Flask, current_app
import logging

from slugify import slugify

logger = logging.getLogger(__name__)
from puffin.canvas.assignments import CanvasAssignment

from .lib import *



class CanvasCourse(CanvasObject):

    def clean(self):
        result = {}
        if self.root_account_id and self["enrollment_term_id"]:
            term = self.conn.maybe_get_term(
                self["root_account_id"], self["enrollment_term_id"]
            )
            if term:
                self["start_at"] = self["start_at"] or term["start_at"]
                self["end_at"] = self["end_at"] or term["end_at"]
                result["term"] = term["name"]
                result["term_slug"] = term["term_slug"]
                if result["term_slug"]:
                    result["slug"] = (
                        f"{self['course_code'].lower()}-{term['term_slug']}"
                    )
        for k in [
            "id",
            "course_code",
            "name",
            "workflow_state",
            "start_at",
            "end_at",
            "locale",
            "sis_course_id",
            "time_zone",
        ]:
            if k in self.data:
                result[k] = self.data[k]
        result['canvas_id'] = result['id']
        if len(self["enrollments"]) > 0 and self["enrollments"][0]["type"] != "teacher":
            return {}
        return result

    @staticmethod
    def get_user_courses(conn: CanvasConnection, userid="self", enrollment=None):
        params = {}
        if enrollment:
            params = {'enrollment_type':enrollment}
        return [
            CanvasCourse(conn, c) for c in conn.get_paginated(f"users/{userid}/courses", params)
        ]

    @staticmethod
    def get_profile(conn: CanvasConnection, userid):
        return conn.get_single(f"users/{userid}/profile")

    def get_users_raw(self):
        params = {
            "include[]": [
                "email",
                "avatar_url",
                "enrollments",
                "locale",
                "effective_locale",
                "test_student",
                "login_id"
            ],
            "per_page": "200",
        }
        return self.conn.get_paginated(f"courses/{self.id}/users", params)

    def get_sections_raw(self):
        params = {"include[]": ["students"], "per_page": "200"}
        return self.conn.get_paginated(f"courses/{self.id}/sections", params)

    def get_peer_reviews(self, assignment_id):
        return self.conn.get_paginated(
            f"courses/{self.id}/assignments/{assignment_id}/peer_reviews"
        )

    def get_submissions(self, assignment_id):
        return self.conn.get_paginated(
            f"courses/{self.id}/assignments/{assignment_id}/submissions"
        )

    def get_users(self):
        jsonUsers = self.get_users_raw()
        users = []

        for u in jsonUsers:
            role = ""
            specific_role = ""
            enrollments = u.get("enrollments", [])
            print("\n")
            print(u["name"], u.get('login_id'))
            for e in enrollments:
                print(" * ", e["enrollment_state"], e["type"], e["role"])
                if e["type"] == "StudentEnrollment" and role in [""]:
                    role = "student"
                    specific_role = e["role"]
                elif e["type"] == "TaEnrollment" and role in ["", "student"]:
                    role = "ta"
                    specific_role = e["role"]
                elif e["type"] == "TeacherEnrollment" and role in ["", "ta", "student"]:
                    role = "teacher"
                    specific_role = e["role"]
                elif e["type"] == "Administrasjon" and role in ["", "ta", "student"]:
                    role = "admin"
                    specific_role = e["role"]

            if role != "":
                if role.startswith("Admin"):
                    role = "admin"
                u["role"] = role
                u["canvas_role"] = specific_role or role
                print("→", role, specific_role)
                users.append(u)
        try:
            fields = "sortable_name,name,login_id,email,id,avatar_url,role,canvas_role".split(
                ","
            )
            with open(
                os.path.join(current_app.config["APP_PATH"], "last_canvas_sync.csv"),
                "w",
            ) as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(users)
        except:
            pass

        return users

    def get_group_categories(self):
        result = self.conn.get_paginated(f"courses/{self.id}/group_categories")
        return [CanvasGroupCategory(self.conn, data) for data in result]

    def get_group_categories_by_name(self):
        result = self.conn.get_paginated(f"courses/{self.id}/group_categories")
        return {data["name"]: CanvasGroupCategory(self.conn, data) for data in result}


    def get_assignment_submissions(self, assignment_id):
        return [CanvasAssignment(self.conn, data) for data in self.conn.get_paginated(f'courses/{self.id}/assignments/{assignment_id}/submissions',{'include':['group','submission_comments'], 'grouped': True})]
    
    def get_assignment(self, assignment_id):
        return CanvasAssignment(self.conn, {'course_id':self.id, 'id':assignment_id})
    
    def grade_assignment_submission(self, assignment_id, user_id, posted_grade, text_comment = None, sticker = None):
        params = {'submission': {'posted_grade':posted_grade}}
        if text_comment != None:
            params['text_comment'] = {'text_comment' : text_comment, 'group_comment' : True}
        if sticker != None:
            params['submission']['sticker'] = sticker
        return self.conn.request('PUT', f'courses/{self.id}/assignments/{assignment_id}/submissions/{user_id}',params)
    
class CanvasGroup(CanvasCreatableObject):
    __create_path__ = "group_categories/{group_category_id}/groups"
    __get_path__ = "groups/{id}"
    name: Required[str]
    description: str
    group_category_id: Required[int]
    is_public: bool = False
    join_level: GroupJoinLevels = GroupJoinLevels.invitation_only
    avatar_id: int

    course_id: ReadOnly[int]  # set by canvas from category
    context_type: ReadOnly[str]  # set by canvas from category

    def add_member(self, user_id: int | Iterable[int], moderator=False):
        if isinstance(user_id, int):
            return self.conn.post(f"groups/{self.id}/memberships", {"user_id": user_id})
        else:
            return [self.add_member(i) for i in user_id]

    def remove_member(self, user_id: int | Iterable[int]):
        if isinstance(user_id, int):
            return self.conn.request("DELETE", f"groups/{self.id}/users/{user_id}")
        else:
            return [self.remove_member(i) for i in user_id]

    def members(self):
        return self.conn.get_paginated(f"groups/{self.id}/memberships")

    def set_members(self, members: list[int]):
        return self.conn.request("PUT", f"groups/{self.id}", {"members":members})


class CanvasGroupCategory(CanvasCreatableObject):
    __create_path__ = "courses/{course_id}/group_categories"
    __get_path__ = "group_categories/{id}"
    name: Required[str]
    role: str | None  # 'communities', 'student_organized', 'imported'
    self_signup: str | None
    auto_leader: str | None
    context_type: ReadOnly[str] = "Course"
    course_id: ReadOnly[int]
    group_limit: int | None
    # sis_group_category_id : int | None
    # sis_import_id : int | None

    def get_groups(self):
        result = self.conn.get_paginated(f"group_categories/{self.id}/groups")
        return [CanvasGroup(self.conn, data) for data in result]

    def get_groups_by_name(self):
        result = self.conn.get_paginated(f"group_categories/{self.id}/groups")
        return {data["name"]: CanvasGroup(self.conn, data) for data in result}



# groups = db.execute(select(Group).where(Group.kind == 'team', Group.course_id == 1807)).scalars().all()
# canvas_groups = category.get_groups_by_name()
