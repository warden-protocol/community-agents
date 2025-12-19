import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import AsyncExitStack, aclosing, asynccontextmanager
from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

import langgraph.version
import langsmith
import structlog
from langchain_core.messages import (
    AIMessageChunk,
    # TODO: Remove explicit dependency
    BaseMessage,
    BaseMessageChunk,
    ToolMessageChunk,
    convert_to_messages,
    message_chunk_to_message,
)
from langgraph.errors import (
    EmptyChannelError,
    EmptyInputError,
    GraphRecursionError,
    InvalidUpdateError,
)
from langgraph.pregel.debug import CheckpointPayload, TaskResultPayload
from langsmith.utils import get_tracer_project
from pydantic import ValidationError
from pydantic.v1 import ValidationError as ValidationErrorLegacy

from langgraph_api import __version__
from langgraph_api import store as api_store
from langgraph_api.asyncio import ValueEvent, wait_if_not_done
from langgraph_api.command import map_cmd
from langgraph_api.feature_flags import (
    UPDATES_NEEDED_FOR_INTERRUPTS,
    USE_DURABILITY,
    USE_RUNTIME_CONTEXT_API,
)
from langgraph_api.graph import get_graph
from langgraph_api.js.base import BaseRemotePregel
from langgraph_api.metadata import HOST, PLAN, USER_API_URL, incr_nodes
from langgraph_api.schema import Run, StreamMode
from langgraph_api.serde import json_dumpb
from langgraph_api.utils.config import run_in_executor
from langgraph_runtime.checkpoint import Checkpointer
from langgraph_runtime.ops import Runs

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig


logger = structlog.stdlib.get_logger(__name__)


async def _filter_context_by_schema(
    context: dict[str, Any], context_schema: dict | None
) -> dict[str, Any]:
    """Filter context parameters based on the context schema.

    Args:
        context: The context dictionary to filter
        context_schema: The JSON schema for valid context parameters

    Returns:
        Filtered context dictionary containing only valid parameters
    """
    if not context_schema or not context:
        return context

    # Extract valid properties from the schema
    properties = context_schema.get("properties", {})
    if not properties:
        return context

    # Filter context to only include parameters defined in the schema
    filtered_context = {}
    for key, value in context.items():
        if key in properties:
            filtered_context[key] = value
        else:
            await logger.adebug(
                f"Filtering out context parameter '{key}' not found in context schema",
                context_key=key,
                available_keys=list(properties.keys()),
            )

    return filtered_context


AnyStream = AsyncIterator[tuple[str, Any]]


def _preproces_debug_checkpoint_task(task: dict[str, Any]) -> dict[str, Any]:
    if (
        "state" not in task
        or not task["state"]
        or "configurable" not in task["state"]
        or not task["state"]["configurable"]
    ):
        return task

    task["checkpoint"] = task["state"]["configurable"]
    del task["state"]
    return task


def _preprocess_debug_checkpoint(
    payload: CheckpointPayload | None,
) -> dict[str, Any] | None:
    from langgraph_api.state import runnable_config_to_checkpoint

    if not payload:
        return None

    # TODO: deprecate the `config`` and `parent_config`` fields
    return {
        **payload,
        "checkpoint": runnable_config_to_checkpoint(payload["config"]),
        "parent_checkpoint": runnable_config_to_checkpoint(
            payload.get("parent_config", None)
        ),
        "tasks": [_preproces_debug_checkpoint_task(t) for t in payload["tasks"]],
    }


@asynccontextmanager
async def async_tracing_context(*args, **kwargs):
    with langsmith.tracing_context(*args, **kwargs):
        yield


