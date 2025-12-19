import asyncio
import os
import uuid
from datetime import UTC, datetime
from typing import Any

import langgraph.version
import orjson
import structlog

import langgraph_api.config as config
from langgraph_api.auth.custom import get_auth_instance
from langgraph_api.config import (
    LANGGRAPH_CLOUD_LICENSE_KEY,
    LANGSMITH_AUTH_ENDPOINT,
    LANGSMITH_CONTROL_PLANE_API_KEY,
    USES_CUSTOM_APP,
    USES_CUSTOM_AUTH,
    USES_INDEXING,
    USES_STORE_TTL,
    USES_THREAD_TTL,
)
from langgraph_api.graph import GRAPHS, is_js_graph
from langgraph_api.http import http_request
from langgraph_api.js.base import is_js_path
from langgraph_license.validation import plus_features_enabled

logger = structlog.stdlib.get_logger(__name__)

INTERVAL = 300
REVISION = os.getenv("LANGSMITH_LANGGRAPH_API_REVISION")
VARIANT = os.getenv("LANGSMITH_LANGGRAPH_API_VARIANT")
PROJECT_ID = os.getenv("LANGSMITH_HOST_PROJECT_ID")
HOST_REVISION_ID = os.getenv("LANGSMITH_HOST_REVISION_ID")
TENANT_ID = os.getenv("LANGSMITH_TENANT_ID")
if PROJECT_ID:
    try:
        uuid.UUID(PROJECT_ID)
    except ValueError:
        raise ValueError(
            f"Invalid project ID: {PROJECT_ID}. Must be a valid UUID"
        ) from None
if TENANT_ID:
    try:
        uuid.UUID(TENANT_ID)
    except ValueError:
        raise ValueError(
            f"Invalid tenant ID: {TENANT_ID}. Must be a valid UUID"
        ) from None
if VARIANT == "cloud":
    HOST = "saas"
elif PROJECT_ID:
    HOST = "byoc"
else:
    HOST = "self-hosted"
PLAN = "enterprise" if plus_features_enabled() else "developer"
USER_API_URL = os.getenv("LANGGRAPH_API_URL", None)

RUN_COUNTER = 0
NODE_COUNTER = 0
FROM_TIMESTAMP = datetime.now(UTC).isoformat()

# Beacon endpoint for license key submissions
BEACON_ENDPOINT = "https://beacon.langchain.com/v1/beacon/metadata/submit"

# LangChain auth endpoint for API key submissions
LANGCHAIN_METADATA_ENDPOINT = None
if LANGSMITH_AUTH_ENDPOINT:
    if "/api/v1" in LANGSMITH_AUTH_ENDPOINT:
        # If the endpoint already has /api/v1 (for self-hosted control plane deployments), we assume it's the correct format
        LANGCHAIN_METADATA_ENDPOINT = (
            LANGSMITH_AUTH_ENDPOINT.rstrip("/") + "/metadata/submit"
        )
    else:
        LANGCHAIN_METADATA_ENDPOINT = (
            LANGSMITH_AUTH_ENDPOINT.rstrip("/") + "/v1/metadata/submit"
        )


def _lang_usage_metadata() -> tuple[dict[str, str], dict[str, int]]:
    js_graph_count = sum(1 for graph_id in GRAPHS if is_js_graph(graph_id))
    py_graph_count = len(GRAPHS) - js_graph_count

    auth_instance = get_auth_instance()
    custom_auth_enabled = auth_instance is not None
    custom_js_auth_enabled = auth_instance == "js"

    js_proxy_middleware_enabled = False
    if (
        config.HTTP_CONFIG
        and (app := config.HTTP_CONFIG.get("app"))
        and isinstance(app, str)
    ):
        app_path = app.split(":", 1)[0]  # type: ignore[possibly-unresolved-reference]
        js_proxy_middleware_enabled = is_js_path(app_path)

    tags = {
        "langgraph.platform.uses_custom_auth": str(custom_auth_enabled),
        "langgraph.platform.uses_js_custom_auth": str(custom_js_auth_enabled),
        "langgraph.platform.uses_js_proxy_middleware": str(js_proxy_middleware_enabled),
    }
    measures = {
        "langgraph.platform.py_graphs": py_graph_count,
        "langgraph.platform.js_graphs": js_graph_count,
    }

    return tags, measures


def incr_runs(*, incr: int = 1) -> None:
    global RUN_COUNTER
    RUN_COUNTER += incr


def incr_nodes(_, *, incr: int = 1) -> None:
    global NODE_COUNTER
    NODE_COUNTER += incr


