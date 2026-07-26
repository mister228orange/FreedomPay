from __future__ import annotations

import logging
from decimal import Decimal

import httpx

from app.config import settings
from app.gateways.abc import PaymentHit
from app.gateways.common import BaseChainGateway, amount_matches

logger = logging.getLogger(__name__)


class TonGateway(BaseChainGateway):
    chain = "ton"
    currency = "TON"
    name = "TON"
    decimals = 9
    min_confirmations = 1
    supports_memo = True

    def wallet(self) -> str:
        return settings.WALLET_TON

    async def find_payment(
        self,
        *,
        address: str,
        amount: Decimal,
        since_unix: int,
        memo: str | None,
    ) -> PaymentHit | None:
        _ = since_unix
        url = f"{settings.rpc_ton().rstrip('/')}/getTransactions"
        headers = {}
        if settings.TON_API_KEY:
            headers["X-API-Key"] = settings.TON_API_KEY
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(
                url, params={"address": address, "limit": 30}, headers=headers
            )
            if r.status_code >= 400:
                logger.warning("TON check failed: %s %s", r.status_code, r.text[:200])
                return None
            body = r.json() or {}
            result = body.get("result") or []
        for tx in result:
            in_msg = tx.get("in_msg") or {}
            value_nano = Decimal(in_msg.get("value") or 0)
            value = value_nano / Decimal(10**9)
            comment = in_msg.get("message")
            if comment is None:
                msg_data = in_msg.get("msg_data") or {}
                comment = msg_data.get("text")
            if memo and comment and str(memo) not in str(comment):
                continue
            if memo and not comment:
                continue
            if value > 0 and amount_matches(self.currency, amount, value):
                txid = ""
                tid = tx.get("transaction_id") or {}
                if isinstance(tid, dict):
                    txid = tid.get("hash") or ""
                txid = txid or tx.get("hash") or ""
                return PaymentHit(
                    txid=str(txid),
                    amount=value,
                    confirmations=1,
                    memo=str(comment) if comment else None,
                )
        return None
