import os

import structlog
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from langgraph_api import asyncio as lg_asyncio
from langgraph_api import config, metadata
from langgraph_api.http_metrics_utils import HTTP_LATENCY_BUCKETS
from langgraph_runtime.database import connect, pool_stats
from langgraph_runtime.metrics import get_metrics
from langgraph_runtime.ops import Runs

logger = structlog.stdlib.get_logger(__name__)

_meter_provider = None
_customer_attributes = {}

_http_request_counter = None
_http_latency_histogram = None


def initialize_self_hosted_metrics():
    global \
        _meter_provider, \
        _http_request_counter, \
        _http_latency_histogram, \
        _customer_attributes

    if not config.LANGGRAPH_METRICS_ENABLED:
        return

    if not config.LANGGRAPH_METRICS_ENDPOINT:
        raise RuntimeError(
            "LANGGRAPH_METRICS_ENABLED is true but no LANGGRAPH_METRICS_ENDPOINT is configured"
        )

    # for now, this is only enabled for fully self-hosted customers
    # we will need to update the otel collector auth model to support hybrid customers
    if not config.LANGGRAPH_CLOUD_LICENSE_KEY:
        logger.warning(
            "Self-hosted metrics require a license key, and do not work with hybrid deployments yet."
        )
        return

    try:
        exporter = OTLPMetricExporter(
            endpoint=config.LANGGRAPH_METRICS_ENDPOINT,
            headers={"X-Langchain-License-Key": config.LANGGRAPH_CLOUD_LICENSE_KEY},
        )

        # this will periodically export metrics to our beacon lgp otel collector in a separate thread
        metric_reader = PeriodicExportingMetricReader(
            exporter=exporter,
            export_interval_millis=config.LANGGRAPH_METRICS_EXPORT_INTERVAL_MS,
        )

        resource_attributes = {
            SERVICE_NAME: config.SELF_HOSTED_OBSERVABILITY_SERVICE_NAME,
        }

        resource = Resource.create(resource_attributes)

        if config.LANGGRAPH_CLOUD_LICENSE_KEY:
            try:
                from langgraph_license.validation import (
                    CUSTOMER_ID,  # type: ignore[unresolved-import]
                    CUSTOMER_NAME,  # type: ignore[unresolved-import]
                )

                if CUSTOMER_ID:
                    _customer_attributes["customer_id"] = CUSTOMER_ID
                if CUSTOMER_NAME:
                    _customer_attributes["customer_name"] = CUSTOMER_NAME
            except ImportError:
                pass
            except Exception as e:
                logger.warning("Failed to get customer info from license", exc_info=e)

        # resolves to pod name in k8s, or container id in docker
        instance_id = os.environ.get("HOSTNAME")
        if instance_id:
            _customer_attributes["instance_id"] = instance_id

        _meter_provider = MeterProvider(
            metric_readers=[metric_reader], resource=resource
        )
        metrics.set_meter_provider(_meter_provider)

        meter = metrics.get_meter("langgraph_api.self_hosted")

        meter.create_observable_gauge(
            name="lg_api_num_pending_runs",
            description="The number of runs currently pending",
            unit="1",
            callbacks=[_get_pending_runs_callback],
        )

        meter.create_observable_gauge(
            name="lg_api_num_running_runs",
            description="The number of runs currently running",
            unit="1",
            callbacks=[_get_running_runs_callback],
        )

        meter.create_observable_gauge(
            name="lg_api_pending_runs_wait_time_max",
            description="The maximum time a run has been pending, in seconds",
            unit="s",
            callbacks=[_get_pending_runs_wait_time_max_callback],
        )

        meter.create_observable_gauge(
            name="lg_api_pending_runs_wait_time_med",
            description="The median pending wait time across runs, in seconds",
            unit="s",
            callbacks=[_get_pending_runs_wait_time_med_callback],
        )

        meter.create_observable_gauge(
            name="lg_api_pending_unblocked_runs_wait_time_max",
            description="The maximum time a run has been pending excluding runs blocked by another run on the same thread, in seconds",
            unit="s",
            callbacks=[_get_pending_unblocked_runs_wait_time_max_callback],
        )

        if config.N_JOBS_PER_WORKER > 0:
            meter.create_observable_gauge(
                name="lg_api_workers_max",
                description="The maximum number of workers available",
                unit="1",
                callbacks=[_get_workers_max_callback],
            )

            meter.create_observable_gauge(
                name="lg_api_workers_active",
                description="The number of currently active workers",
                unit="1",
                callbacks=[_get_workers_active_callback],
            )

            meter.create_observable_gauge(
                name="lg_api_workers_available",
                description="The number of available (idle) workers",
                unit="1",
                callbacks=[_get_workers_available_callback],
            )

        if not config.IS_QUEUE_ENTRYPOINT and not config.IS_EXECUTOR_ENTRYPOINT:
            _http_request_counter = meter.create_counter(
                name="lg_api_http_requests_total",
                description="Total number of HTTP requests",
                unit="1",
            )

            _http_latency_histogram = meter.create_histogram(
                name="lg_api_http_requests_latency_seconds",
                description="HTTP request latency in seconds",
                unit="s",
                explicit_bucket_boundaries_advisory=[
                    b for b in HTTP_LATENCY_BUCKETS if b != float("inf")
                ],
            )

        meter.create_observable_gauge(
            name="lg_api_pg_pool_max",
            description="The maximum size of the postgres connection pool",
            unit="1",
            callbacks=[_get_pg_pool_max_callback],
        )

        meter.create_observable_gauge(
            name="lg_api_pg_pool_size",
            description="Number of connections currently managed by the postgres connection pool",
            unit="1",
            callbacks=[_get_pg_pool_size_callback],
        )

        meter.create_observable_gauge(
            name="lg_api_pg_pool_available",
            description="Number of connections currently idle in the postgres connection pool",
            unit="1",
            callbacks=[_get_pg_pool_available_callback],
        )

        meter.create_observable_gauge(
            name="lg_api_redis_pool_max",
            description="The maximum size of the redis connection pool",
            unit="1",
            callbacks=[_get_redis_pool_max_callback],
        )

        meter.create_observable_gauge(
            name="lg_api_redis_pool_size",
            description="Number of connections currently in use in the redis connection pool",
            unit="1",
            callbacks=[_get_redis_pool_size_callback],
        )

        meter.create_observable_gauge(
            name="lg_api_redis_pool_available",
            description="Number of connections currently idle in the redis connection pool",
            unit="1",
            callbacks=[_get_redis_pool_available_callback],
        )

        logger.info(
            "Self-hosted metrics initialized successfully",
            endpoint=config.LANGGRAPH_METRICS_ENDPOINT,
            export_interval_ms=config.LANGGRAPH_METRICS_EXPORT_INTERVAL_MS,
        )

    except Exception as e:
        logger.exception("Failed to initialize self-hosted metrics", exc_info=e)


