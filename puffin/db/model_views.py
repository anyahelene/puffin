from typing import Any
import flask
import sqlalchemy as sa
from sqlalchemy_utils import create_view
from . import model_tables, database

def _set_colinfo(_cols,_infos):
    for c,i in zip(_cols,_infos):
        c.info.update(i)

def rename_columns(name, source):
    cols = []
    info = []
    for col in source.columns:
        viewspecs = col.info.get('view', {})
        spec = viewspecs.get(name, True)
        if type(spec) == str:
            cols.append(col.label(spec))
            info.append(col.info)
            print('col',cols[-1])
        elif spec and not col.info.get('secret', False):
            cols.append(col)
            info.append(col.info)
    return sa.select(*cols).select_from(source), info

class CourseUser(database.ViewBase):
    __tablename__ = 'course_user'
    _cols,_infos = rename_columns(__tablename__, sa.join(model_tables.User,model_tables.Enrollment).join(model_tables.Course))
    __table__ = create_view(__tablename__, _cols, database.ViewBase.metadata, cascade_on_drop=False)
    _set_colinfo(__table__.c, _infos)
    __col_order__ = [__table__.c.id,__table__.c.role,__table__.c.is_admin]
    __col_hide__ = [__table__.c.course_id, __table__.c.course_canvas_id, __table__.c.course_name,__table__.c.course_slug]

    def __setattr__(self, __name: str, __value: Any) -> None:
        if isinstance(__value, sa.orm.InstanceState):
            return super().__setattr__(__name, __value)
        else:
            print(__name, __value, type(__value))
            raise TypeError(f'{self.__class__.__name__} is immutable/read-only')


def _init(tbl, src_cols):
    cols = list(src_cols)
    infos = [c.info for c in src_cols]
    providers = model_tables.ACCOUNT_PROVIDERS
    ps = list(providers)
    p = ps[0]
    sel = sa.join(tbl, model_tables.Account, sa.and_(tbl.id == model_tables.Account.user_id, model_tables.Account.provider_name == p))
    cols = cols + [model_tables.Account.external_id.label(f'{p}_id'), model_tables.Account.username.label(f'{p}_username')]
    infos = infos + [model_tables.Account.external_id.info, model_tables.Account.username.info]
    #sel = sel.add_columns(Account.external_id.label(f'{p.name}_id'), Account.username.label(f'{p.name}_username'))
    for p in ps[1:]:
        acc = sa.alias(model_tables.Account, f'{p}_account')
        sel = sel.outerjoin(acc, sa.and_(tbl.id == acc.c.user_id, acc.c.provider_name == p))
        cols = cols + [acc.c.external_id.label(f'{p}_id'), acc.c.username.label(f'{p}_username')]
        infos = infos + [model_tables.Account.external_id.info, model_tables.Account.username.info]
    #    sel = sel.add_columns(acc.c.external_id.label(f'{p.name}_id'), acc.c.username.label(f'{p.name}_username'))

    return sa.select(*cols).select_from(sel), infos


class UserAccount(database.ViewBase):
    __tablename__ = 'user_account'
    _cols,_infos = _init(model_tables.User, [model_tables.User.id])
    __table__ = create_view(__tablename__, _cols, database.ViewBase.metadata, cascade_on_drop=False)
    _set_colinfo(__table__.c, _infos)


    def __setattr__(self, __name: str, __value: Any) -> None:
        if isinstance(__value, sa.orm.InstanceState):
            return super().__setattr__(__name, __value)
        else:
            print(__name, __value, type(__value))
            raise TypeError(f'{self.__class__.__name__} is immutable/read-only')

class FullUser(database.ViewBase):
    __tablename__ = 'full_user'
    _cols,_infos = _init(CourseUser, CourseUser.__table__.c)
    __table__ = create_view(__tablename__, _cols, database.ViewBase.metadata, cascade_on_drop=False)
    _set_colinfo(__table__.c, _infos)


    def __setattr__(self, __name: str, __value: Any) -> None:
        if isinstance(__value, sa.orm.InstanceState):
            return super().__setattr__(__name, __value)
        else:
            print(__name, __value, type(__value))
            raise TypeError(f'{self.__class__.__name__} is immutable/read-only')
