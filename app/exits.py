"""Frontend payment exits — web, Telegram, embed widget."""

from __future__ import annotations

from urllib.parse import quote

from app.config import settings
from app.models import Invoice


def build_exits(invoice: Invoice) -> dict[str, str]:
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    return {
        "web": f"{base}/v1/pay/{invoice.id}/page",
        "div": f"{base}/v1/pay/{invoice.id}/div",
        "tg": f"{base}/v1/exits/{invoice.id}/tg",
        "embed": f"{base}/embed?invoice={invoice.id}",
    }


def web_pay_payload(invoice: Invoice) -> dict:
    return {
        "invoice_id": str(invoice.id),
        "chain": invoice.chain,
        "currency": invoice.currency,
        "network": invoice.network,
        "amount": invoice.amount,
        "amount_merchant": invoice.amount_merchant,
        "amount_fee": invoice.amount_fee,
        "address": invoice.address,
        "memo": invoice.memo,
        "status": invoice.status,
        "expires_at": invoice.expires_at,
        "created_at": invoice.created_at,
        "txid": invoice.txid,
        "confirmations": invoice.confirmations,
        "instructions": (
            f"Send exactly {invoice.amount} {invoice.currency} on {invoice.chain} "
            f"({invoice.network}) to {invoice.address}"
            + (f" with memo {invoice.memo}" if invoice.memo else "")
        ),
    }


def telegram_deeplink(invoice: Invoice, bot_username: str | None = None) -> dict:
    text = (
        f"FreedomPay\n"
        f"Pay {invoice.amount} {invoice.currency} ({invoice.chain} / {invoice.network})\n"
        f"Address: {invoice.address}\n"
    )
    if invoice.memo:
        text += f"Memo: {invoice.memo}\n"
    text += f"Invoice: {invoice.id}"

    share = (
        f"https://t.me/share/url?url={quote(settings.PUBLIC_BASE_URL)}"
        f"&text={quote(text)}"
    )
    payload: dict = {
        "invoice_id": str(invoice.id),
        "share_url": share,
        "message": text,
        "chain": invoice.chain,
        "currency": invoice.currency,
        "amount": str(invoice.amount),
        "address": invoice.address,
        "memo": invoice.memo,
    }
    if bot_username:
        payload["bot_url"] = (
            f"https://t.me/{bot_username.lstrip('@')}?start=pay_{invoice.id}"
        )
    return payload
