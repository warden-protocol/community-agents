from functools import partial
from typing import Any
from uuid import uuid4

import jsonschema_rs
import structlog

# TODO: Remove dependency on langchain-core here.
from langchain_core.runnables.utils import create_model
from langgraph.pregel import Pregel
from pydantic import TypeAdapter
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.routing import BaseRoute

from langgraph_api import store as api_store
from langgraph_api.api.encryption_middleware import (
    decrypt_response,
    decrypt_responses,
    encrypt_request,
)
from langgraph_api.feature_flags import FF_USE_CORE_API, USE_RUNTIME_CONTEXT_API
from langgraph_api.graph import get_assistant_id, get_graph
from langgraph_api.grpc.ops import Assistants as GrpcAssistants
from langgraph_api.js.base import BaseRemotePregel
from langgraph_api.route import ApiRequest, ApiResponse, ApiRoute
from langgraph_api.schema import ASSISTANT_ENCRYPTION_FIELDS, ASSISTANT_FIELDS
from langgraph_api.serde import json_loads
from langgraph_api.utils import (
    fetchone,
    get_pagination_headers,
    validate_select_columns,
    validate_uuid,
)
from langgraph_api.utils.headers import get_configurable_headers
from langgraph_api.validation import (
    AssistantCountRequest,
    AssistantCreate,
    AssistantPatch,
    AssistantSearchRequest,
    AssistantVersionChange,
    AssistantVersionsSearchRequest,
    ConfigValidator,
)
from langgraph_runtime.checkpoint import Checkpointer
from langgraph_runtime.database import connect as base_connect
from langgraph_runtime.ops import Assistants
from langgraph_runtime.retry import retry_db

logger = structlog.stdlib.get_logger(__name__)

CrudAssistants = GrpcAssistants if FF_USE_CORE_API else Assistants

connect = partial(base_connect, supports_core_api=FF_USE_CORE_API)

EXCLUDED_CONFIG_SCHEMA = (
    "__pregel_checkpointer",
    "__pregel_store",
    "checkpoint_id",
    "checkpoint_ns",
    "thread_id",
)


def _get_configurable_jsonschema(graph: Pregel) -> dict:
    """Get the JSON schema for the configurable part of the graph.

    Important: we only return the `configurable` part of the schema.

    The default get_config_schema method returns the entire schema (Config),
    which includes other root keys like "max_concurrency", which we
    do not want to expose.

    Args:
        graph: The graph to get the schema for.

    Returns:
       The JSON schema for the configurable part of the graph.

    Whenever we no longer support langgraph < 0.6, we can remove this method
    in favor of graph.get_context_jsonschema().
    """
    # Otherwise, use the config_schema method.
    # TODO: Remove this when we no longer support langgraph < 0.6
    config_schema = graph.config_schema()  # type: ignore[deprecated]
    model_fields = getattr(config_schema, "model_fields", None) or getattr(
        config_schema, "__fields__", None
    )

    if model_fields is not None and "configurable" in model_fields:
        configurable = TypeAdapter(model_fields["configurable"].annotation)
        json_schema = configurable.json_schema()
        if json_schema:
            for key in EXCLUDED_CONFIG_SCHEMA:
                json_schema["properties"].pop(key, None)
        # The type name of the configurable type is not preserved.
        # We'll add it back to the schema if we can.
        if (
            hasattr(graph, "config_type")
            and graph.config_type is not None
            and hasattr(graph.config_type, "__name__")
        ):
            json_schema["title"] = graph.config_type.__name__
        return json_schema
    # If the schema does not have a configurable field, return an empty schema.
    return {}


def _state_jsonschema(graph: Pregel) -> dict | None:
    fields: dict = {}
    for k in graph.stream_channels_list:
        v = graph.channels[k]
        try:
            create_model(k, __root__=(v.UpdateType, None)).model_json_schema()
            fields[k] = (v.UpdateType, None)
        except Exception:
            fields[k] = (Any, None)
    return create_model(graph.get_name("State"), **fields).model_json_schema()


