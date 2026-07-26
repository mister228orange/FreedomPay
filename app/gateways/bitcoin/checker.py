from __future__ import annotations

import logging
from decimal import Decimal

import httpx

from app.config import settings
from app.gateways.abc import PaymentHit
from app.gateways.common import BaseChainGateway, amount_matches

logger = logging.getLogger(__name__)


class BitcoinGateway(BaseChainGateway):
    chain = "bitcoin"
    currency = "BTC"
    name = "Bitcoin"
    decimals = 8
    min_confirmations = 1

    def wallet(self) -> str:
        return settings.WALLET_BTC

    async def find_payment(
        self,
        *,
        address: str,
        amount: Decimal,
        since_unix: int,
        memo: str | None,
    ) -> PaymentHit | None:
        _ = (since_unix, memo)
        url = f"{settings.rpc_btc().rstrip('/')}/address/{address}/txs"
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(url)
            if r.status_code >= 400:
                logger.warning("BTC check failed: %s %s", r.status_code, r.text[:200])
                return None
            txs = r.json()
        for tx in txs:
            status = tx.get("status") or {}
            conf = 1 if status.get("confirmed") else 0
            paid = Decimal("0")
            for vout in tx.get("vout") or []:
                if vout.get("scriptpubkey_address") == address:
                    paid += Decimal(vout.get("value") or 0) / Decimal(10**8)
            if paid > 0 and amount_matches(self.currency, amount, paid):
                return PaymentHit(
                    txid=tx.get("txid") or "",
                    amount=paid,
                    confirmations=conf,
                )
        return None