def shutdown_self_hosted_metrics():
    global _meter_provider

    if _meter_provider:
        try:
            logger.info("Shutting down self-hosted metrics")
            _meter_provider.shutdown(timeout_millis=5000)
            _meter_provider = None
        except Exception as e:
            logger.exception("Failed to shutdown self-hosted metrics", exc_info=e)


def record_http_request(
    method: str, route_path: str, status: int, latency_seconds: float
):
    if not _meter_provider or not _http_request_counter or not _http_latency_histogram:
        return

    attributes = {"method": method, "path": route_path, "status": str(status)}
    if _customer_attributes:
        attributes.update(_customer_attributes)

    _http_request_counter.add(1, attributes)
    _http_latency_histogram.record(latency_seconds, attributes)


def _get_queue_stats():
    async def _fetch_queue_stats():
        try:
            async with connect() as conn:
                return await Runs.stats(conn)
        except Exception as e:
            logger.warning("Failed to get queue stats from database", exc_info=e)
            return {
                "n_pending": 0,
                "n_running": 0,
                "pending_runs_wait_time_max_secs": 0,
                "pending_runs_wait_time_med_secs": 0,
                "pending_unblocked_runs_wait_time_max_secs": 0,
            }

    try:
        future = lg_asyncio.run_coroutine_threadsafe(_fetch_queue_stats())
        return future.result(timeout=5)
    except Exception as e:
        logger.warning("Failed to get queue stats", exc_info=e)
        return {
            "n_pending": 0,
            "n_running": 0,
            "pending_runs_wait_time_max_secs": 0,
            "pending_runs_wait_time_med_secs": 0,
            "pending_unblocked_runs_wait_time_max_secs": 0,
        }


def _get_pool_stats():
    # _get_pool() inside the pool_stats fn will not work correctly if called from the daemon thread created by PeriodicExportingMetricReader,
    # so we submit this as a coro to run in the main event loop
    async def _fetch_pool_stats():
        try:
            return pool_stats(
                metadata.PROJECT_ID, metadata.HOST_REVISION_ID, format="json"
            )
        except Exception as e:
            logger.warning("Failed to get pool stats", exc_info=e)
            return {"postgres": {}, "redis": {}}

    try:
        future = lg_asyncio.run_coroutine_threadsafe(_fetch_pool_stats())
        return future.result(timeout=5)
    except Exception as e:
        logger.warning("Failed to get pool stats", exc_info=e)
        return {"postgres": {}, "redis": {}}


def _get_pending_runs_callback(options: CallbackOptions):
    try:
        stats = _get_queue_stats()
        return [Observation(stats.get("n_pending", 0), attributes=_customer_attributes)]
    except Exception as e:
        logger.warning("Failed to get pending runs", exc_info=e)
        return [Observation(0, attributes=_customer_attributes)]


def _get_running_runs_callback(options: CallbackOptions):
    try:
        stats = _get_queue_stats()
        return [Observation(stats.get("n_running", 0), attributes=_customer_attributes)]
    except Exception as e:
        logger.warning("Failed to get running runs", exc_info=e)
        return [Observation(0, attributes=_customer_attributes)]