def _graph_schemas(graph: Pregel) -> dict:
    try:
        input_schema = graph.get_input_jsonschema()
    except Exception as e:
        logger.warning(
            f"Failed to get input schema for graph {graph.name} with error: `{e!s}`"
        )
        input_schema = None
    try:
        output_schema = graph.get_output_jsonschema()
    except Exception as e:
        logger.warning(
            f"Failed to get output schema for graph {graph.name} with error: `{e!s}`"
        )
        output_schema = None
    try:
        state_schema = _state_jsonschema(graph)
    except Exception as e:
        logger.warning(
            f"Failed to get state schema for graph {graph.name} with error: `{e!s}`"
        )
        state_schema = None

    try:
        config_schema = _get_configurable_jsonschema(graph)
    except Exception as e:
        logger.warning(
            f"Failed to get config schema for graph {graph.name} with error: `{e!s}`"
        )
        config_schema = None

    if USE_RUNTIME_CONTEXT_API:
        try:
            context_schema = graph.get_context_jsonschema()
        except Exception as e:
            logger.warning(
                f"Failed to get context schema for graph {graph.name} with error: `{e!s}`"
            )
            context_schema = graph.config_schema()  # type: ignore[deprecated]
    else:
        context_schema = None

    return {
        "input_schema": input_schema,
        "output_schema": output_schema,
        "state_schema": state_schema,
        "config_schema": config_schema,
        "context_schema": context_schema,
    }


@retry_db
async def create_assistant(request: ApiRequest) -> ApiResponse:
    """Create an assistant."""
    payload = await request.json(AssistantCreate)
    if assistant_id := payload.get("assistant_id"):
        validate_uuid(assistant_id, "Invalid assistant ID: must be a UUID")
    config = payload.get("config")
    if config:
        try:
            ConfigValidator.validate(config)
        except jsonschema_rs.ValidationError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    encrypted_payload = await encrypt_request(
        payload,
        "assistant",
        ASSISTANT_ENCRYPTION_FIELDS,
    )

    async with connect() as conn:
        assistant = await CrudAssistants.put(
            conn,
            assistant_id or str(uuid4()),
            config=encrypted_payload.get("config") or {},
            context=encrypted_payload.get("context"),  # None if not provided
            graph_id=payload["graph_id"],
            metadata=encrypted_payload.get("metadata") or {},
            if_exists=payload.get("if_exists") or "raise",
            name=payload.get("name") or "Untitled",
            description=payload.get("description"),
        )

    # Decrypt metadata, config, and context in response
    assistant_data = await fetchone(assistant, not_found_code=409)
    assistant_data = await decrypt_response(
        assistant_data,
        "assistant",
        ASSISTANT_ENCRYPTION_FIELDS,
    )
    return ApiResponse(assistant_data)


@retry_db
async def search_assistants(
    request: ApiRequest,
) -> ApiResponse:
    """List assistants."""
    payload = await request.json(AssistantSearchRequest)
    select = validate_select_columns(payload.get("select") or None, ASSISTANT_FIELDS)
    offset = int(payload.get("offset") or 0)
    config = payload.get("config")
    if config:
        try:
            ConfigValidator.validate(config)
        except jsonschema_rs.ValidationError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
    async with connect() as conn:
        assistants_iter, next_offset = await CrudAssistants.search(
            conn,
            graph_id=payload.get("graph_id"),
            name=payload.get("name"),
            metadata=payload.get("metadata"),
            limit=int(payload.get("limit") or 10),
            offset=offset,
            sort_by=payload.get("sort_by"),
            sort_order=payload.get("sort_order"),
            select=select,
        )
    assistants, response_headers = await get_pagination_headers(
        assistants_iter, next_offset, offset
    )

    # Decrypt metadata, config, and context in all returned assistants
    decrypted_assistants = await decrypt_responses(
        assistants,
        "assistant",
        ASSISTANT_ENCRYPTION_FIELDS,
    )

    return ApiResponse(decrypted_assistants, headers=response_headers)


@retry_db
async def count_assistants(
    request: ApiRequest,
) -> ApiResponse:
    """Count assistants."""
    payload = await request.json(AssistantCountRequest)
    async with connect() as conn:
        count = await CrudAssistants.count(
            conn,
            graph_id=payload.get("graph_id"),
            name=payload.get("name"),
            metadata=payload.get("metadata"),
        )
    return ApiResponse(count)


@retry_db
async def get_assistant(
    request: ApiRequest,
) -> ApiResponse:
    assistant_id = request.path_params["assistant_id"]
    """Get an assistant by ID."""
    validate_uuid(assistant_id, "Invalid assistant ID: must be a UUID")
    async with connect() as conn:
        assistant = await CrudAssistants.get(conn, assistant_id)

    # Decrypt metadata, config, and context in response
    assistant_data = await fetchone(assistant)
    assistant_data = await decrypt_response(
        assistant_data,
        "assistant",
        ASSISTANT_ENCRYPTION_FIELDS,
    )
    return ApiResponse(assistant_data)


