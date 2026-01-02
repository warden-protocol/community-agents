"""Implement A2A (Agent2Agent) endpoint for JSON-RPC 2.0 protocol.

The Agent2Agent (A2A) Protocol is an open standard designed to facilitate
communication and interoperability between independent AI agent systems.

A2A Protocol specification:
https://a2a-protocol.org/dev/specification/

The implementation currently supports JSON-RPC 2.0 transport only.
Push notifications are not implemented.
"""

import functools
import uuid
from datetime import UTC, datetime
from typing import Any, Literal, NotRequired, cast

import orjson
import structlog
from langgraph_sdk.client import LangGraphClient, get_client
from starlette.datastructures import Headers
from starlette.responses import JSONResponse, Response
from typing_extensions import TypedDict

from langgraph_api import __version__
from langgraph_api.metadata import USER_API_URL
from langgraph_api.route import ApiRequest, ApiRoute
from langgraph_api.sse import EventSourceResponse
from langgraph_api.utils.cache import LRUCache

logger = structlog.stdlib.get_logger(__name__)

# Cache for assistant schemas (assistant_id -> schemas dict)
_assistant_schemas_cache = LRUCache[dict[str, Any]](max_size=1000, ttl=60)

MAX_HISTORY_LENGTH_REQUESTED = 10
LANGGRAPH_HISTORY_QUERY_LIMIT = 500


# ============================================================================
# JSON-RPC 2.0 Base Types (shared with MCP)
# ============================================================================


class JsonRpcErrorObject(TypedDict):
    code: int
    message: str
    data: NotRequired[Any]


class JsonRpcRequest(TypedDict):
    jsonrpc: Literal["2.0"]
    id: str | int
    method: str
    params: NotRequired[dict[str, Any]]


class JsonRpcResponse(TypedDict):
    jsonrpc: Literal["2.0"]
    id: str | int
    result: NotRequired[dict[str, Any]]
    error: NotRequired[JsonRpcErrorObject]


class JsonRpcNotification(TypedDict):
    jsonrpc: Literal["2.0"]
    method: str
    params: NotRequired[dict[str, Any]]


# ============================================================================
# A2A Specific Error Codes
# ============================================================================

# Standard JSON-RPC error codes
ERROR_CODE_PARSE_ERROR = -32700
ERROR_CODE_INVALID_REQUEST = -32600
ERROR_CODE_METHOD_NOT_FOUND = -32601
ERROR_CODE_INVALID_PARAMS = -32602
ERROR_CODE_INTERNAL_ERROR = -32603

# A2A-specific error codes (in server error range -32000 to -32099)
ERROR_CODE_TASK_NOT_FOUND = -32001
ERROR_CODE_TASK_NOT_CANCELABLE = -32002
ERROR_CODE_PUSH_NOTIFICATION_NOT_SUPPORTED = -32003
ERROR_CODE_UNSUPPORTED_OPERATION = -32004
ERROR_CODE_CONTENT_TYPE_NOT_SUPPORTED = -32005
ERROR_CODE_INVALID_AGENT_RESPONSE = -32006


# ============================================================================
# Constants and Configuration
# ============================================================================

A2A_PROTOCOL_VERSION = "0.3.0"


@functools.lru_cache(maxsize=1)
def _client() -> LangGraphClient:
    """Get a client for local operations."""
    return get_client(url=None)


async def _get_assistant(
    assistant_id: str, headers: Headers | dict[str, Any] | None
) -> dict[str, Any]:
    """Get assistant with proper 404 error handling.

    Args:
        assistant_id: The assistant ID to get
        headers: Request headers

    Returns:
        The assistant dictionary

    Raises:
        ValueError: If assistant not found or other errors
    """
    try:
        return await get_client().assistants.get(assistant_id, headers=headers)
    except Exception as e:
        if (
            hasattr(e, "response")
            and hasattr(e.response, "status_code")
            and e.response.status_code == 404
        ):
            raise ValueError(f"Assistant '{assistant_id}' not found") from e
        raise ValueError(f"Failed to get assistant '{assistant_id}': {e}") from e


