"""Scheduled payment-detection tasks (Taskiq)."""

from __future__ import annotations

import logging

from sqlmodel import Session

from app.broker import broker
from app.config import settings
from app.db import engine
from app.services.invoices import poll_pending

logger = logging.getLogger(__name__)

_CHAINS = (
    "bitcoin",
    "ton",
    "ton-usdt",
    "solana",
    "solana-usdc",
    "ethereum",
    "polygon",
    "tron",
    "monero",
)


def _poll_schedules() -> list[dict]:
    """One interval schedule per chain (seconds from settings)."""
    return [
        {
            "schedule_id": f"poll:{chain}",
            "interval": settings.poll_interval_for(chain),
            "args": [chain],
        }
        for chain in _CHAINS
    ]


@broker.task(task_name="freedompay.poll_chain", schedule=_poll_schedules())
async def poll_chain_invoices(chain: str) -> int:
    """Poll open invoices for a single chain (kicked by TaskiqScheduler)."""
    try:
        with Session(engine) as session:
            n = await poll_pending(session, chain=chain)
            if n:
                logger.info("Polled %s open %s invoice(s)", n, chain)
            return n
    except Exception:  # noqa: BLE001
        logger.exception("Poll failed for chain=%s", chain)
        return 0
