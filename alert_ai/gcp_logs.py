"""Query GCP Cloud Logging for logs related to an alert."""

import logging
from datetime import datetime, timedelta, timezone

from google.cloud import logging as cloud_logging

from alert_ai.config import settings

logger = logging.getLogger(__name__)

_client: cloud_logging.Client | None = None


def _get_client() -> cloud_logging.Client:
    global _client
    if _client is None:
        _client = cloud_logging.Client(project=settings.gcp_project_id)
    return _client


def build_filter(context: dict) -> str:
    """Build a Cloud Logging filter from alert context.

    Args:
        context: Extracted alert context with optional keys:
            - service: service/resource name
            - error_type: exception/error class
            - keywords: list of search terms
    """
    now = datetime.now(timezone.utc)
    lookback = now - timedelta(minutes=settings.log_lookback_minutes)

    parts = [
        f'severity >= {settings.log_min_severity}',
        f'timestamp >= "{lookback.isoformat()}"',
    ]

    # Narrow to service if detected
    service = context.get("service")
    if service:
        # Match against common GCP resource label fields
        parts.append(
            f'(resource.labels.service_name = "{service}"'
            f' OR resource.labels.container_name = "{service}"'
            f' OR labels.service = "{service}")'
        )

    # Add error type as text search
    error_type = context.get("error_type")
    if error_type:
        parts.append(f'textPayload : "{error_type}" OR jsonPayload.message : "{error_type}"')

    return "\n".join(parts)


def fetch_logs(context: dict, max_entries: int = 50) -> list[dict]:
    """Fetch relevant log entries from GCP Cloud Logging.

    Returns a list of simplified log entry dicts.
    """
    client = _get_client()
    log_filter = build_filter(context)

    logger.info("Querying GCP logs with filter:\n%s", log_filter)

    entries = []
    for entry in client.list_entries(
        filter_=log_filter,
        order_by=cloud_logging.DESCENDING,
        max_results=max_entries,
        resource_names=[f"projects/{settings.gcp_project_id}"],
    ):
        entries.append(_simplify_entry(entry))

    logger.info("Fetched %d log entries", len(entries))
    return entries


def _simplify_entry(entry) -> dict:
    """Extract the useful fields from a log entry."""
    result = {
        "timestamp": str(entry.timestamp),
        "severity": entry.severity,
        "logger": entry.logger_name,
    }

    # Get the actual message content
    if entry.payload_type == "TextPayload":
        result["message"] = entry.payload
    elif entry.payload_type == "JsonPayload":
        payload = dict(entry.payload)
        result["message"] = payload.get("message", "")
        # Include stack trace if present
        if "stack_trace" in payload:
            result["stack_trace"] = payload["stack_trace"]
        elif "stackTrace" in payload:
            result["stack_trace"] = payload["stackTrace"]
        # Include any httpRequest info
        if "httpRequest" in payload:
            result["http_request"] = payload["httpRequest"]
    elif entry.payload_type == "ProtoPayload":
        result["message"] = str(entry.payload)

    # Resource info
    if entry.resource:
        result["resource_type"] = entry.resource.type
        result["resource_labels"] = dict(entry.resource.labels)

    return result
