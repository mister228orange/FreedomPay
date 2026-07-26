from __future__ import annotations

import hashlib
import logging
import secrets
import string
import uuid
from decimal import ROUND_DOWN, Decimal

import httpx
from sqlmodel import Session, col, select

from app.config import settings
from app.exits import build_exits
from app.gateways.registry import get_checker
from app.models import Invoice, InvoiceStatus, _dec_str
from app.pricing import (
    ceil_to_usd_step,
    is_dust,
    to_usd,
    usd_to_native,
)
from app.qrpay import payment_payload
from app.schemas import InvoiceCreate, InvoicePublic
from app.timeutil import unix_now

logger = logging.getLogger(__name__)

# Unambiguous short alphabet for memos (no 0/O/1/I)
_MEMO_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def _quantize_down(amount: Decimal, decimals: int) -> Decimal:
    q = Decimal("1").scaleb(-decimals)
    return amount.quantize(q, rounding=ROUND_DOWN)


def _calc_fee_usd(merchant_usd: Decimal) -> Decimal:
    pct = Decimal(str(settings.SERVICE_FEE_PERCENT))
    raw = (merchant_usd * pct) / Decimal("100")
    return ceil_to_usd_step(raw)


def _open_amounts(session: Session, chain: str) -> set[str]:
    rows = session.exec(
        select(Invoice.amount).where(
            Invoice.chain == chain,
            col(Invoice.status).in_(
                [InvoiceStatus.PENDING.value, InvoiceStatus.DETECTED.value]
            ),
        )
    ).all()
    return {str(a) for a in rows}


def _unique_pay_amount(
    session: Session,
    *,
    chain: str,
    total: Decimal,
    decimals: int,
    invoice_key: str,
    require_unique_amount: bool,
) -> Decimal:
    base = _quantize_down(total, decimals)
    if not require_unique_amount:
        return base

    digest = hashlib.sha256(invoice_key.encode()).hexdigest()
    mod = 10 ** min(4, max(decimals - 2, 1))
    n = int(digest[:8], 16) % mod
    candidate = _quantize_down(base + (Decimal(n) / Decimal(10**decimals)), decimals)
    taken = _open_amounts(session, chain)
    step = Decimal("1").scaleb(-decimals)
    guard = 0
    while _dec_str(candidate) in taken and guard < 10_000:
        candidate = _quantize_down(candidate + step, decimals)
        guard += 1
    return candidate


def _unique_memo(session: Session, chain: str) -> str | None:
    checker = get_checker(chain)
    if not checker.gateway_info().supports_memo:
        return None
    length = int(settings.MEMO_LENGTH)
    taken = {
        m
        for m in session.exec(
            select(Invoice.memo).where(
                Invoice.chain == chain,
                col(Invoice.status).in_(
                    [InvoiceStatus.PENDING.value, InvoiceStatus.DETECTED.value]
                ),
                col(Invoice.memo).is_not(None),  # type: ignore[attr-defined]
            )
        ).all()
        if m
    }
    for _ in range(64):
        memo = "".join(secrets.choice(_MEMO_ALPHABET) for _ in range(length))
        if memo not in taken:
            return memo
    # Extremely unlikely fallback
    return "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length + 2)
    )


def _txid_already_used(session: Session, txid: str, invoice_id: uuid.UUID) -> bool:
    if not txid:
        return False
    row = session.exec(
        select(Invoice).where(
            Invoice.txid == txid,
            Invoice.id != invoice_id,
            col(Invoice.status).in_(
                [
                    InvoiceStatus.DETECTED.value,
                    InvoiceStatus.CONFIRMED.value,
                ]
            ),
        )
    ).first()
    return row is not None


