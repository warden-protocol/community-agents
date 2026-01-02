import os

if not (
    (disable_truststore := os.getenv("DISABLE_TRUSTSTORE"))
    and disable_truststore.lower() == "true"
):
    import truststore

    truststore.inject_into_ssl()

import asyncio
import functools
import json
import logging.config
import pathlib
import signal
import socket

import structlog

from langgraph_api.utils.errors import GraphLoadError, HealthServerStartupError
from langgraph_runtime import lifespan
from langgraph_runtime.database import healthcheck, pool_stats
from langgraph_runtime.metrics import get_metrics

logger = structlog.stdlib.get_logger(__name__)


def _ensure_port_available(host: str, port: int) -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
    except OSError as exc:
        raise HealthServerStartupError(host, port, exc) from exc


async def health_and_metrics_server():
    import uvicorn
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse, PlainTextResponse
    from starlette.routing import Route

    from langgraph_api.api.meta import METRICS_FORMATS

    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("LANGGRAPH_SERVER_HOST", "0.0.0.0")

    async def health_endpoint(request):
        # if db or redis is not healthy, this will raise an exception
        await healthcheck()
        return JSONResponse({"status": "ok"})

    async def metrics_endpoint(request: Request):
        metrics_format = request.query_params.get("format", "prometheus")
        if metrics_format not in METRICS_FORMATS:
            await logger.awarning(
                f"metrics format {metrics_format} not supported, falling back to prometheus"
            )
            metrics_format = "prometheus"

        metrics = get_metrics()
        worker_metrics = metrics["workers"]
        workers_max = worker_metrics["max"]
        workers_active = worker_metrics["active"]
        workers_available = worker_metrics["available"]

        project_id = os.getenv("LANGSMITH_HOST_PROJECT_ID")
        revision_id = os.getenv("LANGSMITH_HOST_REVISION_ID")

        pg_redis_stats = pool_stats(
            project_id=project_id,
            revision_id=revision_id,
            format=metrics_format,
        )

        if metrics_format == "json":
            resp = {
                **pg_redis_stats,
                "workers": worker_metrics,
            }
            return JSONResponse(resp)
        elif metrics_format == "prometheus":
            metrics_lines = [
                "# HELP lg_api_workers_max The maximum number of workers available.",
                "# TYPE lg_api_workers_max gauge",
                f'lg_api_workers_max{{project_id="{project_id}", revision_id="{revision_id}"}} {workers_max}',
                "# HELP lg_api_workers_active The number of currently active workers.",
                "# TYPE lg_api_workers_active gauge",
                f'lg_api_workers_active{{project_id="{project_id}", revision_id="{revision_id}"}} {workers_active}',
                "# HELP lg_api_workers_available The number of available (idle) workers.",
                "# TYPE lg_api_workers_available gauge",
                f'lg_api_workers_available{{project_id="{project_id}", revision_id="{revision_id}"}} {workers_available}',
            ]

            metrics_lines.extend(pg_redis_stats)

            return PlainTextResponse(
                "\n".join(metrics_lines),
                media_type="text/plain; version=0.0.4; charset=utf-8",
            )

    app = Starlette(
        routes=[
            Route("/ok", health_endpoint),
            Route("/metrics", metrics_endpoint),
        ]
    )

    try:
        _ensure_port_available(host, port)
    except HealthServerStartupError as exc:
        await logger.aerror(
            str(exc),
            host=exc.host,
            port=exc.port,
            cause=str(exc.cause),
        )
        raise

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="error",
        access_log=False,
    )
    # Server will run indefinitely until the process is terminated
    server = uvicorn.Server(config)

    logger.info(f"Health and metrics server started at http://{host}:{port}")
    try:
        await server.serve()
    except SystemExit as exc:
        if exc.code == 0:
            return
        try:
            _ensure_port_available(host, port)
        except HealthServerStartupError as port_exc:
            await logger.aerror(
                str(port_exc),
                host=port_exc.host,
                port=port_exc.port,
                cause=str(port_exc.cause),
            )
            raise port_exc from None
        error = HealthServerStartupError(host, port, exc)
        await logger.aerror(
            str(error), host=error.host, port=error.port, cause=str(error.cause)
        )
        raise error from None
    except OSError as exc:
        error = HealthServerStartupError(host, port, exc)
        await logger.aerror(
            str(error), host=error.host, port=error.port, cause=str(error.cause)
        )
        raise error from exc


async def entrypoint(
    grpc_port: int | None = None,
    entrypoint_name: str = "python-queue",
    cancel_event: asyncio.Event | None = None,
):
    from langgraph_api import logging as lg_logging
    from langgraph_api import timing
    from langgraph_api.api import user_router
    from langgraph_api.server import app

    lg_logging.set_logging_context({"entrypoint": entrypoint_name})
    tasks: set[asyncio.Task] = set()
    user_lifespan = None if user_router is None else user_router.router.lifespan_context
    wrapped_lifespan = timing.combine_lifespans(
        functools.partial(
            lifespan.lifespan,
            with_cron_scheduler=False,
            grpc_port=grpc_port,
            taskset=tasks,
            cancel_event=cancel_event,
        ),
        user_lifespan,
    )

    async with wrapped_lifespan(app):
        tasks.add(asyncio.create_task(health_and_metrics_server()))
        await asyncio.gather(*tasks)


async def main(grpc_port: int | None = None, entrypoint_name: str = "python-queue"):
    """Run the queue entrypoint and shut down gracefully on SIGTERM/SIGINT."""

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal() -> None:
        logger.warning("Received termination signal, initiating graceful shutdown")
        stop_event.set()

    try:
        loop.add_signal_handler(signal.SIGTERM, _handle_signal)
    except (NotImplementedError, RuntimeError):
        signal.signal(signal.SIGTERM, lambda *_: _handle_signal())

    entry_task = asyncio.create_task(
        entrypoint(
            grpc_port=grpc_port,
            entrypoint_name=entrypoint_name,
            cancel_event=stop_event,
        )
    )
    # Handle the case where the entrypoint errors out
    entry_task.add_done_callback(lambda _: stop_event.set())
    await stop_event.wait()

    logger.warning("Cancelling queue entrypoint task")
    entry_task.cancel()
    try:
        await entry_task
    except asyncio.CancelledError:
        pass
    except (GraphLoadError, HealthServerStartupError) as exc:
        raise SystemExit(1) from exc
    except RuntimeError as exc:
        if str(exc) == "generator didn't yield":
            last_error = lifespan.get_last_error()
            if last_error is not None:
                logger.exception(
                    "Application startup failed",
                    error_type=type(last_error).__name__,
                    error_message=str(last_error),
                )
                raise SystemExit(1) from None
        raise


if __name__ == "__main__":
    from langgraph_api import config

    config.IS_QUEUE_ENTRYPOINT = True
    with open(pathlib.Path(__file__).parent.parent / "logging.json") as file:
        loaded_config = json.load(file)
        logging.config.dictConfig(loaded_config)
    try:
        import uvloop  # type: ignore[unresolved-import]

        uvloop.install()
    except ImportError:
        pass
    # run the entrypoint
    asyncio.run(main())
