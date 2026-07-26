"""Taskiq broker + scheduler for non-blocking invoice polling."""

from __future__ import annotations

from taskiq import InMemoryBroker, TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

# In-process broker: scheduler kiq() runs poll tasks as asyncio tasks (non-blocking).
broker = InMemoryBroker()

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
