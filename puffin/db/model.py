import csv
import datetime
import enum
import json
import sys
from typing import Optional
from typing_extensions import Annotated
import regex
from slugify import slugify
from sqlalchemy import DDL, ForeignKey, ForeignKeyConstraint, UniqueConstraint, create_engine, func, inspect, select, text, JSON, event
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase, Mapped, mapped_column, Session
from datetime import datetime
from puffin import settings
from .database import Base, db_session, init_db
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

roles = {
    'Administrasjon': 'admin',
    'Undervisningsassistent': 'ta',
    'Undervisingsassistent': 'ta',
    'StudentEnrollment': 'student',
    'TaEnrollment': 'ta',
    'Emneansvarlig': 'teacher',
}

__VALID_DISPLAY_NAME_CHARS__ = r'[\p{print}]'
__VALID_SLUG_CHARS__ = r'[a-z0-9-]'
VALID_DISPLAY_NAME_REGEX = regex.compile(f'^{__VALID_DISPLAY_NAME_CHARS__}+$')
VALID_DISPLAY_NAME_PREFIX = regex.compile(f'^{__VALID_DISPLAY_NAME_CHARS__}+')
VALID_SLUG_REGEX = regex.compile(f'^{__VALID_SLUG_CHARS__}+$')
VALID_SLUG_PREFIX = regex.compile(f'^{__VALID_SLUG_CHARS__}+')

###########################################################################################


class LogType(enum.Enum):
    UPDATE = "UPDATE"
    INSERT = "INSERT"
    DELETE = "DELETE"


class JoinModel(enum.Enum):
    RESTRICTED = "Restricted – members of the parent group can join freely"
    OPEN = "Open – users can join/leave freely"
    AUTO = "Auto – users are automatically added to this group"
    CLOSED = "Closed – group owner must add users"


str_30 = Annotated[str, 30]


def create_triggers(cls, session: Session = None):
    def quote(s):
        return "'" + s + "'"
    # PGSql
    old_data = 'to_jsonb(OLD)'
    new_data = 'to_jsonb(NEW)'
    # SQLite
    old_data = f' json_object({",".join([f"{quote(col.name)}, OLD.{col.name}" for col in cls.__table__.columns])})'
    new_data = f' json_object({",".join([f"{quote(col.name)}, NEW.{col.name}" for col in cls.__table__.columns])})'

    trig1 = DDL(
        f'CREATE TRIGGER IF NOT EXISTS log_{cls.__tablename__}_update AFTER UPDATE ON {cls.__tablename__} BEGIN\n'
        + '  INSERT INTO audit_log (timestamp, table_name, row_id, type, old_data, new_data) '
        + f'  VALUES (CURRENT_TIMESTAMP, "{cls.__tablename__}", NEW.id, "UPDATE", {old_data}, {new_data});'
        + 'END;')
    trig2 = DDL(
        f'CREATE TRIGGER IF NOT EXISTS log_{cls.__tablename__}_insert AFTER INSERT ON {cls.__tablename__} BEGIN\n'
        + '  INSERT INTO audit_log (timestamp, table_name, row_id, type, old_data, new_data) '
        + f'  VALUES (CURRENT_TIMESTAMP, "{cls.__tablename__}", NEW.id, "INSERT", NULL, {new_data});'
        + 'END;')
    trig3 = DDL(
        f'CREATE TRIGGER IF NOT EXISTS log_{cls.__tablename__}_delete AFTER DELETE ON {cls.__tablename__} BEGIN\n'
        + '  INSERT INTO audit_log (timestamp, table_name, row_id, type, old_data, new_data) '
        + f'  VALUES (CURRENT_TIMESTAMP, "{cls.__tablename__}", OLD.id, "DELETE", {old_data}, NULL);'
        + 'END;')
    if session == None:
        event.listen(cls.__table__, "after_create", trig1)
        event.listen(cls.__table__, "after_create", trig2)
        event.listen(cls.__table__, "after_create", trig3)
    else:
        session.execute(trig1)
        session.execute(trig2)
        session.execute(trig3)


