"""Taskiq broker + scheduler for non-blocking invoice polling."""

from __future__ import annotations

from taskiq import AsyncBroker, InMemoryBroker, TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from app.config import settings


def _build_broker() -> AsyncBroker:
    """Redis broker in Compose; in-memory for local/dev/tests."""
    if settings.REDIS_URL:
        from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

        return ListQueueBroker(url=settings.REDIS_URL).with_result_backend(
            RedisAsyncResultBackend(redis_url=settings.REDIS_URL)
        )
    return InMemoryBroker()


broker = _build_broker()

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)

# Register scheduled tasks on import (worker + scheduler need this).
import app.tasks.polling  # noqa: E402, F401
