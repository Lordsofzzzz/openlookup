"""Privacy-safe diagnostic events and request correlation."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from uuid import uuid4

import httpx

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger("openlookup.diagnostics")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname.lower(),
                "event": record.msg,
                **record.fields,
            }
        )


def configure_logging():
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def event(name, *, level=logging.INFO, **fields):
    logger.log(
        level, name, extra={"fields": {"request_id": request_id.get(), **fields}}
    )


def failure(exc):
    # Use controlled descriptions: arbitrary exception text can contain queries,
    # credentials or response bodies even after simple string redaction.
    details = {"error_type": type(exc).__name__}
    if isinstance(exc, httpx.HTTPStatusError):
        details.update(
            error_message="Provider returned an HTTP error",
            http_status=exc.response.status_code,
        )
    elif isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        details["error_message"] = "Provider request timed out"
    elif isinstance(exc, httpx.ConnectError):
        details["error_message"] = (
            "TLS certificate verification failed"
            if "CERTIFICATE_VERIFY_FAILED" in str(exc).upper()
            else "Provider connection failed"
        )
    else:
        details["error_message"] = "Provider lookup failed"
    return details


class RequestContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        identifier = uuid4().hex
        token = request_id.set(identifier)

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                message = dict(message)
                message["headers"] = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"x-request-id"
                ] + [(b"x-request-id", identifier.encode("ascii"))]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            request_id.reset(token)
