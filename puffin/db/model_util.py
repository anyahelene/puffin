from datetime import datetime
import json
import logging
from typing import IO, Tuple, Type, TypeVar
import regex
from slugify import slugify
import sqlalchemy as sa
from puffin.db import database

from puffin.db.model_views import CourseUser, FullUser, UserAccount

from .model_tables import Account, AssignmentModel, Course, Group, Id, JoinModel, LogType, User, Membership, Enrollment, LastSync
logger = logging.getLogger(__name__)

roles = {
    'Administrasjon': 'admin',
    'Undervisningsassistent': 'ta',
    'Undervisingsassistent': 'ta',
    'StudentEnrollment': 'student',
    'TaEnrollment': 'ta',
    'Emneansvarlig': 'teacher',
}


def create_triggers(cls, session: sa.orm.Session = None):
    def quote(s):
        return "'" + s + "'"
    # PGSql
    old_data = 'to_jsonb(OLD)'
    new_data = 'to_jsonb(NEW)'
    # SQLite
    old_data = f' json_object({",".join([f"{quote(col.name)}, OLD.{col.name}" for col in cls.__table__.columns])})'
    new_data = f' json_object({",".join([f"{quote(col.name)}, NEW.{col.name}" for col in cls.__table__.columns])})'

    trig1 = sa.DDL(
        f'CREATE TRIGGER IF NOT EXISTS log_{cls.__tablename__}_update AFTER UPDATE ON "{cls.__tablename__}" BEGIN\n'
        + '  INSERT INTO audit_log (timestamp, table_name, row_id, type, old_data, new_data) '
        + f'  VALUES (CURRENT_TIMESTAMP, "{cls.__tablename__}", NEW.id, "UPDATE", {old_data}, {new_data});'
        + 'END;')
    trig2 = sa.DDL(
        f'CREATE TRIGGER IF NOT EXISTS log_{cls.__tablename__}_insert AFTER INSERT ON "{cls.__tablename__}" BEGIN\n'
        + '  INSERT INTO audit_log (timestamp, table_name, row_id, type, old_data, new_data) '
        + f'  VALUES (CURRENT_TIMESTAMP, "{cls.__tablename__}", NEW.id, "INSERT", NULL, {new_data});'
        + 'END;')
    trig3 = sa.DDL(
        f'CREATE TRIGGER IF NOT EXISTS log_{cls.__tablename__}_delete AFTER DELETE ON "{cls.__tablename__}" BEGIN\n'
        + '  INSERT INTO audit_log (timestamp, table_name, row_id, type, old_data, new_data) '
        + f'  VALUES (CURRENT_TIMESTAMP, "{cls.__tablename__}", OLD.id, "DELETE", {old_data}, NULL);'
        + 'END;')
    if session == None:
        sa.event.listen(cls.__table__, "after_create", trig1)
        sa.event.listen(cls.__table__, "after_create", trig2)
        sa.event.listen(cls.__table__, "after_create", trig3)
    else:
        session.execute(trig1)
        session.execute(trig2)
        session.execute(trig3)


T = TypeVar('T', covariant=True)


def new_id(session: sa.orm.Session, cls: Type[T]) -> int:
    with session.begin_nested() as ss:
        id = Id(type=cls.__tablename__)
        print(1, id)
        session.add(id)
        print(2, id)
    print(3, id)
    return id.id


def get_or_define(session: sa.orm.Session, cls: Type[T], filter: dict, default: dict, add_new=True) -> Tuple[T, bool]:
    obj = session.execute(sa.select(cls).filter_by(**filter)).scalar_one_or_none()
    if obj != None:
        session.add(obj)
        return obj, False
    if 'id' in filter:
        obj = cls(**filter, **default)
    else:
        obj = cls(id=new_id(session, cls), **filter, **default)
    if add_new:
        session.add(obj)
    return obj, True


def update_from_uib(session: sa.orm.Session, row, course, changes=None, sync_time: datetime = None):
    """Create or update user and uib/mitt_uib accounts from Mitt UiB data."""
    name = row['sortable_name']
    (lastname, firstname) = [s.strip() for s in name.split(',', 1)]

    user, creat1 = get_or_define(session, User, {'key': f'canvas#{row["id"]}'},
                                 {'firstname': firstname, 'lastname': lastname, 'email': row['email']})

    # get or create UiB user (has login name as user name)
    uib_user, creat2 = get_or_define(session, Account, {'username': row['login_id'], 'provider_name': 'canvas'},
                                     {'external_id': int(row['id']), 'user': user, 'email': row['email'], 'fullname': name})
    # if creat1 or creat2:
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
        role = row['role']
        #role = roles.get(row['role'], row['role'])
        enrollment, creat3 = get_or_define(session, Enrollment, {
            'course': course, 'user': user}, {'role': role})
        if enrollment.role != role:
            enrollment.role = role
    #    if creat3:
    #        session.commit()

    if sync_time:
        LastSync.set_sync(session, uib_user, sync_time)
        # session.commit()

    if row.get('gituser') and row.get('gitid'):
        gitid = int(row['gitid'])
        git_user, creat4 = get_or_define(session, Account, {'username': row['gituser'],
                                                            'provider_name': 'gitlab'}, {'user_id': user.id, 'external_id': gitid, 'fullname': name})
    #    if creat4:
    #        session.commit()

    if changes != None:
        for obj in session.dirty:
            changes.append((obj.__tablename__, obj.id))
    session.commit()
    return uib_user


