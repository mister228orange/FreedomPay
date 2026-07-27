from __future__ import annotations

from decimal import Decimal

import httpx

from app.config import settings
from app.gateways.abc import PaymentHit
from app.gateways.common import BaseChainGateway, amount_matches


class TronGateway(BaseChainGateway):
    chain = "tron"
    blockchain = "tron"
    currency = "TRX"
    name = "Tron"
    decimals = 6
    min_confirmations = 1

    def wallet(self) -> str:
        return settings.WALLET_TRX

    async def find_payment(
        self,
        *,
        address: str,
        amount: Decimal,
        since_unix: int,
        memo: str | None,
    ) -> PaymentHit | None:
        _ = (since_unix, memo, address)
        url = (
            f"{settings.rpc_tron().rstrip('/')}/v1/accounts/"
            f"{self.receive_address()}/transactions"
        )
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(url, params={"limit": 30, "only_to": "true"})
            if r.status_code >= 400:
                return None
            payload = r.json()
        for tx in payload.get("data") or []:
            raw = tx.get("raw_data") or {}
            for c in raw.get("contract") or []:
                param = (c.get("parameter") or {}).get("value") or {}
                value = Decimal(param.get("amount") or 0) / Decimal(10**6)
                if value > 0 and amount_matches(self.currency, amount, value):
                    return PaymentHit(
                        txid=tx.get("txID") or "",
                        amount=value,
                        confirmations=1,
                    )
        return None
