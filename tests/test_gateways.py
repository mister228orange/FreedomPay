from decimal import Decimal

from app.config import settings
from app.pricing import ceil_to_usd_step, is_dust, usd_to_native


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["message"] == "ok"


def test_dust_threshold_usd():
    assert is_dust("USDT", Decimal("0.09")) is True
    assert is_dust("USDT", Decimal("0.10")) is False


def test_ceil_usd_to_dime():
    assert ceil_to_usd_step(Decimal("1.01")) == Decimal("1.10")
    assert ceil_to_usd_step(Decimal("1.00")) == Decimal("1.00")
    assert ceil_to_usd_step(Decimal("0.11")) == Decimal("0.20")


def test_get_available_gateway_filters_empty_wallets(client, monkeypatch):
    monkeypatch.setattr(settings, "WALLET_BTC", "tb1qtest")
    monkeypatch.setattr(settings, "WALLET_ETH", "")
    monkeypatch.setattr(settings, "WALLET_XMR", "")
    monkeypatch.setattr(settings, "WALLET_TON", "EQ_test")
    monkeypatch.setattr(settings, "WALLET_SOL", "SoLTest111")
    monkeypatch.setattr(settings, "WALLET_TRX", "")
    monkeypatch.setattr(settings, "WALLET_POLYGON", "")
    monkeypatch.setattr(settings, "NETWORK", "testnet")
    monkeypatch.setattr(settings, "SERVICE_FEE_PERCENT", Decimal("1.5"))

    r = client.get("/v1/gateways")
    assert r.status_code == 200
    body = r.json()
    chains = {g["chain"] for g in body["data"]}
    assert chains == {"bitcoin", "ton", "ton-usdt", "solana", "solana-usdc"}
    assert body["default_fiat"] == "USD"
    assert Decimal(body["usd_precision"]) == Decimal("0.10")
    assert body["memo_length"] == 4
    assert "groups" in body
    group_ids = {g["id"] for g in body["groups"]}
    assert {"bitcoin", "ton", "solana"} <= group_ids
    for g in body["data"]:
        assert "web" in g["exits"]
        assert "embed" in g["exits"]
        assert g["payment_ttl_seconds"] > 0
        assert g["poll_interval_seconds"] > 0
        assert g["logo_url"]
        assert g["blockchain"]


def test_ton_usdt_invoice_and_qr(client, monkeypatch):
    monkeypatch.setattr(settings, "WALLET_TON", "EQ_demo_ton")
    monkeypatch.setattr(settings, "API_KEY", "test-key")
    monkeypatch.setattr(settings, "SERVICE_FEE_PERCENT", Decimal("0"))
    monkeypatch.setattr(settings, "DUST_IGNORE_USD", Decimal("0.10"))
    monkeypatch.setattr(settings, "MERCHANT_WEBHOOK_URL", "")
    monkeypatch.setattr(settings, "NETWORK", "testnet")

    r = client.post(
        "/v1/invoices",
        headers={"X-API-Key": "test-key"},
        json={"chain": "ton-usdt", "amount": "10"},
    )
    assert r.status_code == 200, r.text
    inv = r.json()
    assert inv["currency"] == "USDT"
    assert inv["chain"] == "ton-usdt"
    assert inv["memo"]
    assert "jetton=" in inv["qr_payload"]
    assert Decimal(inv["amount"]) == Decimal("10.00")


def test_per_chain_poll_interval_config():
    assert settings.poll_interval_for("bitcoin") == settings.POLL_INTERVAL_BTC
    assert settings.poll_interval_for("ton") == settings.POLL_INTERVAL_TON
    assert settings.poll_interval_for("solana") == settings.POLL_INTERVAL_SOL
    assert settings.poll_interval_for("unknown-chain") == settings.POLL_INTERVAL_SECONDS


def test_per_chain_payment_ttl(client, monkeypatch):
    monkeypatch.setattr(settings, "WALLET_BTC", "tb1qtest")
    monkeypatch.setattr(settings, "WALLET_TON", "EQ_test")
    monkeypatch.setattr(settings, "WALLET_SOL", "")
    monkeypatch.setattr(settings, "WALLET_ETH", "")
    monkeypatch.setattr(settings, "WALLET_XMR", "")
    monkeypatch.setattr(settings, "WALLET_TRX", "")
    monkeypatch.setattr(settings, "WALLET_POLYGON", "")
    monkeypatch.setattr(settings, "INVOICE_TTL_BTC", 3600)
    monkeypatch.setattr(settings, "INVOICE_TTL_TON", 1200)
    monkeypatch.setattr(settings, "API_KEY", "test-key")
    monkeypatch.setattr(settings, "SERVICE_FEE_PERCENT", Decimal("0"))
    monkeypatch.setattr(settings, "DUST_IGNORE_USD", Decimal("0.10"))
    monkeypatch.setattr(settings, "PRICE_USD_BTC", Decimal("95000"))
    monkeypatch.setattr(settings, "PRICE_USD_TON", Decimal("5"))
    monkeypatch.setattr(settings, "MERCHANT_WEBHOOK_URL", "")

    gateways = client.get("/v1/gateways").json()["data"]
    by_chain = {g["chain"]: g["payment_ttl_seconds"] for g in gateways}
    assert by_chain["bitcoin"] == 3600
    assert by_chain["ton"] == 1200

    from app.timeutil import unix_now

    before = unix_now()
    r = client.post(
        "/v1/invoices",
        headers={"X-API-Key": "test-key"},
        json={"chain": "bitcoin", "amount": "20"},
    )
    assert r.status_code == 200, r.text
    inv = r.json()
    assert inv["expires_at"] - inv["created_at"] == 3600
    assert inv["expires_at"] >= before + 3600


