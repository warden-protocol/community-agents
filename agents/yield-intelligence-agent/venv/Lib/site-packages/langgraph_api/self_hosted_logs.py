import logging
import os
from typing import cast

import structlog
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.util.types import Attributes

from langgraph_api import config
from langgraph_api.logging import OTLPFormatter

logger = structlog.stdlib.get_logger(__name__)

_logger_provider = None
_customer_attributes = {}


# see https://github.com/open-telemetry/opentelemetry-python/issues/3649 for why we need this
class AttrFilteredLoggingHandler(LoggingHandler):
    DROP_ATTRIBUTES = ("_logger",)

    @staticmethod
    def _get_attributes(record: logging.LogRecord) -> Attributes:
        base_attributes = LoggingHandler._get_attributes(record)
        attributes = {
            k: v
            for k, v in base_attributes.items()
            if k not in AttrFilteredLoggingHandler.DROP_ATTRIBUTES
        }
        if _customer_attributes:
            attributes.update(_customer_attributes)
        return cast("Attributes", attributes)


def initialize_self_hosted_logs() -> None:
    global _logger_provider

    if not config.LANGGRAPH_LOGS_ENABLED:
        return

    if not config.LANGGRAPH_LOGS_ENDPOINT:
        raise RuntimeError(
            "LANGGRAPH_LOGS_ENABLED is true but no LANGGRAPH_LOGS_ENDPOINT is configured"
        )

    # For now, this is only enabled for fully self-hosted customers
    # We will need to update the otel collector auth model to support hybrid customers
    if not config.LANGGRAPH_CLOUD_LICENSE_KEY:
        logger.warning(
            "Self-hosted logs require a license key, and do not work with hybrid deployments yet."
        )
        return

    try:
        resource_attributes = {
            SERVICE_NAME: config.SELF_HOSTED_OBSERVABILITY_SERVICE_NAME,
        }

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

                # resolves to pod name in k8s, or container id in docker
                instance_id = os.environ.get("HOSTNAME")
                if instance_id:
                    _customer_attributes["instance_id"] = instance_id
            except ImportError:
                pass
            except Exception as e:
                logger.warning("Failed to get customer info from license", exc_info=e)

        if config.IS_QUEUE_ENTRYPOINT:
            _customer_attributes["entrypoint"] = "queue"
        elif config.IS_EXECUTOR_ENTRYPOINT:
            _customer_attributes["entrypoint"] = "executor"
        else:
            _customer_attributes["entrypoint"] = "api"

        _logger_provider = LoggerProvider(
            resource=Resource.create(resource_attributes),
        )
        _logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(
                OTLPLogExporter(
                    endpoint=config.LANGGRAPH_LOGS_ENDPOINT,
                    headers={
                        "X-Langchain-License-Key": config.LANGGRAPH_CLOUD_LICENSE_KEY,
                    },
                )
            )
        )
        handler = AttrFilteredLoggingHandler(logger_provider=_logger_provider)
        handler.setFormatter(OTLPFormatter("%(message)s", None, "%"))
        logging.getLogger().addHandler(handler)

        logger.info(
            "Self-hosted logs initialized successfully",
            endpoint=config.LANGGRAPH_LOGS_ENDPOINT,
        )
    except Exception as e:
        logger.exception("Failed to initialize self-hosted logs", exc_info=e)


def shutdown_self_hosted_logs() -> None:
    global _logger_provider

    if _logger_provider:
        try:
            logger.info("Shutting down self-hosted logs")
            _logger_provider.shutdown()
            _logger_provider = None
        except Exception as e:
            logger.exception("Failed to shutdown self-hosted logs", exc_info=e)