async def astream_state(
    run: Run,
    attempt: int,
    done: ValueEvent,
    *,
    on_checkpoint: Callable[[CheckpointPayload | None], None] = lambda _: None,
    on_task_result: Callable[[TaskResultPayload], None] = lambda _: None,
) -> AnyStream:
    """Stream messages from the runnable."""
    run_id = str(run["run_id"])
    # extract args from run
    kwargs = run["kwargs"].copy()
    kwargs.pop("webhook", None)
    kwargs.pop("resumable", False)
    if USE_DURABILITY:
        checkpoint_during = kwargs.pop("checkpoint_during")
        if not kwargs.get("durability") and checkpoint_during:
            kwargs["durability"] = "async" if checkpoint_during else "exit"
    else:
        durability = kwargs.pop("durability")
        if not kwargs.get("checkpoint_during") and durability in ("async", "exit"):
            kwargs["checkpoint_during"] = durability == "async"
    subgraphs = kwargs.get("subgraphs", False)
    temporary = kwargs.pop("temporary", False)
    context = kwargs.pop("context", None)
    config = cast("RunnableConfig", kwargs.pop("config"))
    configurable = config["configurable"]
    stack = AsyncExitStack()
    graph = await stack.enter_async_context(
        get_graph(
            configurable["graph_id"],
            config,
            store=(await api_store.get_store()),
            checkpointer=None if temporary else Checkpointer(),
        )
    )

    # Filter context parameters based on context schema if available
    if context and USE_RUNTIME_CONTEXT_API and not isinstance(graph, BaseRemotePregel):
        try:
            context_schema = graph.get_context_jsonschema()
            context = await _filter_context_by_schema(context, context_schema)
        except Exception as e:
            await logger.adebug(
                f"Failed to get context schema for filtering: {e}", exc_info=e
            )

    input = kwargs.pop("input")
    if cmd := kwargs.pop("command"):
        input = map_cmd(cmd)
    stream_mode: list[StreamMode] = kwargs.pop("stream_mode")
    feedback_keys = kwargs.pop("feedback_keys", None)
    stream_modes_set: set[StreamMode] = set(stream_mode) - {"events"}
    if "debug" not in stream_modes_set:
        stream_modes_set.add("debug")
    if "messages-tuple" in stream_modes_set and not isinstance(graph, BaseRemotePregel):
        stream_modes_set.remove("messages-tuple")
        stream_modes_set.add("messages")
    if "updates" not in stream_modes_set and UPDATES_NEEDED_FOR_INTERRUPTS:
        stream_modes_set.add("updates")
        only_interrupt_updates = True
    else:
        only_interrupt_updates = False
    # attach attempt metadata
    config["metadata"]["run_attempt"] = attempt
    # attach langgraph metadata
    config["metadata"]["langgraph_version"] = langgraph.version.__version__
    config["metadata"]["langgraph_api_version"] = __version__
    config["metadata"]["langgraph_plan"] = PLAN
    config["metadata"]["langgraph_host"] = HOST
    config["metadata"]["langgraph_api_url"] = USER_API_URL
    # attach node counter
    is_remote_pregel = isinstance(graph, BaseRemotePregel)
    if not is_remote_pregel:
        configurable["__pregel_node_finished"] = incr_nodes

    # attach run_id to config
    # for attempts beyond the first, use a fresh, unique run_id
    config = {**config, "run_id": run["run_id"]} if attempt == 1 else config
    # set up state
    checkpoint: CheckpointPayload | None = None
    messages: dict[str, BaseMessageChunk] = {}
    use_astream_events = "events" in stream_mode or isinstance(graph, BaseRemotePregel)
    # yield metadata chunk
    yield "metadata", {"run_id": run_id, "attempt": attempt}

    #  is a langsmith tracing project is specified, additionally pass that in to tracing context
    if ls_project := configurable.get("__langsmith_project__"):
        updates = None
        if example_id := configurable.get("__langsmith_example_id__"):
            updates = {"reference_example_id": example_id}

        await stack.enter_async_context(
            async_tracing_context(
                replicas=[
                    {
                        "project_name": ls_project,
                        "updates": updates,
                    },
                    {
                        "project_name": get_tracer_project(),
                        "updates": None,
                    },
                ]
            )
        )

    # stream run
    if use_astream_events:
        if USE_RUNTIME_CONTEXT_API:
            kwargs["context"] = context
        async with (
            stack,
            aclosing(  # type: ignore[invalid-argument-type]
                graph.astream_events(
                    input,
                    config,
                    version="v2",
                    stream_mode=list(stream_modes_set),
                    **kwargs,
                )
            ) as stream,
        ):
            sentinel = object()
            while True:
                event = await wait_if_not_done(anext(stream, sentinel), done)
                if event is sentinel:
                    break
                event = cast("dict", event)
                if event.get("tags") and "langsmith:hidden" in event["tags"]:
                    continue
                if (
                    "messages" in stream_mode
                    and isinstance(graph, BaseRemotePregel)
                    and event["event"] == "on_custom_event"
                    and event["name"]
                    in (
                        "messages/complete",
                        "messages/partial",
                        "messages/metadata",
                    )
                ):
                    yield event["name"], event["data"]
                # TODO support messages-tuple for js graphs
                if event["event"] == "on_chain_stream" and event["run_id"] == run_id:
                    if subgraphs:
                        ns, mode, chunk = event["data"]["chunk"]
                    else:
                        mode, chunk = event["data"]["chunk"]
                        ns = None
                    # --- begin shared logic with astream ---
                    if mode == "debug":
                        if chunk["type"] == "checkpoint":
                            checkpoint = _preprocess_debug_checkpoint(chunk["payload"])
                            chunk["payload"] = checkpoint
                            on_checkpoint(checkpoint)
                        elif chunk["type"] == "task_result":
                            on_task_result(chunk["payload"])
                    if mode == "messages":
                        if "messages-tuple" in stream_mode:
                            if subgraphs and ns:
                                yield f"messages|{'|'.join(ns)}", chunk
                            else:
                                yield "messages", chunk
                        else:
                            msg_, meta = cast(
                                "tuple[BaseMessage | dict, dict[str, Any]]", chunk
                            )
                            is_chunk = False
                            if isinstance(msg_, dict):
                                if (
                                    "chunk" in msg_.get("type", "").lower()
                                    or "chunk" in msg_.get("role", "").lower()
                                ):
                                    if "ai" in msg_.get("role", "").lower():
                                        msg = AIMessageChunk(**msg_)  # type: ignore[arg-type]
                                    elif "tool" in msg_.get("role", "").lower():
                                        msg = ToolMessageChunk(**msg_)  # type: ignore[arg-type]
                                    else:
                                        msg = BaseMessageChunk(**msg_)  # type: ignore[arg-type]
                                    is_chunk = True
                                else:
                                    msg = convert_to_messages([msg_])[0]
                            else:
                                msg = msg_
                            if msg.id in messages:
                                messages[msg.id] += msg
                            else:
                                messages[msg.id] = msg
                                yield "messages/metadata", {msg.id: {"metadata": meta}}
                            yield (
                                (
                                    "messages/partial"
                                    if isinstance(msg, BaseMessageChunk)
                                    else "messages/complete"
                                ),
                                [
                                    (
                                        message_chunk_to_message(messages[msg.id])
                                        if not is_chunk
                                        else messages[msg.id]
                                    )
                                ],
                            )
                    elif mode in stream_mode:
                        if subgraphs and ns:
                            yield f"{mode}|{'|'.join(ns)}", chunk
                        else:
                            yield mode, chunk
                    elif (
                        mode == "updates"
                        and isinstance(chunk, dict)
                        and "__interrupt__" in chunk
                        and len(chunk["__interrupt__"]) > 0
                        and only_interrupt_updates
                    ):
                        # If the interrupt doesn't have any actions (e.g. interrupt before or after a node is specified), we don't return the interrupt at all today.
                        if subgraphs and ns:
                            yield "values|{'|'.join(ns)}", chunk
                        else:
                            yield "values", chunk
                    # --- end shared logic with astream ---
                elif "events" in stream_mode:
                    yield "events", event
    else:
        output_keys = kwargs.pop("output_keys", graph.output_channels)
        if USE_RUNTIME_CONTEXT_API:
            kwargs["context"] = context
        async with (
            stack,
            aclosing(
                graph.astream(
                    input,
                    config,
                    stream_mode=list(stream_modes_set),
                    output_keys=output_keys,
                    **kwargs,
                )
            ) as stream,
        ):
            sentinel = object()
            while True:
                event = await wait_if_not_done(anext(stream, sentinel), done)
                if event is sentinel:
                    break
                if subgraphs:
                    ns, mode, chunk = cast("tuple[str, str, dict[str, Any]]", event)
                else:
                    mode, chunk = cast("tuple[str, dict[str, Any]]", event)
                    ns = None
                # --- begin shared logic with astream_events ---
                if mode == "debug":
                    if chunk["type"] == "checkpoint":
                        checkpoint = _preprocess_debug_checkpoint(chunk["payload"])
                        chunk["payload"] = checkpoint
                        on_checkpoint(checkpoint)
                    elif chunk["type"] == "task_result":
                        on_task_result(chunk["payload"])
                if mode == "messages":
                    if "messages-tuple" in stream_mode:
                        if subgraphs and ns:
                            yield f"messages|{'|'.join(ns)}", chunk
                        else:
                            yield "messages", chunk
                    else:
                        msg_, meta = cast(
                            "tuple[BaseMessage | dict, dict[str, Any]]", chunk
                        )
                        is_chunk = False
                        if isinstance(msg_, dict):
                            if (
                                "chunk" in msg_.get("type", "").lower()
                                or "chunk" in msg_.get("role", "").lower()
                            ):
                                if "ai" in msg_.get("role", "").lower():
                                    msg = AIMessageChunk(**msg_)  # type: ignore[arg-type]
                                elif "tool" in msg_.get("role", "").lower():
                                    msg = ToolMessageChunk(**msg_)  # type: ignore[arg-type]
                                else:
                                    msg = BaseMessageChunk(**msg_)  # type: ignore[arg-type]
                                is_chunk = True
                            else:
                                msg = convert_to_messages([msg_])[0]
                        else:
                            msg = msg_
                        if msg.id in messages:
                            messages[msg.id] += msg
                        else:
                            messages[msg.id] = msg
                            yield "messages/metadata", {msg.id: {"metadata": meta}}
                        yield (
                            (
                                "messages/partial"
                                if isinstance(msg, BaseMessageChunk)
                                else "messages/complete"
                            ),
                            [
                                (
                                    message_chunk_to_message(messages[msg.id])
                                    if not is_chunk
                                    else messages[msg.id]
                                )
                            ],
                        )
                elif mode in stream_mode:
                    if subgraphs and ns:
                        yield f"{mode}|{'|'.join(ns)}", chunk
                    else:
                        yield mode, chunk
                elif (
                    mode == "updates"
                    and isinstance(chunk, dict)
                    and "__interrupt__" in chunk
                    and len(chunk["__interrupt__"]) > 0
                    and only_interrupt_updates
                ):
                    # If the interrupt doesn't have any actions (e.g. interrupt before or after a node is specified), we don't return the interrupt at all today.
                    if subgraphs and ns:
                        yield f"values|{'|'.join(ns)}", chunk
                    else:
                        yield "values", chunk
                # --- end shared logic with astream_events ---
    if is_remote_pregel:
        # increment the remote runs
        try:
            nodes_executed = await graph.fetch_nodes_executed()
            incr_nodes(None, incr=nodes_executed)
        except Exception as e:
            logger.warning(f"Failed to fetch nodes executed for {graph.graph_id}: {e}")
    else:
        await logger.adebug("Graph is not an instance of BaseRemotePregel")

    # Get feedback URLs
    if feedback_keys:
        feedback_urls = await run_in_executor(
            None, get_feedback_urls, run_id, feedback_keys
        )
        yield "feedback", feedback_urls