@retry_db
async def get_assistant_graph(
    request: ApiRequest,
) -> ApiResponse:
    """Get an assistant by ID."""
    assistant_id = get_assistant_id(str(request.path_params["assistant_id"]))
    validate_uuid(assistant_id, "Invalid assistant ID: must be a UUID")
    async with connect() as conn:
        assistant_ = await CrudAssistants.get(conn, assistant_id)
        assistant = await fetchone(assistant_)
    config = json_loads(assistant["config"])
    configurable = config.setdefault("configurable", {})
    configurable.update(get_configurable_headers(request.headers))

    async with get_graph(
        assistant["graph_id"],
        config,
        checkpointer=Checkpointer(),
        store=(await api_store.get_store()),
    ) as graph:
        xray: bool | int = False
        xray_query = request.query_params.get("xray")
        if xray_query:
            if xray_query in ("true", "True"):
                xray = True
            elif xray_query in ("false", "False"):
                xray = False
            else:
                try:
                    xray = int(xray_query)
                except ValueError:
                    raise HTTPException(422, detail="Invalid xray value") from None

                if xray <= 0:
                    raise HTTPException(422, detail="Invalid xray value") from None

        if isinstance(graph, BaseRemotePregel):
            drawable_graph = await graph.fetch_graph(xray=xray)
            json_graph = drawable_graph.to_json()
            for node in json_graph.get("nodes", []):
                if (data := node.get("data")) and isinstance(data, dict):
                    data.pop("id", None)
            return ApiResponse(json_graph)

        try:
            drawable_graph = await graph.aget_graph(xray=xray)
            json_graph = drawable_graph.to_json()
            for node in json_graph.get("nodes", []):
                if (data := node.get("data")) and isinstance(data, dict):
                    data.pop("id", None)
            return ApiResponse(json_graph)
        except NotImplementedError:
            raise HTTPException(
                422, detail="The graph does not support visualization"
            ) from None


@retry_db
async def get_assistant_subgraphs(
    request: ApiRequest,
) -> ApiResponse:
    """Get an assistant by ID."""
    assistant_id = request.path_params["assistant_id"]
    validate_uuid(assistant_id, "Invalid assistant ID: must be a UUID")
    async with connect() as conn:
        assistant_ = await CrudAssistants.get(conn, assistant_id)
        assistant = await fetchone(assistant_)

    config = json_loads(assistant["config"])
    configurable = config.setdefault("configurable", {})
    configurable.update(get_configurable_headers(request.headers))
    async with get_graph(
        assistant["graph_id"],
        config,
        checkpointer=Checkpointer(),
        store=(await api_store.get_store()),
    ) as graph:
        namespace = request.path_params.get("namespace")

        if isinstance(graph, BaseRemotePregel):
            return ApiResponse(
                await graph.fetch_subgraphs(
                    namespace=namespace,
                    recurse=request.query_params.get("recurse", "False")
                    in ("true", "True"),
                )
            )

        try:
            return ApiResponse(
                {
                    ns: _graph_schemas(subgraph)
                    async for ns, subgraph in graph.aget_subgraphs(
                        namespace=namespace,
                        recurse=request.query_params.get("recurse", "False")
                        in ("true", "True"),
                    )
                }
            )
        except NotImplementedError:
            raise HTTPException(
                422, detail="The graph does not support visualization"
            ) from None


@retry_db
async def get_assistant_schemas(
    request: ApiRequest,
) -> ApiResponse:
    """Get an assistant by ID."""
    assistant_id = request.path_params["assistant_id"]
    validate_uuid(assistant_id, "Invalid assistant ID: must be a UUID")
    async with connect() as conn:
        assistant_ = await CrudAssistants.get(conn, assistant_id)
        assistant = await fetchone(assistant_)

    config = json_loads(assistant["config"])
    configurable = config.setdefault("configurable", {})
    configurable.update(get_configurable_headers(request.headers))
    async with get_graph(
        assistant["graph_id"],
        config,
        checkpointer=Checkpointer(),
        store=(await api_store.get_store()),
    ) as graph:
        if isinstance(graph, BaseRemotePregel):
            schemas = await graph.fetch_state_schema()
            return ApiResponse(
                {
                    "graph_id": assistant["graph_id"],
                    "input_schema": schemas.get("input"),
                    "output_schema": schemas.get("output"),
                    "state_schema": schemas.get("state"),
                    "config_schema": schemas.get("config"),
                    "context_schema": schemas.get("context"),
                }
            )

        schemas = _graph_schemas(graph)

        return ApiResponse(
            {
                "graph_id": assistant["graph_id"],
                **schemas,
            }
        )


