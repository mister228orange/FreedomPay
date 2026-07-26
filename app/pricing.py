"""USD conversion helpers — fiat default, ceil to 10¢, round native up."""

from __future__ import annotations

from decimal import ROUND_UP, Decimal

from app.config import settings

USD_STEP = Decimal("0.10")


def price_usd(currency: str) -> Decimal:
    key = currency.strip().upper()
    table = {
        "BTC": Decimal(str(settings.PRICE_USD_BTC)),
        "TON": Decimal(str(settings.PRICE_USD_TON)),
        "SOL": Decimal(str(settings.PRICE_USD_SOL)),
        "ETH": Decimal(str(settings.PRICE_USD_ETH)),
        "POL": Decimal(str(settings.PRICE_USD_POL)),
        "TRX": Decimal(str(settings.PRICE_USD_TRX)),
        "XMR": Decimal(str(settings.PRICE_USD_XMR)),
        "USDT": Decimal("1"),
        "USDC": Decimal("1"),
        "USD": Decimal("1"),
    }
    return table.get(key, Decimal("0"))


def to_usd(currency: str, amount: Decimal) -> Decimal:
    return Decimal(str(amount)) * price_usd(currency)


def ceil_to_usd_step(amount_usd: Decimal, step: Decimal | None = None) -> Decimal:
    """Round USD **up** to step precision (default 10 cents)."""
    step = step or Decimal(str(settings.USD_PRECISION))
    if step <= 0:
        step = USD_STEP
    amt = Decimal(str(amount_usd))
    if amt <= 0:
        return Decimal("0")
    units = (amt / step).to_integral_value(rounding=ROUND_UP)
    return (units * step).quantize(step)


def usd_to_native(currency: str, amount_usd: Decimal, decimals: int) -> Decimal:
    """Convert USD → native crypto, rounding **up** (payer never underpays)."""
    px = price_usd(currency)
    if px <= 0:
        raise ValueError(f"No USD price configured for {currency}")
    raw = Decimal(str(amount_usd)) / px
    q = Decimal("1").scaleb(-decimals)
    return raw.quantize(q, rounding=ROUND_UP)


def is_dust(currency: str, amount: Decimal) -> bool:
    """True if below configured junk threshold (default $0.10 USDT/USD)."""
    threshold = Decimal(str(settings.DUST_IGNORE_USD))
    usd = to_usd(currency, amount)
    if usd <= 0:
        return False
    return usd < threshold