async def _validate_supports_messages(
    assistant: dict[str, Any],
    headers: Headers | dict[str, Any] | None,
    parts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate that assistant supports messages if text parts are present.

    If the parts contain text parts, the agent must support the 'messages' field.
    If the parts only contain data parts, no validation is performed.

    Args:
        assistant: The assistant dictionary
        headers: Request headers
        parts: The original A2A message parts

    Returns:
        The schemas dictionary from the assistant

    Raises:
        ValueError: If assistant doesn't support messages when text parts are present
    """
    assistant_id = assistant["assistant_id"]

    cached_schemas = await _assistant_schemas_cache.get(assistant_id)
    if cached_schemas is not None:
        schemas = cached_schemas
    else:
        try:
            schemas = await get_client().assistants.get_schemas(
                assistant_id, headers=headers
            )
            _assistant_schemas_cache.set(assistant_id, schemas)
        except Exception as e:
            raise ValueError(
                f"Failed to get schemas for assistant '{assistant_id}': {e}"
            ) from e

    # Validate messages field only if there are text parts
    has_text_parts = any(part.get("kind") == "text" for part in parts)
    if has_text_parts:
        input_schema = schemas.get("input_schema")
        if not input_schema:
            raise ValueError(
                f"Assistant '{assistant_id}' has no input schema defined. "
                f"A2A conversational agents using text parts must have an input schema with a 'messages' field."
            )

        properties = input_schema.get("properties", {})
        if "messages" not in properties:
            graph_id = assistant["graph_id"]
            raise ValueError(
                f"Assistant '{assistant_id}' (graph '{graph_id}') does not support A2A conversational messages. "
                f"Graph input schema must include a 'messages' field to accept text parts. "
                f"Available input fields: {list(properties.keys())}"
            )

    return schemas


def _process_a2a_message_parts(
    parts: list[dict[str, Any]], message_role: str
) -> dict[str, Any]:
    """Convert A2A message parts to LangChain messages format.

    Args:
        parts: List of A2A message parts
        message_role: A2A message role ("user" or "agent")

    Returns:
        Input content with messages in LangChain format

    Raises:
        ValueError: If message parts are invalid
    """
    messages = []
    additional_data = {}

    for part in parts:
        part_kind = part.get("kind")

        if part_kind == "text":
            # Text parts become messages with role based on A2A message role
            if "text" not in part:
                raise ValueError("TextPart must contain a 'text' field")

            # Map A2A role to LangGraph role
            langgraph_role = "human" if message_role == "user" else "assistant"
            messages.append({"role": langgraph_role, "content": part["text"]})

        elif part_kind == "data":
            # Data parts become structured input parameters
            part_data = part.get("data", {})
            if not isinstance(part_data, dict):
                raise ValueError(
                    "DataPart must contain a JSON object in the 'data' field"
                )
            additional_data.update(part_data)

        else:
            raise ValueError(
                f"Unsupported part kind '{part_kind}'. "
                f"A2A agents support 'text' and 'data' parts only."
            )

    if not messages and not additional_data:
        raise ValueError("Message must contain at least one valid text or data part")

    # Create input with messages in LangChain format
    input_content = {}
    if messages:
        input_content["messages"] = messages
    if additional_data:
        input_content.update(additional_data)

    return input_content


def _extract_a2a_response(result: dict[str, Any]) -> str:
    """Extract the last assistant message from graph execution result.

    Args:
        result: Graph execution result

    Returns:
        Content of the last assistant message

    Raises:
        ValueError: If result doesn't contain messages or is invalid
    """
    if "__error__" in result:
        # Let the caller handle errors
        return str(result)

    if "messages" not in result:
        # Fallback to the full result if no messages schema. It is not optimal to do A2A on assistants without
        # a messages key, but it is not a hard requirement.
        return str(result)

    messages = result["messages"]
    if not isinstance(messages, list) or not messages:
        return str(result)

    # Find the last assistant message
    for message in reversed(messages):
        if (
            isinstance(message, dict)
            and message.get("role") == "assistant"
            and "content" in message
        ) or (message.get("type") == "ai" and "content" in message):
            return message["content"]

    # If no assistant message found, return the last message content
    last_message = messages[-1]
    if isinstance(last_message, dict):
        return last_message.get("content", str(last_message))

    return str(last_message)


def _lc_stream_items_to_a2a_message(
    items: list[dict[str, Any]],
    *,
    task_id: str,
    context_id: str,
    role: Literal["agent", "user"] = "agent",
) -> dict[str, Any]:
    """Convert LangChain stream "messages/*" items into a valid A2A Message.

    This takes the list found in a messages/* StreamPart's data field and
    constructs a single A2A Message object, concatenating textual content and
    preserving select structured metadata into a DataPart.

    Args:
        items: List of LangChain message dicts from stream (e.g., with keys like
            "content", "type", "response_metadata", "tool_calls", etc.)
        task_id: The A2A task ID this message belongs to
        context_id: The A2A context ID (thread) for grouping
        role: A2A role; defaults to "agent" for streamed assistant output

    Returns:
        A2A Message dict with required fields and minimally valid parts.
    """
    # Aggregate any text content across items
    text_parts: list[str] = []
    # Collect a small amount of structured data for debugging/traceability
    extra_data: dict[str, Any] = {}

    def _sse_safe_text(s: str) -> str:
        return s.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")

    for it in items:
        if not isinstance(it, dict):
            continue
        content = it.get("content")
        if isinstance(content, str) and content:
            text_parts.append(_sse_safe_text(content))

        # Preserve a couple of useful fields if present
        # Keep this small to avoid bloating the message payload
        rm = it.get("response_metadata")
        if isinstance(rm, dict) and rm:
            extra_data.setdefault("response_metadata", rm)
        tc = it.get("tool_calls")
        if isinstance(tc, list) and tc:
            extra_data.setdefault("tool_calls", tc)

    parts: list[dict[str, Any]] = []
    if text_parts:
        parts.append({"kind": "text", "text": "".join(text_parts)})
    if extra_data:
        parts.append({"kind": "data", "data": extra_data})

    # Ensure we always produce a minimally valid A2A Message
    if not parts:
        parts = [{"kind": "text", "text": ""}]

    return {
        "role": role,
        "parts": parts,
        "messageId": str(uuid.uuid4()),
        "taskId": task_id,
        "contextId": context_id,
        "kind": "message",
    }


def _lc_items_to_status_update_event(
    items: list[dict[str, Any]],
    *,
    task_id: str,
    context_id: str,
    state: str = "working",
) -> dict[str, Any]:
    """Build a TaskStatusUpdateEvent embedding a converted A2A Message.

    This avoids emitting standalone Message results (which some clients reject)
    and keeps message content within the status update per spec.
    """
    message = _lc_stream_items_to_a2a_message(
        items, task_id=task_id, context_id=context_id, role="agent"
    )
    return {
        "taskId": task_id,
        "contextId": context_id,
        "kind": "status-update",
        "status": {
            "state": state,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
        },
        "final": False,
    }


def _map_runs_create_error_to_rpc(
    exception: Exception, assistant_id: str, thread_id: str | None = None
) -> dict[str, Any]:
    """Map runs.create() exceptions to A2A JSON-RPC error responses.

    Args:
        exception: Exception from runs.create()
        assistant_id: The assistant ID that was used
        thread_id: The thread ID that was used (if any)

    Returns:
        A2A error response dictionary
    """
    if hasattr(exception, "response") and hasattr(exception.response, "status_code"):
        status_code = exception.response.status_code
        error_text = str(exception)

        if status_code == 404:
            # Check if it's a thread or assistant not found
            if "thread" in error_text.lower() or "Thread" in error_text:
                return {
                    "error": {
                        "code": ERROR_CODE_INVALID_PARAMS,
                        "message": f"Thread '{thread_id}' not found. Please create the thread first before sending messages to it.",
                        "data": {
                            "thread_id": thread_id,
                            "error_type": "thread_not_found",
                        },
                    }
                }
            else:
                return {
                    "error": {
                        "code": ERROR_CODE_INVALID_PARAMS,
                        "message": f"Assistant '{assistant_id}' not found",
                    }
                }
        elif status_code == 400:
            return {
                "error": {
                    "code": ERROR_CODE_INVALID_PARAMS,
                    "message": f"Invalid request: {error_text}",
                }
            }
        elif status_code == 403:
            return {
                "error": {
                    "code": ERROR_CODE_INVALID_PARAMS,
                    "message": "Access denied to assistant or thread",
                }
            }
        else:
            return {
                "error": {
                    "code": ERROR_CODE_INVALID_PARAMS,
                    "message": f"Failed to create run: {error_text}",
                }
            }

    return {
        "error": {
            "code": ERROR_CODE_INTERNAL_ERROR,
            "message": f"Internal server error: {exception!s}",
        }
    }


def _map_runs_get_error_to_rpc(
    exception: Exception, task_id: str, thread_id: str
) -> dict[str, Any]:
    """Map runs.get() exceptions to A2A JSON-RPC error responses.

    Args:
        exception: Exception from runs.get()
        task_id: The task/run ID that was requested
        thread_id: The thread ID that was requested

    Returns:
        A2A error response dictionary
    """
    if hasattr(exception, "response") and hasattr(exception.response, "status_code"):
        status_code = exception.response.status_code
        error_text = str(exception)

        status_code_handlers = {
            404: {
                "error": {
                    "code": ERROR_CODE_TASK_NOT_FOUND,
                    "message": f"Task '{task_id}' not found in thread '{thread_id}'",
                }
            },
            400: {
                "error": {
                    "code": ERROR_CODE_INVALID_PARAMS,
                    "message": f"Invalid request: {error_text}",
                }
            },
            403: {
                "error": {
                    "code": ERROR_CODE_INVALID_PARAMS,
                    "message": "Access denied to task",
                }
            },
        }

        return status_code_handlers.get(
            status_code,
            {
                "error": {
                    "code": ERROR_CODE_INVALID_PARAMS,
                    "message": f"Failed to get task: {error_text}",
                }
            },
        )

    return {
        "error": {
            "code": ERROR_CODE_INTERNAL_ERROR,
            "message": f"Internal server error: {exception!s}",
        }
    }


def _convert_messages_to_a2a_format(
    messages: list[dict[str, Any]],
    task_id: str,
    context_id: str,
) -> list[dict[str, Any]]:
    """Convert LangChain messages to A2A message format.

    Args:
        messages: List of LangChain messages
        task_id: The task ID to assign to all messages
        context_id: The context ID to assign to all messages

    Returns:
        List of A2A messages
    """

    # Convert each LangChain message to A2A format
    a2a_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            msg_type = msg.get("type", "ai")
            msg_role = msg.get("role", "")
            content = msg.get("content", "")

            # Support both LangChain style (type: "human"/"ai") and OpenAI style (role: "user"/"assistant")
            # Map to A2A roles: "human"/"user" -> "user", everything else -> "agent"
            a2a_role = "user" if msg_type == "human" or msg_role == "user" else "agent"

            a2a_message = {
                "role": a2a_role,
                "parts": [{"kind": "text", "text": str(content)}],
                "messageId": str(uuid.uuid4()),
                "taskId": task_id,
                "contextId": context_id,
                "kind": "message",
            }
            a2a_messages.append(a2a_message)

    return a2a_messages


async def _create_task_response(
    task_id: str,
    context_id: str,
    result: dict[str, Any],
    assistant_id: str,
) -> dict[str, Any]:
    """Create A2A Task response structure for both success and failure cases.

    Args:
        task_id: The task/run ID
        context_id: The context/thread ID
        message: Original A2A message from request
        result: LangGraph execution result
        assistant_id: The assistant ID used
        headers: Request headers

    Returns:
        A2A Task response dictionary
    """
    # Convert result messages to A2A message format
    messages = result.get("messages", []) or []
    thread_history = _convert_messages_to_a2a_format(messages, task_id, context_id)

    base_task = {
        "id": task_id,
        "contextId": context_id,
        "history": thread_history,
        "kind": "task",
    }

    if "__error__" in result:
        base_task["status"] = {
            "state": "failed",
            "message": {
                "role": "agent",
                "parts": [
                    {
                        "kind": "text",
                        "text": f"Error executing assistant: {result['__error__']['error']}",
                    }
                ],
                "messageId": str(uuid.uuid4()),
                "taskId": task_id,
                "contextId": context_id,
                "kind": "message",
            },
        }
    else:
        artifact_id = str(uuid.uuid4())
        artifacts = [
            {
                "artifactId": artifact_id,
                "name": "Assistant Response",
                "description": f"Response from assistant {assistant_id}",
                "parts": [
                    {
                        "kind": "text",
                        "text": _extract_a2a_response(result),
                    }
                ],
            }
        ]

        base_task["status"] = {
            "state": "completed",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        base_task["artifacts"] = artifacts

    return {"result": base_task}


# ============================================================================
# Main A2A Endpoint Handler
# ============================================================================


def handle_get_request() -> Response:
    """Handle HTTP GET requests (streaming not currently supported).

    Returns:
        405 Method Not Allowed
    """
    return Response(status_code=405)


def handle_delete_request() -> Response:
    """Handle HTTP DELETE requests (session termination not currently supported).

    Returns:
        404 Not Found
    """
    return Response(status_code=405)


async def handle_post_request(request: ApiRequest, assistant_id: str) -> Response:
    """Handle HTTP POST requests containing JSON-RPC messages.

    Args:
        request: The incoming HTTP request
        assistant_id: The assistant ID from the URL path

    Returns:
        JSON-RPC response
    """
    body = await request.body()

    try:
        message = orjson.loads(body)
    except orjson.JSONDecodeError:
        return create_error_response("Invalid JSON payload", 400)

    if not isinstance(message, dict):
        return create_error_response("Invalid message format", 400)

    if message.get("jsonrpc") != "2.0":
        return create_error_response(
            "Invalid JSON-RPC message. Missing or invalid jsonrpc version", 400
        )

    # Route based on message type
    id_ = message.get("id")
    method = message.get("method")

    accept_header = request.headers.get("Accept") or ""
    if method == "message/stream":
        if not _accepts_media_type(accept_header, "text/event-stream"):
            return create_error_response(
                "Accept header must include text/event-stream for streaming", 400
            )
    else:
        if not _accepts_media_type(accept_header, "application/json"):
            return create_error_response(
                "Accept header must include application/json", 400
            )

    if id_ is not None and method:
        # JSON-RPC request
        return await handle_jsonrpc_request(
            request, cast("JsonRpcRequest", message), assistant_id
        )
    elif id_ is not None:
        # JSON-RPC response (not expected in A2A server context)
        return handle_jsonrpc_response()
    elif method:
        # JSON-RPC notification
        return handle_jsonrpc_notification(cast("JsonRpcNotification", message))
    else:
        return create_error_response(
            "Invalid message format. Message must be a JSON-RPC request, "
            "response, or notification",
            400,
        )


def create_error_response(message: str, status_code: int) -> Response:
    """Create a JSON error response.

    Args:
        message: Error message
        status_code: HTTP status code

    Returns:
        JSON error response
    """
    return Response(
        content=orjson.dumps({"error": message}),
        status_code=status_code,
        media_type="application/json",
    )


def _accepts_media_type(accept_header: str, media_type: str) -> bool:
    """Return True if the Accept header allows the provided media type."""
    if not accept_header:
        return False

    target = media_type.lower()
    for media_range in accept_header.split(","):
        value = media_range.strip().lower()
        if not value:
            continue
        candidate = value.split(";", 1)[0].strip()
        if candidate == "*/*" or candidate == target:
            return True
        if candidate.endswith("/*"):
            type_prefix = candidate.split("/", 1)[0]
            if target.startswith(f"{type_prefix}/"):
                return True
    return False


# ============================================================================
# JSON-RPC Message Handlers
# ============================================================================


async def handle_jsonrpc_request(
    request: ApiRequest, message: JsonRpcRequest, assistant_id: str
) -> Response:
    """Handle JSON-RPC requests with A2A methods.

    Args:
        request: The HTTP request
        message: Parsed JSON-RPC request
        assistant_id: The assistant ID from the URL path

    Returns:
        JSON-RPC response
    """
    method = message["method"]
    params = message.get("params", {})
    # Route to appropriate A2A method handler
    if method == "message/stream":
        return await handle_message_stream(request, params, assistant_id, message["id"])
    elif method == "message/send":
        result_or_error = await handle_message_send(request, params, assistant_id)
    elif method == "tasks/get":
        result_or_error = await handle_tasks_get(request, params)
    elif method == "tasks/cancel":
        result_or_error = await handle_tasks_cancel(request, params)
    else:
        result_or_error = {
            "error": {
                "code": ERROR_CODE_METHOD_NOT_FOUND,
                "message": f"Method not found: {method}",
            }
        }

    response_keys = set(result_or_error.keys())
    if not (response_keys == {"result"} or response_keys == {"error"}):
        raise AssertionError(
            "Internal server error. Invalid response format in A2A implementation"
        )

    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": message["id"],
            **result_or_error,
        }
    )


