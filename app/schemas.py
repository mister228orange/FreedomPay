from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class GatewayPublic(BaseModel):
    chain: str
    currency: str
    name: str
    decimals: int
    min_confirmations: int
    supports_memo: bool
    network: str
    payment_ttl_seconds: int
    poll_interval_seconds: int
    exits: list[str]


class GatewaysResponse(BaseModel):
    data: list[GatewayPublic]
    count: int
    network: str
    service_fee_percent: Decimal
    default_fiat: str
    usd_precision: Decimal
    memo_length: int


class InvoiceCreate(BaseModel):
    chain: str
    amount: Decimal = Field(
        gt=0,
        description="Amount in fiat (USD by default) or native if amount_unit=native",
    )
    amount_unit: Literal["usd", "native"] = "usd"
    external_ref: str | None = None
    callback_url: str | None = None


class InvoicePublic(BaseModel):
    id: uuid.UUID
    chain: str
    currency: str
    network: str
    fiat: str
    amount_usd: Decimal
    amount_usd_fee: Decimal
    amount_merchant: Decimal
    amount_fee: Decimal
    amount: Decimal
    address: str
    memo: str | None
    status: str
    external_ref: str | None
    txid: str | None
    confirmations: int
    created_at: int
    expires_at: int
    paid_at: int | None
    exits: dict[str, str]
    pay_url: str
    embed_url: str
    page_url: str
    div_url: str
    qr_url: str
    qr_payload: str


class Message(BaseModel):
    message: str
