from typing import get_args
from uuid import uuid4

from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.routing import BaseRoute

from langgraph_api.api.encryption_middleware import (
    decrypt_response,
    decrypt_responses,
    encrypt_request,
)
from langgraph_api.feature_flags import FF_USE_CORE_API
from langgraph_api.grpc.ops import Threads as GrpcThreads
from langgraph_api.route import ApiRequest, ApiResponse, ApiRoute
from langgraph_api.schema import (
    THREAD_ENCRYPTION_FIELDS,
    THREAD_FIELDS,
    ThreadStreamMode,
)
from langgraph_api.sse import EventSourceResponse
from langgraph_api.state import state_snapshot_to_thread_state
from langgraph_api.utils import (
    fetchone,
    get_pagination_headers,
    validate_select_columns,
    validate_stream_id,
    validate_uuid,
)
from langgraph_api.utils.headers import get_configurable_headers
from langgraph_api.validation import (
    ThreadCountRequest,
    ThreadCreate,
    ThreadPatch,
    ThreadSearchRequest,
    ThreadStateCheckpointRequest,
    ThreadStateSearch,
    ThreadStateUpdate,
)
from langgraph_runtime.database import connect
from langgraph_runtime.ops import Threads
from langgraph_runtime.retry import retry_db

CrudThreads = GrpcThreads if FF_USE_CORE_API else Threads


@retry_db
async def create_thread(
    request: ApiRequest,
):
    """Create a thread."""
    payload = await request.json(ThreadCreate)
    if thread_id := payload.get("thread_id"):
        validate_uuid(thread_id, "Invalid thread ID: must be a UUID")

    # Encrypt metadata before storing
    encrypted_payload = await encrypt_request(
        payload,
        "thread",
        ["metadata"],
    )

    async with connect() as conn:
        thread_id = thread_id or str(uuid4())
        iter = await CrudThreads.put(
            conn,
            thread_id,
            metadata=encrypted_payload.get("metadata") or {},
            if_exists=payload.get("if_exists") or "raise",
            ttl=payload.get("ttl"),
        )
        config = {
            "configurable": {
                **get_configurable_headers(request.headers),
                "thread_id": thread_id,
            }
        }
        if supersteps := payload.get("supersteps"):
            try:
                await Threads.State.bulk(
                    conn,
                    config=config,
                    supersteps=supersteps,
                )
            except HTTPException as e:
                detail = f"Thread {thread_id} was created, but there were problems updating the state: {e.detail}"
                raise HTTPException(status_code=201, detail=detail) from e

    # Decrypt thread fields in response
    thread = await fetchone(iter, not_found_code=409)
    thread = await decrypt_response(
        thread,
        "thread",
        THREAD_ENCRYPTION_FIELDS,
    )
    return ApiResponse(thread)


@retry_db
async def search_threads(
    request: ApiRequest,
):
    """List threads."""
    payload = await request.json(ThreadSearchRequest)
    select = validate_select_columns(payload.get("select") or None, THREAD_FIELDS)
    limit = int(payload.get("limit") or 10)
    offset = int(payload.get("offset") or 0)

    async with connect() as conn:
        threads_iter, next_offset = await CrudThreads.search(
            conn,
            status=payload.get("status"),
            values=payload.get("values"),
            metadata=payload.get("metadata"),
            ids=payload.get("ids"),
            limit=limit,
            offset=offset,
            sort_by=payload.get("sort_by"),
            sort_order=payload.get("sort_order"),
            select=select,
        )
    threads, response_headers = await get_pagination_headers(
        threads_iter, next_offset, offset
    )

    # Decrypt metadata, values, interrupts, and error in all returned threads
    decrypted_threads = await decrypt_responses(
        threads,
        "thread",
        THREAD_ENCRYPTION_FIELDS,
    )

    return ApiResponse(decrypted_threads, headers=response_headers)


@retry_db
async def count_threads(
    request: ApiRequest,
):
    """Count threads."""
    payload = await request.json(ThreadCountRequest)
    async with connect() as conn:
        count = await CrudThreads.count(
            conn,
            status=payload.get("status"),
            values=payload.get("values"),
            metadata=payload.get("metadata"),
        )
    return ApiResponse(count)


@retry_db
async def get_thread_state(
    request: ApiRequest,
):
    """Get state for a thread."""
    thread_id = request.path_params["thread_id"]
    validate_uuid(thread_id, "Invalid thread ID: must be a UUID")
    subgraphs = request.query_params.get("subgraphs") in ("true", "True")
    async with connect() as conn:
        config = {
            "configurable": {
                **get_configurable_headers(request.headers),
                "thread_id": thread_id,
            }
        }
        state = state_snapshot_to_thread_state(
            await Threads.State.get(conn, config=config, subgraphs=subgraphs)
        )
    return ApiResponse(state)


