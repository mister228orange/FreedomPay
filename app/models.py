from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

from app.timeutil import unix_now


class InvoiceStatus(StrEnum):
    PENDING = "pending"
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    FAILED = "failed"


def _dec_str(value: Decimal | str) -> str:
    """Store decimals as strings — SQLite Numeric maps to float otherwise."""
    return format(Decimal(str(value)), "f")


class Invoice(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    chain: str = Field(index=True, max_length=32)
    currency: str = Field(max_length=16)
    fiat: str = Field(default="USD", max_length=8)
    # Fiat totals (USD), stored as decimal strings
    amount_usd: str = Field(default="0", max_length=64)
    amount_usd_fee: str = Field(default="0", max_length=64)
    # Native crypto amounts (SQLite-safe strings)
    amount_merchant: str = Field(max_length=64)
    amount_fee: str = Field(max_length=64)
    # Total customer must send (merchant + fee), used for on-chain match
    amount: str = Field(max_length=64)
    address: str = Field(max_length=256)
    memo: str | None = Field(default=None, max_length=128)
    status: str = Field(default=InvoiceStatus.PENDING.value, index=True, max_length=32)
    external_ref: str | None = Field(default=None, max_length=255, index=True)
    callback_url: str | None = Field(default=None, max_length=512)
    txid: str | None = Field(default=None, max_length=128)
    confirmations: int = 0
    network: str = Field(default="testnet", max_length=16)
    created_at: int = Field(default_factory=unix_now)
    expires_at: int
    paid_at: int | None = None
    meta_json: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
