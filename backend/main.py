import os
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

os.environ["USE_TF"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TRANSFORMERS_NO_TF"] = "1"

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.extension import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

from api.deps import limiter
from api.routes.health import router as health_router
from api.routes.media import router as media_router
from api.routes.monitor import router as monitor_router
from api.routes.pipeline import router as pipeline_router
from api.routes.social import router as social_router
from core.config import get_settings
from core.logging import configure_logging, get_logger, log_event
from db.mongo import ping_db

configure_logging()
logger = get_logger("truthmates.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await ping_db()
        log_event(logger, "startup_complete", database="reachable")
    except Exception as exc:
        log_event(
            logger,
            "startup_warning",
            level="warning",
            database="unreachable",
            error=str(exc),
        )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="TruthMates API",
        version="1.0.0",
        description="AI pipeline for civic misinformation analysis",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        started_at = perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            log_event(
                logger,
                "request_failed",
                level="error",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        log_event(
            logger,
            "request_complete",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    app.include_router(health_router)
    app.include_router(monitor_router)
    app.include_router(pipeline_router)
    app.include_router(media_router)
    app.include_router(social_router)
    return app


app = create_app()
