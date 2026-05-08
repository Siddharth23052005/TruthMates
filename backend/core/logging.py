from __future__ import annotations

import json
import logging
from time import perf_counter


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, event: str, **fields) -> None:
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, ensure_ascii=True, default=str))


def stage_start() -> float:
    return perf_counter()


def stage_duration_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)
