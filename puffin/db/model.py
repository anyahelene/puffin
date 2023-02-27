import csv
import datetime
import enum
import json
import sys
from typing import IO, Any, Optional, Tuple, TypeVar, Type
from typing_extensions import Annotated
import regex
from slugify import slugify
from sqlalchemy import DDL, ForeignKey, ForeignKeyConstraint, Selectable, Table, UniqueConstraint, alias, and_, create_engine, func, inspect, join, select, text, JSON, event, DateTime
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase, Mapped, mapped_column, Session, InstanceState
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy_utils import create_view
from datetime import datetime
from puffin import settings
from .database import Base, ViewBase, db_session, rename_columns
import logging

from puffin.db import database
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
        f'CREATE TRIGGER IF NOT EXISTS log_{cls.__tablename__}_update AFTER UPDATE ON "{cls.__tablename__}" BEGIN\n'
        + '  INSERT INTO audit_log (timestamp, table_name, row_id, type, old_data, new_data) '
        + f'  VALUES (CURRENT_TIMESTAMP, "{cls.__tablename__}", NEW.id, "UPDATE", {old_data}, {new_data});'
        + 'END;')
    trig2 = DDL(
        f'CREATE TRIGGER IF NOT EXISTS log_{cls.__tablename__}_insert AFTER INSERT ON "{cls.__tablename__}" BEGIN\n'
        + '  INSERT INTO audit_log (timestamp, table_name, row_id, type, old_data, new_data) '
        + f'  VALUES (CURRENT_TIMESTAMP, "{cls.__tablename__}", NEW.id, "INSERT", NULL, {new_data});'
        + 'END;')
    trig3 = DDL(
        f'CREATE TRIGGER IF NOT EXISTS log_{cls.__tablename__}_delete AFTER DELETE ON "{cls.__tablename__}" BEGIN\n'
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
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
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

providers = {}

class Id(Base):
    __tablename__ = 'id'
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str_30]

class Provider(Base):
    __tablename__ = 'provider'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str_30]
    has_external_id: Mapped[bool] = mapped_column(
        doc="Whether accounts have a unique numeric id")
    is_primary: Mapped[bool] = mapped_column(server_default='FALSE')

class Account(Base):
    __tablename__ = 'account'
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=False, doc="Internal account id",
        info={'view':{'course_user':False}})
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("provider.id"), doc="Account provider",
        info={'view':{'course_user':False}})
    user_id: Mapped[int] = mapped_column(ForeignKey(
        "user.id"), doc="User this account is associated with",
        info={'view':{'course_user':False}})
    external_id: Mapped[Optional[int]] = mapped_column(unique=True,
        doc="Provider's numeric user id (if any)")
    username: Mapped[str] = mapped_column(
        unique=True, doc="Provider's username for this account")
    expiry_date: Mapped[Optional[datetime]] = mapped_column(info={'view':{'course_user':False}})
    email: Mapped[Optional[str]] = mapped_column(info={'view':{'course_user':False}})
    fullname: Mapped[str] = mapped_column(info={'view':{'course_user':False}})
    note: Mapped[Optional[str]] = mapped_column(info={'view':{'course_user':False}})
    avatar_url: Mapped[Optional[str]] = mapped_column(info={'view':{'course_user':False}})

    user = relationship("User", back_populates="accounts")
    provider = relationship("Provider")

    @property
    def is_expired(self):
        return self.expiry_date != None and self.expiry_date > datetime.now()


class Course(Base):
    __tablename__ = 'course'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False,info={'view':{'course_user':False}})
    external_id: Mapped[int] = mapped_column(unique=True,info={'view':{'course_user':'course_canvas_id'}})
    name: Mapped[str] = mapped_column(info={'view':{'course_user':'course_name'}})
    slug: Mapped[str] = mapped_column(info={'view':{'course_user':'course_slug'}})
    expiry_date: Mapped[Optional[datetime]] = mapped_column(info={'view':{'course_user':False}})

    @property
    def is_expired(self):
        return self.expiry_date != None and self.expiry_date > datetime.now()


