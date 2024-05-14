import datetime
import enum
from typing import Optional, Type
from typing_extensions import Annotated
from sqlalchemy import ForeignKey, ForeignKeyConstraint, UniqueConstraint, inspect, text, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column, Session
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.mutable import MutableDict
from datetime import datetime
from .database import Base
import logging

_logger = logging.getLogger(__name__)

###########################################################################################

_str_16 = Annotated[str, 16]
_str_30 = Annotated[str, 30]
ACCOUNT_PROVIDERS = {
    'canvas': {'primary': True, 'has_external_id': True},
    'gitlab': {'has_external_id': True},
    'discord': {}
}

ROLES = {
    'user': 'Identified by user_id',
    'peer': 'Anyone enrolled in the same course as current resource',
    'teacher': 'Anyone enrolled as ta, teacher or admin in the same course',
    'admin': 'Anyone enrolled as teacher or admin in the same course',
    'member': 'Anyone enrolled in current course/group'
}
PRIVILEGED_ROLES = ['ta','teacher','admin']
ROLE_ICONS = {'student': '🧑‍🎓', 'ta':'🧑‍💻', 'teacher': '🧑‍🏫', 'admin': '🧑‍💼', '': '🤷'}
ACCESS = {
    'read': 'Can read data unless secret',
    'write': 'Can write data if writable',
    'sync': 'Can \'write\' data synced from canvas / gitlab'
}


class LogType(enum.Enum):
    UPDATE = "UPDATE"
    INSERT = "INSERT"
    DELETE = "DELETE"


class JoinModel(enum.Enum):
    RESTRICTED = "Restricted – members of the parent group can join freely"
    OPEN = "Open – users can join/leave freely"
    AUTO = "Auto – users are automatically added to this group"
    CLOSED = "Closed – group owner must add users"
    REMOVED = "Removed – user was manually removed from group"


class AssignmentModel(enum.Enum):
    GITLAB_STUDENT_FORK = "Gitlab project forked to each student"
    GITLAB_GROUP_FORK = "Gitlab project forked to each student group"
    GITLAB_GROUP_PROJECT = "Gitlab project created by student group"
    GITLAB_STUDENT_PROJECT = "Gitlab project created by student"

class OwnerKind(enum.Enum):
    OWNER_KIND_COURSE = "course"
    OWNER_KIND_USER = "user"
    OWNER_KIND_GROUP = "group"

class AuditLog(Base):
    __tablename__ = 'audit_log'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    timestamp: Mapped[datetime] = mapped_column(
        server_default=text('CURRENT_TIMESTAMP'))
    table_name: Mapped[_str_30]
    row_id: Mapped[int]
    type: Mapped[LogType]
    old_data = mapped_column(JSON, nullable=True)
    new_data = mapped_column(JSON, nullable=True)

    def __repr__(self):
        if self.type == LogType.INSERT:
            return f"INSERT(table={self.table_name}, key={self.row_id}, data={self.new_data})"
        elif self.type == LogType.UPDATE:
            return f"UPDATE(table={self.table_name}, key={self.row_id}, data={self.new_data}, was={self.old_data})"
        elif self.type == LogType.DELETE:
            return f"DELETE(table={self.table_name}, key={self.row_id}, was={self.old_data})"
        return self.to_json()


class Id(Base):
    __tablename__ = 'id'
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[_str_30] = mapped_column(info={'immutable': True})


class Account(Base):
    __tablename__ = 'account'
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=False, doc="Internal account id",
        info={'view': {'course_user': False}})
    provider_name: Mapped[_str_16] = mapped_column(
        doc="Account provider",
        info={'view': {'course_user': False}})
    user_id: Mapped[int] = mapped_column(ForeignKey(
        "user.id"), doc="User this account is associated with",
        info={'view': {'course_user': False}, 'immutable': True})
    external_id: Mapped[Optional[int]] = mapped_column(unique=True,
                                                       doc="Provider's numeric user id (if any)")
    username: Mapped[str] = mapped_column(
        unique=True, doc="Provider's username for this account")
    expiry_date: Mapped[Optional[datetime]] = mapped_column(
        info={'view': {'course_user': False}})
    email: Mapped[Optional[str]] = mapped_column(
        info={'view': {'course_user': False}})
    fullname: Mapped[str] = mapped_column(
        info={'view': {'course_user': False}})
    note: Mapped[Optional[str]] = mapped_column(
        info={'view': {'course_user': False}})
    email_verified: Mapped[bool] = mapped_column(server_default=text('FALSE'))
    last_login: Mapped[Optional[datetime]] = mapped_column(
        info={'view': {'course_user': False}})
    avatar_url: Mapped[Optional[str]] = mapped_column(
        info={'view': {'course_user': False}})

    user = relationship("User", back_populates="accounts")

    info = {
        'access': {'read': ['user', 'teacher'], 'sync': ['user', 'teacher']}
    }

    @property
    def is_expired(self):
        return self.expiry_date != None and self.expiry_date > datetime.now()