def to_public(invoice: Invoice) -> InvoicePublic:
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    payload = payment_payload(invoice)
    return InvoicePublic(
        id=invoice.id,
        chain=invoice.chain,
        currency=invoice.currency,
        network=invoice.network,
        fiat=invoice.fiat or "USD",
        amount_usd=Decimal(invoice.amount_usd or "0"),
        amount_usd_fee=Decimal(invoice.amount_usd_fee or "0"),
        amount_merchant=Decimal(invoice.amount_merchant),
        amount_fee=Decimal(invoice.amount_fee),
        amount=Decimal(invoice.amount),
        address=invoice.address,
        memo=invoice.memo,
        status=invoice.status,
        external_ref=invoice.external_ref,
        txid=invoice.txid,
        confirmations=invoice.confirmations,
        created_at=invoice.created_at,
        expires_at=invoice.expires_at,
        paid_at=invoice.paid_at,
        exits=build_exits(invoice),
        pay_url=f"{base}/pay/{invoice.id}",
        embed_url=f"{base}/embed?invoice={invoice.id}",
        page_url=f"{base}/v1/pay/{invoice.id}/page",
        div_url=f"{base}/v1/pay/{invoice.id}/div",
        qr_url=f"{base}/v1/pay/{invoice.id}/qr.svg",
        qr_payload=payload,
    )


def create_invoice(session: Session, body: InvoiceCreate) -> Invoice:
    checker = get_checker(body.chain)
    info = checker.gateway_info()
    now = unix_now()
    invoice_id = uuid.uuid4()

    raw = Decimal(str(body.amount))
    dust = Decimal(str(settings.DUST_IGNORE_USD))
    if body.amount_unit == "native":
        if to_usd(info.currency, raw) < dust:
            raise ValueError(
                f"Amount below dust threshold (${dust} USDT/USD)"
            )
        merchant_usd = ceil_to_usd_step(to_usd(info.currency, raw))
    else:
        # Default: amount is USD → reject sub-dust → ceil up to 10¢ → native ceil-up
        if raw < dust:
            raise ValueError(
                f"Amount below dust threshold (${dust} USDT/USD); got ${raw}"
            )
        merchant_usd = ceil_to_usd_step(raw)
    merchant_native = usd_to_native(info.currency, merchant_usd, info.decimals)

    fee_usd = _calc_fee_usd(merchant_usd)
    total_usd = merchant_usd + fee_usd
    # Convert total USD → native (ceil), then apply uniqueness dust if needed
    total_native_base = usd_to_native(info.currency, total_usd, info.decimals)
    fee_native = _quantize_down(
        max(Decimal("0"), total_native_base - merchant_native), info.decimals
    )

    require_unique_amount = not info.supports_memo
    total = _unique_pay_amount(
        session,
        chain=info.chain,
        total=total_native_base,
        decimals=info.decimals,
        invoice_key=str(invoice_id),
        require_unique_amount=require_unique_amount,
    )

    invoice = Invoice(
        id=invoice_id,
        chain=info.chain,
        currency=info.currency,
        fiat="USD",
        amount_usd=_dec_str(total_usd),
        amount_usd_fee=_dec_str(fee_usd),
        amount_merchant=_dec_str(merchant_native),
        amount_fee=_dec_str(fee_native),
        amount=_dec_str(total),
        address=checker.receive_address(),
        memo=_unique_memo(session, info.chain),
        status=InvoiceStatus.PENDING.value,
        external_ref=body.external_ref,
        callback_url=body.callback_url or settings.MERCHANT_WEBHOOK_URL or None,
        network=settings.NETWORK,
        expires_at=now + checker.payment_ttl_seconds(),
    )
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    return invoice


def get_invoice(session: Session, invoice_id: uuid.UUID) -> Invoice | None:
    return session.get(Invoice, invoice_id)