async def consume(
    stream: AnyStream,
    run_id: str | uuid.UUID,
    resumable: bool = False,
    stream_modes: set[StreamMode] | None = None,
    *,
    thread_id: str | uuid.UUID | None = None,
) -> None:
    stream_modes = stream_modes or set()
    if "messages-tuple" in stream_modes:
        stream_modes.add("messages")
    stream_modes.add("metadata")

    async with aclosing(stream):  # type: ignore[invalid-argument-type]
        try:
            async for mode, payload in stream:
                await Runs.Stream.publish(
                    run_id,
                    mode,
                    await run_in_executor(None, json_dumpb, payload),
                    thread_id=thread_id,
                    resumable=resumable and mode.split("|")[0] in stream_modes,
                )
        except Exception as e:
            if isinstance(e, ExceptionGroup):
                e = e.exceptions[0]
            await Runs.Stream.publish(
                run_id,
                "error",
                await run_in_executor(None, json_dumpb, e),
                thread_id=thread_id,
            )
            raise e


def get_feedback_urls(run_id: str, feedback_keys: list[str]) -> dict[str, str]:
    client = get_langsmith_client()
    tokens = client.create_presigned_feedback_tokens(run_id, feedback_keys)
    return {key: token.url for key, token in zip(feedback_keys, tokens, strict=False)}


@lru_cache(maxsize=1)
def get_langsmith_client() -> langsmith.Client:
    return langsmith.Client()


EXPECTED_ERRORS = (
    ValueError,
    InvalidUpdateError,
    GraphRecursionError,
    EmptyInputError,
    EmptyChannelError,
    ValidationError,
    ValidationErrorLegacy,
)
