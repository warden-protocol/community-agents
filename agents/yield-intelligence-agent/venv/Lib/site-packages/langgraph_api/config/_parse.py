from collections.abc import Callable
from typing import Annotated, TypeVar, cast, get_args, get_origin

import orjson
from pydantic import TypeAdapter
from typing_extensions import TypeForm

from langgraph_api.config.schemas import (
    ThreadTTLConfig,
)

TD = TypeVar("TD")


def parse_json(json: str | None, schema: TypeAdapter | None = None) -> dict | None:
    if not json:
        return None
    parsed = schema.validate_json(json) if schema else orjson.loads(json)
    return parsed or None


def parse_schema(
    schema: TypeForm[TD],
) -> Callable[[str | None], TD | None]:
    def composed(json: str | None) -> TD | None:
        return cast("TD | None", parse_json(json, schema=TypeAdapter(schema)))

    # This just gives a nicer error message if the user provides an incompatible value
    if get_origin(schema) is Annotated:
        schema_type = get_args(schema)[0]
        composed.__name__ = schema_type.__name__
    else:
        composed.__name__ = schema.__name__  # type: ignore
    return composed


def parse_thread_ttl(value: str | None) -> ThreadTTLConfig | None:
    if not value:
        return None
    if str(value).strip().startswith("{"):
        return parse_json(value.strip())
    return {
        "strategy": "delete",
        # We permit float values mainly for testing purposes
        "default_ttl": float(value),
        "sweep_interval_minutes": 5.1,
    }