def _get_pending_runs_wait_time_max_callback(options: CallbackOptions):
    try:
        stats = _get_queue_stats()
        value = stats.get("pending_runs_wait_time_max_secs")
        value = 0 if value is None else value
        return [Observation(value, attributes=_customer_attributes)]
    except Exception as e:
        logger.warning("Failed to get max pending wait time", exc_info=e)
        return [Observation(0, attributes=_customer_attributes)]


def _get_pending_runs_wait_time_med_callback(options: CallbackOptions):
    try:
        stats = _get_queue_stats()
        value = stats.get("pending_runs_wait_time_med_secs")
        value = 0 if value is None else value
        return [Observation(value, attributes=_customer_attributes)]
    except Exception as e:
        logger.warning("Failed to get median pending wait time", exc_info=e)
        return [Observation(0, attributes=_customer_attributes)]


def _get_pending_unblocked_runs_wait_time_max_callback(options: CallbackOptions):
    try:
        stats = _get_queue_stats()
        value = stats.get("pending_unblocked_runs_wait_time_max_secs")
        value = 0 if value is None else value
        return [Observation(value, attributes=_customer_attributes)]
    except Exception as e:
        logger.warning("Failed to get max unblocked pending wait time", exc_info=e)
        return [Observation(0, attributes=_customer_attributes)]


def _get_workers_max_callback(options: CallbackOptions):
    try:
        metrics_data = get_metrics()
        worker_metrics = metrics_data.get("workers", {})
        return [
            Observation(worker_metrics.get("max", 0), attributes=_customer_attributes)
        ]
    except Exception as e:
        logger.warning("Failed to get max workers", exc_info=e)
        return [Observation(0, attributes=_customer_attributes)]


def _get_workers_active_callback(options: CallbackOptions):
    try:
        metrics_data = get_metrics()
        worker_metrics = metrics_data.get("workers", {})
        return [
            Observation(
                worker_metrics.get("active", 0), attributes=_customer_attributes
            )
        ]
    except Exception as e:
        logger.warning("Failed to get active workers", exc_info=e)
        return [Observation(0, attributes=_customer_attributes)]


def _get_workers_available_callback(options: CallbackOptions):
    try:
        metrics_data = get_metrics()
        worker_metrics = metrics_data.get("workers", {})
        return [
            Observation(
                worker_metrics.get("available", 0), attributes=_customer_attributes
            )
        ]
    except Exception as e:
        logger.warning("Failed to get available workers", exc_info=e)
        return [Observation(0, attributes=_customer_attributes)]


def _get_pg_pool_max_callback(options: CallbackOptions):
    try:
        stats = _get_pool_stats()
        pg_max = stats.get("postgres", {}).get("pool_max", 0)
        return [Observation(pg_max, attributes=_customer_attributes)]
    except Exception as e:
        logger.warning("Failed to get PG pool max", exc_info=e)
        return [Observation(0, attributes=_customer_attributes)]


def _get_pg_pool_size_callback(options: CallbackOptions):
    try:
        stats = _get_pool_stats()
        pg_size = stats.get("postgres", {}).get("pool_size", 0)
        return [Observation(pg_size, attributes=_customer_attributes)]
    except Exception as e:
        logger.warning("Failed to get PG pool size", exc_info=e)
        return [Observation(0, attributes=_customer_attributes)]


def _get_pg_pool_available_callback(options: CallbackOptions):
    try:
        stats = _get_pool_stats()
        pg_available = stats.get("postgres", {}).get("pool_available", 0)
        return [Observation(pg_available, attributes=_customer_attributes)]
    except Exception as e:
        logger.warning("Failed to get PG pool available", exc_info=e)
        return [Observation(0, attributes=_customer_attributes)]


def _get_redis_pool_max_callback(options: CallbackOptions):
    try:
        stats = _get_pool_stats()
        redis_max = stats.get("redis", {}).get("max_connections", 0)
        return [Observation(redis_max, attributes=_customer_attributes)]
    except Exception as e:
        logger.warning("Failed to get Redis pool max", exc_info=e)
        return [Observation(0, attributes=_customer_attributes)]


def _get_redis_pool_size_callback(options: CallbackOptions):
    try:
        stats = _get_pool_stats()
        redis_size = stats.get("redis", {}).get("in_use_connections", 0)
        return [Observation(redis_size, attributes=_customer_attributes)]
    except Exception as e:
        logger.warning("Failed to get Redis pool size", exc_info=e)
        return [Observation(0, attributes=_customer_attributes)]


def _get_redis_pool_available_callback(options: CallbackOptions):
    try:
        stats = _get_pool_stats()
        redis_available = stats.get("redis", {}).get("idle_connections", 0)
        return [Observation(redis_available, attributes=_customer_attributes)]
    except Exception as e:
        logger.warning("Failed to get Redis pool available", exc_info=e)
        return [Observation(0, attributes=_customer_attributes)]
