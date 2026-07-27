from __future__ import annotations

import logging
from decimal import Decimal

import httpx

from app.config import settings
from app.gateways.abc import PaymentHit
from app.gateways.common import BaseChainGateway, amount_matches

logger = logging.getLogger(__name__)


class TonUsdtGateway(BaseChainGateway):
    """Tether USDT jetton on TON (memo identity)."""

    chain = "ton-usdt"
    currency = "USDT"
    name = "USDT"
    decimals = 6
    min_confirmations = 1
    supports_memo = True
    blockchain = "ton"
    is_token = True

    def __init__(self) -> None:
        self.token_contract = settings.ton_usdt_jetton()

    def wallet(self) -> str:
        return (settings.WALLET_TON_USDT or settings.WALLET_TON).strip()

    async def find_payment(
        self,
        *,
        address: str,
        amount: Decimal,
        since_unix: int,
        memo: str | None,
    ) -> PaymentHit | None:
        _ = since_unix
        jetton = settings.ton_usdt_jetton()
        url = (
            f"{settings.tonapi_base()}/v2/blockchain/accounts/{address}"
            f"/jettons/{jetton}/history"
        )
        headers = {}
        if settings.TON_API_KEY:
            headers["Authorization"] = f"Bearer {settings.TON_API_KEY}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(url, params={"limit": 30}, headers=headers)
            if r.status_code >= 400:
                # Fallback: account events (works when history path differs)
                events_url = f"{settings.tonapi_base()}/v2/accounts/{address}/events"
                r = await client.get(
                    events_url, params={"limit": 30}, headers=headers
                )
                if r.status_code >= 400:
                    logger.warning(
                        "TON USDT check failed: %s %s", r.status_code, r.text[:200]
                    )
                    return None
                return _match_tonapi_events(
                    r.json() or {},
                    amount=amount,
                    memo=memo,
                    jetton=jetton,
                    decimals=self.decimals,
                )
            body = r.json() or {}

        for ev in body.get("events") or body.get("operations") or []:
            hit = _parse_jetton_event(
                ev, amount=amount, memo=memo, decimals=self.decimals
            )
            if hit:
                return hit
        return None


def _parse_jetton_event(
    ev: dict,
    *,
    amount: Decimal,
    memo: str | None,
    decimals: int,
) -> PaymentHit | None:
    comment = None
    for key in ("comment", "text", "memo"):
        if ev.get(key):
            comment = str(ev.get(key))
            break
    simple = ev.get("simple_preview") or {}
    if not comment and simple.get("description"):
        comment = str(simple.get("description"))

    if memo and comment and str(memo) not in str(comment):
        return None
    if memo and not comment:
        # some histories omit comment — still try amount match when no memo gate
        pass

    raw = ev.get("amount") or ev.get("jetton_amount") or 0
    try:
        value = Decimal(str(raw)) / Decimal(10**decimals)
    except Exception:  # noqa: BLE001
        return None
    if value > 0 and amount_matches("USDT", amount, value):
        if memo and not comment:
            return None
        txid = str(
            ev.get("event_id")
            or ev.get("transaction_hash")
            or ev.get("tx_hash")
            or ev.get("hash")
            or ""
        )
        return PaymentHit(
            txid=txid,
            amount=value,
            confirmations=1,
            memo=comment,
        )
    return None


def _match_tonapi_events(
    body: dict,
    *,
    amount: Decimal,
    memo: str | None,
    jetton: str,
    decimals: int,
) -> PaymentHit | None:
    for ev in body.get("events") or []:
        for action in ev.get("actions") or []:
            jt = action.get("JettonTransfer") or action.get("jetton_transfer") or {}
            if not jt:
                continue
            master = (
                ((jt.get("jetton") or {}).get("address"))
                or jt.get("jetton_address")
                or ""
            )
            if jetton and master and jetton not in str(master) and str(master) not in jetton:
                # address forms differ (raw vs user-friendly) — skip strict miss only when both set
                continue
            comment = jt.get("comment") or jt.get("text")
            raw = jt.get("amount") or 0
            try:
                value = Decimal(str(raw)) / Decimal(10**decimals)
            except Exception:  # noqa: BLE001
                continue
            if memo and comment and str(memo) not in str(comment):
                continue
            if memo and not comment:
                continue
            if value > 0 and amount_matches("USDT", amount, value):
                return PaymentHit(
                    txid=str(ev.get("event_id") or ""),
                    amount=value,
                    confirmations=1,
                    memo=str(comment) if comment else None,
                )
    return None
