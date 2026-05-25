"""Orchestrates the alert processing pipeline."""

import logging

from alert_ai.analyzer import analyze
from alert_ai.gcp_logs import fetch_logs

logger = logging.getLogger(__name__)


def process_alert(context: dict) -> str:
    """Main pipeline: fetch logs → analyze → return formatted guidance.

    Args:
        context: Alert context extracted from Slack message.

    Returns:
        Formatted triage guidance string.
    """
    logger.info(
        "Processing alert: service=%s error=%s",
        context.get("service", "unknown"),
        context.get("error_type", "unknown"),
    )

    # 1. Fetch related logs from GCP
    log_entries = fetch_logs(context)

    # 2. Analyze with AI
    guidance = analyze(context, log_entries)

    # 3. Format response
    header = ":robot_face: *Alert AI Triage*\n"
    return header + guidance
