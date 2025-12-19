import os
from os import environ, getenv
from typing import TYPE_CHECKING, Annotated, Literal, TypeVar, cast

from pydantic.functional_validators import AfterValidator
from starlette.config import Config, undefined
from starlette.datastructures import CommaSeparatedStrings

from langgraph_api import traceblock
from langgraph_api.config import _parse
from langgraph_api.config.schemas import (
    AuthConfig,
    CheckpointerConfig,
    CorsConfig,
    EncryptionConfig,
    HttpConfig,
    SerdeConfig,
    StoreConfig,
    ThreadTTLConfig,
    TTLConfig,
    WebhooksConfig,
    webhooks_validator,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# env

env = Config()


TD = TypeVar("TD")


STATS_INTERVAL_SECS = env("STATS_INTERVAL_SECS", cast=int, default=60)

# storage

DATABASE_URI = env("DATABASE_URI", cast=str, default=getenv("POSTGRES_URI", undefined))
MIGRATIONS_PATH = env("MIGRATIONS_PATH", cast=str, default="/storage/migrations")
POSTGRES_POOL_MAX_SIZE = env("LANGGRAPH_POSTGRES_POOL_MAX_SIZE", cast=int, default=150)
RESUMABLE_STREAM_TTL_SECONDS = env(
    "RESUMABLE_STREAM_TTL_SECONDS",
    cast=int,
    default=120,  # 2 minutes
)


def _get_encryption_key(key_str: str | None):
    if not key_str:
        return None
    key = key_str.encode(encoding="utf-8")
    if len(key) not in (16, 24, 32):
        raise ValueError("LANGGRAPH_AES_KEY must be 16, 24, or 32 bytes long.")
    return key


LANGGRAPH_AES_KEY = env("LANGGRAPH_AES_KEY", default=None, cast=_get_encryption_key)

# redis
REDIS_URI = env("REDIS_URI", cast=str)
REDIS_CLUSTER = env("REDIS_CLUSTER", cast=bool, default=False)
REDIS_MAX_CONNECTIONS = env("REDIS_MAX_CONNECTIONS", cast=int, default=2000)
REDIS_CONNECT_TIMEOUT = env("REDIS_CONNECT_TIMEOUT", cast=float, default=10.0)
REDIS_HEALTH_CHECK_INTERVAL = env(
    "REDIS_HEALTH_CHECK_INTERVAL", cast=float, default=10.0
)
REDIS_KEY_PREFIX = env("REDIS_KEY_PREFIX", cast=str, default="")
RUN_STATS_CACHE_SECONDS = env("RUN_STATS_CACHE_SECONDS", cast=int, default=60)

# server
ALLOW_PRIVATE_NETWORK = env("ALLOW_PRIVATE_NETWORK", cast=bool, default=False)
"""Only enable for langgraph dev when server is running on loopback address.

See https://developer.chrome.com/blog/private-network-access-update-2024-03
"""

# gRPC client pool size for persistence server.
GRPC_CLIENT_POOL_SIZE = env("GRPC_CLIENT_POOL_SIZE", cast=int, default=5)

# gRPC message size limits (100MB default)
GRPC_SERVER_MAX_RECV_MSG_BYTES = env(
    "GRPC_SERVER_MAX_RECV_MSG_BYTES", cast=int, default=300 * 1024 * 1024
)
GRPC_SERVER_MAX_SEND_MSG_BYTES = env(
    "GRPC_SERVER_MAX_SEND_MSG_BYTES", cast=int, default=300 * 1024 * 1024
)
GRPC_CLIENT_MAX_RECV_MSG_BYTES = env(
    "GRPC_CLIENT_MAX_RECV_MSG_BYTES", cast=int, default=300 * 1024 * 1024
)
GRPC_CLIENT_MAX_SEND_MSG_BYTES = env(
    "GRPC_CLIENT_MAX_SEND_MSG_BYTES", cast=int, default=300 * 1024 * 1024
)

# Minimum payload size to use the dedicated thread pool for JSON parsing.
# (Otherwise, the payload is parsed directly in the event loop.)
JSON_THREAD_POOL_MINIMUM_SIZE_BYTES = 100 * 1024  # 100 KB

HTTP_CONFIG = env("LANGGRAPH_HTTP", cast=_parse.parse_schema(HttpConfig), default=None)
STORE_CONFIG = env(
    "LANGGRAPH_STORE", cast=_parse.parse_schema(StoreConfig), default=None
)

MOUNT_PREFIX: str | None = env("MOUNT_PREFIX", cast=str, default=None) or (
    HTTP_CONFIG.get("mount_prefix") if HTTP_CONFIG else None
)

CORS_ALLOW_ORIGINS = env("CORS_ALLOW_ORIGINS", cast=CommaSeparatedStrings, default="*")
CORS_CONFIG = env(
    "CORS_CONFIG", cast=_parse.parse_schema(CorsConfig), default=None
) or (HTTP_CONFIG.get("cors") if HTTP_CONFIG else None)
"""
{
    "type": "object",
    "properties": {
        "allow_origins": {
            "type": "array",
            "items": {"type": "string"},
            "default": []
        },
        "allow_methods": {
            "type": "array",
            "items": {"type": "string"},
            "default": ["GET"]
        },
        "allow_headers": {
            "type": "array",
            "items": {"type": "string"},
            "default": []
        },
        "allow_credentials": {
            "type": "boolean",
            "default": false
        },
        "allow_origin_regex": {
            "type": ["string", "null"],
            "default": null
        },
        "expose_headers": {
            "type": "array",
            "items": {"type": "string"},
            "default": []
        },
        "max_age": {
            "type": "integer",
            "default": 600
        }
    }
}
"""
if (
    CORS_CONFIG is not None
    and CORS_ALLOW_ORIGINS != "*"
    and CORS_CONFIG.get("allow_origins") is None
):
    CORS_CONFIG["allow_origins"] = CORS_ALLOW_ORIGINS

# queue

BG_JOB_HEARTBEAT = 120  # seconds
BG_JOB_INTERVAL = 30  # seconds
BG_JOB_MAX_RETRIES = 3
BG_JOB_ISOLATED_LOOPS = env("BG_JOB_ISOLATED_LOOPS", cast=bool, default=False)
BG_JOB_SHUTDOWN_GRACE_PERIOD_SECS = env(
    "BG_JOB_SHUTDOWN_GRACE_PERIOD_SECS",
    cast=int,
    default=180,  # 3 minutes
)
MAX_STREAM_CHUNK_SIZE_BYTES = env(
    "MAX_STREAM_CHUNK_SIZE_BYTES", cast=int, default=1024 * 1024 * 128
)


CHECKPOINTER_CONFIG = env(
    "LANGGRAPH_CHECKPOINTER", cast=_parse.parse_schema(CheckpointerConfig), default=None
)
SERDE: SerdeConfig | None = (
    CHECKPOINTER_CONFIG["serde"]
    if CHECKPOINTER_CONFIG and "serde" in CHECKPOINTER_CONFIG
    else None
)
THREAD_TTL: ThreadTTLConfig | None = env(
    "LANGGRAPH_THREAD_TTL", cast=_parse.parse_thread_ttl, default=None
)
if THREAD_TTL is None and CHECKPOINTER_CONFIG is not None:
    THREAD_TTL = CHECKPOINTER_CONFIG.get("ttl")

N_JOBS_PER_WORKER = env("N_JOBS_PER_WORKER", cast=int, default=10)
BG_JOB_TIMEOUT_SECS = env("BG_JOB_TIMEOUT_SECS", cast=float, default=3600)

FF_CRONS_ENABLED = env("FF_CRONS_ENABLED", cast=bool, default=True)
FF_LOG_DROPPED_EVENTS = env("FF_LOG_DROPPED_EVENTS", cast=bool, default=False)
FF_LOG_QUERY_AND_PARAMS = env("FF_LOG_QUERY_AND_PARAMS", cast=bool, default=False)

# auth

LANGGRAPH_AUTH_TYPE = env("LANGGRAPH_AUTH_TYPE", cast=str, default="noop")
LANGGRAPH_POSTGRES_EXTENSIONS: Literal["standard", "lite"] = env(
    "LANGGRAPH_POSTGRES_EXTENSIONS", cast=str, default="standard"
)
if LANGGRAPH_POSTGRES_EXTENSIONS not in ("standard", "lite"):
    raise ValueError(
        f"Unknown LANGGRAPH_POSTGRES_EXTENSIONS value: {LANGGRAPH_POSTGRES_EXTENSIONS}"
    )
LANGGRAPH_AUTH = env(
    "LANGGRAPH_AUTH", cast=_parse.parse_schema(AuthConfig), default=None
)
LANGGRAPH_ENCRYPTION = env(
    "LANGGRAPH_ENCRYPTION", cast=_parse.parse_schema(EncryptionConfig), default=None
)
LANGSMITH_TENANT_ID = env("LANGSMITH_TENANT_ID", cast=str, default=None)
LANGSMITH_AUTH_VERIFY_TENANT_ID = env(
    "LANGSMITH_AUTH_VERIFY_TENANT_ID",
    cast=bool,
    default=LANGSMITH_TENANT_ID is not None,
)

if LANGGRAPH_AUTH_TYPE == "langsmith":
    LANGSMITH_AUTH_ENDPOINT = env("LANGSMITH_AUTH_ENDPOINT", cast=str)
    LANGSMITH_TENANT_ID = env("LANGSMITH_TENANT_ID", cast=str)
    LANGSMITH_AUTH_VERIFY_TENANT_ID = env(
        "LANGSMITH_AUTH_VERIFY_TENANT_ID", cast=bool, default=True
    )

else:
    LANGSMITH_AUTH_ENDPOINT = env(
        "LANGSMITH_AUTH_ENDPOINT",
        cast=str,
        default=getenv(
            "LANGCHAIN_ENDPOINT",
            getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
        ),
    )

# Webhooks


WEBHOOKS_CONFIG = env(
    "LANGGRAPH_WEBHOOKS",
    cast=cast(
        "Callable[[str | None], WebhooksConfig | None]",
        _parse.parse_schema(
            Annotated[WebhooksConfig, AfterValidator(webhooks_validator)]
        ),
    ),
    default=None,
)

# license

LANGGRAPH_CLOUD_LICENSE_KEY = env("LANGGRAPH_CLOUD_LICENSE_KEY", cast=str, default="")
LANGSMITH_API_KEY = env(
    "LANGSMITH_API_KEY", cast=str, default=getenv("LANGCHAIN_API_KEY", "")
)
# LANGSMITH_CONTROL_PLANE_API_KEY is used for license verification and
# submitting usage metadata to LangSmith SaaS.
#
# Use case: A self-hosted deployment can configure LANGSMITH_API_KEY
# from a self-hosted LangSmith instance (i.e. trace to self-hosted
# LangSmith) and configure LANGSMITH_CONTROL_PLANE_API_KEY from LangSmith SaaS
# to facilitate license key verification and metadata submission.
LANGSMITH_CONTROL_PLANE_API_KEY = env(
    "LANGSMITH_CONTROL_PLANE_API_KEY", cast=str, default=LANGSMITH_API_KEY
)

# if langsmith api key is set, enable tracing unless explicitly disabled

if (
    LANGSMITH_CONTROL_PLANE_API_KEY
    and not getenv("LANGCHAIN_TRACING_V2")
    and not getenv("LANGCHAIN_TRACING")
    and not getenv("LANGSMITH_TRACING_V2")
    and not getenv("LANGSMITH_TRACING")
):
    environ["LANGCHAIN_TRACING_V2"] = "true"

TRACING = (
    env("LANGCHAIN_TRACING_V2", cast=bool, default=None)
    or env("LANGCHAIN_TRACING", cast=bool, default=None)
    or env("LANGSMITH_TRACING_V2", cast=bool, default=None)
    or env("LANGSMITH_TRACING", cast=bool, default=None)
)

# OpenTelemetry
# Centralized enablement flag so app code does not read raw env vars.
# If OTEL_ENABLED is unset, auto-enable when a standard OTLP endpoint var is present.
OTEL_ENABLED = env("OTEL_ENABLED", cast=bool, default=None)
if OTEL_ENABLED is None:
    OTEL_ENABLED = bool(
        getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        or getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    )

# if variant is "licensed", update to "local" if using LANGSMITH_CONTROL_PLANE_API_KEY instead

if (
    getenv("LANGSMITH_LANGGRAPH_API_VARIANT") == "licensed"
    and LANGSMITH_CONTROL_PLANE_API_KEY
):
    environ["LANGSMITH_LANGGRAPH_API_VARIANT"] = "local"


# Metrics.
USES_INDEXING = (
    STORE_CONFIG
    and STORE_CONFIG.get("index")
    and STORE_CONFIG.get("index").get("embed")
)
USES_CUSTOM_APP = HTTP_CONFIG and HTTP_CONFIG.get("app")
USES_CUSTOM_AUTH = bool(LANGGRAPH_AUTH)
USES_THREAD_TTL = bool(THREAD_TTL)
USES_STORE_TTL = bool(STORE_CONFIG and STORE_CONFIG.get("ttl"))

API_VARIANT = env("LANGSMITH_LANGGRAPH_API_VARIANT", cast=str, default="")

# UI
UI_USE_BUNDLER = env("LANGGRAPH_UI_BUNDLER", cast=bool, default=False)

LANGGRAPH_METRICS_ENABLED = env("LANGGRAPH_METRICS_ENABLED", cast=bool, default=False)
LANGGRAPH_METRICS_ENDPOINT = env("LANGGRAPH_METRICS_ENDPOINT", cast=str, default=None)
LANGGRAPH_METRICS_EXPORT_INTERVAL_MS = env(
    "LANGGRAPH_METRICS_EXPORT_INTERVAL_MS", cast=int, default=60000
)
LANGGRAPH_LOGS_ENDPOINT = env("LANGGRAPH_LOGS_ENDPOINT", cast=str, default=None)
LANGGRAPH_LOGS_ENABLED = env("LANGGRAPH_LOGS_ENABLED", cast=bool, default=False)

FF_PYSPY_PROFILING_ENABLED = env("FF_PYSPY_PROFILING_ENABLED", cast=bool, default=False)
if FF_PYSPY_PROFILING_ENABLED:
    import shutil

    pyspy = shutil.which("py-spy")
    if not pyspy:
        raise ValueError(
            "py-spy not found on PATH. Please re-deploy with py-spy installed."
        )
FF_PYSPY_PROFILING_MAX_DURATION_SECS = env(
    "FF_PYSPY_PROFILING_MAX_DURATION_SECS", cast=int, default=240
)
FF_PROFILE_IMPORTS = env("FF_PROFILE_IMPORTS", cast=bool, default=False)

SELF_HOSTED_OBSERVABILITY_SERVICE_NAME = "LGP_Self_Hosted"

IS_QUEUE_ENTRYPOINT = False
IS_EXECUTOR_ENTRYPOINT = False
ref_sha = None
if not os.getenv("LANGCHAIN_REVISION_ID") and (
    ref_sha := os.getenv("LANGSMITH_LANGGRAPH_GIT_REF_SHA")
):
    # This is respected by the langsmith SDK env inference
    # https://github.com/langchain-ai/langsmith-sdk/blob/1b93e4c13b8369d92db891ae3babc3e2254f0e56/python/langsmith/env/_runtime_env.py#L190
    os.environ["LANGCHAIN_REVISION_ID"] = ref_sha

traceblock.patch_requests()

__all__ = [
    "ALLOW_PRIVATE_NETWORK",
    "API_VARIANT",
    "BG_JOB_HEARTBEAT",
    "BG_JOB_INTERVAL",
    "BG_JOB_ISOLATED_LOOPS",
    "BG_JOB_MAX_RETRIES",
    "BG_JOB_SHUTDOWN_GRACE_PERIOD_SECS",
    "BG_JOB_TIMEOUT_SECS",
    "CHECKPOINTER_CONFIG",
    "CORS_ALLOW_ORIGINS",
    "CORS_CONFIG",
    "DATABASE_URI",
    "FF_CRONS_ENABLED",
    "FF_LOG_DROPPED_EVENTS",
    "FF_LOG_QUERY_AND_PARAMS",
    "FF_PYSPY_PROFILING_ENABLED",
    "FF_PYSPY_PROFILING_MAX_DURATION_SECS",
    "GRPC_CLIENT_MAX_RECV_MSG_BYTES",
    "GRPC_CLIENT_MAX_SEND_MSG_BYTES",
    "GRPC_CLIENT_POOL_SIZE",
    "GRPC_SERVER_MAX_RECV_MSG_BYTES",
    "GRPC_SERVER_MAX_SEND_MSG_BYTES",
    "HTTP_CONFIG",
    "IS_EXECUTOR_ENTRYPOINT",
    "IS_QUEUE_ENTRYPOINT",
    "JSON_THREAD_POOL_MINIMUM_SIZE_BYTES",
    "LANGGRAPH_AES_KEY",
    "LANGGRAPH_AUTH",
    "LANGGRAPH_AUTH_TYPE",
    "LANGGRAPH_CLOUD_LICENSE_KEY",
    "LANGGRAPH_LOGS_ENABLED",
    "LANGGRAPH_LOGS_ENDPOINT",
    "LANGGRAPH_METRICS_ENABLED",
    "LANGGRAPH_METRICS_ENDPOINT",
    "LANGGRAPH_METRICS_EXPORT_INTERVAL_MS",
    "LANGGRAPH_POSTGRES_EXTENSIONS",
    "LANGSMITH_API_KEY",
    "LANGSMITH_AUTH_ENDPOINT",
    "LANGSMITH_AUTH_VERIFY_TENANT_ID",
    "LANGSMITH_CONTROL_PLANE_API_KEY",
    "LANGSMITH_TENANT_ID",
    "MAX_STREAM_CHUNK_SIZE_BYTES",
    "MIGRATIONS_PATH",
    "MOUNT_PREFIX",
    "N_JOBS_PER_WORKER",
    "OTEL_ENABLED",
    "POSTGRES_POOL_MAX_SIZE",
    "REDIS_CLUSTER",
    "REDIS_CONNECT_TIMEOUT",
    "REDIS_HEALTH_CHECK_INTERVAL",
    "REDIS_KEY_PREFIX",
    "REDIS_MAX_CONNECTIONS",
    "REDIS_URI",
    "RESUMABLE_STREAM_TTL_SECONDS",
    "RUN_STATS_CACHE_SECONDS",
    "SELF_HOSTED_OBSERVABILITY_SERVICE_NAME",
    "SERDE",
    "STATS_INTERVAL_SECS",
    "STORE_CONFIG",
    "THREAD_TTL",
    "TRACING",
    "UI_USE_BUNDLER",
    "USES_CUSTOM_APP",
    "USES_CUSTOM_AUTH",
    "USES_INDEXING",
    "USES_STORE_TTL",
    "USES_THREAD_TTL",
    "AuthConfig",
    "CheckpointerConfig",
    "CorsConfig",
    "HttpConfig",
    "SerdeConfig",
    "StoreConfig",
    "TTLConfig",
    "ThreadTTLConfig",
    "WebhooksConfig",
]
