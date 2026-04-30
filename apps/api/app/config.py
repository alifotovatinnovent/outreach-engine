"""App configuration loaded from environment variables."""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _clean_secret(v: str) -> str:
    """Strip whitespace + reject any non-ASCII chars that snuck in via copy-paste.

    Render env vars sometimes carry hidden arrow chars (→) or smart quotes when
    pasted from rich-text UIs. httpx will choke on those at header-encode time.
    """
    if not v:
        return v
    cleaned = v.strip()
    try:
        cleaned.encode("ascii")
    except UnicodeEncodeError:
        # Drop any non-ASCII char silently. Better to try with what's left
        # than to fail the entire request later.
        cleaned = cleaned.encode("ascii", "ignore").decode("ascii")
    return cleaned


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator(
        "anthropic_api_key", "apollo_api_key",
        "smartlead_api_key", "smartlead_default_campaign_id",
        "twilio_account_sid", "twilio_auth_token", "twilio_whatsapp_from",
        "hubspot_token", "pipedrive_api_token",
        mode="before",
    )
    @classmethod
    def _clean_secrets(cls, v):
        return _clean_secret(v) if isinstance(v, str) else v

    # Required
    anthropic_api_key: str = ""
    apollo_api_key: str = ""
    database_url: str = "postgresql+psycopg://outreach:outreach@db:5432/outreach"

    # Optional channels
    smartlead_api_key: str = ""
    smartlead_from_email: str = ""
    smartlead_default_campaign_id: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""
    hubspot_token: str = ""
    pipedrive_api_token: str = ""
    pipedrive_domain: str = ""

    # Sender identity (for prompt context)
    sender_name: str = "Ali Fotovat"
    sender_company: str = "INNOVENT Tech"
    sender_role: str = "CEO"
    product_pitch: str = (
        "RFID + IoT asset tracking and real-time monitoring for healthcare and "
        "enterprise operations in UAE."
    )

    app_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"


settings = Settings()


def channel_status() -> dict[str, bool]:
    """Which channels are wired up given current env vars."""
    return {
        "apollo": bool(settings.apollo_api_key),
        "claude": bool(settings.anthropic_api_key),
        "email": bool(settings.smartlead_api_key and settings.smartlead_from_email),
        "whatsapp": bool(
            settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_whatsapp_from
        ),
        "hubspot": bool(settings.hubspot_token),
        "pipedrive": bool(settings.pipedrive_api_token and settings.pipedrive_domain),
    }
