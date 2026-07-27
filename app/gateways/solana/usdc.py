from __future__ import annotations

from decimal import Decimal

import httpx

from app.config import settings
from app.gateways.abc import PaymentHit
from app.gateways.common import BaseChainGateway, amount_matches, json_rpc


class SolanaUsdcGateway(BaseChainGateway):
    """USDC (SPL) on Solana — amount + optional memo identity."""

    chain = "solana-usdc"
    currency = "USDC"
    name = "USDC"
    decimals = 6
    min_confirmations = 1
    supports_memo = True
    blockchain = "solana"
    is_token = True

    def __init__(self) -> None:
        self.token_contract = settings.sol_usdc_mint()

    def wallet(self) -> str:
        return (settings.WALLET_SOL_USDC or settings.WALLET_SOL).strip()

    async def find_payment(
        self,
        *,
        address: str,
        amount: Decimal,
        since_unix: int,
        memo: str | None,
    ) -> PaymentHit | None:
        _ = since_unix
        mint = settings.sol_usdc_mint()
        rpc = settings.rpc_solana()
        async with httpx.AsyncClient(timeout=15.0) as client:
            sigs = await json_rpc(
                client, rpc, "getSignaturesForAddress", [address, {"limit": 20}]
            )
            if not sigs:
                return None
            for item in sigs[:20]:
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
                            "encoding": "jsonParsed",
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
                paid = _spl_delta_to(meta, address=address, mint=mint, decimals=self.decimals)
                if paid is None or paid <= 0:
                    continue
                if not amount_matches(self.currency, amount, paid):
                    continue
                if memo:
                    found_memo = _extract_memo(tx)
                    if not found_memo or str(memo) not in str(found_memo):
                        continue
                return PaymentHit(
                    txid=sig,
                    amount=paid,
                    confirmations=1,
                    memo=memo,
                )
        return None


def _spl_delta_to(
    meta: dict, *, address: str, mint: str, decimals: int
) -> Decimal | None:
    pre = meta.get("preTokenBalances") or []
    post = meta.get("postTokenBalances") or []
    pre_map = {
        (b.get("owner"), (b.get("mint") or "")): Decimal(
            str(((b.get("uiTokenAmount") or {}).get("amount")) or 0)
        )
        for b in pre
    }
    total = Decimal("0")
    for b in post:
        owner = b.get("owner")
        m = b.get("mint") or ""
        if owner != address or m != mint:
            continue
        post_amt = Decimal(
            str(((b.get("uiTokenAmount") or {}).get("amount")) or 0)
        )
        pre_amt = pre_map.get((owner, m), Decimal("0"))
        delta = (post_amt - pre_amt) / Decimal(10**decimals)
        if delta > 0:
            total += delta
    return total if total > 0 else None


def _extract_memo(tx: dict) -> str | None:
    message = ((tx.get("transaction") or {}).get("message")) or {}
    for ix in message.get("instructions") or []:
        parsed = ix.get("parsed") if isinstance(ix, dict) else None
        if isinstance(parsed, dict) and parsed.get("type") == "memo":
            info = parsed.get("info")
            if isinstance(info, str):
                return info
            if isinstance(info, dict) and info.get("memo"):
                return str(info.get("memo"))
        if isinstance(ix, dict) and ix.get("program") == "spl-memo":
            data = ix.get("parsed")
            if isinstance(data, str):
                return data
    return None
