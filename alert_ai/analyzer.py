"""AI-powered log analysis using Claude."""

import json
import logging

import anthropic

from alert_ai.config import settings

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None

SYSTEM_PROMPT = """\
You are an expert SRE / DevOps engineer performing initial triage on a production alert.

You will receive:
1. The original alert message from Slack
2. Related log entries from GCP Cloud Logging

Your job is to:
- Summarize what is happening (the error, affected service, scope of impact)
- Identify the most likely root cause based on the logs
- Provide concrete triage steps (what to check, what to restart, what to rollback)
- Flag if this looks like it needs immediate human escalation vs. can wait
- Note any patterns (is this recurring? correlated with a deploy?)

Keep your response concise and actionable. Use bullet points.
Format for Slack (use *bold*, `code`, and bullet points).
Do NOT speculate beyond what the logs show — say "insufficient data" if unsure.
"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def analyze(alert_context: dict, log_entries: list[dict]) -> str:
    """Analyze alert + logs with Claude and return triage guidance.

    Args:
        alert_context: Extracted context from the Slack alert message.
        log_entries: Simplified GCP log entries.

    Returns:
        Formatted triage guidance string for posting to Slack.
    """
    client = _get_client()

    # Build the user message
    user_parts = []

    user_parts.append("## Original Alert")
    user_parts.append(alert_context.get("raw_text", "(no text)"))

    if alert_context.get("service"):
        user_parts.append(f"\n**Detected service:** {alert_context['service']}")
    if alert_context.get("error_type"):
        user_parts.append(f"**Detected error type:** {alert_context['error_type']}")

    user_parts.append(f"\n## GCP Log Entries ({len(log_entries)} found)")
    if log_entries:
        # Truncate to avoid token limits — keep the most recent and relevant
        for entry in log_entries[:30]:
            user_parts.append(json.dumps(entry, default=str, indent=2))
    else:
        user_parts.append(
            "No matching log entries found in the last "
            f"{settings.log_lookback_minutes} minutes."
        )

    user_message = "\n\n".join(user_parts)

    logger.info("Sending %d chars to Claude for analysis", len(user_message))

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text