def define_gitlab_account(session: sa.orm.Session, user: User, username: str, userid: int, name=None, changes=None, sync_time: datetime = None):
    if not name:
        name = f'{user.firstname} {user.lastname}'
    git_user, created = get_or_define(session, Account, {'username': username,
                                                         'provider_name': 'gitlab'}, {'user_id': user.id, 'external_id': userid, 'fullname': name})
    if sync_time:
        LastSync.set_sync(session, git_user, sync_time)
    if changes != None:
        for obj in session.dirty:
            changes.append((obj.__tablename__, obj.id))
    session.commit()

    sa.select(Account).join
    return git_user


def update_groups_from_uib(session: sa.orm.Session, data, course, changes=None, sync_time: datetime = None):
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
            user = session.execute(sa.select(User).where(Account.user_id == User.id,
                                                         Account.external_id == str(
                                                             student['id']),
                                                         Account.provider_name == 'canvas')).scalar_one_or_none()
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
                                                {'role': en.role, 'join_model': JoinModel.AUTO})
            if membership.role != en.role and membership.join_model == JoinModel.AUTO:
                membership.role = en.role
            if sync_time:
                LastSync.set_sync(session, membership, sync_time)
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


def check_group_membership(db: sa.orm.Session, course: Course, group: Group, user: User, changes=None, students_only=True, join=JoinModel.AUTO, sync_time: datetime = None):
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
    LogType: '|'.join([f"'{n.name}'" for n in LogType]),
    bool: 'boolean',
    JoinModel: '|'.join([f"'{n.name}'" for n in JoinModel]),
    AssignmentModel: '|'.join([f"'{n.name}'" for n in AssignmentModel]),
    dict: 'Record<string,any>'
}
TYPESCRIPT_TYPE_DEFAULTS = {
    dict: '{}'
}

def to_typeScript(filename: str):
    with open(filename, 'w') as f:
        f.write('import { isEqual } from "lodash-es";')
        f.write('export const tables = {};\n')
        for tbl in database._meta.tables:
            table_to_ts(''.join([t.capitalize() for t in tbl.split(
                '_')]), database._meta.tables[tbl], f)
        for tbl in [CourseUser, UserAccount, FullUser]:
            table_to_ts(tbl.__name__, tbl.__table__, f)


def table_to_ts(name: str, table: sa.Table, f: IO):
    cols = [col for col in table.columns if not col.info.get('secret', False)]
    f.write(f'export class _{name} ')
    f.write('{\n')
    f.write('    revision : number;\n')
    for col in cols:
        typ =  TYPESCRIPT_TYPES[col.type.python_type]
        dflt = TYPESCRIPT_TYPE_DEFAULTS.get(col.type.python_type)
        f.write(
            f'    {col.name}{"?" if col.nullable else ""} : {typ}{" = "+dflt if dflt else ""};\n')
    f.write('    constructor(jsonData:Record<string,any>, revision=0) {\n')
    for col in cols:
        if col.name == 'id' or col.info.get('immutable', False):
            f.write(f'        this.{col.name} = jsonData.{col.name};\n')
    f.write('        this.update(jsonData, revision);\n')
    f.write('    }\n')
    f.write('''
    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
''')
    f.write(
        '    update(jsonData:Record<string,any>, revision=0) : boolean {\n')
    f.write(
        '        if(this.id !== jsonData.id) throw new Error("Data doesn\'t match ID");\n')
    f.write('        this.revision = revision;\n')
    f.write('        let changed = false;\n')
    for col in cols:
        if col.name == 'id' or col.info.get('immutable', False):
            continue
        if col.type.python_type == dict:
            f.write(f'        if(!isEqual(this.{col.name}, jsonData.{col.name})) ' + '{\n')
            f.write('            changed = true;\n')
            f.write(f'            this.{col.name} = ' +
                    '{...jsonData.'+col.name+'};\n')
        else:
            f.write(f'        if(this.{col.name} !== jsonData.{col.name}) ' + '{\n')
            f.write('            changed = true;\n')
            f.write(f'            this.{col.name} = jsonData.{col.name};\n')
        f.write('        }\n')
    f.write('        return changed;\n')
    f.write('    }\n')
    f.write('}\n')
    f.write(f'export const {name}_columns = [\n')
    for col in cols:
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
    f.write(f'tables["{name}"] = {name}_columns;\n')