def handle_jsonrpc_response() -> Response:
    """Handle JSON-RPC responses (not expected in server context).

    Args:
        message: Parsed JSON-RPC response

    Returns:
        202 Accepted acknowledgement
    """
    return Response(status_code=202)


def handle_jsonrpc_notification(message: JsonRpcNotification) -> Response:
    """Handle JSON-RPC notifications.

    Args:
        message: Parsed JSON-RPC notification

    Returns:
        202 Accepted acknowledgement
    """
    return Response(status_code=202)


# ============================================================================
# A2A Method Implementations
# ============================================================================


async def handle_message_send(
    request: ApiRequest, params: dict[str, Any], assistant_id: str
) -> dict[str, Any]:
    """Handle message/send requests to create or continue tasks.

    This method:
    1. Accepts A2A Messages containing text/file/data parts
    2. Maps to LangGraph assistant execution
    3. Returns Task objects with status and results

    Args:
        request: HTTP request for auth/headers
        params: A2A MessageSendParams
        assistant_id: The target assistant ID from the URL

    Returns:
        {"result": Task} or {"error": JsonRpcErrorObject}
    """
    client = _client()

    try:
        message = params.get("message")
        if not message:
            return {
                "error": {
                    "code": ERROR_CODE_INVALID_PARAMS,
                    "message": "Missing 'message' in params",
                }
            }

        parts = message.get("parts", [])
        if not parts:
            return {
                "error": {
                    "code": ERROR_CODE_INVALID_PARAMS,
                    "message": "Message must contain at least one part",
                }
            }

        try:
            assistant = await _get_assistant(assistant_id, request.headers)
            await _validate_supports_messages(assistant, request.headers, parts)
        except ValueError as e:
            return {
                "error": {
                    "code": ERROR_CODE_INVALID_PARAMS,
                    "message": str(e),
                }
            }

        # Process A2A message parts into LangChain messages format
        try:
            message_role = message.get(
                "role", "user"
            )  # Default to "user" if role not specified
            input_content = _process_a2a_message_parts(parts, message_role)
        except ValueError as e:
            return {
                "error": {
                    "code": ERROR_CODE_CONTENT_TYPE_NOT_SUPPORTED,
                    "message": str(e),
                }
            }

        context_id = message.get("contextId")

        # If no contextId provided, generate a UUID so we don't pass None to runs.create
        if context_id is None:
            context_id = str(uuid.uuid4())

        try:
            run = await client.runs.create(
                thread_id=context_id,
                assistant_id=assistant_id,
                input=input_content,
                if_not_exists="create",
                headers=request.headers,
            )
        except Exception as e:
            error_response = _map_runs_create_error_to_rpc(e, assistant_id, context_id)
            if error_response.get("error", {}).get("code") == ERROR_CODE_INTERNAL_ERROR:
                raise
            return error_response

        result = await client.runs.join(
            thread_id=run["thread_id"],
            run_id=run["run_id"],
            headers=request.headers,
        )

        task_id = run["run_id"]
        context_id = run["thread_id"]

        return await _create_task_response(
            task_id=task_id,
            context_id=context_id,
            result=result,
            assistant_id=assistant_id,
        )

    except Exception as e:
        logger.exception(f"Error in message/send for assistant {assistant_id}")
        return {
            "error": {
                "code": ERROR_CODE_INTERNAL_ERROR,
                "message": f"Internal server error: {e!s}",
            }
        }


