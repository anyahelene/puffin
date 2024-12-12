from collections import UserDict, namedtuple
from flask import current_app
from typing import Any, Iterable, Self, Annotated
import typing
import enum
import re
import csv
import json
import os
from flask import Flask, current_app
import requests
import re
import logging

from slugify import slugify
from puffin.util.errors import ErrorResponse

logger = logging.getLogger(__name__)

LogEntry = namedtuple('LogEntry', ['msg', 'method', 'url', 'params', 'headers', 'result'])
class CanvasConnection:

    def __init__(
        self, app_or_base_url: Flask | str | None = None, token: str | None = None
    ):
        if isinstance(app_or_base_url, Flask):
            app = app_or_base_url
            app.extensions["puffin_canvas_connection"] = self
            base_url = None
        else:
            app = current_app
            base_url = app_or_base_url
        if app:
            base_url = base_url or app.config.get("CANVAS_BASE_URL")
            token = token or app.config.get("CANVAS_SECRET_TOKEN")
        self.token = token
        self.base_url = base_url
        self.terms = {}
        self.log = []

    def get_single(self, endpoint, params={}, headers={}) -> dict[str, Any]:
        result = self.maybe_request(
            "GET", endpoint, params=params, headers=headers, raise_on_error=True
        )
        assert result != None
        return result

    def post(self, endpoint, params={}, headers={}, debug=False) -> dict[str, Any]:
        result = self.maybe_request(
            "POST",
            endpoint,
            params=params,
            headers=headers,
            raise_on_error=True,
            debug=debug,
        )
        assert result != None
        return result

    def put(self, endpoint, params={}, headers={}, debug=False) -> dict[str, Any]:
        result = self.maybe_request(
            "PUT",
            endpoint,
            params=params,
            headers=headers,
            raise_on_error=True,
            debug=debug,
        )
        assert result != None
        return result

    def request(
        self, method, endpoint, params={}, headers={}, debug=True, do_nothing=False
    ) -> dict[str, Any]:
        result = self.maybe_request(
            method,
            endpoint,
            params=params,
            headers=headers,
            raise_on_error=True,
            debug=debug,
            do_nothing=do_nothing,
        )
        assert result != None
        return result

    def maybe_request(
        self,
        method,
        endpoint,
        params={},
        headers={},
        raise_on_error=False,
        debug=True,
        do_nothing=False,
    ) -> dict[str, Any] | None:
        url = f"{self.base_url}{endpoint}"

        log_entry = self.debug_request(method, url, params, headers, debug)
        self.log.insert(0, log_entry)
        
        if do_nothing:
            return params

        headers["Authorization"] = f"Bearer {self.token}"

        req = requests.request(method, url, json=params, headers=headers)
        if req.ok:
            log_entry = log_entry._replace(result=req.json())
            return log_entry.result
        elif not raise_on_error:
            return None
        else:
            log_entry = log_entry._replace(result=req.status_code)
            logger.error(
                f"Request failed: {self.base_url}{endpoint} {req.status_code} {req.reason}"
            )
            raise ErrorResponse(
                f"Request failed: {req.reason}", endpoint, status_code=req.status_code
            )

    def debug_request(self, method, url, params, headers, debug) -> LogEntry:
        params = params or {}
        headers = {k:headers[k] for k in headers or {} if k not in ['Authorization','Cookie']}
        logger.info(
            "CanvasConnection:  %s %s%sparams=%s%sheaders=%s",
            method,
            url,
            '\n\t' if debug and len(params) > 0 else ', ',
            json.dumps(params),
            '\n\t' if debug and len(headers) > 0 else ', ',
            json.dumps(headers),
        )
        return LogEntry(f'{method} {url}', method, url, params, headers, None)

    def get_paginated(self, endpoint, params={}, headers={}) -> list[dict[str, Any]]:
        result = self.maybe_get_paginated(
            endpoint, params=params, headers=headers, raise_on_error=True
        )
        assert result != None
        return result

    def maybe_get_paginated(
        self, endpoint, params={}, headers={}, raise_on_error=False, debug=True
    ) -> list[dict[str, Any]] | None:
        headers["Authorization"] = f"Bearer {self.token}"
        results = []
        endpoint = f"{self.base_url}{endpoint}"
        params['per_page'] = 200
        while endpoint != None:
            log_entry = self.debug_request('GET*', endpoint, params, headers, debug)
            self.log.insert(0, log_entry)
            
            req = requests.get(endpoint, params=params, headers=headers)
            
            if req.ok:
                results = results + req.json()
                if "next" in req.links:
                    endpoint = req.links["next"]["url"]
                else:
                    endpoint = None
                params = None
            elif raise_on_error:
                log_entry = log_entry._replace(result=req.status_code)
                logger.error(
                    f"Request failed: {endpoint} {req.status_code} {req.reason}"
                )
                raise ErrorResponse(
                    f"Request failed: {req.reason}",
                    endpoint,
                    status_code=req.status_code,
                )
            else:
                return None
        log_entry = log_entry._replace(result=results)
        return results

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



class ObjectLikeDict(UserDict):
    def __init__(self, data={}):
        self.__readonly__ = set(["data", "__readonly__"])
        super().__init__(data)

    def __getattr__(self, name):
        if name not in self.data:
            raise AttributeError(name)
        return self.data[name]

    def __setattr__(self, name, value):
        #print("setattr", name, value)
        if "data" not in self.__dict__:
            #print("presetattr", name, value)
            super().__setattr__(name, value)
        #                raise AttributeError(f"{type(self).__name__} object attribute 'data' is read-only")
        elif name not in self.__readonly__ or name not in self.data:
            self.data[name] = value
        else:
            raise AttributeError(
                f"{type(self).__name__} object attribute '{name}' is read-only"
            )

    def __delattr__(self, name):
        del super().data[name]

    def __dir__(self):
        return [*super().__dir__(), *self.data.keys()]  # , *super().data.keys()]


GroupJoinLevels = enum.StrEnum(
    "GroupJoinLevels",
    ["parent_context_auto_join", "parent_context_request", "invitation_only"],
)

type Required[T] = Annotated[T, "required"]
type Optional[T] = Annotated[T, "optional"]
type ReadOnly[T] = Annotated[T, "readonly"]


def __create_undefined__():
    class Undefined:
        def __str__(self):
            return "Undefined"

        def __repr__(self):
            return "Undefined"

    return Undefined()


Undefined = __create_undefined__()


def required_attrs(cls):
    annos = cls.__annotations__
    return [
        (k, typing.get_args(annos[k])[0], None)
        for k in annos
        if typing.get_origin(annos[k]) == Required
    ]


def all_attrs(cls):
    annos = typing.get_type_hints(cls, include_extras=True)
    return [(k, annos[k], cls.__dict__.get(k, Undefined)) for k in annos]


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
