from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    allowed_origins: list[str]
    admin_api_key: str
    public_api_key: str
    admin_rate_limit: str
    public_rate_limit: str
    vision_provider: str
    vision_model: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_number: str
    twilio_admin_number: str


def _parse_origins(value: str) -> list[str]:
    origins = [item.strip() for item in (value or "").split(",") if item.strip()]
    return origins or ["http://localhost:5173", "http://127.0.0.1:5173"]


def get_settings() -> Settings:
    return Settings(
        allowed_origins=_parse_origins(os.environ.get("ALLOWED_ORIGINS", "")),
        admin_api_key=os.environ.get("TRUTHMATES_ADMIN_API_KEY", "").strip(),
        public_api_key=os.environ.get("TRUTHMATES_PUBLIC_API_KEY", "").strip(),
        admin_rate_limit=os.environ.get("TRUTHMATES_ADMIN_RATE_LIMIT", "30/minute"),
        public_rate_limit=os.environ.get("TRUTHMATES_PUBLIC_RATE_LIMIT", "10/minute"),
        vision_provider=os.environ.get("TRUTHMATES_VISION_PROVIDER", "").strip().lower(),
        vision_model=os.environ.get("TRUTHMATES_VISION_MODEL", "").strip(),
        twilio_account_sid=os.environ.get("TWILIO_ACCOUNT_SID", "").strip(),
        twilio_auth_token=os.environ.get("TWILIO_AUTH_TOKEN", "").strip(),
        twilio_whatsapp_number=os.environ.get("TWILIO_WHATSAPP_NUMBER", "").strip(),
        twilio_admin_number=os.environ.get("TWILIO_ADMIN_NUMBER", "").strip(),
    )
