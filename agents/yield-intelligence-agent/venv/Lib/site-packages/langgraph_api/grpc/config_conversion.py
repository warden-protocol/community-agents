"""Conversion utils for the RunnableConfig."""

# THIS IS DUPLICATED
# TODO: WFH - Deduplicate with the executor logic by moving into a separate package
# Sequencing in the next PR.
from typing import Any, cast

import orjson
from langchain_core.runnables.config import RunnableConfig

from langgraph_api.grpc.generated import (
    engine_common_pb2,
    enum_durability_pb2,
)

CONFIG_KEY_SEND = "__pregel_send"
CONFIG_KEY_READ = "__pregel_read"
CONFIG_KEY_RESUMING = "__pregel_resuming"
CONFIG_KEY_TASK_ID = "__pregel_task_id"
CONFIG_KEY_THREAD_ID = "thread_id"
CONFIG_KEY_CHECKPOINT_MAP = "checkpoint_map"
CONFIG_KEY_CHECKPOINT_ID = "checkpoint_id"
CONFIG_KEY_CHECKPOINT_NS = "checkpoint_ns"
CONFIG_KEY_SCRATCHPAD = "__pregel_scratchpad"
CONFIG_KEY_DURABILITY = "__pregel_durability"
CONFIG_KEY_GRAPH_ID = "graph_id"


def _durability_to_proto(
    durability: str,
) -> enum_durability_pb2.Durability:
    match durability:
        case "async":
            return enum_durability_pb2.Durability.ASYNC
        case "sync":
            return enum_durability_pb2.Durability.SYNC
        case "exit":
            return enum_durability_pb2.Durability.EXIT
        case _:
            raise ValueError(f"invalid durability: {durability}")


def _durability_from_proto(
    durability: enum_durability_pb2.Durability,
) -> str:
    match durability:
        case enum_durability_pb2.Durability.ASYNC:
            return "async"
        case enum_durability_pb2.Durability.SYNC:
            return "sync"
        case enum_durability_pb2.Durability.EXIT:
            return "exit"
        case _:
            raise ValueError(f"invalid durability: {durability}")


def config_to_proto(
    config: RunnableConfig,
) -> engine_common_pb2.EngineRunnableConfig | None:
    # Prepare kwargs for construction
    if not config:
        return None
    cp = {**config}
    pb_config = engine_common_pb2.EngineRunnableConfig()
    for k, v in (cp.pop("metadata", None) or {}).items():
        if k == "run_attempt":
            pb_config.run_attempt = v
        elif k == "run_id":
            pb_config.server_run_id = str(v)
        else:
            pb_config.metadata_json[k] = orjson.dumps(v)
    if run_name := cp.pop("run_name", None):
        pb_config.run_name = run_name

    if run_id := cp.pop("run_id", None):
        pb_config.run_id = str(run_id)

    if (max_concurrency := cp.pop("max_concurrency", None)) and isinstance(
        max_concurrency, int
    ):
        pb_config.max_concurrency = max_concurrency

    if (recursion_limit := cp.pop("recursion_limit", None)) and isinstance(
        recursion_limit, int
    ):
        pb_config.recursion_limit = recursion_limit

    # Handle collections after construction
    if (tags := cp.pop("tags", None)) and isinstance(tags, list):
        pb_config.tags.extend(tags)

    if (configurable := cp.pop("configurable", None)) and isinstance(
        configurable, dict
    ):
        _inject_configurable_into_proto(configurable, pb_config)
    if cp:
        pb_config.extra_json.update({k: orjson.dumps(v) for k, v in cp.items()})

    return pb_config


RESTRICTED_RESERVED_CONFIGURABLE_KEYS = {
    CONFIG_KEY_SEND,
    CONFIG_KEY_READ,
    CONFIG_KEY_SCRATCHPAD,
}


