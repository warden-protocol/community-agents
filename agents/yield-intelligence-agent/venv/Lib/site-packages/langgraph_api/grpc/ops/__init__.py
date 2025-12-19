"""gRPC-based operations for LangGraph API."""

from __future__ import annotations

import asyncio
import functools
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, overload

import orjson
import structlog
from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import Struct  # type: ignore[import]
from grpc import StatusCode
from grpc.aio import AioRpcError
from langgraph_sdk.schema import Config
from starlette.exceptions import HTTPException

from langgraph_api.auth.custom import handle_event as auth_handle_event
from langgraph_api.grpc.generated import core_api_pb2 as pb
from langgraph_api.serde import json_dumpb
from langgraph_api.utils import get_auth_ctx

if TYPE_CHECKING:
    from langgraph_api.schema import Context

__all__ = ["Assistants", "Threads"]

logger = structlog.stdlib.get_logger(__name__)

GRPC_STATUS_TO_HTTP_STATUS = {
    StatusCode.NOT_FOUND: HTTPStatus.NOT_FOUND,
    StatusCode.ALREADY_EXISTS: HTTPStatus.CONFLICT,
    StatusCode.INVALID_ARGUMENT: HTTPStatus.UNPROCESSABLE_ENTITY,
}


def map_if_exists(if_exists: str) -> Any:
    """Map if_exists string to protobuf OnConflictBehavior."""
    from langgraph_api.grpc.generated import core_api_pb2 as pb

    if if_exists == "do_nothing":
        return pb.OnConflictBehavior.DO_NOTHING
    return pb.OnConflictBehavior.RAISE


@overload
def consolidate_config_and_context(
    config: Config | None, context: None
) -> tuple[Config, None]: ...


@overload
def consolidate_config_and_context(
    config: Config | None, context: Context
) -> tuple[Config, Context]: ...


def consolidate_config_and_context(
    config: Config | None, context: Context | None
) -> tuple[Config, Context | None]:
    """Return a new (config, context) with consistent configurable/context.

    Does not mutate the passed-in objects. If both configurable and context
    are provided, raises 400. If only one is provided, mirrors it to the other.
    """
    cfg: Config = Config(config or {})
    ctx: Context | None = dict(context) if context is not None else None
    configurable = cfg.get("configurable")

    if configurable and ctx:
        raise HTTPException(
            status_code=400,
            detail="Cannot specify both configurable and context. Prefer setting context alone."
            " Context was introduced in LangGraph 0.6.0 and "
            "is the long term planned replacement for configurable.",
        )

    if configurable:
        ctx = configurable
    elif ctx is not None:
        cfg["configurable"] = ctx

    return cfg, ctx


def dict_to_struct(data: dict[str, Any]) -> Struct:
    """Convert a dictionary to a protobuf Struct."""
    struct = Struct()
    if data:
        struct.update(data)
    return struct


def struct_to_dict(struct: Struct) -> dict[str, Any]:
    """Convert a protobuf Struct to a dictionary."""
    return MessageToDict(struct) if struct else {}


def exception_to_struct(exception: BaseException | None) -> Struct | None:
    """Convert an exception to a protobuf Struct."""
    if exception is None:
        return None
    import orjson

    try:
        payload = orjson.loads(json_dumpb(exception))
    except orjson.JSONDecodeError:
        payload = {"error": type(exception).__name__, "message": str(exception)}
    return dict_to_struct(payload)


def _map_sort_order(sort_order: str | None) -> Any:
    """Map string sort_order to protobuf enum."""
    from langgraph_api.grpc.generated import core_api_pb2 as pb

    if sort_order and sort_order.upper() == "ASC":
        return pb.SortOrder.ASC
    return pb.SortOrder.DESC


def _handle_grpc_error(error: AioRpcError) -> None:
    """Handle gRPC errors and convert to appropriate exceptions."""
    raise HTTPException(
        status_code=GRPC_STATUS_TO_HTTP_STATUS.get(
            error.code(), HTTPStatus.INTERNAL_SERVER_ERROR
        ),
        detail=str(error.details()),
    )


def _serialize_filter_value(value: Any) -> str:
    """Serialize a filter value to a valid JSON string for JSONB comparison.

    Uses orjson for serialization to handle UUIDs, datetimes, etc.
    All values are returned as valid JSON strings that can be parsed with ::jsonb.

    Examples:
        "johndoe" -> '"johndoe"' (JSON string)
        uuid.UUID("...") -> '"uuid-string"' (JSON string)
        datetime(...) -> '"2024-03-15T12:15:00+00:00"' (JSON string)
        42 -> '42' (JSON number)
        {"foo": "bar"} -> '{"foo": "bar"}' (JSON object)
    """
    # Serialize everything with orjson to get valid JSON
    json_bytes = orjson.dumps(value)
    return json_bytes.decode("utf-8")