async def _get_historical_messages_for_task(
    context_id: str,
    task_run_id: str,
    request_headers: Headers,
    history_length: int | None = None,
) -> list[Any]:
    """Get historical messages for a specific task by matching run_id."""
    history = await get_client().threads.get_history(
        context_id,
        limit=LANGGRAPH_HISTORY_QUERY_LIMIT,
        metadata={"run_id": task_run_id},
        headers=request_headers,
    )

    if history:
        # Find the checkpoint with the highest step number (final state for this task)
        target_checkpoint = max(
            history, key=lambda c: c.get("metadata", {}).get("step", 0)
        )
        values = target_checkpoint["values"]
        messages = values.get("messages", [])

        # Apply client-requested history length limit per A2A spec
        if history_length is not None and len(messages) > history_length:
            # Return the most recent messages up to the limit
            messages = messages[-history_length:]
        return messages
    else:
        return []


async def handle_tasks_get(
    request: ApiRequest, params: dict[str, Any]
) -> dict[str, Any]:
    """Handle tasks/get requests to retrieve task status.

    This method:
    1. Accepts task ID from params
    2. Maps to LangGraph run/thread status
    3. Returns current Task state and results

    Args:
        request: HTTP request for auth/headers
        params: A2A TaskQueryParams containing task ID

    Returns:
        {"result": Task} or {"error": JsonRpcErrorObject}
    """
    client = _client()

    try:
        task_id = params.get("id")
        context_id = params.get("contextId")
        history_length = params.get("historyLength")

        if not task_id:
            return {
                "error": {
                    "code": ERROR_CODE_INVALID_PARAMS,
                    "message": "Missing required parameter: id (task_id)",
                }
            }

        if not context_id:
            return {
                "error": {
                    "code": ERROR_CODE_INVALID_PARAMS,
                    "message": "Missing required parameter: contextId (thread_id)",
                }
            }

        # Validate history_length parameter per A2A spec
        if history_length is not None:
            if not isinstance(history_length, int) or history_length < 0:
                return {
                    "error": {
                        "code": ERROR_CODE_INVALID_PARAMS,
                        "message": "historyLength must be a non-negative integer",
                    }
                }
            if history_length > MAX_HISTORY_LENGTH_REQUESTED:
                return {
                    "error": {
                        "code": ERROR_CODE_INVALID_PARAMS,
                        "message": f"historyLength cannot exceed {MAX_HISTORY_LENGTH_REQUESTED}",
                    }
                }

        try:
            run_info = await client.runs.get(
                thread_id=context_id,
                run_id=task_id,
                headers=request.headers,
            )
        except Exception as e:
            error_response = _map_runs_get_error_to_rpc(e, task_id, context_id)
            if error_response.get("error", {}).get("code") == ERROR_CODE_INTERNAL_ERROR:
                # For unmapped errors, re-raise to be caught by outer exception handler
                raise
            return error_response

        assistant_id = run_info.get("assistant_id")
        if assistant_id:
            try:
                await _get_assistant(assistant_id, request.headers)
            except ValueError as e:
                return {
                    "error": {
                        "code": ERROR_CODE_INVALID_PARAMS,
                        "message": str(e),
                    }
                }

        lg_status = run_info.get("status", "unknown")

        if lg_status == "pending":
            a2a_state = "submitted"
        elif lg_status == "running":
            a2a_state = "working"
        elif lg_status == "success":
            a2a_state = "completed"
        elif lg_status == "interrupted":
            a2a_state = "input-required"
        elif lg_status in ["error", "timeout"]:
            a2a_state = "failed"
        else:
            a2a_state = "submitted"

        try:
            task_run_id = run_info.get("run_id")
            messages = await _get_historical_messages_for_task(
                context_id, task_run_id, request.headers, history_length
            )
            thread_history = _convert_messages_to_a2a_format(
                messages, task_id, context_id
            )
        except Exception as e:
            await logger.aexception(f"Failed to get thread state for tasks/get: {e}")
            thread_history = []

        # Build the A2A Task response
        task_response = {
            "id": task_id,
            "contextId": context_id,
            "history": thread_history,
            "kind": "task",
            "status": {
                "state": a2a_state,
            },
        }

        # Add result message if completed
        if a2a_state == "completed":
            task_response["status"]["message"] = {
                "role": "agent",
                "parts": [{"kind": "text", "text": "Task completed successfully"}],
                "messageId": str(uuid.uuid4()),
                "taskId": task_id,
            }
        elif a2a_state == "failed":
            task_response["status"]["message"] = {
                "role": "agent",
                "parts": [
                    {"kind": "text", "text": f"Task failed with status: {lg_status}"}
                ],
                "messageId": str(uuid.uuid4()),
                "taskId": task_id,
            }

        return {"result": task_response}

    except Exception as e:
        await logger.aerror(
            f"Error in tasks/get for task {params.get('id')}: {e!s}", exc_info=True
        )
        return {
            "error": {
                "code": ERROR_CODE_INTERNAL_ERROR,
                "message": f"Internal server error: {e!s}",
            }
        }


