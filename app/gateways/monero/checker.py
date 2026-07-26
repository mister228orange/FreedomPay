from __future__ import annotations

from decimal import Decimal

from app.config import settings
from app.gateways.abc import PaymentHit
from app.gateways.common import BaseChainGateway


class MoneroGateway(BaseChainGateway):
    chain = "monero"
    currency = "XMR"
    name = "Monero"
    decimals = 12
    min_confirmations = 10
    supports_memo = True

    def wallet(self) -> str:
        return settings.WALLET_XMR

    async def find_payment(
        self,
        *,
        address: str,
        amount: Decimal,
        since_unix: int,
        memo: str | None,
    ) -> PaymentHit | None:
        _ = (address, amount, since_unix, memo)
        return None
