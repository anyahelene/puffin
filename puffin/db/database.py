from datetime import datetime
import enum
from io import TextIOWrapper
import json
from typing import Any, cast
from flask import Flask
from sqlalchemy import Column, MetaData, Table, create_engine, select, event
from sqlalchemy.orm import Session, scoped_session, sessionmaker, DeclarativeBase, Query,MappedAsDataclass
from werkzeug.security import generate_password_hash

from puffin.util.util import DateEncoder

db_scoped_session : scoped_session = scoped_session(sessionmaker())
db_session : Session = cast(Session, db_scoped_session)

def configure(app:Flask):
    global engine
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], echo=False, future=True)
    db_scoped_session.configure(autocommit=False,
                         autoflush=False,
                         bind=engine)
_naming_convention = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_`%(constraint_name)s`",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
      }
_meta = MetaData(naming_convention=_naming_convention)
_viewmeta = MetaData(naming_convention=_naming_convention)
class PreBase():
    __table__ : Table
    __tablename__ : str

    def __setattr__(self, __name: str, __value: Any) -> None:
        if not hasattr(self, __name) or getattr(self, __name) != __value:
            return super().__setattr__(__name, __value)

    def to_json(self):
        def col_json(col):
            val = getattr(self, col.key)
            if isinstance(val, enum.Enum):
                return val.name
            else:
                return val
        result = {col.key : col_json(col) for col in self.__table__.c if not col.info.get('secret', False)}
        result['_type'] = self.__tablename__
        return result
    
    def to_result(self, privileged=False):
        def col_json(col):
            val = getattr(self, col.key)
            if isinstance(val, enum.Enum):
                return val.name
            else:
                return val
        result : dict[str,Any] = {col.key : col_json(col) for col in self.__table__.c if not col.info.get('secret', False)}
        if not privileged:
            if 'json_data' in result:
                tmp = result.copy()
                allowed = getattr(self, 'info', {}).get('public_json', [])
                result['json_data'] = {k:v for k,v in result['json_data'].items() if k in allowed}
                print('PROTECT', allowed, tmp.get('json_data'), result.get('json_data'))
        result['_type'] = self.__tablename__
        return result

    def __repr__(self):
        return json.dumps(self.to_json(), cls=DateEncoder)

class Base(PreBase, DeclarativeBase):
    metadata = _meta
class ViewBase(PreBase, DeclarativeBase):
    metadata = _viewmeta

def init(app:Flask|None):
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    from . import auth_model, model_tables, model_views, model_util
    for cls in model_tables.logged_tables:
        model_util.create_triggers(cls, db_scoped_session)

    _viewmeta.drop_all(engine)
    _viewmeta.create_all(engine)
    if app and app.config.get('PUFFIN_SUPER_USER') and app.config.get('PUFFIN_SUPER_PASSWORD'):
        super_user, created = model_util.get_or_define(db_scoped_session, model_tables.User, {'id':0,'key':'internal#root'},
            {'firstname':'Dr.','lastname':'Superpuff','is_admin':True,'email':app.config['PUFFIN_SUPER_USER']})
        if created:
            super_user.password = generate_password_hash(app.config['PUFFIN_SUPER_PASSWORD'])
        db_scoped_session.commit()

    #Base.metadata.create_all(engine)
    Base.query = db_scoped_session.query_property()

