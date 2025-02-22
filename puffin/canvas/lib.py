from flask import current_app
from typing import Any
import enum
import re
from flask import Flask, current_app
import re
import logging

from slugify import slugify
from puffin.util.apicalls import ApiConnection, ObjectLikeDict, Undefined, all_attrs, required_attrs

logger = logging.getLogger(__name__)

class CanvasConnection(ApiConnection):

    def __init__(
        self, app_or_base_url: Flask | str | None = None, token: str | None = None
    ):
        if isinstance(app_or_base_url, Flask):
            app = app_or_base_url
            app.extensions["puffin_canvas_connection"] = self
            base_url = ''
        else:
            app = current_app
            base_url = app_or_base_url
        if app:
            base_url = base_url or app.config.get("CANVAS_BASE_URL")
            token = token or app.config.get("CANVAS_SECRET_TOKEN")

        super().__init__(base_url or '', token or '')

        self.terms = {}

    def get_term(self, root, term_id) -> dict[str, Any]:
        term = self.maybe_get_term(root, term_id, raise_on_error=True)
        assert term != None
        return term

    def maybe_get_term(self, root, term_id, raise_on_error=False):
        result = self.terms.get((root, term_id))
        if not result:
            result = self.maybe_request(
                "GET", f"accounts/{root}/terms/{term_id}", raise_on_error=raise_on_error
            )
            if result:
                mo = re.match(r"^(\w).*(\d\d)$", result.get("name", ""))
                if mo:
                    result["term_slug"] = f"{mo.group(2)}{mo.group(1).lower()}"
                else:
                    result["term_slug"] = slugify(result["name"])
                self.terms[(root, term_id)] = result
        return result

    def course(self, id: int, stub: bool = False, **kwargs):
        from .canvas import CanvasCourse
        return CanvasCourse.by_id(self, id, stub=stub, **kwargs)

    def group(self, id: int, stub: bool = False, **kwargs):
        from .canvas import CanvasGroup
        return CanvasGroup.by_id(self, id, stub=stub, **kwargs)

    def group_category(self, id: int, stub: bool = False, **kwargs):
        from .canvas import CanvasGroupCategory
        return CanvasGroupCategory.by_id(self, id, stub=stub, **kwargs)


if globals().get("connection"):
    print("reload!")
    globals()["connection"] = CanvasConnection(
        globals()["connection"].base_url, globals()["connection"].token
    )

GroupJoinLevels = enum.StrEnum(
    "GroupJoinLevels",
    ["parent_context_auto_join", "parent_context_request", "invitation_only"],
)


camelcase_pattern = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def typename(cls_or_object):
    if not isinstance(cls_or_object, type):
        return typename(cls_or_object.__class__)
    if hasattr(cls_or_object, "__typename__"):
        return cls_or_object.__typename__
    else:
        return camelcase_pattern.sub(
            "_", cls_or_object.__name__.removeprefix("Canvas")
        ).lower()


class CanvasObject(ObjectLikeDict):
    id: int

    def __init__(self, conn: CanvasConnection, data: dict):
        self.conn = conn
        super().__init__(data)

    @classmethod
    def by_id(cls, conn: CanvasConnection, id: int, stub: bool = False, **kwargs):
        if stub == True:
            data = {"id": id}
            data.update(kwargs)
            return cls(conn, data)
        path = getattr(cls, "__get_path__", typename(cls) + "s/{id}").format(
            id=id, **kwargs
        )
        result = conn.get_single(path)
        return cls(conn, result)


class CanvasCreatableObject(CanvasObject):
    @classmethod
    def create(cls, conn: CanvasConnection, **kwargs):
        path = getattr(cls, "__create_path__").format(id=id, **kwargs)
        for n, t, _ in required_attrs(cls):
            if not isinstance(kwargs.get(n), t):
                raise AttributeError(f"missing expected parameter: {n} : {t.__name__}")
        params = {}
        for n, t, d in all_attrs(cls):
            if n in kwargs:
                params[n] = kwargs[n]
            elif d is not Undefined:
                params[n] = d
        print("payload", params)
        result = conn.post(path, params)
        return cls(conn, result)