@retry_db
async def get_thread_state_at_checkpoint(
    request: ApiRequest,
):
    """Get state for a thread."""
    thread_id = request.path_params["thread_id"]
    validate_uuid(thread_id, "Invalid thread ID: must be a UUID")
    checkpoint_id = request.path_params["checkpoint_id"]
    async with connect() as conn:
        config = {
            "configurable": {
                **get_configurable_headers(request.headers),
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }
        state = state_snapshot_to_thread_state(
            await Threads.State.get(
                conn,
                config=config,
                subgraphs=request.query_params.get("subgraphs") in ("true", "True"),
            )
        )
    return ApiResponse(state)


@retry_db
async def get_thread_state_at_checkpoint_post(
    request: ApiRequest,
):
    """Get state for a thread."""
    thread_id = request.path_params["thread_id"]
    validate_uuid(thread_id, "Invalid thread ID: must be a UUID")
    payload = await request.json(ThreadStateCheckpointRequest)
    async with connect() as conn:
        config = {
            "configurable": {
                **payload["checkpoint"],
                **get_configurable_headers(request.headers),
                "thread_id": thread_id,
            }
        }
        state = state_snapshot_to_thread_state(
            await Threads.State.get(
                conn,
                config=config,
                subgraphs=payload.get("subgraphs", False),
            )
        )
    return ApiResponse(state)


@retry_db
async def update_thread_state(
    request: ApiRequest,
):
    """Add state to a thread."""
    thread_id = request.path_params["thread_id"]
    validate_uuid(thread_id, "Invalid thread ID: must be a UUID")
    payload = await request.json(ThreadStateUpdate)
    config = {"configurable": {"thread_id": thread_id}}
    if payload.get("checkpoint_id"):
        config["configurable"]["checkpoint_id"] = payload["checkpoint_id"]
    if payload.get("checkpoint"):
        config["configurable"].update(payload["checkpoint"])
    try:
        if user_id := request.user.display_name:
            config["configurable"]["user_id"] = user_id
    except AssertionError:
        pass
    config["configurable"].update(get_configurable_headers(request.headers))
    async with connect() as conn:
        inserted = await Threads.State.post(
            conn,
            config,
            payload.get("values"),
            payload.get("as_node"),
        )
    return ApiResponse(inserted)


@retry_db
async def get_thread_history(
    request: ApiRequest,
):
    """Get all past states for a thread."""
    thread_id = request.path_params["thread_id"]
    validate_uuid(thread_id, "Invalid thread ID: must be a UUID")
    limit_ = request.query_params.get("limit", 1)
    try:
        limit = int(limit_)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid limit {limit_}") from None
    before = request.query_params.get("before")
    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": "",
            **get_configurable_headers(request.headers),
        }
    }
    async with connect() as conn:
        states = [
            state_snapshot_to_thread_state(c)
            for c in await Threads.State.list(
                conn, config=config, limit=limit, before=before
            )
        ]
    return ApiResponse(states)


@retry_db
async def get_thread_history_post(
    request: ApiRequest,
):
    """Get all past states for a thread."""
    thread_id = request.path_params["thread_id"]
    validate_uuid(thread_id, "Invalid thread ID: must be a UUID")
    payload = await request.json(ThreadStateSearch)
    config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
    config["configurable"].update(payload.get("checkpoint", {}))
    config["configurable"].update(get_configurable_headers(request.headers))
    async with connect() as conn:
        states = [
            state_snapshot_to_thread_state(c)
            for c in await Threads.State.list(
                conn,
                config=config,
                limit=int(payload.get("limit") or 1),
                before=payload.get("before"),
                metadata=payload.get("metadata"),
            )
        ]
    return ApiResponse(states)


@retry_db
async def get_thread(
    request: ApiRequest,
):
    """Get a thread by ID."""
    thread_id = request.path_params["thread_id"]
    validate_uuid(thread_id, "Invalid thread ID: must be a UUID")
    async with connect() as conn:
        thread = await CrudThreads.get(conn, thread_id)

    # Decrypt metadata, values, interrupts, and error in response
    thread_data = await fetchone(thread)
    thread_data = await decrypt_response(
        thread_data,
        "thread",
        THREAD_ENCRYPTION_FIELDS,
    )
    return ApiResponse(thread_data)


