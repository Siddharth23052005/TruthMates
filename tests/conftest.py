from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

_local_appdata = REPO_ROOT / ".test-local-appdata"
_local_appdata.mkdir(exist_ok=True)
os.environ["LOCALAPPDATA"] = str(_local_appdata)
os.environ["APPDATA"] = str(_local_appdata)
os.environ["CREWAI_STORAGE_DIR"] = "truthmates-tests"

try:
    import slowapi  # type: ignore # noqa: F401
except ModuleNotFoundError:
    slowapi_module = types.ModuleType("slowapi")
    errors_module = types.ModuleType("slowapi.errors")
    middleware_module = types.ModuleType("slowapi.middleware")
    responses_module = types.ModuleType("slowapi.responses")
    util_module = types.ModuleType("slowapi.util")

    class RateLimitExceeded(Exception):
        pass

    class SlowAPIMiddleware:
        def __init__(self, app, **_kwargs):
            self.app = app

        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)

    class Limiter:
        def __init__(self, *args, **kwargs):
            self.key_func = kwargs.get("key_func")

        def limit(self, _value):
            def decorator(func):
                return func
            return decorator

    async def _rate_limit_exceeded_handler(_request, _exc):
        return None

    def get_remote_address(_request):
        return "testclient"

    slowapi_module.Limiter = Limiter
    errors_module.RateLimitExceeded = RateLimitExceeded
    middleware_module.SlowAPIMiddleware = SlowAPIMiddleware
    responses_module._rate_limit_exceeded_handler = _rate_limit_exceeded_handler
    util_module.get_remote_address = get_remote_address

    sys.modules["slowapi"] = slowapi_module
    sys.modules["slowapi.errors"] = errors_module
    sys.modules["slowapi.middleware"] = middleware_module
    sys.modules["slowapi.responses"] = responses_module
    sys.modules["slowapi.util"] = util_module


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("TRUTHMATES_PUBLIC_API_KEY", "public-test-key")
    monkeypatch.setenv("TRUTHMATES_ADMIN_API_KEY", "admin-test-key")
    monkeypatch.setenv("TRUTHMATES_PUBLIC_RATE_LIMIT", "1000/minute")
    monkeypatch.setenv("TRUTHMATES_ADMIN_RATE_LIMIT", "1000/minute")
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGODB_DB_NAME", "truthmates_test")


@pytest.fixture
def sample_validated_post() -> dict[str, Any]:
    return {
        "claim": "Sample claim",
        "analysis_key": "analysis-1",
        "source_ref": "manual://1",
        "verdict": "SUPPORTED",
        "trust_score": 82.0,
        "counter_english": "Trusted sources support this claim.",
        "counter_hindi": "Trusted sources support this claim.",
        "sources": ["https://example.gov.in/fact"],
        "flags": {
            "contradicts_pib_fact": False,
            "invalid_source_url": False,
            "trust_score_mismatch": False,
            "missing_hindi": False,
            "hallucinated_stats": False,
            "overly_hedged_language": False,
        },
    }


@pytest.fixture
def verified_facts_fixture() -> list[dict[str, Any]]:
    fixture_path = REPO_ROOT / "tests" / "fixtures" / "verified_facts_sample.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


@pytest_asyncio.fixture
async def app_client():
    if "services.pipeline_service" not in sys.modules:
        pipeline_service_stub = types.ModuleType("services.pipeline_service")

        async def _default_response(*args, **kwargs):
            return {"status": "stub"}

        pipeline_service_stub.health_check_payload = _default_response
        pipeline_service_stub.monitor_logs_payload = _default_response
        pipeline_service_stub.monitor_status_payload = _default_response
        pipeline_service_stub.monitor_summary_payload = _default_response
        pipeline_service_stub.analyze_claim = _default_response
        pipeline_service_stub.scrape_pipeline = _default_response
        pipeline_service_stub.classify_pipeline = _default_response
        pipeline_service_stub.verify_pipeline = _default_response
        pipeline_service_stub.generate_pipeline = _default_response
        pipeline_service_stub.validate_pipeline = _default_response
        pipeline_service_stub.analyze_video_url = _default_response
        pipeline_service_stub.analyze_audio_upload = _default_response
        sys.modules["services.pipeline_service"] = pipeline_service_stub

    from api.deps import limiter
    from api.routes.health import router as health_router
    from api.routes.media import router as media_router
    from api.routes.monitor import router as monitor_router
    from api.routes.pipeline import router as pipeline_router

    app = FastAPI()
    app.state.limiter = limiter
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request.state.request_id = "test-request-id"
        response = await call_next(request)
        response.headers["X-Request-ID"] = "test-request-id"
        return response

    app.include_router(health_router)
    app.include_router(monitor_router)
    app.include_router(pipeline_router)
    app.include_router(media_router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def public_headers() -> dict[str, str]:
    return {"X-API-Key": "public-test-key"}


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"X-API-Key": "admin-test-key"}


class FakeUpdateCollection:
    def __init__(self) -> None:
        self.operations: list[dict[str, Any]] = []

    async def update_one(self, *, filter: dict[str, Any], update: dict[str, Any], upsert: bool) -> None:
        self.operations.append({"filter": filter, "update": update, "upsert": upsert})


class FakeCursor:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self.docs = docs

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, limit: int):
        self.docs = self.docs[:limit]
        return self

    def __aiter__(self):
        self._iter = iter(self.docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class FakeReadCollection:
    def __init__(self, docs: list[dict[str, Any]], count: int | None = None) -> None:
        self.docs = docs
        self._count = len(docs) if count is None else count

    def find(self):
        return FakeCursor(self.docs)

    async def count_documents(self, _query: dict[str, Any]) -> int:
        return self._count