async def handle_tasks_cancel(
    request: ApiRequest, params: dict[str, Any]
) -> dict[str, Any]:
    """Handle tasks/cancel requests to cancel running tasks.

    This method:
    1. Accepts task ID from params
    2. Maps to LangGraph run cancellation
    3. Returns updated Task with canceled state

    Args:
        request: HTTP request for auth/headers
        params: A2A TaskIdParams containing task ID

    Returns:
        {"result": Task} or {"error": JsonRpcErrorObject}
    """
    # TODO: Implement tasks/cancel
    # - Extract task_id from params
    # - Map task_id to run_id
    # - Cancel run via client if possible
    # - Return updated Task with canceled status

    return {
        "error": {
            "code": ERROR_CODE_UNSUPPORTED_OPERATION,
            "message": "Task cancellation is not currently supported",
        }
    }


# ============================================================================
# Agent Card Generation
# ============================================================================


async def generate_agent_card(request: ApiRequest, assistant_id: str) -> dict[str, Any]:
    """Generate A2A Agent Card for a specific assistant.

    Each LangGraph assistant becomes its own A2A agent with a dedicated
    agent card describing its individual capabilities and skills.

    Args:
        request: HTTP request for auth/headers
        assistant_id: The specific assistant ID to generate card for

    Returns:
        A2A AgentCard dictionary for the specific assistant
    """
    client = _client()

    assistant = await _get_assistant(assistant_id, request.headers)
    schemas = await client.assistants.get_schemas(assistant_id, headers=request.headers)

    # Extract schema information for metadata
    input_schema = schemas.get("input_schema", {})
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    assistant_name = assistant["name"]
    assistant_description = (
        assistant.get("description") or f"{assistant_name} assistant"
    )

    # For now, each assistant has one main skill - itself
    skills = [
        {
            "id": f"{assistant_id}-main",
            "name": f"{assistant_name} Capabilities",
            "description": assistant_description,
            "tags": ["assistant", "langgraph"],
            "examples": [],
            "inputModes": ["application/json", "text/plain"],
            "outputModes": ["application/json", "text/plain"],
            "metadata": {
                "inputSchema": {
                    "required": required,
                    "properties": sorted(properties.keys()),
                    "supportsA2A": "messages" in properties,
                }
            },
        }
    ]

    if USER_API_URL:
        base_url = USER_API_URL.rstrip("/")
    else:
        # Fallback to constructing from request
        scheme = request.url.scheme
        host = request.url.hostname or "localhost"
        port = request.url.port
        path = request.url.path.removesuffix("/.well-known/agent-card.json")
        if port and (
            (scheme == "http" and port != 80) or (scheme == "https" and port != 443)
        ):
            base_url = f"{scheme}://{host}:{port}{path}"
        else:
            base_url = f"{scheme}://{host}"

    return {
        "protocolVersion": A2A_PROTOCOL_VERSION,
        "name": assistant_name,
        "description": assistant_description,
        "url": f"{base_url}/a2a/{assistant_id}",
        "preferredTransport": "JSONRPC",
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,  # Not implemented yet
            "stateTransitionHistory": False,
        },
        "defaultInputModes": ["application/json", "text/plain"],
        "defaultOutputModes": ["application/json", "text/plain"],
        "skills": skills,
        "version": __version__,
    }


