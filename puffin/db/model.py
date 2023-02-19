import csv
import datetime
import enum
import json
import sys
from typing import Optional
from typing_extensions import Annotated
from sqlalchemy import DDL, ForeignKey, ForeignKeyConstraint, UniqueConstraint, create_engine, func, inspect, select, text, JSON, event
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, validators, IntegerField, ValidationError
from puffin import settings
from .database import Base, db_session, init_db

roles = {
    'Administrasjon': 'admin',
    'Undervisningsassistent': 'ta',
    'Undervisingsassistent': 'ta',
    'StudentEnrollment': 'student',
    'TaEnrollment': 'ta',
    'Emneansvarlig': 'emneansvarlig',
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


str_30 = Annotated[str, 30]


def create_triggers(cls):
    def quote(s):
        return "'" + s + "'"
    # PGSql
    old_data = 'to_jsonb(OLD)'
    new_data = 'to_jsonb(NEW)'
    # SQLite
    old_data = f' json_object({",".join([f"{quote(col.name)}, OLD.{col.name}" for col in cls.__table__.columns])})'
    new_data = f' json_object({",".join([f"{quote(col.name)}, NEW.{col.name}" for col in cls.__table__.columns])})'

    event.listen(cls.__table__, "after_create", DDL(
        'CREATE TRIGGER IF NOT EXISTS log_%(table)s_update AFTER UPDATE ON %(table)s BEGIN\n'
        + '  INSERT INTO audit_log (timestamp, table_name, row_id, type, old_data, new_data) '
        + f'  VALUES (CURRENT_TIMESTAMP, "%(table)s", NEW.id, "UPDATE", {old_data}, {new_data});'
        + 'END;'))
    event.listen(cls.__table__, "after_create", DDL(
        'CREATE TRIGGER IF NOT EXISTS log_%(table)s_insert AFTER INSERT ON %(table)s BEGIN\n'
        + '  INSERT INTO audit_log (timestamp, table_name, row_id, type, old_data, new_data) '
        + f'  VALUES (CURRENT_TIMESTAMP, "%(table)s", NEW.id, "INSERT", NULL, {new_data});'
        + 'END;'))
    event.listen(cls.__table__, "after_create", DDL(
        'CREATE TRIGGER IF NOT EXISTS log_%(table)s_delete AFTER DELETE ON %(table)s BEGIN\n'
        + '  INSERT INTO audit_log (timestamp, table_name, row_id, type, old_data, new_data) '
        + f'  VALUES (CURRENT_TIMESTAMP, "%(table)s", OLD.id, "DELETE", {old_data}, NULL);'
        + 'END;'))


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
        if self.type == 'INSERT':
            return f"INSERT(table={self.table_name}, key={self.row_id}, data={self.new_data})"
        elif self.type == 'UPDATE':
            return f"UPDATE(table={self.table_name}, key={self.row_id}, data={self.new_data}, was={self.old_data})"
        elif self.type == 'DELETE':
            return f"DELETE(table={self.table_name}, key={self.row_id}, was={self.old_data})"


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
                'note': self.note, 'avatar_url': self.avatar_url, 'active': not self.is_expired()
                }

    def is_expired(self):
        return self.expiry_date != None and self.expiry_date > datetime.now()


class Course(Base):
    __tablename__ = 'course'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    slug: Mapped[str]
    expiry_date: Mapped[Optional[datetime]]

    def to_json(self):
        return {'id': self.id, 'name': self.name, 'slug': self.slug, 'expiry_date': self.expiry_date, 'active': not self.is_expired()}

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

    course = relationship("Course")
    parent = relationship("Group")

    def to_json(self):
        return {'id': self.id, 'kind': self.kind, 'course_id': self.course_id, 'parent_id': self.parent_id, 'external_id': self.external_id, 'name': self.name,  'slug': self.slug}


class CreateGroupForm(FlaskForm):
    name = StringField('Group name', [validators.regexp(
        settings.VALID_DISPLAY_NAME_REGEX)])
    kind = StringField('Group kind', [validators.regexp(
        settings.VALID_DISPLAY_NAME_REGEX)])
    join_model = SelectField('Joining', choices=[(x.name, x.value.capitalize(
    )) for x in JoinModel], default=JoinModel.RESTRICTED.name)
    slug = StringField('Slug', [validators.regexp(settings.VALID_SLUG_REGEX)])
    submit = SubmitField('Submit')

class Membership(Base):
    __tablename__ = 'membership'
    __table_args__ = (UniqueConstraint("user_id", "group_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    group_id: Mapped[int] = mapped_column(ForeignKey('subgroup.id'))
    role: Mapped[str]

    user = relationship("User", back_populates="memberships")
    group = relationship("Group")

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
        return not self.is_expired()

    @property
    def is_authenticated(self) -> bool:
        return not self.is_expired()

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return str(self.id)

    def is_expired(self) -> bool:
        return self.expiry_date != None and self.expiry_date > datetime.now()

    def to_json(self):
        return {
            'id': self.id, 'firstname': self.firstname, 'lastname': self.lastname,
            'email': self.email(), 'avatar_url': self.avatar_url(), 'active': not self.is_expired()
        }

    def enrollment(self, course:Course|int|str) -> Enrollment | None:
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

    def account(self, provider:Provider|int|str) -> Account | None:
        for acc in self.accounts:
            if acc.provider == provider or acc.provider_id == provider or acc.provider.name == provider:
                return acc
        return None

    def email(self) -> str | None:
        for acc in self.accounts:
            return acc.email
        return None

    def avatar_url(self) -> str | None:
        for acc in self.accounts:
            if acc.avatar_url != None:
                return acc.avatar_url
        return None

    def roles(self) -> dict[int,str]:
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
