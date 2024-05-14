"""
X-Real-IP Proxy Fix
Based on X-Forwarded-For Proxy fix from werkzeug.middleware.proxy_fix
=========================

This module provides a middleware that adjusts the WSGI environ based on
the ``X-Real-IP`` header that a proxy in front of an application may
set.

When an application is running behind a proxy server, WSGI may see the
request as coming from that server rather than the real client. Proxies
set various headers to track where the request actually came from.

This middleware should only be used if the application is actually
behind such a proxy, and should be configured with the number of proxies
that are chained in front of it. Not all proxies set all the headers.
Since incoming headers can be faked, you must set how many proxies are
setting each header so the middleware knows what to trust.

.. autoclass:: ProxyFix

:copyright: 2007 Pallets
:license: BSD-3-Clause
"""
from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from _typeshed.wsgi import StartResponse
    from _typeshed.wsgi import WSGIApplication
    from _typeshed.wsgi import WSGIEnvironment


class ProxyFix:
    """Adjust the WSGI environ based on ``X-Forwarded-`` that proxies in
    front of the application may set.

    -   ``X-Real-IP`` sets ``REMOTE_ADDR``.

    You must tell the middleware how many proxies set each header so it
    knows what values to trust. It is a security issue to trust values
    that came from the client rather than a proxy.

    The original values of the headers are stored in the WSGI
    environ as ``werkzeug.proxy_fix.orig``, a dict.

    :param app: The WSGI application to wrap.

    .. code-block:: python

        from werkzeug.middleware.proxy_fix import ProxyFix
        # App is behind one proxy that sets the -For and -Host headers.
        app = ProxyFix(app, x_for=1, x_host=1)
    """

    def __init__(
        self,
        app: WSGIApplication,
    ) -> None:
        self.app = app

    def __call__(
        self, environ: WSGIEnvironment, start_response: StartResponse
    ) -> t.Iterable[bytes]:
        """Modify the WSGI environ based on the various ``Forwarded``
        headers before calling the wrapped application. Store the
        original environ values in ``werkzeug.proxy_fix.orig_{key}``.
        """
        environ_get = environ.get
        orig_remote_addr = environ_get("REMOTE_ADDR")

        environ.update(
            {
                    "ORIG_REMOTE_ADDR": orig_remote_addr,
            }
        )

        x_real_ip = environ_get("HTTP_X_REAL_IP")

        return self.app(environ, start_response)
