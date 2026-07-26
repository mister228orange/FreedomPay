from __future__ import annotations

from app.config import settings
from app.gateways.abc import AbstractChainGateway, GatewayInfo
from app.gateways.bitcoin import BitcoinGateway
from app.gateways.ethereum import EthereumGateway
from app.gateways.monero import MoneroGateway
from app.gateways.polygon import PolygonGateway
from app.gateways.solana import SolanaGateway
from app.gateways.ton import TonGateway
from app.gateways.tron import TronGateway


def all_gateways() -> list[AbstractChainGateway]:
    return [
        BitcoinGateway(),
        MoneroGateway(),
        TonGateway(),
        SolanaGateway(),
        TronGateway(),
        PolygonGateway(),
        EthereumGateway(),
    ]


def get_available_gateways() -> list[GatewayInfo]:
    """Return enabled chains with native currency + supported frontend exits."""
    out: list[GatewayInfo] = []
    for gateway in all_gateways():
        info = gateway.gateway_info()
        if info.address_configured:
            out.append(info)
    return out


def get_checker(chain: str) -> AbstractChainGateway:
    """Resolve a configured chain gateway (alias kept for invoice service)."""
    key = chain.strip().lower()
    for gateway in all_gateways():
        if gateway.chain == key:
            if not gateway.is_configured():
                raise ValueError(f"Gateway {chain} is not configured (wallet empty)")
            return gateway
    raise ValueError(f"Unknown gateway: {chain}")


def configured_wallet_map() -> dict[str, str]:
    return {
        "bitcoin": settings.WALLET_BTC,
        "monero": settings.WALLET_XMR,
        "ton": settings.WALLET_TON,
        "solana": settings.WALLET_SOL,
        "tron": settings.WALLET_TRX,
        "polygon": settings.WALLET_POLYGON or settings.WALLET_ETH,
        "ethereum": settings.WALLET_ETH,
    }