async def handle_agent_card_endpoint(request: ApiRequest) -> Response:
    """Serve Agent Card for a specific assistant.

    Expected URL: /.well-known/agent-card.json?assistant_id=uuid

    Args:
        request: HTTP request

    Returns:
        JSON response with Agent Card for the specific assistant
    """
    try:
        # Get assistant_id from query parameters
        assistant_id = request.query_params.get("assistant_id")

        if not assistant_id:
            error_response = {
                "error": {
                    "code": ERROR_CODE_INVALID_PARAMS,
                    "message": "Missing required query parameter: assistant_id",
                }
            }
            return Response(
                content=orjson.dumps(error_response),
                status_code=400,
                media_type="application/json",
            )

        agent_card = await generate_agent_card(request, assistant_id)
        return JSONResponse(agent_card)

    except ValueError as e:
        # A2A validation error or assistant not found
        error_response = {
            "error": {
                "code": ERROR_CODE_INVALID_PARAMS,
                "message": str(e),
            }
        }
        return Response(
            content=orjson.dumps(error_response),
            status_code=400,
            media_type="application/json",
        )
    except Exception as e:
        logger.exception("Failed to generate agent card")
        error_response = {
            "error": {
                "code": ERROR_CODE_INTERNAL_ERROR,
                "message": f"Internal server error: {e!s}",
            }
        }
        return Response(
            content=orjson.dumps(error_response),
            status_code=500,
            media_type="application/json",
        )


