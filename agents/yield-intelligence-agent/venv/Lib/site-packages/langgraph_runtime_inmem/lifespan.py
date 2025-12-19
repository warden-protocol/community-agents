import asyncio
import signal
from contextlib import asynccontextmanager
from typing import Any

import structlog
from langchain_core.runnables.config import RunnableConfig, var_child_runnable_config
from langgraph.constants import CONF
from starlette.applications import Starlette

from langgraph_runtime_inmem import queue
from langgraph_runtime_inmem.database import start_pool, stop_pool

logger = structlog.stdlib.get_logger(__name__)


_LAST_LIFESPAN_ERROR: BaseException | None = None


def get_last_error() -> BaseException | None:
    return _LAST_LIFESPAN_ERROR


@asynccontextmanager
async def lifespan(
    app: Starlette | None = None,
    cancel_event: asyncio.Event | None = None,
    taskset: set[asyncio.Task] | None = None,
    **kwargs: Any,
):
    import langgraph_api.config as config
    from langgraph_api import __version__, feature_flags, graph, thread_ttl
    from langgraph_api import store as api_store
    from langgraph_api.asyncio import SimpleTaskGroup, set_event_loop
    from langgraph_api.http import start_http_client, stop_http_client
    from langgraph_api.js.ui import start_ui_bundler, stop_ui_bundler
    from langgraph_api.metadata import metadata_loop

    from langgraph_runtime_inmem import __version__ as langgraph_runtime_inmem_version

    await logger.ainfo(
        f"Starting In-Memory runtime with langgraph-api={__version__} and in-memory runtime={langgraph_runtime_inmem_version}",
        version=__version__,
        langgraph_runtime_inmem_version=langgraph_runtime_inmem_version,
    )
    try:
        current_loop = asyncio.get_running_loop()
        set_event_loop(current_loop)
    except RuntimeError:
        await logger.aerror("Failed to set loop")

    global _LAST_LIFESPAN_ERROR
    _LAST_LIFESPAN_ERROR = None

    await start_http_client()
    await start_pool()
    await start_ui_bundler()

    async def _log_graph_load_failure(err: graph.GraphLoadError) -> None:
        cause = err.__cause__ or err.cause
        log_fields = err.log_fields()
        log_fields["action"] = "fix_user_graph"
        await logger.aerror(
            f"Graph '{err.spec.id}' failed to load: {err.cause_message}",
            **log_fields,
        )
        await logger.adebug(
            "Full graph load failure traceback (internal)",
            **{k: v for k, v in log_fields.items() if k != "user_traceback"},
            exc_info=cause,
        )

    try:
        async with SimpleTaskGroup(
            cancel=True,
            cancel_event=cancel_event,
            taskgroup_name="Lifespan",
        ) as tg:
            tg.create_task(metadata_loop())
            await api_store.collect_store_from_env()
            store_instance = await api_store.get_store()
            if not api_store.CUSTOM_STORE:
                tg.create_task(store_instance.start_ttl_sweeper())  # type: ignore
            else:
                await logger.ainfo("Using custom store. Skipping store TTL sweeper.")
            tg.create_task(thread_ttl.thread_ttl_sweep_loop())

            if feature_flags.USE_RUNTIME_CONTEXT_API:
                from langgraph._internal._constants import CONFIG_KEY_RUNTIME
                from langgraph.runtime import Runtime

                langgraph_config: RunnableConfig = {
                    CONF: {CONFIG_KEY_RUNTIME: Runtime(store=store_instance)}
                }
            else:
                from langgraph.constants import CONFIG_KEY_STORE

                langgraph_config: RunnableConfig = {
                    CONF: {CONFIG_KEY_STORE: store_instance}
                }

            var_child_runnable_config.set(langgraph_config)

            # Keep after the setter above so users can access the store from within the factory function
            try:
                await graph.collect_graphs_from_env(True)
            except graph.GraphLoadError as exc:
                _LAST_LIFESPAN_ERROR = exc
                await _log_graph_load_failure(exc)
                raise
            if config.N_JOBS_PER_WORKER > 0:
                tg.create_task(queue_with_signal())

            yield
    except graph.GraphLoadError as exc:
        _LAST_LIFESPAN_ERROR = exc
        raise
    except asyncio.CancelledError:
        pass
    finally:
        await api_store.exit_store()
        await stop_ui_bundler()
        await graph.stop_remote_graphs()
        await stop_http_client()
        await stop_pool()


async def queue_with_signal():
    try:
        await queue.queue()
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.exception("Queue failed. Signaling shutdown", exc_info=exc)
        signal.raise_signal(signal.SIGINT)


lifespan.get_last_error = get_last_error  # type: ignore[attr-defined]
