import contextvars
import re
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Protocol, TypeAlias, TypeVar, cast

import structlog
from langgraph_sdk import Auth
from starlette.authentication import AuthCredentials, BaseUser
from starlette.exceptions import HTTPException
from starlette.schemas import BaseSchemaGenerator

from langgraph_api.auth.custom import SimpleUser
from langgraph_api.utils.uuids import uuid7

logger = structlog.stdlib.get_logger(__name__)


T = TypeVar("T")
Row: TypeAlias = dict[str, Any]
AuthContext = contextvars.ContextVar[Auth.types.BaseAuthContext | None](
    "AuthContext", default=None
)
STREAM_ID_PATTERN = re.compile(r"^\d+(-(\d+|\*))?$")


@asynccontextmanager
async def with_user(
    user: BaseUser | None = None, auth: AuthCredentials | list[str] | None = None
):
    current = get_auth_ctx()
    set_auth_ctx(user, auth)
    yield
    if current is None:
        return
    set_auth_ctx(
        cast("BaseUser", current.user), AuthCredentials(scopes=current.permissions)
    )


def set_auth_ctx(
    user: BaseUser | None, auth: AuthCredentials | list[str] | None
) -> None:
    if user is None and auth is None:
        AuthContext.set(None)
    else:
        AuthContext.set(
            Auth.types.BaseAuthContext(
                permissions=(
                    auth.scopes if isinstance(auth, AuthCredentials) else (auth or [])
                ),
                user=user or SimpleUser(""),
            )
        )


def get_auth_ctx() -> Auth.types.BaseAuthContext | None:
    return AuthContext.get()


def get_user_id(user: BaseUser | None) -> str | None:
    if user is None:
        return None
    try:
        return user.identity
    except NotImplementedError:
        try:
            return user.display_name
        except NotImplementedError:
            pass


class AsyncCursorProto(Protocol):
    async def fetchone(self) -> Row: ...

    async def fetchall(self) -> list[Row]: ...

    async def __aiter__(self) -> AsyncIterator[Row]:
        yield ...


class AsyncPipelineProto(Protocol):
    async def sync(self) -> None: ...


class AsyncConnectionProto(Protocol):
    @asynccontextmanager
    async def pipeline(self) -> AsyncIterator[AsyncPipelineProto]:
        yield ...

    async def execute(self, query: str, *args, **kwargs) -> AsyncCursorProto: ...


async def fetchone(
    it: AsyncIterator[T],
    *,
    not_found_code: int = 404,
    not_found_detail: str | None = None,
) -> T:
    """Fetch the first row from an async iterator."""
    try:
        return await anext(it)
    except StopAsyncIteration:
        raise HTTPException(
            status_code=not_found_code, detail=not_found_detail
        ) from None


def validate_uuid(uuid_str: str, invalid_uuid_detail: str | None) -> uuid.UUID:
    try:
        return uuid.UUID(uuid_str)
    except ValueError:
        raise HTTPException(status_code=422, detail=invalid_uuid_detail) from None


def validate_stream_id(stream_id: str | None, invalid_stream_id_detail: str | None):
    """
    Validate Redis stream ID format.
    Valid formats:
    - timestamp-sequence (e.g., "1724342400000-0")
    - timestamp-* (e.g., "1724342400000-*")
    - timestamp only (e.g., "1724342400000")
    - "-" (special case, represents the beginning of the stream, use if you want to replay all events)
    """
    if not stream_id or stream_id == "-":
        return stream_id

    if STREAM_ID_PATTERN.match(stream_id):
        return stream_id
    raise HTTPException(status_code=422, detail=invalid_stream_id_detail)


def next_cron_date(schedule: str, base_time: datetime) -> datetime:
    import croniter  # type: ignore[unresolved-import]

    cron_iter = croniter.croniter(schedule, base_time)
    return cron_iter.get_next(datetime)


class SchemaGenerator(BaseSchemaGenerator):
    def __init__(self, base_schema: dict[str, Any]) -> None:
        self.base_schema = base_schema

    def get_schema(self, routes: list) -> dict[str, Any]:
        schema = dict(self.base_schema)
        schema.setdefault("paths", {})
        endpoints_info = self.get_endpoints(routes)

        for endpoint in endpoints_info:
            try:
                parsed = self.parse_docstring(endpoint.func)
            except AssertionError:
                logger.warning("Could not parse docstrings for route %s", endpoint.path)
                parsed = {}

            if endpoint.path not in schema["paths"]:
                schema["paths"][endpoint.path] = {}

            schema["paths"][endpoint.path][endpoint.http_method] = parsed

        return schema


async def get_pagination_headers(
    resource: AsyncIterator[T],
    next_offset: int | None,
    offset: int,
) -> tuple[list[T], dict[str, str]]:
    resources = [r async for r in resource]
    if next_offset is None:
        response_headers = {"X-Pagination-Total": str(len(resources) + offset)}
    else:
        response_headers = {
            "X-Pagination-Total": str(next_offset + 1),  # Next offset will be "n"
            "X-Pagination-Next": str(next_offset),
        }
    return resources, response_headers


def validate_select_columns(
    select: list[str] | None, allowed: set[str]
) -> list[str] | None:
    """Validate select columns against an allowed set.

    Returns the input list (or None) if valid, otherwise raises HTTP 422.
    """
    if not select:
        return None
    invalid = [col for col in select if col not in allowed]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid select columns: {invalid}. Expected: {allowed}",
        )
    return select


__all__ = [
    "AsyncConnectionProto",
    "AsyncCursorProto",
    "AsyncPipelineProto",
    "SchemaGenerator",
    "fetchone",
    "get_pagination_headers",
    "next_cron_date",
    "uuid7",
    "validate_select_columns",
    "validate_uuid",
]
