from datetime import datetime
import enum
from io import TextIOWrapper
import json
from typing import Any
from flask import Flask
from sqlalchemy import Column, MetaData, Table, create_engine, select, event
from sqlalchemy.orm import scoped_session, sessionmaker, DeclarativeBase, Query,MappedAsDataclass
from puffin import settings
from werkzeug.security import generate_password_hash

engine = create_engine(settings.DB_URL, echo=True, future=True)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
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

    def __repr__(self):
        return json.dumps(self.to_json())

class Base(PreBase, DeclarativeBase):
    metadata = _meta
class ViewBase(PreBase, DeclarativeBase):
    metadata = _viewmeta

def init(app:Flask):
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    from . import model, auth_model
    for cls in model.logged_tables:
        model.create_triggers(cls, db_session)

    _viewmeta.drop_all(engine)
    _viewmeta.create_all(engine)
    if app and app.config['PUFFIN_SUPER_USER'] and app.config['PUFFIN_SUPER_PASSWORD']:
        super_user, created = model.get_or_define(db_session, model.User, {'id':0,'key':'internal#root'},
            {'firstname':'Dr.','lastname':'Superpuff','is_admin':True,'email':app.config['PUFFIN_SUPER_USER']})
        if created:
            super_user.password = generate_password_hash(app.config['PUFFIN_SUPER_PASSWORD'])

    #Base.metadata.create_all(engine)
    Base.query = db_session.query_property()
    model.setup_providers()

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
    return select(*cols).select_from(source), info
