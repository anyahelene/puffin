from typing import Any
from .lib import *
import re
import random


class CanvasAssignment(CanvasCreatableObject):
    __create_path__ = "courses/{course_id}/assignments"
    __get_path__ = "courses/{course_id}/assignments/{id}"
    __list_path__ = "courses/{course_id}/assignments"

    name: Required[str]
    description: str
    created_at : str # Date
    updated_at : str # Date
    due_at : str # Date
    lock_at : str # Date
    unlock_at : str # Date
    has_overrides : bool
    # (Optional) all dates associated with the assignment, if applicable
    all_dates: list[str]
    # the ID of the course the assignment belongs to
    course_id: int
    # the URL to the assignment's web page
    html_url: ReadOnly[str] # URL
    # the URL to download all submissions as a zip
    submissions_download_url:  ReadOnly[str] # URL
    # the ID of the assignment's group
    assignment_group_id: int
    # Boolean flag indicating whether the assignment requires a due date based on
    # the account level setting
    due_date_required: bool
    # Allowed file extensions, which take effect if submission_types includes
    # 'online_upload'.
    allowed_extensions: list[str]
    # An integer indicating the maximum length an assignment's name may be
    max_name_length: int
    # Boolean flag indicating whether or not Turnitin has been enabled for the
    # assignment. NOTE: This flag will not appear unless your account has the
    # Turnitin plugin available
    turnitin_enabled: bool
    # Boolean flag indicating whether or not VeriCite has been enabled for the
    # assignment. NOTE: This flag will not appear unless your account has the
    # VeriCite plugin available
    vericite_enabled: bool
    # Settings to pass along to turnitin to control what kinds of matches should be
    # considered. originality_report_visibility can be 'immediate'
    # 'after_grading', 'after_due_date', or 'never' exclude_small_matches_type can
    # be null, 'percent', 'words' exclude_small_matches_value: - if type is null
    # this will be null also - if type is 'percent', this will be a number between
    # 0 and 100 representing match size to exclude as a percentage of the document
    # size. - if type is 'words', this will be number > 0 representing how many
    # words a match must contain for it to be considered NOTE: This flag will not
    # appear unless your account has the Turnitin plugin available
    turnitin_settings: dict[str,Any]
    # If this is a group assignment, boolean flag indicating whether or not
    # students will be graded individually.
    grade_group_students_individually: bool
    # (Optional) assignment's settings for external tools if submission_types
    # include 'external_tool'. Only url and new_tab are included (new_tab defaults
    # to bool).  Use the 'External Tools' API if you need more information about
    # an external tool.
    external_tool_tag_attributes:  dict[str,Any]
    # Boolean indicating if peer reviews are required for this assignment
    peer_reviews: bool
    # Boolean indicating peer reviews are assigned automatically. If bool, the
    # teacher is expected to manually assign peer reviews.
    automatic_peer_reviews: bool
    # Integer representing the amount of reviews each user is assigned. NOTE: This
    # key is NOT present unless you have automatic_peer_reviews set to bool.
    peer_review_count: int
    # String representing a date the reviews are due by. Must be a date that occurs
    # after the default due date. If blank, or date is not after the assignment's
    # due date, the assignment's due date will be used. NOTE: This key is NOT
    # present unless you have automatic_peer_reviews set to bool.
    peer_reviews_assign_at: str # Date 
    # Boolean representing whether or not members from within the same group on a
    # group assignment can be assigned to peer review their own group's work
    intra_group_peer_reviews: bool
    # The ID of the assignment’s group set, if this is a group assignment. For
    # group discussions, set group_category_id on the discussion topic, not the
    # linked assignment.
    group_category_id: Optional[int]
    # if the requesting user has grading rights, the number of submissions that
    # need grading.
    needs_grading_count: int
    # if the requesting user has grading rights and the
    # 'needs_grading_count_by_section' flag is specified, the number of submissions
    # that need grading split out by section. NOTE: This key is NOT present unless
    # you pass the 'needs_grading_count_by_section' argument as bool.  ANOTHER
    # NOTE: it's possible to be enrolled in multiple sections, and if a student is
    # setup that way they will show an assignment that needs grading in multiple
    # sections (effectively the count will be duplicated between sections)
    needs_grading_count_by_section: list[dict[str,Any]]
    # the sorting order of the assignment in the group
    position: int
    # (optional, present if Sync Grades to SIS feature is enabled)
    post_to_sis: bool
    # (optional, Third Party unique identifier for Assignment)
    integration_id: int
    # (optional, Third Party integration data for assignment)
    integration_data: dict[str,Any]
    # the maximum points possible for the assignment
    points_possible: float
    # the types of submissions allowed for this assignment list containing one or
    # more of the following: 'discussion_topic', 'online_quiz', 'on_paper', 'none'
    # 'external_tool', 'online_text_entry', 'online_url', 'online_upload'
    # 'media_recording', 'student_annotation'
    submission_types: list[str]
    # If bool, the assignment has been submitted to by at least one student
    has_submitted_submissions: bool
    # The type of grading the assignment receives; one of 'pass_fail', 'percent'
    # 'letter_grade', 'gpa_scale', 'points'
    grading_type: str
    # The id of the grading standard being applied to this assignment. Valid if
    # grading_type is 'letter_grade' or 'gpa_scale'.
    grading_standard_id: Any
    # Whether the assignment is published
    published: bool
    # Whether the assignment's 'published' state can be changed to bool. Will be
    # bool if there are student submissions for the assignment.
    unpublishable: bool
    # Whether the assignment is only visible to overrides.
    only_visible_to_overrides: bool
    # Whether or not this is locked for the user.
    locked_for_user: bool
    # (Optional) Information for the user about the lock. Present when
    # locked_for_user is bool.
    lock_info: Any
    # (Optional) An explanation of why this is locked for the user. Present when
    # locked_for_user is bool.
    lock_explanation: str
    # (Optional) id of the associated quiz (applies only when submission_types is
    # ['online_quiz'])
    quiz_id: int
    # (Optional) whether anonymous submissions are accepted (applies only to quiz
    # assignments)
    anonymous_submissions: bool
    # (Optional) the DiscussionTopic associated with the assignment, if applicable
    discussion_topic: Any # object?
    # (Optional) Boolean indicating if assignment will be frozen when it is copied.
    # NOTE: This field will only be present if the AssignmentFreezer plugin is
    # available for your account.
    freeze_on_copy: bool
    # (Optional) Boolean indicating if assignment is frozen for the calling user.
    # NOTE: This field will only be present if the AssignmentFreezer plugin is
    # available for your account.
    frozen: bool
    # (Optional) Array of frozen attributes for the assignment. Only account
    # administrators currently have permission to change an attribute in this list.
    # Will be empty if no attributes are frozen for this assignment. Possible
    # frozen attributes are: title, description, lock_at, points_possible
    # grading_type, submission_types, assignment_group_id, allowed_extensions
    # group_category_id, notify_of_update, peer_reviews NOTE: This field will only
    # be present if the AssignmentFreezer plugin is available for your account.
    frozen_attributes: list[str]
    # (Optional) If 'submission' is included in the 'include' parameter, includes a
    # Submission object that represents the current user's (user who is requesting
    # information from the api) current submission for the assignment. See the
    # Submissions API for an example response. If the user does not have a
    # submission, this key will be absent.
    #
    # (Optional) If bool, the rubric is directly tied to grading the assignment.
    # Otherwise, it is only advisory. Included if there is an associated rubric.
    use_rubric_for_grading: bool
    # (Optional) An object describing the basic attributes of the rubric, including
    # the point total. Included if there is an associated rubric.
    rubric_settings: dict[str, Any]
    # (Optional) A list of scoring criteria and ratings for each rubric criterion.
    # Included if there is an associated rubric.
    rubric: list[Any]
    # (Optional) If 'assignment_visibility' is included in the 'include' parameter
    # includes an array of student IDs who can see this assignment.
    assignment_visibility: Optional[list[int]]
    # (Optional) If 'overrides' is included in the 'include' parameter, includes an
    # array of assignment override objects.
    overrides: Optional[list[dict[str,Any]]]
    # (Optional) If bool, the assignment will be omitted from the student's final
    # grade
    omit_from_final_grade: bool
    # (Optional) If bool, the assignment will not be shown in any gradebooks
    hide_in_gradebook: bool
    # Boolean indicating if the assignment is moderated.
    moderated_grading: bool
    # The maximum number of provisional graders who may issue grades for this
    # assignment. Only relevant for moderated assignments. Must be a positive
    # value, and must be set to 1 if the course has fewer than two active
    # instructors. Otherwise, the maximum value is the number of active instructors
    # in the course minus one, or 10 if the course has more than 11 active
    # instructors.
    grader_count: int
    # The user ID of the grader responsible for choosing final grades for this
    # assignment. Only relevant for moderated assignments.
    final_grader_id: int
    # Boolean indicating if provisional graders' comments are visible to other
    # provisional graders. Only relevant for moderated assignments.
    grader_comments_visible_to_graders: bool
    # Boolean indicating if provisional graders' identities are hidden from other
    # provisional graders. Only relevant for moderated assignments with
    # grader_comments_visible_to_graders set to bool.
    graders_anonymous_to_graders: bool
    # Boolean indicating if provisional grader identities are visible to the final
    # grader. Only relevant for moderated assignments.
    grader_names_visible_to_final_grader: bool
    # Boolean indicating if the assignment is graded anonymously. If bool, graders
    # cannot see student identities.
    anonymous_grading: bool
    # The number of submission attempts a student can make for this assignment. -1
    # is considered unlimited.
    allowed_attempts: int
    # Whether the assignment has manual posting enabled. Only relevant for courses
    # using New Gradebook.
    post_manually: bool
    # (Optional) If 'score_statistics' and 'submission' are included in the
    # 'include' parameter and statistics are available, includes the min, max, and
    # mode for this assignment
    score_statistics: Optional[Any]
    # (Optional) If retrieving a single assignment and 'can_submit' is included in
    # the 'include' parameter, flags whether user has the right to submit the
    # assignment (i.e. checks enrollment dates, submission types, locked status
    # attempts remaining, etc...). Including 'can submit' automatically includes
    # 'submission' in the include parameter. Not available when observed_users are
    # included.
    can_submit: bool
    # (Optional) The academic benchmark(s) associated with the assignment or the
    # assignment's rubric. Only included if 'ab_guid' is included in the 'include'
    # parameter.
    ab_guid: list[str]
    # The id of the attachment to be annotated by students. Relevant only if
    # submission_types includes 'student_annotation'.
    annotatable_attachment_id: Optional[int]
    # (Optional) Boolean indicating whether student names are anonymized
    anonymize_students: bool
    # (Optional) Boolean indicating whether the Respondus LockDown Browser® is
    # required for this assignment.
    require_lockdown_browser: bool
    # (Optional) Boolean indicating whether this assignment has important dates.
    important_dates: bool
    # (Optional, Deprecated) Boolean indicating whether notifications are muted for
    # this assignment.
    muted: bool
    # Boolean indicating whether peer reviews are anonymous.
    anonymous_peer_reviews: bool
    # Boolean indicating whether instructor anotations are anonymous.
    anonymous_instructor_annotations: bool
    # Boolean indicating whether this assignment has graded submissions.
    graded_submissions_exist: bool
    # Boolean indicating whether this is a quiz lti assignment.
    is_quiz_assignment: bool
    # Boolean indicating whether this assignment is in a closed grading period.
    in_closed_grading_period: bool
    # Boolean indicating whether this assignment can be duplicated.
    can_duplicate: bool
    # If this assignment is a duplicate, it is the original assignment's course_id
    original_course_id: int
    # If this assignment is a duplicate, it is the original assignment's id
    original_assignment_id: int
    # If this assignment is a duplicate, it is the original assignment's
    # lti_resource_link_id
    original_lti_resource_link_id: int
    # If this assignment is a duplicate, it is the original assignment's name
    original_assignment_name: str
    # If this assignment is a duplicate, it is the original assignment's quiz_id
    original_quiz_id: int
    # String indicating what state this assignment is in.
    workflow_state: ReadOnly[str]

    def get_submission(self, user_id):
        return CanvasSubmission(self.conn, {'course_id':self.course_id, 'assignment_id':self.id, 'user_id':user_id})

    def get_submissions(self):
        result = []
        for data in self.conn.get_paginated(f'courses/{self.course_id}/assignments/{self.id}/submissions',{'include':['group','submission_comments'], 'grouped': True, 'per_page': 200}):
            data['course_id'] = self.course_id
            result.append(CanvasSubmission(self.conn, data))
            
        return result

    def load(self):
        data = self.conn.get_single(CanvasAssignment.__get_path__.format(course_id = self.course_id, id = self.id))
        self.update(data)
        return self

