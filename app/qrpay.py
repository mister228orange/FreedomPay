"""Build scannable payment payloads + QR SVG."""

from __future__ import annotations

from decimal import Decimal
from urllib.parse import quote

from app.config import settings
from app.models import Invoice


def payment_payload(invoice: Invoice) -> str:
    """URI / text wallets can scan for a simple transfer."""
    amount = str(invoice.amount)
    addr = invoice.address
    memo = invoice.memo or ""
    chain = invoice.chain

    if chain == "bitcoin":
        return f"bitcoin:{addr}?amount={amount}"

    if chain == "ton":
        nano = int(Decimal(amount) * Decimal(10**9))
        q = f"ton://transfer/{addr}?amount={nano}"
        if memo:
            q += f"&text={quote(memo)}"
        return q

    if chain == "ton-usdt":
        units = int(Decimal(amount) * Decimal(10**6))
        jetton = settings.ton_usdt_jetton()
        q = f"ton://transfer/{addr}?jetton={jetton}&amount={units}"
        if memo:
            q += f"&text={quote(memo)}"
        return q

    if chain == "solana":
        q = f"solana:{addr}?amount={amount}"
        if memo:
            q += f"&memo={quote(memo)}"
        return q

    if chain == "solana-usdc":
        mint = settings.sol_usdc_mint()
        q = f"solana:{addr}?amount={amount}&spl-token={mint}"
        if memo:
            q += f"&memo={quote(memo)}"
        return q

    if chain in {"ethereum", "polygon"}:
        return f"ethereum:{addr}?value={amount}"

    lines = [
        f"FreedomPay {invoice.currency}",
        f"Address: {addr}",
        f"Amount: {amount}",
    ]
    if memo:
        lines.append(f"Memo: {memo}")
    return "\n".join(lines)


def qr_svg(payload: str, *, scale: int = 4) -> str:
    try:
        import segno
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("segno is required for QR generation") from exc
    import io

    qr = segno.make(payload, error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="svg", scale=scale, border=1)
    return buf.getvalue().decode("utf-8")