class Course(Base):
    __tablename__ = 'course'
    id: Mapped[int] = \
        mapped_column(primary_key=True, autoincrement=False,
                      info={'view': {'course_user': False}})
    external_id: Mapped[int] = \
        mapped_column(unique=True,
                      info={'view': {'course_user': 'course_canvas_id'},
                            'immutable': True,
                            'form': 'canvas_course'})
    name: Mapped[str] = mapped_column(
        info={'view': {'course_user': 'course_name'}})
    slug: Mapped[str] = mapped_column(
        info={'view': {'course_user': 'course_slug'},
              'form': {'slugify': 'name'}})
    expiry_date: Mapped[Optional[datetime]] = mapped_column(
        info={'view': {'course_user': False}})
    json_data = mapped_column(MutableDict.as_mutable(JSON), server_default="{}", nullable=False,
                              info={'view': {'course_user': False, 'full_user': False}})

    info = {
        'access': {'read': 'member', 'write': 'admin', 'sync': ['teacher']},
        'data': {
            'gitlab_path': 'gitlab:path',
            'gitlab_student_path': 'gitlab:path',
            'course_code': 'str',
            'locale': 'locale',
            'sis_course_id': 'str',
            'time_zone': 'timezone'
        }
    }

    @property
    def is_expired(self):
        return self.expiry_date != None and self.expiry_date > datetime.now()