@retry_db
async def patch_thread(
    request: ApiRequest,
):
    """Update a thread."""
    thread_id = request.path_params["thread_id"]
    validate_uuid(thread_id, "Invalid thread ID: must be a UUID")
    payload = await request.json(ThreadPatch)

    # Encrypt metadata before storing
    encrypted_payload = await encrypt_request(
        payload,
        "thread",
        ["metadata"],
    )

    async with connect() as conn:
        thread = await CrudThreads.patch(
            conn,
            thread_id,
            metadata=encrypted_payload.get("metadata") or {},
            ttl=payload.get("ttl"),
        )
    thread_data = await fetchone(thread)
    # Decrypt metadata, values, interrupts, and error in response
    thread_data = await decrypt_response(
        thread_data,
        "thread",
        THREAD_ENCRYPTION_FIELDS,
    )
    return ApiResponse(thread_data)


@retry_db
async def delete_thread(request: ApiRequest):
    """Delete a thread by ID."""
    thread_id = request.path_params["thread_id"]
    validate_uuid(thread_id, "Invalid thread ID: must be a UUID")
    async with connect() as conn:
        tid = await CrudThreads.delete(conn, thread_id)
    await fetchone(tid)
    return Response(status_code=204)


@retry_db
async def copy_thread(request: ApiRequest):
    thread_id = request.path_params["thread_id"]
    async with connect() as conn:
        iter = await CrudThreads.copy(conn, thread_id)
    thread_data = await fetchone(iter, not_found_code=409)
    # Decrypt metadata, values, interrupts, and error in response
    thread_data = await decrypt_response(
        thread_data,
        "thread",
        THREAD_ENCRYPTION_FIELDS,
    )
    return ApiResponse(thread_data)


@retry_db
async def join_thread_stream(request: ApiRequest):
    """Join a thread stream."""
    thread_id = request.path_params["thread_id"]
    validate_uuid(thread_id, "Invalid thread ID: must be a UUID")
    last_event_id = request.headers.get("last-event-id") or None
    validate_stream_id(
        last_event_id, "Invalid last-event-id: must be a valid Redis stream ID"
    )

    # Parse stream_modes parameter - can be single string or comma-separated list
    stream_modes_param = request.query_params.get("stream_modes")
    if stream_modes_param:
        if "," in stream_modes_param:
            # Handle comma-separated list
            stream_modes = [mode.strip() for mode in stream_modes_param.split(",")]
        else:
            # Handle single value
            stream_modes = [stream_modes_param]
        # Validate each mode
        for mode in stream_modes:
            if mode not in get_args(ThreadStreamMode):
                raise HTTPException(
                    status_code=422, detail=f"Invalid stream mode: {mode}"
                )
    else:
        # Default to run_modes
        stream_modes = ["run_modes"]

    return EventSourceResponse(
        Threads.Stream.join(
            thread_id,
            last_event_id=last_event_id,
            stream_modes=stream_modes,
        ),
    )


threads_routes: list[BaseRoute] = [
    ApiRoute("/threads", endpoint=create_thread, methods=["POST"]),
    ApiRoute("/threads/search", endpoint=search_threads, methods=["POST"]),
    ApiRoute("/threads/count", endpoint=count_threads, methods=["POST"]),
    ApiRoute("/threads/{thread_id}", endpoint=get_thread, methods=["GET"]),
    ApiRoute("/threads/{thread_id}", endpoint=patch_thread, methods=["PATCH"]),
    ApiRoute("/threads/{thread_id}", endpoint=delete_thread, methods=["DELETE"]),
    ApiRoute("/threads/{thread_id}/state", endpoint=get_thread_state, methods=["GET"]),
    ApiRoute(
        "/threads/{thread_id}/state", endpoint=update_thread_state, methods=["POST"]
    ),
    ApiRoute(
        "/threads/{thread_id}/history", endpoint=get_thread_history, methods=["GET"]
    ),
    ApiRoute("/threads/{thread_id}/copy", endpoint=copy_thread, methods=["POST"]),
    ApiRoute(
        "/threads/{thread_id}/history",
        endpoint=get_thread_history_post,
        methods=["POST"],
    ),
    ApiRoute(
        "/threads/{thread_id}/state/{checkpoint_id}",
        endpoint=get_thread_state_at_checkpoint,
        methods=["GET"],
    ),
    ApiRoute(
        "/threads/{thread_id}/state/checkpoint",
        endpoint=get_thread_state_at_checkpoint_post,
        methods=["POST"],
    ),
    ApiRoute(
        "/threads/{thread_id}/stream",
        endpoint=join_thread_stream,
        methods=["GET"],
    ),
]
