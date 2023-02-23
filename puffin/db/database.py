import json
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, DeclarativeBase, Query
from puffin import settings

engine = create_engine(settings.DB_URL, echo=False, future=True)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
_meta = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_`%(constraint_name)s`",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
      })
      
class Base(DeclarativeBase):
    metadata = _meta
    query: Query
    pass

    def __repr__(self):
        if hasattr(self, 'to_json'):
            return json.dumps(self.to_json())
        else:
            return super().__repr__()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    from . import model, auth_model
    for cls in model.logged_tables:
        model.create_triggers(cls, db_session)

    #Base.metadata.create_all(engine)
    Base.query = db_session.query_property()
    model.setup_providers()

