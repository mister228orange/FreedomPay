"""
Abstract contracts for the FreedomPay merchant-acceptor workflow.

End-to-end lifecycle (implementations must follow this order):

1. **Catalog** — load which currencies/chains are shown to users.
2. **Rates** — resolve USD marks for conversion.
3. **Invoice** — accept fiat (USD), ceil to precision, convert → native (ceil).
4. **Identity** — attach short memo and/or unique amount dust so parallel
   invoices on one address do not collide.
5. **Present** — expose page / div / QR / embed exits for the payer.
6. **Detect** — poll chain gateways for matching inbound transfers.
7. **Confirm** — require min confirmations, claim txid once, webhook merchant.
8. **Dust gate** — ignore inbound junk below DUST_IGNORE_USD (~$0.10).

Each blockchain lives under ``app/gateways/<chain>/`` and subclasses
``AbstractChainGateway``. Do not bypass steps when adding a new chain.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Sequence


@dataclass(frozen=True)
class GatewayInfo:
    chain: str
    currency: str
    name: str
    decimals: int
    min_confirmations: int
    address_configured: bool
    network: str
    supports_memo: bool = False
    payment_ttl_seconds: int = 1800
    poll_interval_seconds: int = 20
    blockchain: str = ""
    blockchain_name: str = ""
    logo_url: str = ""
    is_token: bool = False
    token_contract: str | None = None
    exits: list[str] = field(
        default_factory=lambda: ["web", "div", "tg", "embed"]
    )


@dataclass
class PaymentHit:
    txid: str
    amount: Decimal
    confirmations: int
    memo: str | None = None


@dataclass(frozen=True)
class CurrencySpec:
    """One display/payable currency from the catalog."""

    id: str
    chain: str
    symbol: str
    name: str
    decimals: int
    enabled: bool
    display: bool
    supports_memo: bool
    wallet_env: str
    rate: dict[str, Any]
    min_confirmations: int = 1
    payment_ttl_seconds: int = 1800


@dataclass(frozen=True)
class RateQuote:
    """USD mark price for one unit of native asset."""

    symbol: str
    usd: Decimal
    provider: str
    raw: dict[str, Any] | None = None


class AbstractCurrencyCatalog(ABC):
    """Step 1 — currency list for UI / API."""

    @abstractmethod
    def load(self) -> Sequence[CurrencySpec]:
        """Return all defined currencies."""

    @abstractmethod
    def displayed(self) -> Sequence[CurrencySpec]:
        """Currencies that should appear in user-facing gateway lists."""

    @abstractmethod
    def get(self, currency_id: str) -> CurrencySpec | None:
        """Lookup by id / symbol / chain key."""


class AbstractRateProvider(ABC):
    """Step 2 — live (or static) USD rate for a catalog currency."""

    name: str

    @abstractmethod
    async def get_usd_price(self, spec: CurrencySpec) -> RateQuote:
        """Return USD per 1 whole unit of ``spec.symbol``."""


class AbstractChainGateway(ABC):
    """
    Step 6 — watch-only inbound payment detection on one chain.

    Must match invoice identity (memo and/or exact amount) and ignore dust.
    Payment await window is chain-specific via ``payment_ttl_seconds``.
    Poll cadence is chain-specific via ``poll_interval_seconds``.
    """

    chain: str
    currency: str
    name: str
    decimals: int
    min_confirmations: int
    supports_memo: bool = False

    @abstractmethod
    def is_configured(self) -> bool:
        """True when a receive address is set for this chain."""

    @abstractmethod
    def receive_address(self) -> str:
        """Watch-only address customers pay to."""

    @abstractmethod
    def payment_ttl_seconds(self) -> int:
        """How long (seconds) to await payment before the invoice expires."""

    @abstractmethod
    def poll_interval_seconds(self) -> int:
        """How often (seconds) to poll this chain for matching payments."""

    @abstractmethod
    async def find_payment(
        self,
        *,
        address: str,
        amount: Decimal,
        since_unix: int,
        memo: str | None,
    ) -> PaymentHit | None:
        """Return a payment hit if a matching on-chain transfer is found."""

    @abstractmethod
    def gateway_info(self) -> GatewayInfo:
        """Public metadata for API / UI catalog."""


class AbstractPaymentWorkflow(ABC):
    """
    Orchestrator for steps 1–8.

    Concrete class wires catalog → rates → invoice service → gateways →
    webhooks. Keep side effects (DB, HTTP) behind these methods so new
    chains/rate sources plug in without rewriting the merchant API.
    """

    @abstractmethod
    def list_display_currencies(self) -> Sequence[CurrencySpec]:
        """Currencies shown to users (display + wallet ready)."""

    @abstractmethod
    async def resolve_usd_price(self, symbol: str) -> RateQuote:
        """Fresh or cached USD mark used for invoice conversion."""

    @abstractmethod
    async def create_invoice(
        self, *, chain: str, amount_usd: Decimal, **kwargs: Any
    ) -> Any:
        """Steps 2–5: rate → ceil USD → native → identity → persist."""

    @abstractmethod
    async def check_invoice(self, invoice_id: Any) -> Any:
        """Steps 6–8: detect / confirm / webhook."""
