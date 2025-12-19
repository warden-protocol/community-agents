import asyncio
import functools
import importlib
import importlib.util
import os

import structlog
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import BaseRoute, Route

from langgraph_api import timing
from langgraph_api.api.a2a import a2a_routes
from langgraph_api.api.assistants import assistants_routes
from langgraph_api.api.mcp import mcp_routes
from langgraph_api.api.meta import meta_info, meta_metrics
from langgraph_api.api.openapi import get_openapi_spec
from langgraph_api.api.profile import profile_routes
from langgraph_api.api.runs import runs_routes
from langgraph_api.api.store import store_routes
from langgraph_api.api.threads import threads_routes
from langgraph_api.api.ui import ui_routes
from langgraph_api.auth.middleware import auth_middleware
from langgraph_api.config import (
    FF_PYSPY_PROFILING_ENABLED,
    HTTP_CONFIG,
    LANGGRAPH_ENCRYPTION,
    MIGRATIONS_PATH,
    MOUNT_PREFIX,
)
from langgraph_api.graph import js_bg_tasks
from langgraph_api.js.base import is_js_path
from langgraph_api.timing import profiled_import
from langgraph_api.validation import DOCS_HTML
from langgraph_runtime.database import connect, healthcheck

logger = structlog.stdlib.get_logger(__name__)


async def ok(request: Request, *, disabled: bool = False):
    if disabled:
        # We still expose an /ok endpoint even if disable_meta is set so that
        # the operator knows the server started up.
        return JSONResponse({"ok": True})
    check_db = int(request.query_params.get("check_db", "0"))  # must be "0" or "1"
    if check_db:
        await healthcheck()
    if js_bg_tasks:
        from langgraph_api.js.remote import js_healthcheck

        await js_healthcheck()
    return JSONResponse({"ok": True})


async def openapi(request: Request):
    spec = await asyncio.to_thread(get_openapi_spec)
    return Response(spec, media_type="application/json")


async def docs(request: Request):
    return HTMLResponse(DOCS_HTML.format(mount_prefix=MOUNT_PREFIX or ""))


shadowable_meta_routes: list[BaseRoute] = [
    Route("/", ok, methods=["GET"]),  # Root health check for load balancers
    Route("/info", meta_info, methods=["GET"]),
]
unshadowable_meta_routes: list[BaseRoute] = [
    Route("/ok", ok, methods=["GET"]),
    Route("/metrics", meta_metrics, methods=["GET"]),
    Route("/docs", docs, methods=["GET"]),
    Route("/openapi.json", openapi, methods=["GET"]),
]

middleware_for_protected_routes = [auth_middleware]

# Add encryption context middleware if encryption is configured
if LANGGRAPH_ENCRYPTION:
    from langgraph_api.api.encryption_middleware import EncryptionContextMiddleware

    middleware_for_protected_routes.append(Middleware(EncryptionContextMiddleware))

protected_routes: list[BaseRoute] = []

if HTTP_CONFIG:
    if not HTTP_CONFIG.get("disable_assistants"):
        protected_routes.extend(assistants_routes)
    if not HTTP_CONFIG.get("disable_runs"):
        protected_routes.extend(runs_routes)
    if not HTTP_CONFIG.get("disable_threads"):
        protected_routes.extend(threads_routes)
    if not HTTP_CONFIG.get("disable_store"):
        protected_routes.extend(store_routes)
    if FF_PYSPY_PROFILING_ENABLED:
        protected_routes.extend(profile_routes)
    if not HTTP_CONFIG.get("disable_ui"):
        protected_routes.extend(ui_routes)
    if not HTTP_CONFIG.get("disable_mcp"):
        protected_routes.extend(mcp_routes)
    if not HTTP_CONFIG.get("disable_a2a"):
        protected_routes.extend(a2a_routes)
else:
    protected_routes.extend(assistants_routes)
    protected_routes.extend(runs_routes)
    protected_routes.extend(threads_routes)
    protected_routes.extend(store_routes)
    if FF_PYSPY_PROFILING_ENABLED:
        protected_routes.extend(profile_routes)
    protected_routes.extend(ui_routes)
    protected_routes.extend(mcp_routes)
    protected_routes.extend(a2a_routes)


def _metadata_fn(app_import: str) -> dict[str, str]:
    return {"app": app_import}


@timing.timer(
    message="Loaded custom app from {app}",
    metadata_fn=_metadata_fn,
    warn_threshold_secs=3,
    warn_message=(
        "Import for custom app {app} exceeded the expected startup time. "
        "Slow initialization (often due to work executed at import time) can delay readiness, "
        "reduce scale-out capacity, and may cause deployments to be marked unhealthy."
    ),
    error_threshold_secs=30,
)
def load_custom_app(app_import: str) -> Starlette | None:
    # Expect a string in either "path/to/file.py:my_variable" or "some.module.in:my_variable"
    path, name = app_import.rsplit(":", 1)

    # skip loading custom app if it's a js path
    # we are handling this in `langgraph_api.js.remote.JSCustomHTTPProxyMiddleware`
    if is_js_path(path):
        return None

    try:
        os.environ["__LANGGRAPH_DEFER_LOOPBACK_TRANSPORT"] = "true"
        with profiled_import(app_import):
            if os.path.isfile(path) or path.endswith(".py"):
                # Import from file path using a unique module name.
                spec = importlib.util.spec_from_file_location(
                    "user_router_module", path
                )
                if spec is None or spec.loader is None:
                    raise ImportError(f"Cannot load spec from {path}")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            else:
                # Import as a normal module.
                module = importlib.import_module(path)
        user_router = getattr(module, name)
        if not isinstance(user_router, Starlette):
            raise TypeError(
                f"Object '{name}' in module '{path}' is not a Starlette or FastAPI application. "
                "Please initialize your app by importing and using the appropriate class: "
                "\nfrom starlette.applications import Starlette\n\napp = Starlette(...)\n\n"
                "or\n\nfrom fastapi import FastAPI\n\napp = FastAPI(...)\n\n"
            )
    except ImportError as e:
        raise ImportError(f"Failed to import app module '{path}'") from e
    except AttributeError as e:
        raise AttributeError(f"App '{name}' not found in module '{path}'") from e
    finally:
        os.environ.pop("__LANGGRAPH_DEFER_LOOPBACK_TRANSPORT", None)
    return user_router


user_router: Starlette | None = None
if HTTP_CONFIG:
    if HTTP_CONFIG.get("disable_meta"):
        shadowable_meta_routes = [
            Route(
                "/ok", functools.partial(ok, disabled=True), methods=["GET"], name="ok"
            )
        ]
        unshadowable_meta_routes = []

    if router_import := HTTP_CONFIG.get("app"):
        user_router = load_custom_app(router_import)
        if user_router:
            user_router.router.lifespan_context = timing.wrap_lifespan_context_aenter(
                user_router.router.lifespan_context,
            )


if "inmem" in MIGRATIONS_PATH:

    async def truncate(request: Request):
        from langgraph_runtime.checkpoint import Checkpointer

        await asyncio.to_thread(Checkpointer().clear)
        async with connect() as conn:
            await asyncio.to_thread(conn.clear)
        return JSONResponse({"ok": True})

    unshadowable_meta_routes.insert(
        0, Route("/internal/truncate", truncate, methods=["POST"])
    )
