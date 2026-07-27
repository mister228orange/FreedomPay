from __future__ import annotations

from decimal import Decimal

import httpx

from app.config import settings
from app.gateways.abc import PaymentHit
from app.gateways.common import BaseChainGateway, amount_matches, json_rpc


class SolanaGateway(BaseChainGateway):
    chain = "solana"
    currency = "SOL"
    name = "SOL"
    decimals = 9
    min_confirmations = 1
    supports_memo = True
    blockchain = "solana"

    def wallet(self) -> str:
        return settings.WALLET_SOL

    async def find_payment(
        self,
        *,
        address: str,
        amount: Decimal,
        since_unix: int,
        memo: str | None,
    ) -> PaymentHit | None:
        _ = since_unix
        rpc = settings.rpc_solana()
        async with httpx.AsyncClient(timeout=12.0) as client:
            sigs = await json_rpc(
                client, rpc, "getSignaturesForAddress", [address, {"limit": 15}]
            )
            if not sigs:
                return None
            for item in sigs[:15]:
                sig = item.get("signature")
                if not sig:
                    continue
                tx = await json_rpc(
                    client,
                    rpc,
                    "getTransaction",
                    [
                        sig,
                        {
                            "encoding": "json",
                            "maxSupportedTransactionVersion": 0,
                            "commitment": "confirmed",
                        },
                    ],
                )
                if not tx:
                    continue
                meta = tx.get("meta") or {}
                if meta.get("err"):
                    continue
                pre = meta.get("preBalances") or []
                post = meta.get("postBalances") or []
                keys = (
                    ((tx.get("transaction") or {}).get("message") or {}).get(
                        "accountKeys"
                    )
                    or []
                )
                for i, key in enumerate(keys):
                    k = key if isinstance(key, str) else (key or {}).get("pubkey")
                    if k != address or i >= len(pre) or i >= len(post):
                        continue
                    delta = Decimal(post[i] - pre[i]) / Decimal(10**9)
                    if delta > 0 and amount_matches(self.currency, amount, delta):
                        return PaymentHit(
                            txid=sig,
                            amount=delta,
                            confirmations=1,
                            memo=memo,
                        )
        return None
