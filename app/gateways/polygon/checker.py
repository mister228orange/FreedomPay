from __future__ import annotations

from decimal import Decimal

from app.config import settings
from app.gateways.abc import PaymentHit
from app.gateways.common import BaseChainGateway, evm_find_native


class PolygonGateway(BaseChainGateway):
    chain = "polygon"
    blockchain = "polygon"
    currency = "POL"
    name = "Polygon"
    decimals = 18
    min_confirmations = 8

    def wallet(self) -> str:
        return (settings.WALLET_POLYGON or settings.WALLET_ETH).strip()

    async def find_payment(
        self,
        *,
        address: str,
        amount: Decimal,
        since_unix: int,
        memo: str | None,
    ) -> PaymentHit | None:
        _ = (since_unix, memo)
        return await evm_find_native(
            rpc=settings.rpc_polygon(),
            address=address,
            amount=amount,
            currency=self.currency,
        )