def _filters_to_proto(filters: dict[str, Any] | None) -> list[pb.AuthFilter]:
    """Convert Python auth filters to gRPC proto format.

    We have some weird auth semantics today:
    - Objects are supported in the $eq operator, but not in the $contains operator or default case.
    - List of numbers in contains don't work anywhere. This is fine and can be removed in the future.
    - Odd nesting doesn't work anywhere (e.g. filter {"outer_key": "inner_value"} won't match on {"outer_key": {"inner_key": "inner_value"}})

    Args:
        filters: Python dict with filter values, e.g., {"owner": "user123"}

    Returns:
        List of AuthFilter proto messages, empty list if no filters
    """
    if not filters:
        return []

    proto_filters: list[pb.AuthFilter] = []

    for key, filter_value in filters.items():
        auth_filter = pb.AuthFilter()

        if key == "$or":
            # Recursively convert each filter and flatten the results
            nested_filters = []
            for filter_dict in filter_value:
                nested_filters.extend(_filters_to_proto(filter_dict))
            auth_filter.or_filter.CopyFrom(pb.OrAuthFilter(filters=nested_filters))
            proto_filters.append(auth_filter)
        elif key == "$and":
            # Recursively convert each filter and flatten the results
            nested_filters = []
            for filter_dict in filter_value:
                nested_filters.extend(_filters_to_proto(filter_dict))
            auth_filter.and_filter.CopyFrom(pb.AndAuthFilter(filters=nested_filters))
            proto_filters.append(auth_filter)
        else:
            # We expect one key in the dict with a specific known value
            if isinstance(filter_value, dict):
                if len(filter_value.keys()) != 1:
                    logger.error(
                        "Error parsing filter: filter_value is not a dict with one key"
                    )
                    raise HTTPException(
                        status_code=500,
                        detail="Your auth handler returned a filter with an invalid value. The value must be a dict with one key. Check the filter returned by your auth handler.",
                    )

                operator = next(iter(filter_value.keys()))
                value = filter_value[operator]

                if operator == "$eq":
                    matchstr = _serialize_filter_value(value)
                    auth_filter.eq.CopyFrom(pb.EqAuthFilter(key=key, match=matchstr))
                elif operator == "$contains":
                    if isinstance(value, list):
                        matches = [_serialize_filter_value(item) for item in value]
                        auth_filter.contains.CopyFrom(
                            pb.ContainsAuthFilter(key=key, matches=matches)
                        )
                    else:
                        # If the value itself is not a list, wrap it as a single-item list
                        serialized = _serialize_filter_value(value)
                        auth_filter.contains.CopyFrom(
                            pb.ContainsAuthFilter(key=key, matches=[serialized])
                        )
                else:
                    logger.error(
                        "Error parsing filter: operator is not $eq or $contains"
                    )
                    raise HTTPException(
                        status_code=500,
                        detail="Your auth handler returned a filter with an invalid key. The key must be one of $eq or $contains. Check the filter returned by your auth handler.",
                    )
            # Otherwise, it's the default case - simple value means equality check
            else:
                # Serialize with orjson (for proper datetime/UUID handling), then unwrap if it's a JSON string
                matchstr = _serialize_filter_value(filter_value)
                auth_filter.eq.CopyFrom(pb.EqAuthFilter(key=key, match=matchstr))
            proto_filters.append(auth_filter)

    return proto_filters


class Authenticated:
    """Base class for authenticated operations (matches storage_postgres interface)."""

    resource: str = "assistants"

    @classmethod
    async def handle_event(
        cls,
        ctx: Any,  # Auth context
        action: str,
        value: Any,
    ) -> list[pb.AuthFilter]:
        """Handle authentication event and convert filters to gRPC proto format.

        Args:
            ctx: Auth context (from get_auth_ctx())
            action: Action being performed (e.g., "create", "read", "update", "delete", "search")
            value: Value being operated on

        Returns:
            List of AuthFilter proto messages, empty list if no filters
        """
        # Get auth context if not provided
        if ctx is None:
            ctx = get_auth_ctx()

        # If still no context, no auth filters needed
        if ctx is None:
            return []

        # Create auth context for the handler
        from langgraph_sdk import Auth

        auth_ctx = Auth.types.AuthContext(
            resource=cls.resource,
            action=action,
            user=ctx.user,
            permissions=ctx.permissions,
        )

        # Call the auth system to get filters
        filters = await auth_handle_event(auth_ctx, value)

        # Convert Python filters to gRPC proto format
        return _filters_to_proto(filters)


def grpc_error_guard(cls):
    """Class decorator to wrap async methods and handle gRPC errors uniformly."""
    for name, attr in list(cls.__dict__.items()):
        func = None
        wrapper_type = None
        if isinstance(attr, staticmethod):
            func = attr.__func__
            wrapper_type = staticmethod
        elif isinstance(attr, classmethod):
            func = attr.__func__
            wrapper_type = classmethod
        elif callable(attr):
            func = attr

        if func and asyncio.iscoroutinefunction(func):

            def make_wrapper(f):
                @functools.wraps(f)
                async def wrapped(*args, **kwargs):
                    try:
                        return await f(*args, **kwargs)
                    except AioRpcError as e:
                        _handle_grpc_error(e)

                return wrapped  # noqa: B023

            wrapped = make_wrapper(func)
            if wrapper_type is staticmethod:
                setattr(cls, name, staticmethod(wrapped))
            elif wrapper_type is classmethod:
                setattr(cls, name, classmethod(wrapped))
            else:
                setattr(cls, name, wrapped)
    return cls


# Import at the end to avoid circular imports
from .assistants import Assistants  # noqa: E402
from .threads import Threads  # noqa: E402
