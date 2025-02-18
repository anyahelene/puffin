import sqlalchemy as sa
from sqlalchemy.ext import compiler
from sqlalchemy.schema import DDLElement
from sqlalchemy.sql import table

class CreateView(DDLElement):
    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable


class DropView(DDLElement):
    def __init__(self, name):
        self.name = name


@compiler.compiles(CreateView)
def _create_view(element, compiler, **kw):
    return "CREATE VIEW %s AS %s" % (
        element.name,
        compiler.sql_compiler.process(element.selectable, literal_binds=True),
    )


@compiler.compiles(DropView)
def _drop_view(element, compiler, **kw):
    return "DROP VIEW %s" % (element.name)


def view_exists(ddl, target, connection, **kw):
    return ddl.name in sa.inspect(connection).get_view_names()


def view_doesnt_exist(ddl, target, connection, **kw):
    return not view_exists(ddl, target, connection, **kw)

def view(name, metadata, selectable):
    t = table(name)
    cols = []
    for col in selectable.selected_columns:
        viewspecs = col.info.get('view', {})
        spec = viewspecs.get(name, True)
        if type(spec) == str:
            cols.append(col._make_proxy(t, name=spec))
            print('col',cols[-1])
        elif spec and not col.info.get('secret', False):
            cols.append(col._make_proxy(t))
    print(cols)

    t._columns._populate_separate_keys(cols)

    sa.event.listen(
        metadata,
        "after_create",
        CreateView(name, selectable).execute_if(callable_=view_doesnt_exist), # type: ignore
    )
    sa.event.listen(
        metadata, "before_drop", DropView(name).execute_if(callable_=view_exists) # type: ignore
    )
    return t


if __name__ == "__main__":

    engine = sa.create_engine("sqlite://", echo=True)
    metadata = sa.MetaData()
    stuff = sa.Table(
        "stuff",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("data", sa.String(50)),
    )

    more_stuff = sa.Table(
        "more_stuff",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("stuff_id", sa.Integer, sa.ForeignKey("stuff.id")),
        sa.Column("data", sa.String(50)),
    )

    # the .label() is to suit SQLite which needs explicit label names
    # to be given when creating the view
    # See http://www.sqlite.org/c3ref/column_name.html
    stuff_view = view(
        "stuff_view",
        metadata,
        sa.select(
            stuff.c.id.label("id"),
            stuff.c.data.label("data"),
            more_stuff.c.data.label("moredata"),
        )
        .select_from(stuff.join(more_stuff))
        .where(stuff.c.data.like(("%orange%"))),
    )

    assert stuff_view.primary_key == [stuff_view.c.id]

    with engine.begin() as conn:
        metadata.create_all(conn)

    with engine.begin() as conn:
        conn.execute(
            stuff.insert(),
            [
                {"data": "apples"},
                {"data": "pears"},
                {"data": "oranges"},
                {"data": "orange julius"},
                {"data": "apple jacks"},
            ],
        )

        conn.execute(
            more_stuff.insert(),
            [
                {"stuff_id": 3, "data": "foobar"},
                {"stuff_id": 4, "data": "foobar"},
            ],
        )

    with engine.connect() as conn:
        assert conn.execute(
            sa.select(stuff_view.c.data, stuff_view.c.moredata)
        ).all() == [("oranges", "foobar"), ("orange julius", "foobar")]

    # illustrate ORM usage
    from sqlalchemy.orm import declarative_base
    from sqlalchemy.orm import Session

    Base = declarative_base(metadata=metadata)

    class MyStuff(Base):
        __table__ = stuff_view

        def __repr__(self):
            return f"MyStuff({self.id!r}, {self.data!r}, {self.moredata!r})"

    with Session(engine) as s:
        print(s.query(MyStuff).all())