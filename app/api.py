from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from sqlmodel import Session

from app.config import settings
from app.db import get_session
from app.exits import telegram_deeplink, web_pay_payload
from app.gateways.registry import get_available_gateways
from app.pay_html import render_pay_div, render_pay_page
from app.qrpay import payment_payload, qr_svg
from app.schemas import (
    GatewayPublic,
    GatewaysResponse,
    InvoiceCreate,
    InvoicePublic,
    Message,
)
from app.services import invoices as invoice_service

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


def require_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
    api_key: Annotated[str | None, Query()] = None,
) -> None:
    key = x_api_key or api_key
    if not key or key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.get("/health", response_model=Message)
def health() -> Message:
    return Message(message="ok")


@router.get("/v1/gateways", response_model=GatewaysResponse)
def get_available_gateway() -> GatewaysResponse:
    items = [
        GatewayPublic(
            chain=g.chain,
            currency=g.currency,
            name=g.name,
            decimals=g.decimals,
            min_confirmations=g.min_confirmations,
            supports_memo=g.supports_memo,
            network=g.network,
            payment_ttl_seconds=g.payment_ttl_seconds,
            poll_interval_seconds=g.poll_interval_seconds,
            exits=list(g.exits),
        )
        for g in get_available_gateways()
    ]
    return GatewaysResponse(
        data=items,
        count=len(items),
        network=settings.NETWORK,
        service_fee_percent=settings.SERVICE_FEE_PERCENT,
        default_fiat=settings.DEFAULT_FIAT,
        usd_precision=settings.USD_PRECISION,
        memo_length=settings.MEMO_LENGTH,
    )


@router.post(
    "/v1/invoices",
    response_model=InvoicePublic,
    dependencies=[Depends(require_api_key)],
)
def create_invoice(body: InvoiceCreate, session: SessionDep) -> InvoicePublic:
    try:
        invoice = invoice_service.create_invoice(session, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return invoice_service.to_public(invoice)


@router.get(
    "/v1/invoices/{invoice_id}",
    response_model=InvoicePublic,
    dependencies=[Depends(require_api_key)],
)
def read_invoice(invoice_id: uuid.UUID, session: SessionDep) -> InvoicePublic:
    invoice = invoice_service.get_invoice(session, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice_service.to_public(invoice)


@router.get("/v1/public/invoices/{invoice_id}", response_model=InvoicePublic)
def read_invoice_public(invoice_id: uuid.UUID, session: SessionDep) -> InvoicePublic:
    invoice = invoice_service.get_invoice(session, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice_service.to_public(invoice)


@router.post(
    "/v1/invoices/{invoice_id}/check",
    response_model=InvoicePublic,
    dependencies=[Depends(require_api_key)],
)
async def check_invoice(invoice_id: uuid.UUID, session: SessionDep) -> InvoicePublic:
    invoice = invoice_service.get_invoice(session, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice = await invoice_service.check_invoice(session, invoice)
    return invoice_service.to_public(invoice)


@router.post(
    "/v1/invoices/{invoice_id}/simulate",
    response_model=InvoicePublic,
    dependencies=[Depends(require_api_key)],
)
async def simulate_invoice(invoice_id: uuid.UUID, session: SessionDep) -> InvoicePublic:
    invoice = invoice_service.get_invoice(session, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    try:
        invoice = await invoice_service.simulate_paid(session, invoice)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return invoice_service.to_public(invoice)


@router.get("/v1/pay/{invoice_id}/page", response_class=HTMLResponse)
def pay_full_page(
    invoice_id: uuid.UUID,
    session: SessionDep,
    size: Literal["sm", "md", "lg"] = "md",
    width: int | None = Query(default=None, ge=180, le=1200),
) -> HTMLResponse:
    """Full HTML checkout page (QR + copyable fields)."""
    invoice = invoice_service.get_invoice(session, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return HTMLResponse(render_pay_page(invoice, size=size, width=width))


@router.get("/v1/pay/{invoice_id}/div", response_class=HTMLResponse)
def pay_div_only(
    invoice_id: uuid.UUID,
    session: SessionDep,
    size: Literal["sm", "md", "lg"] = "md",
    width: int | None = Query(default=None, ge=180, le=1200),
) -> HTMLResponse:
    """Embeddable HTML fragment: only the pay `<div>` (sized via `size` / `width`)."""
    invoice = invoice_service.get_invoice(session, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return HTMLResponse(
        render_pay_div(invoice, size=size, width=width, show_chrome=True),
        headers={"Access-Control-Allow-Origin": "*"},
    )


@router.get("/v1/pay/{invoice_id}/qr.svg")
def pay_qr_svg(invoice_id: uuid.UUID, session: SessionDep) -> Response:
    invoice = invoice_service.get_invoice(session, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    try:
        svg = qr_svg(payment_payload(invoice), scale=5)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/v1/exits/{invoice_id}/web")
def exit_web(invoice_id: uuid.UUID, session: SessionDep) -> dict:
    invoice = invoice_service.get_invoice(session, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return web_pay_payload(invoice)


@router.get("/v1/exits/{invoice_id}/tg")
def exit_tg(invoice_id: uuid.UUID, session: SessionDep) -> dict:
    invoice = invoice_service.get_invoice(session, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return telegram_deeplink(invoice)


@router.get("/v1/config/public")
def public_config() -> dict:
    return {
        "network": settings.NETWORK,
        "demo_mode": settings.DEMO_MODE and settings.NETWORK == "testnet",
        "service_fee_percent": str(settings.SERVICE_FEE_PERCENT),
        "dust_ignore_usd": str(settings.DUST_IGNORE_USD),
        "default_fiat": settings.DEFAULT_FIAT,
        "usd_precision": str(settings.USD_PRECISION),
        "memo_length": settings.MEMO_LENGTH,
        "public_base_url": settings.PUBLIC_BASE_URL,
    }
