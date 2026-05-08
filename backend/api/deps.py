from __future__ import annotations

from fastapi import Header, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import get_settings


limiter = Limiter(key_func=get_remote_address)


def require_admin_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.admin_api_key:
        return
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin API key.")


def require_public_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.public_api_key:
        return
    if x_api_key != settings.public_api_key:
        raise HTTPException(status_code=401, detail="Invalid public API key.")