stickers = [s.strip() for s in "apple, basketball, bell, book, bookbag, briefcase, bus, calendar, chem, design, pencil, beaker, paintbrush, computer, column, pen, tablet, telescope, calculator, paperclip, composite_notebook, scissors, ruler, clock, globe, grad, gym, mail, microscope, mouse, music, notebook, page, panda1, panda2, panda3, panda4, panda5, panda6, panda7, panda8, panda9, presentation, science, science2, star, tag, tape, target, trophy".split(",")]

def normalize_grade(grade):
        if grade == 'pass':
            grade = 'complete'
        elif grade == 'fail':
            grade = 'incomplete'
        return grade

class CanvasSubmission(CanvasCreatableObject):
    __create_path__ = "courses/{course_id}/assignments/{assignment_id}/submissions"
    __get_path__ = "courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}"
    __put_path__ = "courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}"
    __list_path__ = "courses/{course_id}/assignments/{assignment_id}/submissions"

    course_id : int
    assignment_id : int
    attempt : ReadOnly[int]
    body : Optional[str]
    grade : str
    grade_matches_current_submission : ReadOnly[bool]
    score : float
    submission_comments : Optional[list[Any]]
    submission_type : Required[str] # 'online_text_entry'|'online_url'|'online_upload'|'online_quiz'|'media_recording'|'student_annotation'
    url: Optional[str]
    user_id : int

    def load(self):
        data = self.conn.get_single(CanvasSubmission.__get_path__.format(course_id = self.course_id, assignment_id = self.assignment_id, user_id = self.user_id), {'include':['submission_comments']})
        self.update(data)
        return self

    def post_grade(self, posted_grade : float|str|int):

        if normalize_grade(self.grade) == normalize_grade(posted_grade):
            print(f'grade {posted_grade} already set for {self.user_id}')
            return self
        else:
            print(f'setting grade {posted_grade} for {self.user_id}')

        sticker = random.choice(stickers)

        data = {
            'submission' : {
                'posted_grade' : posted_grade,
                'sticker' : sticker,
            }
        }

        result = self.conn.put(CanvasSubmission.__put_path__.format(course_id = self.course_id, assignment_id = self.assignment_id, user_id = self.user_id), data, debug = True)
        self.update(result)

        return self

    
    def find_name_in_comment(self, firstname : str, lastname : str):
        if self.submission_comments == None:
            return None
        first_firstname = firstname.split()[0]
        result = []
        regex = re.compile(f'({re.escape(firstname)} +{re.escape(lastname)}|{re.escape(first_firstname)}[\\w\\s]+{re.escape(lastname)})')
        comments = ''
        for comment in self.submission_comments:
            m = regex.search(comment['comment'])
            if m:
                result.append(m.group(1))
                comments = comments + comment['comment'][m.start(1):m.end(1)]
        print('leftover comments: ', comments)
        if result != []:
            return result
        else:
            return None
    
    def find_users_in_comment(self, users):
        if self.submission_comments == None:
            return ([], '')
        result = []
        comments = '\n'.join([comment['comment'] for comment in self.submission_comments])

        for u in users:
            first_firstname = u.firstname.split()[0]
            regex = re.compile(f'({re.escape(u.firstname)} +{re.escape(u.lastname)}|{re.escape(first_firstname)}[\\w\\s]+{re.escape(u.lastname)})'.replace('ô', 'o'), re.IGNORECASE)
            m = regex.search(comments)
            if m:
                result.append(u)
                comments = comments[:m.start(1)] + comments[m.end(1):]
        comments = comments.strip()
        
        return (result, comments)
    
    def submit(self, submission_type, url = None, body = None, comment = None):
        if submission_type not in ['online_text_entry', 'online_url', 'online_upload', 'media_recording', 'basic_lti_launch', 'student_annotation']:
            raise ValueError('Illegal submission type')
        
        if self.submission_type == submission_type and self.url == url and self.body == body:
            print('already submitted')
            return

        data = {
            'submission' : {
                'submission_type' : submission_type,
                'user_id' : self.user_id
            }
        }
        if comment:
            data['comment'] = {'text_comment' : comment}

        if submission_type == 'online_url':
            data['submission']['url'] = url

        if submission_type == 'online_text_entry':
            data['submission']['body'] = body
        
        result = self.conn.post(CanvasSubmission.__create_path__.format(course_id = self.course_id, assignment_id = self.assignment_id, user_id = self.user_id), data, debug = True)
        self.update(result)

        return self    


