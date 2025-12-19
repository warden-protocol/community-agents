"""ASGI transport that lets you schedule to the main loop.

Adapted from: https://github.com/encode/httpx/blob/6c7af967734bafd011164f2a1653abc87905a62b/httpx/_transports/asgi.py#L1
"""

from __future__ import annotations

import typing

from httpx import ASGITransport as ASGITransportBase
from httpx import AsyncByteStream, Request, Response

if typing.TYPE_CHECKING:  # pragma: no cover
    import asyncio

    import trio  # type: ignore[unresolved-import]

    Event = asyncio.Event | trio.Event

__all__ = ["ASGITransport"]


def is_running_trio() -> bool:
    try:
        # sniffio is a dependency of trio.

        # See https://github.com/python-trio/trio/issues/2802
        import sniffio  # type: ignore[unresolved-import]

        if sniffio.current_async_library() == "trio":
            return True
    except ImportError:  # pragma: nocover
        pass

    return False


def create_event() -> Event:
    if is_running_trio():
        import trio  # type: ignore[unresolved-import]

        return trio.Event()

    import asyncio

    return asyncio.Event()


class ASGIResponseStream(AsyncByteStream):
    def __init__(self, body: list[bytes]) -> None:
        self._body = body

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield b"".join(self._body)


class ASGITransport(ASGITransportBase):
    """
    A custom AsyncTransport that handles sending requests directly to an ASGI app.

    ```python
    transport = httpx.ASGITransport(
        app=app,
        root_path="/submount",
        client=("1.2.3.4", 123)
    )
    client = httpx.AsyncClient(transport=transport)
    ```

    Arguments:

    * `app` - The ASGI application.
    * `raise_app_exceptions` - Boolean indicating if exceptions in the application
       should be raised. Default to `True`. Can be set to `False` for use cases
       such as testing the content of a client 500 response.
    * `root_path` - The root path on which the ASGI application should be mounted.
    * `client` - A two-tuple indicating the client IP and port of incoming requests.
    ```
    """

    async def handle_async_request(
        self,
        request: Request,
    ) -> Response:
        from langgraph_api.asyncio import call_soon_in_main_loop

        if not isinstance(request.stream, AsyncByteStream):
            raise ValueError("Request stream must be an AsyncByteStream")

        # ASGI scope.
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": request.method,
            "headers": [(k.lower(), v) for (k, v) in request.headers.raw],
            "scheme": request.url.scheme,
            "path": request.url.path,
            "raw_path": request.url.raw_path.split(b"?")[0],
            "query_string": request.url.query,
            "server": (request.url.host, request.url.port),
            "client": self.client,
            "root_path": self.root_path,
        }

        # Request.
        request_body_chunks = request.stream.__aiter__()
        request_complete = False

        # Response.
        status_code = None
        response_headers = None
        body_parts = []
        response_started = False
        response_complete = create_event()

        # ASGI callables.

        async def receive() -> dict[str, typing.Any]:
            nonlocal request_complete

            if request_complete:
                await response_complete.wait()
                return {"type": "http.disconnect"}

            try:
                body = await request_body_chunks.__anext__()
            except StopAsyncIteration:
                request_complete = True
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.request", "body": body, "more_body": True}

        async def send(message: typing.MutableMapping[str, typing.Any]) -> None:
            nonlocal status_code, response_headers, response_started

            if message["type"] == "http.response.start":
                if response_started:
                    raise RuntimeError("Response already started")
                status_code = message["status"]
                response_headers = message.get("headers", [])
                response_started = True

            elif message["type"] == "http.response.body":
                if response_complete.is_set():
                    raise RuntimeError("Response already complete")
                body = message.get("body", b"")
                more_body = message.get("more_body", False)

                if body and request.method != "HEAD":
                    body_parts.append(body)

                if not more_body:
                    response_complete.set()

        try:
            await call_soon_in_main_loop(self.app(scope, receive, send))
        except Exception:
            if self.raise_app_exceptions:
                raise

            response_complete.set()
            if status_code is None:
                status_code = 500
            if response_headers is None:
                response_headers = {}

        if not response_complete.is_set():
            raise RuntimeError("Response not complete")
        if status_code is None:
            raise RuntimeError("Status code not set")
        if response_headers is None:
            raise RuntimeError("Response headers not set")

        stream = ASGIResponseStream(body_parts)

        return Response(status_code, headers=response_headers, stream=stream)