def _inject_configurable_into_proto(
    configurable: dict[str, Any], proto: engine_common_pb2.EngineRunnableConfig
) -> None:
    extra = {}
    for key, value in configurable.items():
        if key == CONFIG_KEY_RESUMING:
            proto.resuming = bool(value)
        elif key == CONFIG_KEY_TASK_ID:
            proto.task_id = str(value)
        elif key == CONFIG_KEY_THREAD_ID:
            proto.thread_id = str(value)
        elif key == CONFIG_KEY_CHECKPOINT_MAP:
            proto.checkpoint_map.update(cast("dict[str, str]", value))
        elif key == CONFIG_KEY_CHECKPOINT_ID:
            proto.checkpoint_id = str(value)
        elif key == CONFIG_KEY_CHECKPOINT_NS:
            proto.checkpoint_ns = str(value)
        elif key == CONFIG_KEY_DURABILITY and value:
            proto.durability = _durability_to_proto(value)
        elif key not in RESTRICTED_RESERVED_CONFIGURABLE_KEYS:
            extra[key] = value
    if extra:
        proto.extra_configurable_json.update(
            {k: orjson.dumps(v) for k, v in extra.items()}
        )


def context_to_json_bytes(context: dict[str, Any] | Any) -> bytes | None:
    """Convert context to JSON bytes for proto serialization."""
    if context is None:
        return None

    # Convert dataclass or other objects to dict if needed
    if hasattr(context, "__dict__") and not hasattr(context, "items"):
        # Convert dataclass to dict
        context_dict = context.__dict__
    elif hasattr(context, "items"):
        # Already a dict-like object
        context_dict = dict(context)
    else:
        # Try to convert to dict using vars()
        context_dict = vars(context) if hasattr(context, "__dict__") else {}

    return orjson.dumps(context_dict)


def config_from_proto(
    config_proto: engine_common_pb2.EngineRunnableConfig | None,
) -> RunnableConfig:
    if not config_proto:
        return RunnableConfig(tags=[], metadata={}, configurable={})

    configurable = _configurable_from_proto(config_proto)

    metadata = {}
    for k, v in config_proto.metadata_json.items():
        metadata[k] = orjson.loads(v)
    if config_proto.HasField("run_attempt"):
        metadata["run_attempt"] = config_proto.run_attempt
    if config_proto.HasField("server_run_id"):
        metadata["run_id"] = config_proto.server_run_id

    config = RunnableConfig()
    if config_proto.extra_json:
        for k, v in config_proto.extra_json.items():
            config[k] = orjson.loads(v)  # type: ignore[invalid-key]
    if config_proto.tags:
        config["tags"] = list(config_proto.tags)
    if metadata:
        config["metadata"] = metadata
    if configurable:
        config["configurable"] = configurable
    if config_proto.HasField("run_name"):
        config["run_name"] = config_proto.run_name

    if config_proto.HasField("max_concurrency"):
        config["max_concurrency"] = config_proto.max_concurrency

    if config_proto.HasField("recursion_limit"):
        config["recursion_limit"] = config_proto.recursion_limit

    return config


def _configurable_from_proto(
    config_proto: engine_common_pb2.EngineRunnableConfig,
) -> dict[str, Any]:
    configurable = {}

    if config_proto.HasField("resuming"):
        configurable[CONFIG_KEY_RESUMING] = config_proto.resuming

    if config_proto.HasField("task_id"):
        configurable[CONFIG_KEY_TASK_ID] = config_proto.task_id

    if config_proto.HasField("thread_id"):
        configurable[CONFIG_KEY_THREAD_ID] = config_proto.thread_id

    if config_proto.HasField("checkpoint_id"):
        configurable[CONFIG_KEY_CHECKPOINT_ID] = config_proto.checkpoint_id

    if config_proto.HasField("checkpoint_ns"):
        configurable[CONFIG_KEY_CHECKPOINT_NS] = config_proto.checkpoint_ns

    if config_proto.HasField("durability"):
        durability = _durability_from_proto(config_proto.durability)
        if durability:
            configurable[CONFIG_KEY_DURABILITY] = durability

    if config_proto.HasField("graph_id"):
        configurable[CONFIG_KEY_GRAPH_ID] = config_proto.graph_id

    if len(config_proto.checkpoint_map) > 0:
        configurable[CONFIG_KEY_CHECKPOINT_MAP] = dict(config_proto.checkpoint_map)

    if len(config_proto.extra_configurable_json) > 0:
        for k, v in config_proto.extra_configurable_json.items():
            configurable[k] = orjson.loads(v)

    return configurable