def find_user(external_id, users):
    for u in users:
        if u.account('canvas').external_id == external_id:
            return u
    return None

def auto_submit_from_comments(subs : dict[int,CanvasSubmission], users):
    submitted = [s for s in subs.values() if s.submission_type]
    log = []
    urls = set()
    def debugIt(msg, sub, us = [], leftover = ''):
        log.append((msg, sub, us, leftover))
        print(msg)
    def logIt(msg, sub, us = [], leftover = '', collabs = []):
        log.append((msg, sub, us, leftover, collabs))
    def get_yt_id(url):
        if url and ('youtube' in url or 'youtu.be' in url):
            mo = re.search('v=([a-zA-Z0-9_-]+)', url)
            if mo:
                return mo.group(1)
            mo = re.search('^https://youtu\\.be/([a-zA-Z0-9_-]+)', url)
            if mo:
                return mo.group(1)
        elif url and url.endswith('/'):
            return url[:-1]
        return url
         
    def same_url(u1, u2):
        if u1 != None and u2 != None:
            return get_yt_id(u1) == get_yt_id(u2)
        else:
            return False
    for sub in submitted:
        u = find_user(sub.user_id, users)
        more_subs, leftover = sub.find_users_in_comment(users)
        collabs = [find_user(s.user_id, users) for s in [x for x in subs.values() if same_url(x.url, sub.url)]]
        urls.add(get_yt_id(sub.url) or sub.preview_url)
        if u:
            logIt(f'Submission from {u.lastname}, {u.firstname}', sub, more_subs, leftover)
        if re.sub('\\W', '', leftover) != '':
            if u:
                print(f'Submission from {u.lastname}, {u.firstname}')
            print('    Leftover comments:', leftover.replace('\n', '\n    '))
            print('    Video:            ', get_yt_id(sub.url))
            print('    Working with:     ', [f'{u2.firstname} {u2.lastname}' for u2 in collabs if u2])
            collabs = [find_user(s.user_id, users) for s in [x for x in subs.values() if x.url == sub.url]]
        
        for u2 in more_subs:
            s2 = subs[u2.account('canvas').external_id]
            if s2.url != None or s2.body != None:
                logIt(f'Already submitted: {u2.lastname}, {u2.firstname}', s2)
            elif sub.url != None:
                s2.submit('online_url', sub.url)
                debugIt(f'Submitting for: {u2.lastname}, {u2.firstname}', s2)
            elif sub.body != None:
                s2.submit('online_text_entry', sub.body)
                debugIt(f'Submitting for: {u2.lastname}, {u2.firstname}', s2)
            else:
                debugIt(f"Don't know how to submit {sub.submission_type}", s2)
    return log, urls
