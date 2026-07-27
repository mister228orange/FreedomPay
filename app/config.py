from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    API_KEY: str = "dev-freedompay"
    PUBLIC_BASE_URL: str = "http://localhost:8090"
    MERCHANT_WEBHOOK_URL: str = ""
    MERCHANT_WEBHOOK_SECRET: str = ""

    NETWORK: Literal["mainnet", "testnet"] = "testnet"
    # Allow POST /v1/invoices/{id}/simulate on testnet only
    DEMO_MODE: bool = True

    # Default payment await window; per-chain overrides below win when set
    INVOICE_TTL_SECONDS: int = 1800
    INVOICE_TTL_BTC: int = 3600
    INVOICE_TTL_TON: int = 1800
    INVOICE_TTL_SOL: int = 900
    INVOICE_TTL_ETH: int = 3600
    INVOICE_TTL_POL: int = 1800
    INVOICE_TTL_TRX: int = 1800
    INVOICE_TTL_XMR: int = 7200

    # Default poll cadence; per-chain overrides below
    POLL_INTERVAL_SECONDS: int = 20
    POLL_INTERVAL_BTC: int = 30
    POLL_INTERVAL_TON: int = 15
    POLL_INTERVAL_SOL: int = 10
    POLL_INTERVAL_ETH: int = 20
    POLL_INTERVAL_POL: int = 15
    POLL_INTERVAL_TRX: int = 20
    POLL_INTERVAL_XMR: int = 60

    # Run Taskiq scheduler inside the API process (InMemoryBroker only)
    TASKIQ_EMBEDDED: bool = True

    # Empty → SQLite locally; Compose sets Postgres
    DATABASE_URL: str = "sqlite:///./data/freedompay.db"
    # Empty → InMemoryBroker; Compose sets Redis for worker/scheduler
    REDIS_URL: str = ""

    # Service commission (% of merchant amount), e.g. 1.5 = 1.5%
    SERVICE_FEE_PERCENT: Decimal = Field(default=Decimal("1.5"))

    # Fiat default for invoice amounts (converted to native with ceil)
    DEFAULT_FIAT: str = "USD"
    # USD amount precision — round **up** to this step (10 cents)
    USD_PRECISION: Decimal = Field(default=Decimal("0.10"))
    # Short payment memo / comment length (env-specific, default 4)
    MEMO_LENGTH: int = Field(default=4, ge=3, le=16)

    # Ignore inbound txs / reject invoices below this USD (≈ USDT) value
    DUST_IGNORE_USD: Decimal = Field(default=Decimal("0.10"))

    # Rough USD marks for dust gate (override via env; not a live oracle)
    PRICE_USD_BTC: Decimal = Field(default=Decimal("95000"))
    PRICE_USD_TON: Decimal = Field(default=Decimal("5"))
    PRICE_USD_SOL: Decimal = Field(default=Decimal("150"))
    PRICE_USD_ETH: Decimal = Field(default=Decimal("3500"))
    PRICE_USD_POL: Decimal = Field(default=Decimal("0.50"))
    PRICE_USD_TRX: Decimal = Field(default=Decimal("0.15"))
    PRICE_USD_XMR: Decimal = Field(default=Decimal("160"))

    # Watch-only receive addresses (testnet or mainnet depending on NETWORK)
    WALLET_BTC: str = ""
    WALLET_XMR: str = ""
    WALLET_TON: str = ""
    WALLET_SOL: str = ""
    WALLET_TRX: str = ""
    WALLET_ETH: str = ""
    WALLET_POLYGON: str = ""
    # Optional token receive overrides (empty → reuse native wallet on that chain)
    WALLET_TON_USDT: str = ""
    WALLET_SOL_USDC: str = ""

    # Token contract / mint overrides (empty → network defaults)
    TOKEN_TON_USDT: str = ""
    TOKEN_SOL_USDC: str = ""

    # Optional RPC overrides (empty → pick from NETWORK defaults)
    RPC_BTC: str = ""
    RPC_ETH: str = ""
    RPC_POLYGON: str = ""
    RPC_TRON: str = ""
    RPC_SOLANA: str = ""
    RPC_TON: str = ""
    RPC_XMR: str = ""
    TON_API_KEY: str = ""

    def rpc_btc(self) -> str:
        if self.RPC_BTC:
            return self.RPC_BTC
        return (
            "https://mempool.space/testnet/api"
            if self.NETWORK == "testnet"
            else "https://mempool.space/api"
        )

    def rpc_solana(self) -> str:
        if self.RPC_SOLANA:
            return self.RPC_SOLANA
        return (
            "https://api.devnet.solana.com"
            if self.NETWORK == "testnet"
            else "https://api.mainnet-beta.solana.com"
        )

    def rpc_ton(self) -> str:
        if self.RPC_TON:
            return self.RPC_TON
        # toncenter testnet
        return (
            "https://testnet.toncenter.com/api/v2"
            if self.NETWORK == "testnet"
            else "https://toncenter.com/api/v2"
        )

    def rpc_eth(self) -> str:
        return self.RPC_ETH or "https://eth.llamarpc.com"

    def rpc_polygon(self) -> str:
        return self.RPC_POLYGON or "https://polygon-rpc.com"

    def rpc_tron(self) -> str:
        return self.RPC_TRON or "https://api.trongrid.io"

    def invoice_ttl_for(self, chain: str) -> int:
        """Seconds to await payment before an invoice expires (per chain)."""
        key = chain.strip().lower()
        by_chain = {
            "bitcoin": self.INVOICE_TTL_BTC,
            "btc": self.INVOICE_TTL_BTC,
            "ton": self.INVOICE_TTL_TON,
            "ton-usdt": self.INVOICE_TTL_TON,
            "solana": self.INVOICE_TTL_SOL,
            "sol": self.INVOICE_TTL_SOL,
            "solana-usdc": self.INVOICE_TTL_SOL,
            "ethereum": self.INVOICE_TTL_ETH,
            "eth": self.INVOICE_TTL_ETH,
            "polygon": self.INVOICE_TTL_POL,
            "pol": self.INVOICE_TTL_POL,
            "tron": self.INVOICE_TTL_TRX,
            "trx": self.INVOICE_TTL_TRX,
            "monero": self.INVOICE_TTL_XMR,
            "xmr": self.INVOICE_TTL_XMR,
        }
        return int(by_chain.get(key, self.INVOICE_TTL_SECONDS))

    def poll_interval_for(self, chain: str) -> int:
        """Seconds between payment-detection polls for a chain."""
        key = chain.strip().lower()
        by_chain = {
            "bitcoin": self.POLL_INTERVAL_BTC,
            "btc": self.POLL_INTERVAL_BTC,
            "ton": self.POLL_INTERVAL_TON,
            "ton-usdt": self.POLL_INTERVAL_TON,
            "solana": self.POLL_INTERVAL_SOL,
            "sol": self.POLL_INTERVAL_SOL,
            "solana-usdc": self.POLL_INTERVAL_SOL,
            "ethereum": self.POLL_INTERVAL_ETH,
            "eth": self.POLL_INTERVAL_ETH,
            "polygon": self.POLL_INTERVAL_POL,
            "pol": self.POLL_INTERVAL_POL,
            "tron": self.POLL_INTERVAL_TRX,
            "trx": self.POLL_INTERVAL_TRX,
            "monero": self.POLL_INTERVAL_XMR,
            "xmr": self.POLL_INTERVAL_XMR,
        }
        return max(1, int(by_chain.get(key, self.POLL_INTERVAL_SECONDS)))

    def ton_usdt_jetton(self) -> str:
        if self.TOKEN_TON_USDT:
            return self.TOKEN_TON_USDT.strip()
        # Tether USD jetton master (mainnet); override for testnet via env
        return "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs"

    def sol_usdc_mint(self) -> str:
        if self.TOKEN_SOL_USDC:
            return self.TOKEN_SOL_USDC.strip()
        if self.NETWORK == "testnet":
            return "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
        return "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    def tonapi_base(self) -> str:
        return (
            "https://testnet.tonapi.io"
            if self.NETWORK == "testnet"
            else "https://tonapi.io"
        )


settings = Settings()