class Group(Base):
    __tablename__ = 'group'
    __table_args__ = (UniqueConstraint("course_id", "slug"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    kind: Mapped[str] = \
        mapped_column(info={'form': {'select': 'group_kind'}})
    course_id: Mapped[int] = mapped_column(
        ForeignKey("course.id"), info={'immutable': True})
    parent_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("group.id"))
    external_id: Mapped[Optional[str]] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(info={'access': {'write': 'member'}})
    slug: Mapped[str] = \
        mapped_column(info={'form': {'slugify': 'name'}, 'type':'group.slug'})
    join_model: Mapped[JoinModel] = mapped_column(default=JoinModel.RESTRICTED)
    join_source: Mapped[Optional[str]] = mapped_column(
        doc="E.g. gitlab(project_id)", default=None)
    json_data = mapped_column(MutableDict.as_mutable(JSON), server_default="{}", nullable=False)
    info = {
        'access': {'read': 'course:member', 'sync': 'member'},
        'public_json' : ['project_name','public_info']
    }

    course = relationship("Course")
    parent = relationship("Group")
    memberships = relationship("Membership")


class Membership(Base):
    __tablename__ = 'membership'
    __table_args__ = (UniqueConstraint("user_id", "group_id"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey('user.id'), info={'immutable': True,
                                     'access': {'read': 'peer'}})
    group_id: Mapped[int] = mapped_column(
        ForeignKey('group.id'), info={'immutable': True})
    role: Mapped[str] = mapped_column(info = {'icons': ROLE_ICONS})
    join_model: Mapped[JoinModel] = mapped_column(default=JoinModel.RESTRICTED)

    info = {
        'access': {'read': 'group:course:member'}
    }

    user = relationship("User", back_populates="memberships")
    group = relationship("Group", back_populates="memberships")


class Enrollment(Base):
    __tablename__ = 'enrollment'
    __table_args__ = (UniqueConstraint("user_id", "course_id"),
                      ForeignKeyConstraint(['user_id'], ['user.id']),
                      ForeignKeyConstraint(['course_id'], ['course.id'])
                      )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False, info={
                                    'view': {'course_user': False}})
    user_id: Mapped[int] = mapped_column(
        info={'view': {'course_user': False}, 'immutable': True,
              'access': {'read': 'peer'}}
    )
    course_id: Mapped[int] = mapped_column(info={'immutable': True})
    role: Mapped[str] = mapped_column(
        info={'icons': ROLE_ICONS,
              'access': {'write': 'admin', 'read': 'peer'}})

    info = {
        'access': {'read': 'course:member'}
    }

    user = relationship("User", back_populates="enrollments")
    course = relationship("Course")

class User(Base):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    key: Mapped[str] = mapped_column(
        unique=True, info={'hide': True, 'view': {'course_user': False}})
    lastname: Mapped[str]
    firstname: Mapped[str]
    email: Mapped[str]
    is_admin: Mapped[bool] = mapped_column(server_default=text('FALSE'),
                                           info={'hide':True, 'icons': {'true': '🧑‍💻', '': ' '}})
    locale: Mapped[Optional[_str_30]]
    expiry_date: Mapped[Optional[datetime]] = mapped_column(
        info={'view': {'course_user': False}})
    password: Mapped[Optional[str]] = mapped_column(info={'secret': True, })

    accounts = relationship("Account", back_populates="user")
    enrollments = relationship("Enrollment", back_populates="user")
    memberships = relationship("Membership")

    info = {
        'access': {'read': 'peer', 'write': 'user'}
    }

    @property
    def is_active(self) -> bool:
        return not self.is_expired

    @property
    def is_authenticated(self) -> bool:
        return not self.is_expired

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return str(self.id)

    @property
    def is_expired(self) -> bool:
        return self.expiry_date != None and self.expiry_date > datetime.now()

    def enrollment(self, course: Course | int | str) -> Enrollment | None:
        for en in self.enrollments:
            if en.course == course or en.course_id == course or en.course.name == course:
                return en
        return None

    def membership(self, course=None, kind=None) -> list[Membership]:
        ms = []
        for m in self.memberships:
            if (course == None or m.group.course == course or m.group.course_id == course or m.group.course.name == course) \
                    and (kind == None or m.group.kind == kind) and m.join_model != JoinModel.REMOVED:
                ms.append(m)
        return ms

    def is_member(self, group:Group|int|str) -> bool:
        """Returns true if user is a member of the group. Group can be a group object, a group_id or slug."""
        for m in self.memberships:
            if group in [m.group, m.group_id, m.group.slug]:
                return True        
        return False
    
    def account(self, provider: str) -> Account | None:
        for acc in self.accounts:
            if acc.provider_name == provider:
                return acc
        return None

    @property
    def avatar_url(self) -> str | None:
        for acc in self.accounts:
            if acc.avatar_url != None:
                return acc.avatar_url
        return None

    @property
    def roles(self) -> dict[int, str]:
        roles = {}
        for en in self.enrollments:
            roles[en.course_id] = en.role
        return roles


class Assignment(Base):
    __tablename__ = 'assignment'
    __table_args__ = (UniqueConstraint("slug", "course_id"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(info={'form': True})
    slug: Mapped[str] = mapped_column(info={'form': {'slugify': 'name'}})
    description: Mapped[Optional[str]] = mapped_column(
        info={'form': 'textarea'})
    category: Mapped[_str_30] = mapped_column(
        info={'form': {'select': 'category'}})
    course_id: Mapped[int] = mapped_column(ForeignKey('course.id'))
    assignment_model: Mapped[AssignmentModel] = mapped_column(
        info={'form': {'select': 'assignment_model'}})
    gitlab_id: Mapped[Optional[int]] = \
        mapped_column(info={'form': 'gitlab:project'},
                      doc='GitLab source project (with solution / all tests)')
    gitlab_root_id: Mapped[Optional[int]] = \
        mapped_column(info={'form': 'gitlab:root_project'},
                      doc='GitLab project to be forked to students')
    gitlab_test_id: Mapped[Optional[int]] = \
        mapped_column(info={'form': 'gitlab:test_project'},
                      doc='GitLab project with extra (non-student visible) tests')
    canvas_id: Mapped[Optional[str]] = \
        mapped_column(unique=True, info={'form': 'canvas:assignment'},
                      doc='Corresponding assignment in Canvas')
    release_date: Mapped[Optional[datetime]] = mapped_column(
        info={'form': {'default': 'datetime.now()'}},
        doc='When the assignment should be published')
    due_date: Mapped[Optional[datetime]] = \
        mapped_column(info={'form': True},
                      doc='Default due date')
    grade_by_date: Mapped[Optional[datetime]] = \
        mapped_column(info={'form': True},
                      doc='Date when grading is due')
    json_data = mapped_column(MutableDict.as_mutable(JSON), nullable=False, server_default='{}')

    info = {
        'access': {'read': 'course:member', 'write': 'course:teacher'}
    }


class Grader(Base):
    __tablename__ = 'grader'
    __table_args__ = (UniqueConstraint("grader_id", "student_assignment_id"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    grader_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    student_assignment_id: Mapped[int] = mapped_column(
        ForeignKey('student_assignment.id'))
    grade_by_date: Mapped[Optional[datetime]] = mapped_column()
    graded_date: Mapped[Optional[datetime]] = mapped_column()
    grade_points: Mapped[Optional[int]] = mapped_column()
    grade_report: Mapped[Optional[str]] = mapped_column()


class StudentAssignment(Base):
    __tablename__ = 'student_assignment'
    __table_args__ = (UniqueConstraint("user_id", "assignment_id"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    assignment_id: Mapped[int] = mapped_column(ForeignKey('assignment.id'))
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey('project.id'))
    canvas_id: Mapped[Optional[str]] = mapped_column(unique=True)
    due_date: Mapped[Optional[datetime]] = mapped_column()
    json_data = mapped_column(MutableDict.as_mutable(JSON), server_default="{}", nullable=False)

    info = {
        'access': {'read': ['user', 'course:teacher'], 'write': 'course:teacher', 'sync': ['user', 'course:teacher']}
    }


class Project(Base):
    __tablename__ = 'project'
    __table_args__ = (UniqueConstraint("slug", "namespace_slug"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(info={'form': True, 'sync': True})
    slug: Mapped[str] = \
        mapped_column(info={'form': {'slugify': 'name'}, 'sync': 'immutable'})
    namespace_slug: Mapped[str] = \
        mapped_column(info={'form': False, 'sync': 'immutable'})
    description: Mapped[Optional[str]] =\
        mapped_column(info={'form': 'textarea', 'sync': True})
    course_id: Mapped[int] = mapped_column(ForeignKey('course.id'))
    owner_id: Mapped[int] = mapped_column(doc="A user, group or course id")
    owner_kind: Mapped[_str_16]
    gitlab_id: Mapped[Optional[str]] = mapped_column(unique=True)
    submitted_ref: Mapped[Optional[str]] = mapped_column(
        doc="Identifies actual submission (a tag, branch or commit id)")
    json_data = mapped_column(MutableDict.as_mutable(JSON), server_default="{}", nullable=False)

    info = {
        'access': {'read': ['owner', 'course:teacher'],
                   'write': ['owner', 'course:teacher'],
                   'sync': ['owner', 'course:teacher']}
    }


class ProjectTestRun(Base):
    __tablename__ = 'project_test_run'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    project_id: Mapped[int] = mapped_column(ForeignKey('project.id'))
    timestamp: Mapped[datetime] = mapped_column(
        server_default=text('CURRENT_TIMESTAMP'))
    compile_passed: Mapped[bool]
    test_passed: Mapped[bool]
    result_points: Mapped[int]
    result_text: Mapped[Optional[str]]
    result_url: Mapped[Optional[str]]

    info = {
        'access': {'sync': ['project:owner', 'project:course:teacher']}
    }


class LastSync(Base):
    __tablename__ = 'last_sync'
    __table_args__ = (UniqueConstraint("obj_id", "obj_type"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    obj_id: Mapped[int]
    obj_type: Mapped[_str_30]
    sync_incoming: Mapped[Optional[datetime]]
    sync_outgoing: Mapped[Optional[datetime]]

    @staticmethod
    def set_sync(session: Session, obj: Base, sync_incoming: datetime = None, sync_outgoing: datetime = None):
        data = {'obj_id': obj.id, 'obj_type': obj.__tablename__}
        if sync_incoming:
            data['sync_incoming'] = sync_incoming
        if sync_outgoing:
            data['sync_outgoing'] = sync_outgoing
        session.execute(insert(LastSync).values(data).on_conflict_do_update(
            index_elements=['obj_id', 'obj_type'], set_=data))


logged_tables = Account, Course, User, Enrollment, Membership, Group
