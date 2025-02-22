from collections import UserDict, namedtuple
import os
from flask import current_app
from typing import Any, Annotated
import typing
import re
import json
from flask import Flask, current_app
import requests
import re
import logging

from puffin.util.errors import ErrorResponse

logger = logging.getLogger(__name__)

LogEntry = namedtuple('LogEntry', ['msg', 'method', 'url', 'params', 'headers', 'result'])
class ApiConnection:

    def __init__(
        self, base_url: str, token: str
    ):
        self.token = token
        self.base_url = base_url
        self.log = []

    def get_single(self, endpoint, params={}, headers={}, use_form=False) -> dict[str, Any]:
        result = self.maybe_request(
            "GET", endpoint, params=params, headers=headers, raise_on_error=True, use_form=use_form
        )
        assert result != None
        return result

    def post(self, endpoint, params={}, headers={}, debug=False, use_form=False) -> dict[str, Any]:
        result = self.maybe_request(
            "POST",
            endpoint,
            params=params,
            headers=headers,
            raise_on_error=True,
            debug=debug,
            use_form=use_form
        )
        assert result != None
        return result

    def put(self, endpoint, params={}, headers={}, debug=False, use_form=False) -> dict[str, Any]:
        result = self.maybe_request(
            "PUT",
            endpoint,
            params=params,
            headers=headers,
            raise_on_error=True,
            debug=debug,
            use_form=use_form
        )
        assert result != None
        return result

    def request(
        self, method, endpoint, params={}, headers={}, debug=True, do_nothing=False, use_form=False
    ) -> dict[str, Any]:
        result = self.maybe_request(
            method,
            endpoint,
            params=params,
            headers=headers,
            raise_on_error=True,
            debug=debug,
            do_nothing=do_nothing,
            use_form=use_form
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
        use_form=False
    ) -> dict[str, Any] | None:
        url = f'{self.base_url.rstrip("/")}/{endpoint.lstrip("/")}'

        log_entry = self.debug_request(method, url, params, headers, debug)
        self.log.insert(0, log_entry)
        
        if do_nothing:
            return params

        headers["Authorization"] = f"Bearer {self.token}"
        # TODO: add Accept
        if use_form:
            req = requests.request(method, url, params=params, headers=headers)
        else:
            req = requests.request(method, url, json=params, headers=headers)

        if req.ok:
            if 'json' in req.headers.get('Content-Type', ''):
                log_entry = log_entry._replace(result=req.json())
            else:
                log_entry = log_entry._replace(result={'status':'ok', 'data':req.text})
            return log_entry.result
        elif not raise_on_error:
            return None
        else:
            if 'json' in req.headers.get('Content-Type', ''):
                result = req.json()
                result['status_code'] = req.status_code
            else:
                result ={'status':'error', 'status_code':req.status_code, 'data':req.text}
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
            "ApiConnection:  %s %s%sparams=%s%sheaders=%s",
            method,
            url,
            '\n\t' if debug and len(params) > 0 else ', ',
            json.dumps(params),
            '\n\t' if debug and len(headers) > 0 else ', ',
            json.dumps(headers),
        )
        return LogEntry(f'{method} {url}', method, url, params, headers, None)

    def get_paginated(self, endpoint, params={}, headers={}, use_form=False) -> list[dict[str, Any]]:
        result = self.maybe_get_paginated(
            endpoint, params=params, headers=headers, raise_on_error=True, use_form=use_form
        )
        assert result != None
        return result

    def maybe_get_paginated(
        self, endpoint, params={}, headers={}, raise_on_error=False, debug=True, use_form=False
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
