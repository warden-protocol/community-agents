"""Implement MCP endpoint for Streamable HTTP protocol.

The current version of the RFC can be found here:

https://github.com/modelcontextprotocol/specification/blob/0f4924b07447073cbe1e29fbe64e42d379b52b04/docs/specification/draft/basic/transports.md#streamable-http

Tools specification:

https://github.com/modelcontextprotocol/specification/blob/0f4924b07447073cbe1e29fbe64e42d379b52b04/docs/specification/draft/server/tools.md

Message format:

https://github.com/modelcontextprotocol/specification/blob/0f4924b07447073cbe1e29fbe64e42d379b52b04/docs/specification/draft/basic/messages.md

Error handling with tools:

https://github.com/modelcontextprotocol/specification/blob/0f4924b07447073cbe1e29fbe64e42d379b52b04/docs/specification/draft/server/tools.md#error-handling

Streamable HTTP is a protocol that allows for the use of HTTP as transport.

The protocol supports both stateless and stateful interactions, and allows
the server to respond via either Application/JSON or text/event-stream.

LangGraph's implementation is currently stateless and only uses Application/JSON.

1. Adding stateful sessions: A stateful session would in theory allow agents used
as tools to remember past interactions. We likely do not want to map a session
to a thread ID as a single session may involve more than one tool call.
We would need to map a session to a collection of threads.

2. text/event-stream (SSE): Should be simple to add we'd want to make sure
we know what information we want to stream; e.g., progress notifications or
custom notifications.

In addition, the server could support resumability by allowing clients to specify
a Last-Event-ID in the request headers.
"""

import functools
import json
from typing import Any, NotRequired, cast

from langgraph_sdk.client import LangGraphClient, get_client
from starlette.responses import JSONResponse, Response
from structlog import getLogger
from typing_extensions import TypedDict

from langgraph_api.route import ApiRequest, ApiRoute

logger = getLogger(__name__)


class JsonRpcErrorObject(TypedDict):
    code: int
    message: str
    data: NotRequired[Any]


class JsonRpcRequest(TypedDict):
    jsonrpc: str  # Must be "2.0"
    id: str | int
    method: str
    params: NotRequired[dict[str, Any]]


class JsonRpcResponse(TypedDict):
    jsonrpc: str  # Must be "2.0"
    id: str | int
    result: NotRequired[dict[str, Any]]
    error: NotRequired[JsonRpcErrorObject]


class JsonRpcNotification(TypedDict):
    jsonrpc: str  # Must be "2.0"
    method: str
    params: NotRequired[dict[str, Any]]


@functools.lru_cache(maxsize=1)
def _client() -> LangGraphClient:
    """Get a client for local operations."""
    return get_client(url=None)


# Workaround assistant name not exposed in the Assistants.search API
MAX_ASSISTANTS = 1000
DEFAULT_PAGE_SIZE = 100

# JSON-RPC error codes: https://www.jsonrpc.org/specification#error_object
ERROR_CODE_INVALID_PARAMS = -32602
ERROR_CODE_METHOD_NOT_FOUND = -32601


def _get_version() -> str:
    """Get langgraph-api version."""
    from langgraph_api import __version__

    return __version__


async def handle_mcp_endpoint(request: ApiRequest) -> Response:
    """MCP endpoint handler the implements the Streamable HTTP protocol.

    The handler is expected to support the following methods:

    - POST: Process a JSON-RPC request
    - DELETE: Terminate a session

    We currently do not support:
    - /GET (initiates a streaming session)
        This endpoint can be used to RESUME a previously interrupted session.
    - text/event-stream (streaming) response from the server.

    Support for these can be added, we just need to determine what information
    from the agent we want to stream.

    One possibility is to map "custom" stream mode to server side notifications.

    Args:
        request: The incoming request object

    Returns:
        The response to the request
    """
    # Route request based on HTTP method
    if request.method == "DELETE":
        return handle_delete_request()
    elif request.method == "GET":
        return handle_get_request()
    elif request.method == "POST":
        return await handle_post_request(request)
    else:
        # Method not allowed
        return Response(status_code=405)


def handle_delete_request() -> Response:
    """Handle HTTP DELETE requests for session termination.

    Returns:
        Response with appropriate status code
    """
    return Response(status_code=404)


