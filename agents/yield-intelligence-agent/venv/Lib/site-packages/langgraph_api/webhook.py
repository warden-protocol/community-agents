import asyncio
import ipaddress
import socket
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import structlog
from starlette.exceptions import HTTPException

from langgraph_api.config import HTTP_CONFIG, WEBHOOKS_CONFIG
from langgraph_api.config.schemas import WebhookUrlPolicy
from langgraph_api.http import get_http_client, get_loopback_client, http_request

if TYPE_CHECKING:
    from langgraph_api.worker import WorkerResult

logger = structlog.stdlib.get_logger(__name__)


async def validate_webhook_url_or_raise(url: str) -> None:
    """Validate a user-provided webhook URL against configured policy.

    No-ops when WEBHOOKS_CONFIG is not set (preserves legacy behavior).
    """
    cfg = WEBHOOKS_CONFIG
    if not cfg:
        return

    policy = WebhookUrlPolicy(cfg.get("url") or {})
    allowed_domains = policy.get("allowed_domains") or []
    allowed_ports = policy.get("allowed_ports")
    max_url_length = int(policy.get("max_url_length", 4096))
    # TODO: We should flip this in the next minor release
    require_https = bool(policy.get("require_https", False))
    disable_loopback = bool(policy.get("disable_loopback", False))

    if len(url) > max_url_length:
        raise HTTPException(status_code=422, detail="Webhook URL too long")

    # Relative loopback URL (internal route)
    if url.startswith("/"):
        if disable_loopback:
            raise HTTPException(
                status_code=422, detail="Loopback webhooks are disabled"
            )
        # The other checks would fail here, so we can just return
        return

    parsed = urlparse(url)
    if require_https and parsed.scheme.lower() != "https":
        raise HTTPException(status_code=422, detail="Webhook must use https")

    # Port policy: only enforce if configured; omit default enforcement otherwise
    if allowed_ports:
        if parsed.port is not None:
            port = parsed.port
        else:
            port = 443 if parsed.scheme == "https" else 80
        if port not in allowed_ports:
            raise HTTPException(
                status_code=422, detail=f"Webhook port {port} not allowed"
            )

    host = parsed.hostname or ""
    if not host:
        raise HTTPException(
            status_code=422, detail=f"Invalid webhook hostname '{host}'"
        )

    # Domain allowlist
    if allowed_domains:
        host_allowed = False
        for pattern in allowed_domains:
            pattern = pattern.strip().lower()
            if pattern.startswith("*."):
                base = pattern[2:]
                if host.lower().endswith("." + base):
                    host_allowed = True
                    break
            else:
                if host.lower() == pattern:
                    host_allowed = True
                    break
        if not host_allowed:
            raise HTTPException(status_code=422, detail="Webhook domain not allowed")

    # Note we don't do default SSRF protections mainly because it would require a minor bump since it could break valid use cases.
    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, host, None)
    except Exception as e:
        raise HTTPException(
            status_code=422, detail="Failed to resolve webhook host"
        ) from e

    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            # Skip non-IP entries just in case
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
        ):
            raise HTTPException(
                status_code=422, detail="Webhook host resolves to a disallowed IP"
            )


async def call_webhook(result: "WorkerResult") -> None:
    if HTTP_CONFIG and HTTP_CONFIG.get("disable_webhooks"):
        logger.info(
            "Webhooks disabled, skipping webhook call", webhook=result["webhook"]
        )
        return

    checkpoint = result["checkpoint"]
    payload = {
        **result["run"],
        "status": result["status"],
        "run_started_at": result["run_started_at"],
        "run_ended_at": result["run_ended_at"],
        "webhook_sent_at": datetime.now(UTC).isoformat(),
        "values": checkpoint["values"] if checkpoint else None,
    }
    if exception := result["exception"]:
        payload["error"] = str(exception)
    webhook = result.get("webhook")
    if webhook:
        try:
            # We've already validated on ingestion, but you could technically have an issue if you re-deployed with a different environment
            await validate_webhook_url_or_raise(webhook)
            # Note: header templates should have already been evaluated against the env at load time.
            headers = WEBHOOKS_CONFIG.get("headers") if WEBHOOKS_CONFIG else None

            if webhook.startswith("/"):
                # Call into this own app
                webhook_client = get_loopback_client()
            else:
                webhook_client = get_http_client()
            await http_request(
                "POST",
                webhook,
                json=payload,
                headers=headers,
                client=webhook_client,
            )
            await logger.ainfo(
                "Background worker called webhook",
                webhook=result["webhook"],
                run_id=str(result["run"]["run_id"]),
            )
        except Exception as exc:
            logger.exception(
                f"Background worker failed to call webhook {result['webhook']}",
                exc_info=exc,
                webhook=result["webhook"],
            )