class AuditLog(Base):
    __tablename__ = 'audit_log'
    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        server_default=text('CURRENT_TIMESTAMP'))
    table_name: Mapped[str_30]
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

    def to_json(self):
        return dict(id=self.id, timestamp=self.timestamp, table_name=self.table_name, row_id=self.row_id,
                    type=self.type.name, old_data=self.old_data, new_data=self.new_data)


providers = {}


class Provider(Base):
    __tablename__ = 'provider'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str_30]
    has_ref_id: Mapped[bool] = mapped_column(
        doc="Whether accounts have a unique numeric id")

    def __repr__(self):
        return f"Provider(id={self.id!r}, name={self.name!r})"


class Account(Base):
    __tablename__ = 'account'
    id: Mapped[int] = mapped_column(
        primary_key=True, doc="Internal account id")
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("provider.id"), doc="Account provider")
    user_id: Mapped[int] = mapped_column(ForeignKey(
        "user.id"), doc="User this account is associated with")
    ref_id: Mapped[Optional[int]] = mapped_column(
        doc="Provider's numeric user id (if any)")
    username: Mapped[str] = mapped_column(
        unique=True, doc="Provider's username for this account")
    expiry_date: Mapped[Optional[datetime]]
    email: Mapped[Optional[str]]
    fullname: Mapped[str]
    note: Mapped[Optional[str]]
    avatar_url: Mapped[Optional[str]]

    user = relationship("User", back_populates="accounts")
    provider = relationship("Provider")

    def to_json(self):
        return {'id': self.id, 'provider_id': self.provider_id, 'user_id': self.user_id, 'ref_id': self.ref_id,
                'username': self.username, 'expiry_date': self.expiry_date, 'email': self.email, 'fullname': self.fullname,
                'note': self.note, 'avatar_url': self.avatar_url, 'active': not self.is_expired
                }

    @property
    def is_expired(self):
        return self.expiry_date != None and self.expiry_date > datetime.now()


class Course(Base):
    __tablename__ = 'course'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    slug: Mapped[str]
    expiry_date: Mapped[Optional[datetime]]

    def to_json(self):
        return {'id': self.id, 'name': self.name, 'slug': self.slug, 'expiry_date': self.expiry_date, 'active': not self.is_expired}

    @property
    def is_expired(self):
        return self.expiry_date != None and self.expiry_date > datetime.now()


class Group(Base):
    __tablename__ = 'subgroup'
    __table_args__ = (UniqueConstraint("course_id", "slug"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str]
    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"))
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("subgroup.id"))
    external_id: Mapped[Optional[str]]
    name: Mapped[str]
    slug: Mapped[str]
    join_model: Mapped[JoinModel] = mapped_column(default=JoinModel.RESTRICTED)
    join_source: Mapped[Optional[str]] = mapped_column(doc="E.g. gitlab(project_id)")

    course = relationship("Course")
    parent = relationship("Group")
    memberships = relationship("Membership")

    def to_json(self):
        return {'id': self.id, 'kind': self.kind, 'course_id': self.course_id, 'parent_id': self.parent_id, 'external_id': self.external_id, 'name': self.name,  'slug': self.slug}


