"""Build scannable payment payloads + QR SVG."""

from __future__ import annotations

from decimal import Decimal
from urllib.parse import quote

from app.models import Invoice


def payment_payload(invoice: Invoice) -> str:
    """URI / text wallets can scan for a simple transfer."""
    amount = str(invoice.amount)
    addr = invoice.address
    memo = invoice.memo or ""
    chain = invoice.chain

    if chain == "bitcoin":
        # BIP21
        q = f"bitcoin:{addr}?amount={amount}"
        return q

    if chain == "ton":
        # ton://transfer/<addr>?amount=<nanoton>&text=<memo>
        nano = int(Decimal(amount) * Decimal(10**9))
        q = f"ton://transfer/{addr}?amount={nano}"
        if memo:
            q += f"&text={quote(memo)}"
        return q

    if chain == "solana":
        # Solana Pay transfer request (native SOL)
        q = f"solana:{addr}?amount={amount}"
        if memo:
            q += f"&memo={quote(memo)}"
        return q

    if chain in {"ethereum", "polygon"}:
        return f"ethereum:{addr}?value={amount}"

    # Fallback plain text for copy/scan
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