async def check_invoice(session: Session, invoice: Invoice) -> Invoice:
    now = unix_now()
    if invoice.status in (
        InvoiceStatus.CONFIRMED.value,
        InvoiceStatus.FAILED.value,
    ):
        return invoice
    if now > invoice.expires_at and invoice.status == InvoiceStatus.PENDING.value:
        invoice.status = InvoiceStatus.EXPIRED.value
        session.add(invoice)
        session.commit()
        session.refresh(invoice)
        return invoice

    checker = get_checker(invoice.chain)
    try:
        hit = await checker.find_payment(
            address=invoice.address,
            amount=Decimal(invoice.amount),
            since_unix=invoice.created_at,
            memo=invoice.memo,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Chain check failed for %s", invoice.id)
        session.refresh(invoice)
        return invoice
    if not hit:
        session.refresh(invoice)
        return invoice

    if is_dust(invoice.currency, hit.amount):
        logger.info(
            "Ignoring dust tx %s amount=%s %s",
            hit.txid,
            hit.amount,
            invoice.currency,
        )
        session.refresh(invoice)
        return invoice

    if _txid_already_used(session, hit.txid, invoice.id):
        logger.warning("Tx %s already claimed by another invoice", hit.txid)
        session.refresh(invoice)
        return invoice

    invoice.txid = hit.txid
    invoice.confirmations = hit.confirmations
    info = checker.gateway_info()
    if hit.confirmations >= info.min_confirmations:
        was_pending = invoice.status != InvoiceStatus.CONFIRMED.value
        invoice.status = InvoiceStatus.CONFIRMED.value
        invoice.paid_at = now
        session.add(invoice)
        session.commit()
        session.refresh(invoice)
        if was_pending:
            await _notify_merchant(invoice)
    else:
        invoice.status = InvoiceStatus.DETECTED.value
        session.add(invoice)
        session.commit()
        session.refresh(invoice)
    return invoice


async def simulate_paid(session: Session, invoice: Invoice) -> Invoice:
    if settings.NETWORK != "testnet" or not settings.DEMO_MODE:
        raise ValueError("simulate only allowed on testnet with DEMO_MODE=true")
    if invoice.status == InvoiceStatus.CONFIRMED.value:
        return invoice
    invoice.status = InvoiceStatus.CONFIRMED.value
    invoice.txid = invoice.txid or f"sim_{secrets.token_hex(8)}"
    invoice.confirmations = 99
    invoice.paid_at = unix_now()
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    await _notify_merchant(invoice)
    return invoice


async def _notify_merchant(invoice: Invoice) -> None:
    url = invoice.callback_url or settings.MERCHANT_WEBHOOK_URL
    if not url:
        return
    payload = {
        "invoice_id": str(invoice.id),
        "external_ref": invoice.external_ref,
        "chain": invoice.chain,
        "currency": invoice.currency,
        "network": invoice.network,
        "fiat": invoice.fiat,
        "amount_usd": str(invoice.amount_usd),
        "amount_usd_fee": str(invoice.amount_usd_fee),
        "amount": str(invoice.amount),
        "amount_merchant": str(invoice.amount_merchant),
        "amount_fee": str(invoice.amount_fee),
        "memo": invoice.memo,
        "txid": invoice.txid,
        "status": invoice.status,
        "paid_at": invoice.paid_at,
    }
    headers = {}
    if settings.MERCHANT_WEBHOOK_SECRET:
        headers["X-FreedomPay-Secret"] = settings.MERCHANT_WEBHOOK_SECRET
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            logger.info("Webhook %s → %s", url, r.status_code)
    except Exception:  # noqa: BLE001
        logger.exception("Webhook failed for invoice %s", invoice.id)


async def poll_pending(session: Session, *, chain: str | None = None) -> int:
    now = unix_now()
    stmt = select(Invoice).where(
        col(Invoice.status).in_(
            [InvoiceStatus.PENDING.value, InvoiceStatus.DETECTED.value]
        )
    )
    if chain:
        stmt = stmt.where(Invoice.chain == chain.strip().lower())
    rows = list(session.exec(stmt).all())
    checked = 0
    for invoice in rows:
        if now > invoice.expires_at and invoice.status == InvoiceStatus.PENDING.value:
            invoice.status = InvoiceStatus.EXPIRED.value
            session.add(invoice)
            session.commit()
            continue
        await check_invoice(session, invoice)
        checked += 1
    return checked