def test_invoice_usd_fee_memo_and_page(client, monkeypatch):
    monkeypatch.setattr(settings, "WALLET_TON", "EQ_demo_ton")
    monkeypatch.setattr(settings, "WALLET_BTC", "tb1qdemo")
    monkeypatch.setattr(settings, "WALLET_SOL", "SoLDemo")
    monkeypatch.setattr(settings, "NETWORK", "testnet")
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    monkeypatch.setattr(settings, "SERVICE_FEE_PERCENT", Decimal("1.5"))
    monkeypatch.setattr(settings, "API_KEY", "test-key")
    monkeypatch.setattr(settings, "MERCHANT_WEBHOOK_URL", "")
    monkeypatch.setattr(settings, "DUST_IGNORE_USD", Decimal("0.10"))
    monkeypatch.setattr(settings, "PRICE_USD_TON", Decimal("5"))
    monkeypatch.setattr(settings, "MEMO_LENGTH", 4)
    monkeypatch.setattr(settings, "USD_PRECISION", Decimal("0.10"))

    # $10 USD → fee 1.5% = 0.15 → ceil 0.20 → total $10.20
    r = client.post(
        "/v1/invoices",
        headers={"X-API-Key": "test-key"},
        json={"chain": "ton", "amount": "10", "external_ref": "order-1"},
    )
    assert r.status_code == 200, r.text
    inv = r.json()
    assert inv["fiat"] == "USD"
    assert Decimal(inv["amount_usd"]) == Decimal("10.20")
    assert Decimal(inv["amount_usd_fee"]) == Decimal("0.20")
    assert inv["memo"] and len(inv["memo"]) == 4
    assert inv["memo"].isdigit()
    assert inv["page_url"]
    assert inv["div_url"]
    assert inv["qr_url"]
    assert inv["qr_payload"].startswith("ton://")

    page = client.get(f"/v1/pay/{inv['id']}/page?size=md")
    assert page.status_code == 200
    assert "text/html" in page.headers["content-type"]
    assert "FreedomPay" in page.text
    assert inv["memo"] in page.text
    assert "fp-copy" in page.text

    div = client.get(f"/v1/pay/{inv['id']}/div?size=sm")
    assert div.status_code == 200
    assert 'class="fp-widget"' in div.text
    assert "<!doctype html>" not in div.text.lower()

    qr = client.get(f"/v1/pay/{inv['id']}/qr.svg")
    assert qr.status_code == 200
    assert "svg" in qr.headers["content-type"]

    sim = client.post(
        f"/v1/invoices/{inv['id']}/simulate",
        headers={"X-API-Key": "test-key"},
    )
    assert sim.status_code == 200
    assert sim.json()["status"] == "confirmed"


def test_reject_dust_invoice(client, monkeypatch):
    monkeypatch.setattr(settings, "WALLET_TON", "EQ_demo_ton")
    monkeypatch.setattr(settings, "API_KEY", "test-key")
    monkeypatch.setattr(settings, "DUST_IGNORE_USD", Decimal("0.10"))
    r = client.post(
        "/v1/invoices",
        headers={"X-API-Key": "test-key"},
        json={"chain": "ton", "amount": "0.05"},
    )
    assert r.status_code == 400
    assert "dust" in r.json()["detail"].lower()


def test_btc_unique_amounts_for_parallel_invoices(client, monkeypatch):
    monkeypatch.setattr(settings, "WALLET_BTC", "tb1qdemo")
    monkeypatch.setattr(settings, "API_KEY", "test-key")
    monkeypatch.setattr(settings, "SERVICE_FEE_PERCENT", Decimal("0"))
    monkeypatch.setattr(settings, "DUST_IGNORE_USD", Decimal("0.10"))
    monkeypatch.setattr(settings, "PRICE_USD_BTC", Decimal("95000"))
    monkeypatch.setattr(settings, "MERCHANT_WEBHOOK_URL", "")

    amounts = set()
    for _ in range(3):
        r = client.post(
            "/v1/invoices",
            headers={"X-API-Key": "test-key"},
            json={"chain": "bitcoin", "amount": "20"},  # $20 USD
        )
        assert r.status_code == 200, r.text
        inv = r.json()
        assert inv["memo"] is None
        amounts.add(inv["amount"])
    assert len(amounts) == 3


def test_usd_to_native_rounds_up():
    # $1 / $5 = 0.2 exactly
    assert usd_to_native("TON", Decimal("1.00"), 9) == Decimal("0.200000000")
    # slightly above step needs ceil on native after usd ceil
    n = usd_to_native("TON", Decimal("1.10"), 9)
    assert n >= Decimal("0.22")


def test_embed_js_served(client):
    r = client.get("/embed.js")
    assert r.status_code == 200
    assert "FreedomPay" in r.text
