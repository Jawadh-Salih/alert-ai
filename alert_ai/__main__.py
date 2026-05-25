"""Entry point: python -m alert_ai"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

from alert_ai.slack_listener import start  # noqa: E402

start()