# ============================================================================
# Message Streaming
# ============================================================================


async def handle_message_stream(
    request: ApiRequest,
    params: dict[str, Any],
    assistant_id: str,
    rpc_id: str | int,
) -> Response:
    """Handle message/stream requests and stream JSON-RPC responses via SSE.

    Each SSE "data" is a JSON-RPC 2.0 response object. We emit:
    - An initial TaskStatusUpdateEvent with state "submitted".
    - Optionally a TaskStatusUpdateEvent with state "working" on first update.
    - A final Task result when the run completes.
    - A JSON-RPC error if anything fails.
    """
    client = _client()

    async def stream_body():
        try:
            message = params.get("message")
            if not message:
                yield (
                    b"message",
                    {
                        "jsonrpc": "2.0",
                        "id": rpc_id,
                        "error": {
                            "code": ERROR_CODE_INVALID_PARAMS,
                            "message": "Missing 'message' in params",
                        },
                    },
                )
                return

            parts = message.get("parts", [])
            if not parts:
                yield (
                    b"message",
                    {
                        "jsonrpc": "2.0",
                        "id": rpc_id,
                        "error": {
                            "code": ERROR_CODE_INVALID_PARAMS,
                            "message": "Message must contain at least one part",
                        },
                    },
                )
                return

            try:
                assistant = await _get_assistant(assistant_id, request.headers)
                await _validate_supports_messages(assistant, request.headers, parts)
            except ValueError as e:
                yield (
                    b"message",
                    {
                        "jsonrpc": "2.0",
                        "id": rpc_id,
                        "error": {
                            "code": ERROR_CODE_INVALID_PARAMS,
                            "message": str(e),
                        },
                    },
                )
                return

            # Process A2A message parts into LangChain messages format
            try:
                message_role = message.get("role", "user")
                input_content = _process_a2a_message_parts(parts, message_role)
            except ValueError as e:
                yield (
                    b"message",
                    {
                        "jsonrpc": "2.0",
                        "id": rpc_id,
                        "error": {
                            "code": ERROR_CODE_CONTENT_TYPE_NOT_SUPPORTED,
                            "message": str(e),
                        },
                    },
                )
                return

            run = await client.runs.create(
                thread_id=message.get("contextId"),
                assistant_id=assistant_id,
                stream_mode=["messages", "values"],
                if_not_exists="create",
                input=input_content,
                headers=request.headers,
            )
            context_id = run["thread_id"]
            # Emit initial Task object to establish task context
            initial_task = {
                "id": run["run_id"],
                "contextId": context_id,
                "history": [
                    {
                        **message,
                        "taskId": run["run_id"],
                        "contextId": context_id,
                        "kind": "message",
                    }
                ],
                "kind": "task",
                "status": {
                    "state": "submitted",
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }
            yield (b"message", {"jsonrpc": "2.0", "id": rpc_id, "result": initial_task})
            task_id = run["run_id"]
            stream = client.runs.join_stream(
                run_id=task_id,
                thread_id=context_id,
                headers=request.headers,
            )
            result = None
            err = None
            notified_is_working = False
            async for chunk in stream:
                try:
                    if chunk.event == "metadata":
                        data = chunk.data or {}
                        if data.get("status") == "run_done":
                            final_message = None
                            if isinstance(result, dict):
                                try:
                                    final_text = _extract_a2a_response(result)
                                    final_message = {
                                        "role": "agent",
                                        "parts": [{"kind": "text", "text": final_text}],
                                        "messageId": str(uuid.uuid4()),
                                        "taskId": task_id,
                                        "contextId": context_id,
                                        "kind": "message",
                                    }
                                except Exception:
                                    await logger.aexception(
                                        "Failed to extract final message from result",
                                        result=result,
                                    )
                            if final_message is None:
                                final_message = {
                                    "role": "agent",
                                    "parts": [{"kind": "text", "text": str(result)}],
                                    "messageId": str(uuid.uuid4()),
                                    "taskId": task_id,
                                    "contextId": context_id,
                                    "kind": "message",
                                }
                            completed = {
                                "taskId": task_id,
                                "contextId": context_id,
                                "kind": "status-update",
                                "status": {
                                    "state": "completed",
                                    "message": final_message,
                                    "timestamp": datetime.now(UTC).isoformat(),
                                },
                                "final": True,
                            }
                            yield (
                                b"message",
                                {"jsonrpc": "2.0", "id": rpc_id, "result": completed},
                            )
                            return
                        if data.get("run_id") and not notified_is_working:
                            notified_is_working = True
                            yield (
                                b"message",
                                {
                                    "jsonrpc": "2.0",
                                    "id": rpc_id,
                                    "result": {
                                        "taskId": task_id,
                                        "contextId": context_id,
                                        "kind": "status-update",
                                        "status": {"state": "working"},
                                        "final": False,
                                    },
                                },
                            )
                    elif chunk.event == "error":
                        err = chunk.data
                    elif chunk.event == "values":
                        err = None  # Error was retriable
                        result = chunk.data
                    elif chunk.event.startswith("messages"):
                        err = None  # Error was retriable
                        items = chunk.data or []
                        if isinstance(items, list) and items:
                            update = _lc_items_to_status_update_event(
                                items,
                                task_id=task_id,
                                context_id=context_id,
                                state="working",
                            )
                            yield (
                                b"message",
                                {"jsonrpc": "2.0", "id": rpc_id, "result": update},
                            )
                    else:
                        await logger.awarning(
                            "Ignoring unknown event type: " + chunk.event
                        )

                except Exception as e:
                    await logger.aexception("Failed to process message stream")
                    err = {"error": type(e).__name__, "message": str(e)}
                    continue

            # If we exit unexpectedly, send a final status based on error presence
            final_message = None
            if isinstance(err, dict) and ("__error__" in err or "error" in err):
                msg = (
                    err.get("__error__", {}).get("error")
                    if isinstance(err.get("__error__"), dict)
                    else err.get("message")
                )
                await logger.aerror("Failed to process message stream", err=err)
                final_message = {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": str(msg or "")}],
                    "messageId": str(uuid.uuid4()),
                    "taskId": task_id,
                    "contextId": context_id,
                    "kind": "message",
                }
            fallback = {
                "taskId": task_id,
                "contextId": context_id,
                "kind": "status-update",
                "status": {
                    "state": "failed" if err else "completed",
                    **({"message": final_message} if final_message else {}),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                "final": True,
            }
            yield (b"message", {"jsonrpc": "2.0", "id": rpc_id, "result": fallback})
        except Exception as e:
            await logger.aerror(
                f"Error in message/stream for assistant {assistant_id}: {e!s}",
                exc_info=True,
            )
            yield (
                b"message",
                {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "error": {
                        "code": ERROR_CODE_INTERNAL_ERROR,
                        "message": f"Internal server error: {e!s}",
                    },
                },
            )

    async def consume_():
        async for chunk in stream_body():
            await logger.adebug("A2A.stream_body: Yielding chunk", chunk=chunk)
            yield chunk

    return EventSourceResponse(
        consume_(), headers={"Content-Type": "text/event-stream"}
    )


# ============================================================================
# Route Definitions
# ============================================================================


async def handle_a2a_assistant_endpoint(request: ApiRequest) -> Response:
    """A2A endpoint handler for specific assistant.

    Expected URL: /a2a/{assistant_id}

    Args:
        request: The incoming HTTP request

    Returns:
        JSON-RPC response or appropriate HTTP error response
    """
    # Extract assistant_id from URL path params
    assistant_id = request.path_params.get("assistant_id")
    if not assistant_id:
        return create_error_response("Missing assistant ID in URL", 400)

    if request.method == "POST":
        return await handle_post_request(request, assistant_id)
    elif request.method == "GET":
        return handle_get_request()
    elif request.method == "DELETE":
        return handle_delete_request()
    else:
        return Response(status_code=405)  # Method Not Allowed


a2a_routes = [
    # Per-assistant A2A endpoints: /a2a/{assistant_id}
    ApiRoute(
        "/a2a/{assistant_id}",
        handle_a2a_assistant_endpoint,
        methods=["GET", "POST", "DELETE"],
    ),
    ApiRoute(
        "/.well-known/agent-card.json", handle_agent_card_endpoint, methods=["GET"]
    ),
]
