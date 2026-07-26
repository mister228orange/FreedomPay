"""Shared helpers for watch-only chain gateways."""

from __future__ import annotations

import logging
from decimal import Decimal

import httpx

from app.config import settings
from app.gateways.abc import AbstractChainGateway, GatewayInfo, PaymentHit
from app.pricing import is_dust

logger = logging.getLogger(__name__)

_TOLERANCE = Decimal("0.01")


def amount_matches(currency: str, expected: Decimal, actual: Decimal) -> bool:
    if expected <= 0 or actual <= 0:
        return False
    # Junk / spam below ~$0.10 USDT is never a payment hit
    if is_dust(currency, actual):
        logger.debug("Skip dust %s %s", actual, currency)
        return False
    delta = abs(actual - expected)
    return delta <= expected * _TOLERANCE or delta <= Decimal("0.00000001")


async def json_rpc(
    client: httpx.AsyncClient, url: str, method: str, params: list
):
    r = await client.post(
        url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    )
    if r.status_code >= 400:
        return None
    return (r.json() or {}).get("result")


async def evm_find_native(
    *, rpc: str, address: str, amount: Decimal, currency: str
) -> PaymentHit | None:
    addr = address.lower()
    async with httpx.AsyncClient(timeout=25.0) as client:
        head = await json_rpc(client, rpc, "eth_blockNumber", [])
        if head is None:
            return None
        latest = int(head, 16)
        start = max(0, latest - 40)
        for n in range(latest, start - 1, -1):
            block = await json_rpc(
                client, rpc, "eth_getBlockByNumber", [hex(n), True]
            )
            if not block:
                continue
            for tx in block.get("transactions") or []:
                if not isinstance(tx, dict):
                    continue
                if (tx.get("to") or "").lower() != addr:
                    continue
                value = Decimal(int(tx.get("value") or "0x0", 16)) / Decimal(10**18)
                if value > 0 and amount_matches(currency, amount, value):
                    return PaymentHit(
                        txid=tx.get("hash") or "",
                        amount=value,
                        confirmations=latest - n + 1,
                    )
    return None


class BaseChainGateway(AbstractChainGateway):
    """Common watch-only gateway wiring (wallet + TTL + GatewayInfo)."""

    chain: str
    currency: str
    name: str
    decimals: int
    min_confirmations: int
    supports_memo: bool = False

    def wallet(self) -> str:
        raise NotImplementedError

    def is_configured(self) -> bool:
        return bool(self.wallet().strip())

    def receive_address(self) -> str:
        return self.wallet().strip()

    def payment_ttl_seconds(self) -> int:
        return settings.invoice_ttl_for(self.chain)

    def poll_interval_seconds(self) -> int:
        return settings.poll_interval_for(self.chain)

    def gateway_info(self) -> GatewayInfo:
        return GatewayInfo(
            chain=self.chain,
            currency=self.currency,
            name=self.name,
            decimals=self.decimals,
            min_confirmations=self.min_confirmations,
            address_configured=self.is_configured(),
            network=settings.NETWORK,
            supports_memo=self.supports_memo,
            payment_ttl_seconds=self.payment_ttl_seconds(),
            poll_interval_seconds=self.poll_interval_seconds(),
            exits=["web", "tg", "embed"],
        )
