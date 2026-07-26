from __future__ import annotations

from decimal import Decimal

from app.config import settings
from app.gateways.abc import PaymentHit
from app.gateways.common import BaseChainGateway, evm_find_native


class EthereumGateway(BaseChainGateway):
    chain = "ethereum"
    currency = "ETH"
    name = "Ethereum"
    decimals = 18
    min_confirmations = 3

    def wallet(self) -> str:
        return settings.WALLET_ETH

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
            rpc=settings.rpc_eth(),
            address=address,
            amount=amount,
            currency=self.currency,
        )
