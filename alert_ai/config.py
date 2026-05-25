from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Slack
    slack_bot_token: str
    slack_app_token: str
    slack_signing_secret: str
    alert_channel_ids: str = ""  # comma-separated

    # GCP
    gcp_project_id: str

    # Anthropic
    anthropic_api_key: str

    # Tuning
    log_lookback_minutes: int = 30
    log_min_severity: str = "ERROR"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def monitored_channels(self) -> set[str]:
        return {ch.strip() for ch in self.alert_channel_ids.split(",") if ch.strip()}


settings = Settings()  # type: ignore[call-arg]