class Group(Base):
    __tablename__ = 'group'
    __table_args__ = (UniqueConstraint("course_id", "slug"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    kind: Mapped[str]
    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"))
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("group.id"))
    external_id: Mapped[Optional[str]]  = mapped_column(unique=True)
    name: Mapped[str]
    slug: Mapped[str]
    join_model: Mapped[JoinModel] = mapped_column(default=JoinModel.RESTRICTED)
    join_source: Mapped[Optional[str]] = mapped_column(
        doc="E.g. gitlab(project_id)", default=None)

    course = relationship("Course")
    parent = relationship("Group")
    memberships = relationship("Membership")

class Membership(Base):
    __tablename__ = 'membership'
    __table_args__ = (UniqueConstraint("user_id", "group_id"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    group_id: Mapped[int] = mapped_column(ForeignKey('group.id'))
    role: Mapped[str]
    join_model: Mapped[JoinModel] = mapped_column(default=JoinModel.RESTRICTED)

    user = relationship("User", back_populates="memberships")
    group = relationship("Group", back_populates="memberships")


class Enrollment(Base):
    __tablename__ = 'enrollment'
    __table_args__ = (UniqueConstraint("user_id", "course_id"),
                      ForeignKeyConstraint(['user_id'], ['user.id']),
                      ForeignKeyConstraint(['course_id'], ['course.id'])
                      )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False,info={'view':{'course_user':False}})
    user_id: Mapped[int] = mapped_column(info={'view':{'course_user':False}})
    course_id: Mapped[int]
    role: Mapped[str] = mapped_column(info={'icons':{'student' : '🧑‍🎓', 'admin' : '🧑‍💼','': '🧑‍🏫'}})

    user = relationship("User", back_populates="enrollments")
    course = relationship("Course")

class User(Base):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    key: Mapped[str] = mapped_column(unique=True, info={'hide':True,'view':{'course_user':False}})
    lastname: Mapped[str]
    firstname: Mapped[str]
    email: Mapped[str]
    is_admin: Mapped[bool] = mapped_column(server_default=text('FALSE'),
        info={'icons':{'true' : '🧑‍💻', '': ' '}})
    locale: Mapped[Optional[str_30]]
    expiry_date: Mapped[Optional[datetime]] = mapped_column(info={'view':{'course_user':False}})
    password: Mapped[Optional[str]] = mapped_column(info={'secret':True,})

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

def _set_colinfo(_cols,_infos):
    for c,i in zip(_cols,_infos):
        c.info.update(i)

class CourseUser(ViewBase):
    __tablename__ = 'course_user'
    _cols,_infos = rename_columns(__tablename__, join(User,Enrollment).join(Course))
    __table__ = create_view(__tablename__, _cols, ViewBase.metadata, cascade_on_drop=False)
    _set_colinfo(__table__.c, _infos)
    __col_order__ = [__table__.c.id,__table__.c.role,__table__.c.is_admin]
    __col_hide__ = [__table__.c.course_id, __table__.c.course_canvas_id, __table__.c.course_name,__table__.c.course_slug]
    def __setattr__(self, __name: str, __value: Any) -> None:
        if isinstance(__value, InstanceState):
            return super().__setattr__(__name, __value)
        else:
            print(__name, __value, type(__value))
            raise TypeError(f'{self.__class__.__name__} is immutable/read-only')

def account_info_view():
    cols = [User.id]
    infos = [User.id.info]
    ps = db_session.execute(select(Provider).order_by(Provider.is_primary.desc(), Provider.id)).scalars().all()
    p = ps[0]
    sel = join(User, Account, and_(User.id == Account.user_id, Account.provider_id == p.id))
    cols = cols + [Account.external_id.label(f'{p.name}_id'), Account.username.label(f'{p.name}_username')]
    infos = infos + [Account.external_id.info, Account.username.info]
    #sel = sel.add_columns(Account.external_id.label(f'{p.name}_id'), Account.username.label(f'{p.name}_username'))
    for p in ps[1:]:
        acc = alias(Account, f'{p.name}_account')
        sel = sel.outerjoin(acc, and_(User.id == acc.c.user_id, acc.c.provider_id == p.id))
        cols = cols + [acc.c.external_id.label(f'{p.name}_id'), acc.c.username.label(f'{p.name}_username')]
        infos = infos + [Account.external_id.info, Account.username.info]
    #    sel = sel.add_columns(acc.c.external_id.label(f'{p.name}_id'), acc.c.username.label(f'{p.name}_username'))

    return select(*cols).select_from(sel), infos

class UserAccount(ViewBase):
    __tablename__ = 'user_account'
    _cols, _infos = account_info_view()
    __table__ = create_view(__tablename__, _cols, ViewBase.metadata, cascade_on_drop=False)
    _set_colinfo(__table__.c, _infos)


    def __setattr__(self, __name: str, __value: Any) -> None:
        if isinstance(__value, InstanceState):
            return super().__setattr__(__name, __value)
        else:
            print(__name, __value, type(__value))
            raise TypeError(f'{self.__class__.__name__} is immutable/read-only')

class LastSync(Base):
    __tablename__ = 'last_sync'
    __table_args__ = (UniqueConstraint("obj_id", "obj_type"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    obj_id: Mapped[int]
    obj_type: Mapped[str_30]
    sync_incoming: Mapped[Optional[datetime]]
    sync_outgoing: Mapped[Optional[datetime]]

    @staticmethod
    def set_sync(session:Session, obj:Base, sync_incoming:datetime=None, sync_outgoing:datetime=None):
        data = {'obj_id':obj.id, 'obj_type':obj.__tablename__}
        if sync_incoming:
            data['sync_incoming'] = sync_incoming
        if sync_outgoing:
            data['sync_outgoing'] = sync_outgoing
        session.execute(insert(LastSync).values(data).on_conflict_do_update(index_elements=['obj_id','obj_type'],set_=data))

    
T = TypeVar('T', covariant=True)

def new_id(session: Session, cls: Type[T]) -> int:
    with session.begin_nested() as ss:
        id = Id(type=cls.__tablename__)
        print(1, id)
        session.add(id)
        print(2, id)
    print(3, id)
    return id.id

def get_or_define(session: Session, cls: Type[T], filter: dict, default: dict, add_new=True) -> Tuple[T, bool]:
    obj = session.execute(select(cls).filter_by(**filter)).scalar_one_or_none()
    if obj != None:
        session.add(obj)
        return obj, False
    if 'id' in filter:
        obj = cls(**filter, **default)
    else:
        obj = cls(id= new_id(session, cls), **filter, **default)
    if add_new:
        session.add(obj)
    return obj, True


def setup_providers():
    session = db_session
    # find or create UiB and Mitt UiB account providers
    # mitt_uib, created = get_or_define(session, Provider, {'name': 'mitt.uib.no'}, {})
    uib, created = get_or_define(session, Provider, {
        'name': 'canvas'}, {'has_external_id': True, 'is_primary':True})
    gitlab, created = get_or_define(session, Provider, {
        'name': 'gitlab'}, {'has_external_id': True})
    discord, created = get_or_define(session, Provider, {'name': 'discord'}, {
        'has_external_id': False})
    #session.add_all([uib, gitlab, discord])
    session.commit()  # commit in case we created anything
    # Primary key IDs should now be ready
    providers['canvas'] = uib.id
    providers['discord'] = discord.id
    providers['gitlab'] = gitlab.id


logged_tables = Account, Course, User, Enrollment, Membership, Group


def update_from_uib(session: Session, row, course, changes=None, sync_time:datetime = None):
    """Create or update user and uib/mitt_uib accounts from Mitt UiB data."""
    name = row['sortable_name']
    (lastname, firstname) = [s.strip() for s in name.split(',', 1)]

    user, creat1 = get_or_define(session, User, {'key':f'canvas#{row["id"]}'},
        {'firstname':firstname, 'lastname':lastname, 'email':row['email']})
    
    # get or create UiB user (has login name as user name)
    uib_user, creat2 = get_or_define(session, Account, {'username': row['login_id'], 'provider_id': providers['canvas']},
                                      {'external_id': int(row['id']), 'user':user, 'email': row['email'], 'fullname': name})
    #if creat1 or creat2:
    #    session.commit()
    # name changed?
    if uib_user.fullname != name:
        user.firstname = firstname
        user.lastname = lastname
        uib_user.fullname = name
    # update data
    locale = row.get('locale') or row.get('effective_locale') or None
    if uib_user.email != row['email']:
        user.email = uib_user.email = row['email']
    if uib_user.avatar_url != row['avatar_url']:
        uib_user.avatar_url = row['avatar_url']
    if user.locale != locale:
        user.locale = locale
    if course != None:
        role = roles.get(row['role'], row['role'])
        enrollment, creat3 = get_or_define(session, Enrollment, {
            'course': course, 'user': user}, {'role': role})
        if enrollment.role != role:
            enrollment.role = role
    #    if creat3:
    #        session.commit()

    if sync_time:
        LastSync.set_sync(session, uib_user, sync_time)
        #session.commit()

    if row.get('gituser') and row.get('gitid'):
        gitid = int(row['gitid'])
        git_user, creat4 = get_or_define(session, Account, {'username': row['gituser'],
                                                             'provider_id': providers['gitlab']}, {'user_id': user.id, 'external_id': gitid, 'fullname': name})
    #    if creat4:
    #        session.commit()

    if changes != None:
        for obj in session.dirty:
            changes.append((obj.__tablename__, obj.id))
    session.commit()
    return uib_user


def define_gitlab_account(user: User, username: str, userid: int, name=None, changes=None, sync_time:datetime = None):
    if not name:
        name = f'{user.firstname} {user.lastname}'
    git_user, created = get_or_define(db_session, Account, {'username': username,
                                                            'provider_id': providers['gitlab']}, {'user_id': user.id, 'external_id': userid, 'fullname': name})
    if sync_time:
        LastSync.set_sync(db_session, git_user, sync_time)
    if changes != None:
        for obj in db_session.dirty:
            changes.append((obj.__tablename__, obj.id))
    db_session.commit()

    select(Account).join
    return git_user


def update_groups_from_uib(session: Session, data, course, changes=None, sync_time:datetime = None):
    """Create or update course groups from Mitt UiB data."""
    if data.get('sis_section_id') == None:
        return None
    errors = []
    name = data['name']
    name = regex.sub(r'^.*(Gruppe \d+).*$', r'\1', name)
    group, created = get_or_define(session, Group, {'external_id': data['id']},
                                   {'name': data['name'], 'slug': slugify(data['name']),
                                    'course_id': course.id, 'join_model': JoinModel.AUTO, 'kind': 'section'})
    group.name = name
    group.slug = slugify(name)
    # session.add(group)
    if sync_time:
        LastSync.set_sync(session, group, sync_time)
    print('Group:', group)

    if data.get('students') != None:
        old_members: dict[int, Membership] = {
            m.user_id: m for m in group.memberships}
        print('old members:', old_members)

        for student in data['students']:
            user = session.execute(select(User).where(Account.user_id == User.id,
                                                      Account.external_id == str(
                                                          student['id']),
                                                      Account.provider_id == providers['canvas'])).scalar_one_or_none()
            if user == None:
                errors.append(
                    f'User not found: {student["id"]} – {student["name"]}')
                continue
            en = user.enrollment(course)
            if en == None:
                errors.append(
                    f'User not enrolled in course: {student["id"]} – {student["name"]}')
                continue

            membership, created = get_or_define(session, Membership, {'group_id': group.id, 'user_id': user.id},
                                                {'role': en.role, 'join_model':JoinModel.AUTO})
            if membership.role != en.role and membership.join_model == JoinModel.AUTO:
                membership.role = en.role
            if sync_time:
                LastSync.set_sync(db_session, membership, sync_time)
            # session.add(membership)
            print('add or update membership:', membership)
            if user.id in old_members:
                del old_members[user.id]
        print('missing old members:', old_members)
        for missing in old_members:
            session.delete(old_members[missing])
    if changes != None:
        for obj in session.dirty:
            changes.append((obj.__tablename__, obj.id))
    session.commit()


def check_group_membership(db: Session, course: Course, group: Group, user: User, changes=None, students_only=True, join=JoinModel.AUTO, sync_time:datetime = None):
    en = user.enrollment(course)
    if en:
        if students_only and en.role != 'student':
            logger.info(
                f'check_group_membership(%s): skipping non-sudent: %s', group.slug, user.lastname)
        else:
            membership, created = get_or_define(db, Membership, {'group_id': group.id, 'user_id': user.id},
                                                {'role': en.role, 'join_model': join})
            if membership.role != en.role and membership.join_model == JoinModel.AUTO:
                membership.role = en.role
            # db.add(membership)
            if sync_time:
                LastSync.set_sync(db, membership, sync_time)
            if changes != None:
                for obj in db.dirty:
                    changes.append((obj.__tablename__, obj.id))
            db.commit()
            logger.info(
                f'check_group_membership(%s): add or update membership: %s', group.slug, membership)
    else:
        logger.info(f'check_group_membership(%s): user %s not enrolled in course %s',
                    group.slug, user.lastname, course)


TYPESCRIPT_TYPES = {
    int: 'number',
    str: 'string',
    datetime: 'Date',
    LogType: '|'.join([f"'{n.name}'" for n in JoinModel]),
    bool: 'boolean',
    JoinModel: '|'.join([f"'{n.name}'" for n in JoinModel]),
    dict: 'object'
}

def to_typeScript(filename: str):
    with open(filename, 'w') as f:
        f.write('export const tables = {};\n')
        for tbl in database._meta.tables:
            table_to_ts(tbl, database._meta.tables[tbl], f)
        for tbl in [CourseUser, UserAccount]:
            table_to_ts(tbl.__tablename__, tbl.__table__, f)


def table_to_ts(name: str, table: Table, f: IO):
    f.write(f'export interface {name.capitalize()} ')
    f.write('{\n')
    for col in table.columns:
        f.write(
            f'    {col.name}{"?" if col.nullable else ""} : {TYPESCRIPT_TYPES[col.type.python_type]};\n')
            
    f.write('}\n')
    f.write(f'export const {name}_columns = [\n')
    for col in table.columns:
        if col.info.get('secret', False):
            continue
        f.write('    {\n')
        f.write(f'        name: "{col.name}",\n')
        f.write(f'        type: "{col.type.python_type.__name__}",\n')
        if col.doc:
            f.write(f'        doc: "{col.doc}",\n')
        for key in col.info:
            f.write(f'        {key}: {json.dumps(col.info[key])},\n')
        f.write('    },\n')
    f.write(']\n')
    f.write(f'tables["{table.name}"] = {name}_columns;\n')