async def metadata_loop() -> None:
    try:
        from langgraph_api import __version__
    except ImportError:
        __version__ = None
    if not LANGGRAPH_CLOUD_LICENSE_KEY and not LANGSMITH_CONTROL_PLANE_API_KEY:
        return
    lg_version = langgraph.version.__version__

    if (
        LANGGRAPH_CLOUD_LICENSE_KEY
        and not LANGGRAPH_CLOUD_LICENSE_KEY.startswith("lcl_")
        and not LANGSMITH_CONTROL_PLANE_API_KEY
    ):
        logger.info("Running in air-gapped mode, skipping metadata loop")
        return

    logger.info("Starting metadata loop")

    global RUN_COUNTER, NODE_COUNTER, FROM_TIMESTAMP
    base_tags = _ensure_strings(
        # Tag values must be strings.
        {
            "langgraph.python.version": lg_version,
            "langgraph_api.version": __version__ or "",
            "langgraph.platform.revision": REVISION or "",
            "langgraph.platform.variant": VARIANT or "",
            "langgraph.platform.host": HOST,
            "langgraph.platform.tenant_id": TENANT_ID or "",
            "langgraph.platform.project_id": PROJECT_ID or "",
            "langgraph.platform.plan": PLAN,
            # user app features
            "user_app.uses_indexing": USES_INDEXING or "",
            "user_app.uses_custom_app": USES_CUSTOM_APP or "",
            "user_app.uses_custom_auth": USES_CUSTOM_AUTH or "",
            "user_app.uses_thread_ttl": USES_THREAD_TTL or "",
            "user_app.uses_store_ttl": USES_STORE_TTL or "",
        }
    )
    while True:
        # because we always read and write from coroutines in main thread
        # we don't need a lock as long as there's no awaits in this block
        from_timestamp = FROM_TIMESTAMP
        to_timestamp = datetime.now(UTC).isoformat()
        nodes = NODE_COUNTER
        runs = RUN_COUNTER
        RUN_COUNTER = 0
        NODE_COUNTER = 0
        FROM_TIMESTAMP = to_timestamp
        usage_tags, usage_measures = _lang_usage_metadata()

        base_payload = {
            "from_timestamp": from_timestamp,
            "to_timestamp": to_timestamp,
            "tags": base_tags | _ensure_strings(usage_tags),
            "measures": {
                "langgraph.platform.runs": int(runs),
                "langgraph.platform.nodes": int(nodes),
                **usage_measures,
            },
            "logs": [],
        }

        # Track successful submissions
        submissions_attempted = []
        submissions_failed = []

        # 1. Send to beacon endpoint if license key starts with lcl_
        if LANGGRAPH_CLOUD_LICENSE_KEY and LANGGRAPH_CLOUD_LICENSE_KEY.startswith(
            "lcl_"
        ):
            beacon_payload = {
                **base_payload,
                "license_key": LANGGRAPH_CLOUD_LICENSE_KEY,
            }
            submissions_attempted.append("beacon")
            try:
                await http_request(
                    "POST",
                    BEACON_ENDPOINT,
                    body=orjson.dumps(beacon_payload),
                    headers={"Content-Type": "application/json"},
                )
                await logger.ainfo("Successfully submitted metadata to beacon endpoint")
            except Exception as e:
                submissions_failed.append("beacon")
                await logger.awarning(
                    "Beacon metadata submission failed.", error=str(e)
                )

        # 2. Send to langchain auth endpoint if API key is set
        if LANGSMITH_CONTROL_PLANE_API_KEY and LANGCHAIN_METADATA_ENDPOINT:
            langchain_payload = {
                **base_payload,
                "api_key": LANGSMITH_CONTROL_PLANE_API_KEY,
            }
            submissions_attempted.append("langchain")
            try:
                await http_request(
                    "POST",
                    LANGCHAIN_METADATA_ENDPOINT,
                    body=orjson.dumps(langchain_payload),
                    headers={"Content-Type": "application/json"},
                )
                logger.info("Successfully submitted metadata to LangSmith instance")
            except Exception as e:
                submissions_failed.append("langchain")
                await logger.awarning(
                    "LangChain metadata submission failed.", error=str(e)
                )

        if submissions_attempted and len(submissions_failed) == len(
            submissions_attempted
        ):
            # retry on next iteration
            incr_runs(incr=runs)
            incr_nodes("", incr=nodes)
            FROM_TIMESTAMP = from_timestamp
            await logger.awarning(
                "All metadata submissions failed, will retry",
                attempted=submissions_attempted,
                failed=submissions_failed,
            )

        await asyncio.sleep(INTERVAL)


def _ensure_strings(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: "" if v is None else str(v) for k, v in payload.items()}