class Membership(Base):
    __tablename__ = 'membership'
    __table_args__ = (UniqueConstraint("user_id", "group_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    group_id: Mapped[int] = mapped_column(ForeignKey('subgroup.id'))
    join_model: Mapped[JoinModel] = mapped_column(default=JoinModel.RESTRICTED)
    role: Mapped[str]

    user = relationship("User", back_populates="memberships")
    group = relationship("Group", back_populates="memberships")

    def to_json(self):
        return {'id': self.id, 'user_id': self.user_id, 'group_id': self.group_id, 'role': self.role}


class Enrollment(Base):
    __tablename__ = 'enrollment'
    __table_args__ = (UniqueConstraint("user_id", "course_id"),
                      ForeignKeyConstraint(['user_id'], ['user.id']),
                      ForeignKeyConstraint(['course_id'], ['course.id'])
                      )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    course_id: Mapped[int]
    role: Mapped[str]

    user = relationship("User", back_populates="enrollments")
    course = relationship("Course")

    def to_json(self):
        return {'id': self.id, 'user_id': self.user_id, 'course_id': self.course_id, 'role': self.role}


class User(Base):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(primary_key=True)
    firstname: Mapped[str]
    lastname: Mapped[str]
    is_admin: Mapped[bool] = mapped_column(server_default=text('FALSE'))
    expiry_date: Mapped[Optional[datetime]]
    password: Mapped[Optional[str]]

    accounts = relationship("Account", back_populates="user")
    enrollments = relationship("Enrollment", back_populates="user")
    memberships = relationship("Membership")

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

    def to_json(self):
        return {
            'id': self.id, 'firstname': self.firstname, 'lastname': self.lastname,
            'email': self.email, 'avatar_url': self.avatar_url, 'active': not self.is_expired
        }

    def enrollment(self, course: Course | int | str) -> Enrollment | None:
        for en in self.enrollments:
            if en.course == course or en.course_id == course or en.course.name == course:
                return en
        return None

    def membership(self, course=None, kind=None) -> list[Membership]:
        ms = []
        for m in self.memberships:
            if (course == None or m.group.course == course or m.group.course_id == course or m.group.course.name == course) \
                    and (kind == None or m.group.kind == kind):
                ms.append(m)
        return ms

    def account(self, provider: Provider | int | str) -> Account | None:
        for acc in self.accounts:
            if acc.provider == provider or acc.provider_id == provider or acc.provider.name == provider:
                return acc
        return None

    @property
    def email(self) -> str | None:
        for acc in self.accounts:
            return acc.email
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


def get_or_define(session, cls, filter, default):
    obj = session.execute(select(cls).filter_by(**filter)).scalar_one_or_none()
    if obj == None:
        obj = cls(**filter, **default)
        print("***", obj)
    return obj


def setup_providers():
    session = db_session
    # find or create UiB and Mitt UiB account providers
    # mitt_uib = get_or_define(session, Provider, {'name': 'mitt.uib.no'}, {})
    uib = get_or_define(session, Provider, {
                        'name': 'uib.no'}, {'has_ref_id': True})
    gitlab = get_or_define(session, Provider, {
        'name': 'git.app.uib.no'}, {'has_ref_id': True})
    discord = get_or_define(session, Provider, {'name': 'discord.com'}, {
                            'has_ref_id': False})
    session.add_all([uib, gitlab, discord])
    session.commit()  # commit in case we created anything
    # Primary key IDs should now be ready
    providers['uib'] = uib.id
    providers['discord.com'] = discord.id
    providers['git.app.uib.no'] = gitlab.id


logged_tables = Account, Course, User, Enrollment, Membership, Group


def update_from_uib(session: Session, row, course):
    """Create or update user and uib/mitt_uib accounts from Mitt UiB data."""
    name = row['sortable_name']
    (lastname, firstname) = [s.strip() for s in name.split(',', 1)]
    # get or create UiB user (has login name as user name)
    uib_user = get_or_define(session, Account, {'username': row['login_id'], 'provider_id': providers['uib']},
                             {'ref_id': int(row['id']), 'email': row['email'], 'fullname': name})
    # get or create Mitt UiB user (has Canvas id as user name)
    # mitt_uib_user = get_or_define(session, Account, {'username': row['id'], 'provider_id': providers['mitt_uib']}, {
    #                              'email': row['email'], 'fullname': name})
    # create User object if necessary

    if uib_user.user == None:
        user = User(firstname=firstname, lastname=lastname)
        uib_user.user = user
    else:
        user = uib_user.user
    session.add_all([user, uib_user])
    session.commit()
    print(user)
    # name changed?
    if uib_user.fullname != name:
        # session.add(user)
        user.firstname = firstname
        user.lastname = lastname
        uib_user.fullname = name
    # update data
    user.email = uib_user.email = row['email']
    uib_user.avatar_url = row['avatar_url']
    if course != None:
        role = roles.get(row['role'], row['role'])
        enrollment = get_or_define(session, Enrollment, {
                                   'course': course, 'user': user}, {'role': role})
        session.add(enrollment)

    if row.get('gituser') and row.get('gitid'):
        gitid = int(row['gitid'])
        git_user = get_or_define(session, Account, {'username': row['gituser'],
                                                    'provider_id': providers['git.app.uib.no']}, {'user_id': user.id, 'ref_id': gitid, 'fullname': name})
        session.add(git_user)

    return uib_user

def define_gitlab_account(user:User, username:str, userid:int, name=None, commit = False):
    if not name:
        name = f'{user.firstname} {user.lastname}'
    git_user = get_or_define(db_session, Account, {'username': username,
                                                    'provider_id': providers['git.app.uib.no']}, {'user_id': user.id, 'ref_id': userid, 'fullname': name})
    db_session.add(git_user)
    if commit:
        db_session.commit()
    return git_user

def update_groups_from_uib(session: Session, data, course):
    """Create or update course groups from Mitt UiB data."""
    if data.get('sis_section_id') == None:
        return None
    errors = []
    name = data['name']
    name = regex.sub(r'^.*(Gruppe \d+).*$', r'\1', name)
    group = get_or_define(session, Group, {'external_id': data['id']},
                          {'name': data['name'], 'slug': slugify(data['name']),
                              'course_id': course.id, 'join_model': JoinModel.AUTO, 'kind': 'section'})
    group.name = name
    group.slug = slugify(name)
    session.add(group)
    session.commit()
    print('Group:', group)

    if data.get('students') != None:
        old_members : dict[int,Membership] = {m.user_id: m for m in group.memberships}
        print('old members:', old_members)

        for student in data['students']:
            user = session.execute(select(User).where(Account.user_id == User.id,
                                               Account.ref_id == str(student['id']),
                                               Account.provider_id == providers['uib'])).scalar_one_or_none()
            if user == None:
                errors.append(f'User not found: {student["id"]} – {student["name"]}')
                continue
            en = user.enrollment(course)
            if en == None:
                errors.append(f'User not enrolled in course: {student["id"]} – {student["name"]}')
                continue

            membership = get_or_define(session, Membership, {'group_id':group.id,'user_id':user.id},
                        {'role':en.role})
            if membership.role != en.role:
                membership.role = en.role
            session.add(membership)
            print('add or update membership:', membership)
            if user.id in old_members:
                del old_members[user.id]
        print('missing old members:', old_members)
        for missing in old_members:
            session.delete(old_members[missing])

    session.commit()

def check_group_membership(db:Session, course:Course, group:Group, user:User, students_only=True, join=JoinModel.AUTO):
    en = user.enrollment(course)
    if en:
        if students_only and en.role != 'student':
            logger.info(f'check_group_membership(%s): skipping non-sudent: %s', group.slug, user.lastname)
        else:    
            membership = get_or_define(db, Membership, {'group_id':group.id,'user_id':user.id},
                                {'role':en.role, 'join_model':join})
            if membership.role != en.role and membership.join_model == JoinModel.AUTO:
                membership.role = en.role
            db.add(membership)
            db.commit()
            logger.info(f'check_group_membership(%s): add or update membership: %s', group.slug, membership)
    else:
        logger.info(f'check_group_membership(%s): user %s not enrolled in course %s', group.slug, user.lastname, course)