def handle_get_request() -> Response:
    """Handle HTTP GET requests for streaming (not currently supported).

    Returns:
        Method not allowed response
    """
    # Does not support streaming at the moment
    return Response(status_code=405)


async def handle_post_request(request: ApiRequest) -> Response:
    """Handle HTTP POST requests for JSON-RPC messaging.

    Args:
        request: The incoming request object

    Returns:
        Response to the JSON-RPC message
    """
    body = await request.body()

    # Validate JSON
    try:
        message = json.loads(body)
    except json.JSONDecodeError:
        return create_error_response("Invalid JSON", 400)

    # Validate Accept header
    if not is_valid_accept_header(request):
        return create_error_response(
            "Accept header must include application/json or text/event-stream", 400
        )

    # Validate message format
    if not isinstance(message, dict):
        return create_error_response("Invalid message format.", 400)

    # Determine message type and route to appropriate handler
    id_ = message.get("id")
    method = message.get("method")

    # Check for required jsonrpc field
    if message.get("jsonrpc") != "2.0":
        return create_error_response(
            "Invalid JSON-RPC message. Missing or invalid jsonrpc version.", 400
        )

    # Careful ID checks as the integer 0 is a valid ID
    if id_ is not None and method:
        # JSON-RPC request
        return await handle_jsonrpc_request(request, cast("JsonRpcRequest", message))
    elif id_ is not None:
        # JSON-RPC response
        return handle_jsonrpc_response(cast("JsonRpcResponse", message))
    elif method:
        # JSON-RPC notification
        return handle_jsonrpc_notification(cast("JsonRpcNotification", message))
    else:
        # Invalid message format
        return create_error_response(
            "Invalid message format. A message is to be either a JSON-RPC "
            "request, response, or notification."
            "Please see the Messages section of the Streamable HTTP RFC "
            "for more information.",
            400,
        )


def is_valid_accept_header(request: ApiRequest) -> bool:
    """Check if the Accept header contains supported content types.

    Args:
        request: The incoming request

    Returns:
        True if header contains application/json or text/event-stream
    """
    accept_header = request.headers.get("Accept", "")
    accepts_json = "application/json" in accept_header
    accepts_sse = "text/event-stream" in accept_header
    return accepts_json or accepts_sse


def create_error_response(message: str, status_code: int) -> Response:
    """Create a JSON error response.

    Args:
        message: The error message
        status_code: The HTTP status code

    Returns:
        JSON response with error details
    """
    return Response(
        content=json.dumps({"error": message}),
        status_code=status_code,
        media_type="application/json",
    )


async def handle_jsonrpc_request(
    request: ApiRequest,
    message: JsonRpcRequest,
) -> Response:
    """Handle JSON-RPC requests (messages with both id and method).

    Args:
        request: The incoming request object
        message: The parsed JSON-RPC message

    Returns:
        Response to the request
    """
    method = message["method"]
    params = message.get("params", {})

    if method == "initialize":
        result_or_error = handle_initialize_request(message)
    elif method == "tools/list":
        result_or_error = await handle_tools_list(request, params)
    elif method == "tools/call":
        result_or_error = await handle_tools_call(request, params)
    else:
        result_or_error = {
            "error": {
                "code": ERROR_CODE_METHOD_NOT_FOUND,
                "message": f"Method not found: {method}",
            }
        }

    # Process the result or error output
    exists = {"error", "result"} - set(result_or_error.keys())
    if len(exists) != 1:
        raise AssertionError(
            "Internal server error. Invalid response in MCP protocol implementation."
        )

    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": message["id"],
            **result_or_error,
        }
    )


def handle_initialize_request(message: JsonRpcRequest) -> dict[str, Any]:
    """Handle initialize requests to create a new session.

    Args:
        message: The JSON-RPC request message

    Returns:
        Response with new session details
    """
    return {
        "result": {
            # Official type-script SDK client only works with
            # protocol version 2024-11-05 currently.
            # The protocol is versioning the messages schema and not the transport.
            # https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle#lifecycle-phases
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": False,
                }
            },
            "serverInfo": {"name": "LangGraph", "version": _get_version()},
        }
    }