@retry_db
async def patch_assistant(
    request: ApiRequest,
) -> ApiResponse:
    """Update an assistant."""
    assistant_id = request.path_params["assistant_id"]
    validate_uuid(assistant_id, "Invalid assistant ID: must be a UUID")
    payload = await request.json(AssistantPatch)
    config = payload.get("config")
    if config:
        try:
            ConfigValidator.validate(config)
        except jsonschema_rs.ValidationError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    encrypted_fields = await encrypt_request(
        payload,
        "assistant",
        ASSISTANT_ENCRYPTION_FIELDS,
    )

    async with connect() as conn:
        assistant = await CrudAssistants.patch(
            conn,
            assistant_id,
            config=encrypted_fields.get("config"),
            context=encrypted_fields.get("context"),
            graph_id=payload.get("graph_id"),
            metadata=encrypted_fields.get("metadata"),
            name=payload.get("name"),
            description=payload.get("description"),
        )

    # Decrypt metadata, config, and context in response
    assistant_data = await fetchone(assistant)
    assistant_data = await decrypt_response(
        assistant_data,
        "assistant",
        ASSISTANT_ENCRYPTION_FIELDS,
    )
    return ApiResponse(assistant_data)


@retry_db
async def delete_assistant(request: ApiRequest) -> Response:
    """Delete an assistant by ID."""
    assistant_id = request.path_params["assistant_id"]
    validate_uuid(assistant_id, "Invalid assistant ID: must be a UUID")
    async with connect() as conn:
        aid = await CrudAssistants.delete(conn, assistant_id)
    await fetchone(aid)
    return Response(status_code=204)


@retry_db
async def get_assistant_versions(request: ApiRequest) -> ApiResponse:
    """Get all versions of an assistant."""
    assistant_id = request.path_params["assistant_id"]
    validate_uuid(assistant_id, "Invalid assistant ID: must be a UUID")
    payload = await request.json(AssistantVersionsSearchRequest)
    async with connect() as conn:
        assistants_iter = await CrudAssistants.get_versions(
            conn,
            assistant_id,
            metadata=payload.get("metadata") or {},
            limit=int(payload.get("limit", 10)),
            offset=int(payload.get("offset", 0)),
        )
    assistants = [assistant async for assistant in assistants_iter]
    if not assistants:
        raise HTTPException(
            status_code=404, detail=f"Assistant {assistant_id} not found"
        )

    # Decrypt metadata, config, and context in all assistant versions
    decrypted_assistants = await decrypt_responses(
        assistants,
        "assistant",
        ASSISTANT_ENCRYPTION_FIELDS,
    )

    return ApiResponse(decrypted_assistants)


@retry_db
async def set_latest_assistant_version(request: ApiRequest) -> ApiResponse:
    """Change the version of an assistant."""
    assistant_id = request.path_params["assistant_id"]
    payload = await request.json(AssistantVersionChange)
    validate_uuid(assistant_id, "Invalid assistant ID: must be a UUID")
    async with connect() as conn:
        assistant = await CrudAssistants.set_latest(
            conn, assistant_id, payload.get("version")
        )

    # Decrypt metadata, config, and context in response
    assistant_data = await fetchone(assistant, not_found_code=404)
    assistant_data = await decrypt_response(
        assistant_data,
        "assistant",
        ASSISTANT_ENCRYPTION_FIELDS,
    )
    return ApiResponse(assistant_data)


assistants_routes: list[BaseRoute] = [
    ApiRoute("/assistants", create_assistant, methods=["POST"]),
    ApiRoute("/assistants/search", search_assistants, methods=["POST"]),
    ApiRoute("/assistants/count", count_assistants, methods=["POST"]),
    ApiRoute(
        "/assistants/{assistant_id}/latest",
        set_latest_assistant_version,
        methods=["POST"],
    ),
    ApiRoute(
        "/assistants/{assistant_id}/versions", get_assistant_versions, methods=["POST"]
    ),
    ApiRoute("/assistants/{assistant_id}", get_assistant, methods=["GET"]),
    ApiRoute("/assistants/{assistant_id}/graph", get_assistant_graph, methods=["GET"]),
    ApiRoute(
        "/assistants/{assistant_id}/schemas", get_assistant_schemas, methods=["GET"]
    ),
    ApiRoute(
        "/assistants/{assistant_id}/subgraphs", get_assistant_subgraphs, methods=["GET"]
    ),
    ApiRoute(
        "/assistants/{assistant_id}/subgraphs/{namespace}",
        get_assistant_subgraphs,
        methods=["GET"],
    ),
    ApiRoute("/assistants/{assistant_id}", patch_assistant, methods=["PATCH"]),
    ApiRoute("/assistants/{assistant_id}", delete_assistant, methods=["DELETE"]),
]

assistants_routes = [route for route in assistants_routes if route is not None]
