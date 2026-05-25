"""Slack Bolt app that listens for alert messages and triggers analysis."""

import logging
import re

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from alert_ai.config import settings

logger = logging.getLogger(__name__)

app = App(token=settings.slack_bot_token, signing_secret=settings.slack_signing_secret)


def extract_error_context(text: str) -> dict:
    """Pull structured info from an alert message.

    Tries to extract:
      - service name (from common alert formats)
      - error/exception type
      - keywords for log searching
    """
    context: dict = {"raw_text": text}

    # Common patterns: "[SERVICE] Error: ...", "Alert: SERVICE - ..."
    service_patterns = [
        r"\[([A-Za-z0-9_-]+)\]",  # [my-service]
        r"Alert:\s*([A-Za-z0-9_-]+)",  # Alert: my-service
        r"service[=:]\s*([A-Za-z0-9_-]+)",  # service=my-service
    ]
    for pattern in service_patterns:
        match = re.search(pattern, text)
        if match:
            context["service"] = match.group(1)
            break

    # Extract error type
    error_match = re.search(
        r"((?:[A-Z][a-z]+)+(?:Error|Exception|Failure|Timeout))", text
    )
    if error_match:
        context["error_type"] = error_match.group(1)

    # Extract keywords: remove common stop words, keep meaningful tokens
    words = re.findall(r"[A-Za-z0-9_.-]{3,}", text)
    stop = {"the", "and", "for", "from", "with", "this", "that", "has", "was", "are", "alert"}
    context["keywords"] = [w for w in words if w.lower() not in stop][:15]

    return context


def _should_process(channel: str) -> bool:
    """Check if we should process messages from this channel."""
    monitored = settings.monitored_channels
    # If no channels configured, process all
    return not monitored or channel in monitored


@app.event("message")
def handle_message(event: dict, say):
    """Handle incoming messages in monitored channels."""
    # Avoid import at top level to prevent circular imports
    from alert_ai.orchestrator import process_alert

    channel = event.get("channel", "")
    text = event.get("text", "")
    subtype = event.get("subtype")

    # Skip message edits, deletions, bot messages
    if subtype is not None:
        return

    if not _should_process(channel):
        return

    if not text:
        return

    logger.info("Alert intercepted in %s: %s", channel, text[:100])

    context = extract_error_context(text)
    context["channel"] = channel
    context["ts"] = event.get("ts", "")

    # Post a thinking indicator
    thinking = say(
        text=":mag: Analyzing this alert...",
        thread_ts=event.get("ts"),
    )

    try:
        result = process_alert(context)
        say(
            text=result,
            thread_ts=event.get("ts"),
        )
    except Exception:
        logger.exception("Failed to process alert")
        say(
            text=":warning: Sorry, I couldn't analyze this alert. Check the logs for details.",
            thread_ts=event.get("ts"),
        )


def start():
    """Start the Slack app in Socket Mode."""
    handler = SocketModeHandler(app, settings.slack_app_token)
    logger.info("Alert AI is listening...")
    handler.start()
