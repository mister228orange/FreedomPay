from __future__ import annotations

from collections import defaultdict

from app.config import settings
from app.gateways.abc import AbstractChainGateway, GatewayInfo
from app.gateways.bitcoin import BitcoinGateway
from app.gateways.ethereum import EthereumGateway
from app.gateways.monero import MoneroGateway
from app.gateways.polygon import PolygonGateway
from app.gateways.solana import SolanaGateway, SolanaUsdcGateway
from app.gateways.ton import TonGateway, TonUsdtGateway
from app.gateways.tron import TronGateway


def all_gateways() -> list[AbstractChainGateway]:
    return [
        BitcoinGateway(),
        TonGateway(),
        TonUsdtGateway(),
        SolanaGateway(),
        SolanaUsdcGateway(),
        EthereumGateway(),
        PolygonGateway(),
        TronGateway(),
        MoneroGateway(),
    ]


def get_available_gateways() -> list[GatewayInfo]:
    """Return enabled payment options (native + tokens) with wallets configured."""
    out: list[GatewayInfo] = []
    for gateway in all_gateways():
        info = gateway.gateway_info()
        if info.address_configured:
            out.append(info)
    return out


def group_gateways(items: list[GatewayInfo]) -> list[dict]:
    """Group available currencies by blockchain for UI catalogs."""
    buckets: dict[str, list[GatewayInfo]] = defaultdict(list)
    order: list[str] = []
    for info in items:
        bid = info.blockchain or info.chain
        if bid not in buckets:
            order.append(bid)
        buckets[bid].append(info)
    groups: list[dict] = []
    for bid in order:
        currencies = buckets[bid]
        head = currencies[0]
        groups.append(
            {
                "id": bid,
                "name": head.blockchain_name or bid.title(),
                "logo_url": head.logo_url,
                "network": head.network,
                "currencies": currencies,
            }
        )
    return groups


def get_checker(chain: str) -> AbstractChainGateway:
    """Resolve a configured chain gateway (alias kept for invoice service)."""
    key = chain.strip().lower().replace("_", "-")
    aliases = {
        "btc": "bitcoin",
        "sol": "solana",
        "usdt": "ton-usdt",
        "usdc": "solana-usdc",
        "ton_usdt": "ton-usdt",
        "solana_usdc": "solana-usdc",
        "sol-usdc": "solana-usdc",
    }
    key = aliases.get(key, key)
    for gateway in all_gateways():
        if gateway.chain == key:
            if not gateway.is_configured():
                raise ValueError(f"Gateway {chain} is not configured (wallet empty)")
            return gateway
    raise ValueError(f"Unknown gateway: {chain}")


def configured_wallet_map() -> dict[str, str]:
    return {
        "bitcoin": settings.WALLET_BTC,
        "ton": settings.WALLET_TON,
        "ton-usdt": settings.WALLET_TON_USDT or settings.WALLET_TON,
        "solana": settings.WALLET_SOL,
        "solana-usdc": settings.WALLET_SOL_USDC or settings.WALLET_SOL,
        "monero": settings.WALLET_XMR,
        "tron": settings.WALLET_TRX,
        "polygon": settings.WALLET_POLYGON or settings.WALLET_ETH,
        "ethereum": settings.WALLET_ETH,
    }
