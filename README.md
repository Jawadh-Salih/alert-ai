# Alert AI

Slack alert interceptor that analyzes GCP logs with AI to provide triage guidance.

When an error alert lands in a Slack channel, Alert AI:

1. **Intercepts** the message via Slack Socket Mode
2. **Queries** GCP Cloud Logging for related error logs
3. **Analyzes** the logs with Claude to identify root cause
4. **Responds** in-thread with actionable triage guidance

## Setup

### Prerequisites

- Python 3.11+
- A Slack app with Socket Mode enabled and `channels:history`, `chat:write` scopes
- GCP project with Cloud Logging API enabled
- Anthropic API key

### Install

```bash
pip install -e .
```

### Configure

```bash
cp .env.example .env
# Fill in your tokens and project ID
```

**Slack App Setup:**
1. Create a Slack app at https://api.slack.com/apps
2. Enable Socket Mode (generates `SLACK_APP_TOKEN` starting with `xapp-`)
3. Add Bot Token Scopes: `channels:history`, `chat:write`, `channels:read`
4. Subscribe to `message.channels` event
5. Install to workspace (generates `SLACK_BOT_TOKEN` starting with `xoxb-`)
6. Invite the bot to your alert channel(s)

**GCP Setup:**
- Uses Application Default Credentials by default (`gcloud auth application-default login`)
- Or set `GOOGLE_APPLICATION_CREDENTIALS` to a service account key path
- Needs `roles/logging.viewer` on the project

### Run

```bash
python -m alert_ai
```

## Architecture

```
Slack Channel
    │
    ▼
slack_listener.py  ──▶  extract_error_context()
    │
    ▼
orchestrator.py
    │
    ├──▶  gcp_logs.py   ──▶  Cloud Logging API
    │
    └──▶  analyzer.py   ──▶  Claude API
    │
    ▼
Slack Thread Reply (triage guidance)
```