def handle_jsonrpc_response(message: JsonRpcResponse) -> Response:
    """Handle JSON-RPC responses (messages with id but no method).

    Args:
        message: The parsed JSON-RPC response message

    Returns:
        Acknowledgement response
    """
    # For any responses, we just acknowledge receipt
    return Response(status_code=202)


def handle_jsonrpc_notification(message: JsonRpcNotification) -> Response:
    """Handle JSON-RPC notifications (messages with method but no id).

    Args:
        message: The parsed JSON-RPC message

    Returns:
        Response to the notification
    """
    return Response(status_code=202)


async def handle_tools_list(
    request: ApiRequest, params: dict[str, Any]
) -> dict[str, Any]:
    """Handle tools/list request to get available assistants as tools.

    Args:
        request: The incoming request object. Used for propagating any headers
                 for authentication purposes.
        params: The parameters for the tools/list request

    Returns:
        Dictionary containing list of available tools
    """
    client = _client()

    try:
        cursor = params.get("cursor", 0)
        cursor = int(cursor)
    except ValueError:
        cursor = 0

    # Get assistants from the API
    # For now set a large limit to get all assistants
    assistants = await client.assistants.search(
        offset=cursor, limit=DEFAULT_PAGE_SIZE, headers=request.headers
    )

    if len(assistants) == DEFAULT_PAGE_SIZE:
        next_cursor = cursor + DEFAULT_PAGE_SIZE
    else:
        next_cursor = None

    # Format assistants as tools for MCP
    tools = []
    seen_names = set()
    for assistant in assistants:
        id_ = assistant.get("assistant_id")
        name = assistant["name"]

        if name in seen_names:
            await logger.awarning(f"Duplicate assistant name found {name}", name=name)
        else:
            seen_names.add(name)

        schemas = await client.assistants.get_schemas(id_, headers=request.headers)
        description = assistant.get("description") or ""
        tools.append(
            {
                "name": name,
                "inputSchema": schemas.get("input_schema", {}),
                "description": description,
            },
        )

    result = {"tools": tools}

    if next_cursor is not None:
        result["nextCursor"] = next_cursor

    return {
        "result": result,
    }


async def handle_tools_call(
    request: ApiRequest, params: dict[str, Any]
) -> dict[str, Any]:
    """Handle tools/call request to execute an assistant.

    Args:
        request: The incoming request
        params: The parameters for the tool call

    Returns:
        The result of the tool execution
    """
    client = _client()

    tool_name = params.get("name")

    if not tool_name:
        return {
            "jsonrpc": "2.0",
            "id": 3,
            "error": {
                "code": ERROR_CODE_INVALID_PARAMS,
                "message": f"Unknown tool: {tool_name}",
            },
        }

    arguments = params.get("arguments", {})
    assistants = await client.assistants.search(
        limit=MAX_ASSISTANTS, headers=request.headers
    )
    matching_assistant = [
        assistant for assistant in assistants if assistant["name"] == tool_name
    ]

    num_assistants = len(matching_assistant)

    if num_assistants == 0:
        return {
            "jsonrpc": "2.0",
            "id": 3,
            "error": {
                "code": ERROR_CODE_INVALID_PARAMS,
                "message": f"Unknown tool: {tool_name}",
            },
        }
    elif num_assistants > 1:
        return {
            "jsonrpc": "2.0",
            "id": 3,
            "error": {
                "code": ERROR_CODE_INVALID_PARAMS,
                "message": "Multiple tools found with the same name.",
            },
        }
    else:
        tool_name = matching_assistant[0]["assistant_id"]

    value = await client.runs.wait(
        thread_id=None,
        assistant_id=tool_name,
        input=arguments,
        raise_error=False,
        headers=request.headers,
    )

    if "__error__" in value:
        # This is a run-time error in the tool.
        return {
            "result": {
                "isError": True,
                "content": [
                    {"type": "text", "text": value["__error__"]["error"]},
                ],
            }
        }

    # All good, return the result
    return {
        "result": {
            "content": [
                {"type": "text", "text": repr(value)},
            ]
        }
    }


# Define routes for the MCP endpoint
mcp_routes = [
    ApiRoute("/mcp", handle_mcp_endpoint, methods=["GET", "POST", "DELETE"]),
]
