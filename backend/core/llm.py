from __future__ import annotations

import os

from core.config import get_settings

def build_crewai_llm(provider: str = "cerebras", *, temperature: float = 0.0):
    from crewai import LLM

    if provider == "together":
        return LLM(
            model="together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo",
            api_key=os.environ["TOGETHER_API_KEY"],
            base_url="https://api.together.xyz/v1",
            temperature=temperature,
        )
    if provider == "cerebras":
        return LLM(
            model="llama3.1-8b",
            api_key=os.environ["CEREBRAS_API_KEY"],
            base_url="https://api.cerebras.ai/v1",
            temperature=temperature,
        )
    raise ValueError(f"Unsupported LLM provider: {provider}")


def media_llm_provider_order() -> tuple[str, str]:
    return ("cerebras", "together")


def get_vision_client_config() -> dict[str, str] | None:
    settings = get_settings()
    provider = settings.vision_provider
    model = settings.vision_model

    if not provider or not model:
        return None

    if provider == "together":
        api_key = os.environ.get("TOGETHER_API_KEY", "").strip()
        if not api_key:
            return None
        return {
            "provider": "together",
            "model": model,
            "api_key": api_key,
            "base_url": "https://api.together.xyz/v1",
        }

    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None
        return {
            "provider": "openai",
            "model": model,
            "api_key": api_key,
            "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").strip(),
        }

    return None
