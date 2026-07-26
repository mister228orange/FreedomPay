# FreedomPay

Non-custodial, build-in crypto merchant acceptor for **BTC / TON / SOL** (optional ETH / POL / TRX / XMR stubs).

Watch-only wallets · testnet-ready · service fee · embeddable checkout widget.

---

## Overview

FreedomPay is a lightweight merchant payment gateway: you create an invoice in USD (or crypto), show the payer an address / memo / QR, and FreedomPay watches the chain until the payment confirms, then hits your webhook.

**What it is**

- Watch-only — private keys never leave your wallets; FreedomPay only observes receive addresses.
- Multi-chain — memo-based (TON, SOL) and amount-dust (BTC, EVM) matching so concurrent invoices do not collide.
- Embeddable — full pay page, HTML fragment, QR SVG, and a drop-in `embed.js` widget.
- Merchant-friendly — service fee, dust gate, testnet `DEMO_MODE` simulate, and a signed webhook callback.

**What it is not**

- Not a custodian or exchange — funds go straight to your configured wallets.
- Not a full fiat processor yet — invoice pricing is USD-marked crypto today; national fiat rails are on the roadmap.
- Not a bot platform yet — HTTP + embed are the integration surface; Telegram / Element adapters are planned.

---

## Advice

- Prefer **memo chains** (TON, SOL) when many users may pay similar amounts; amount-dust on BTC/EVM works but is noisier for the payer.
- Tune **`POLL_INTERVAL_*`** per chain: faster chains (SOL/TON) can poll more often; BTC/XMR can stay slower to ease RPC load.
- Always set a stable `PUBLIC_BASE_URL` in production so `pay_url` / `embed_url` / QR deep-links resolve correctly.
- Keep `API_KEY` and `MERCHANT_WEBHOOK_SECRET` out of the frontend; create invoices from your backend only.
- Start on `NETWORK=testnet` with `DEMO_MODE=true`, verify webhook + `external_ref` flow, then flip to mainnet wallets.
- Treat `PRICE_USD_*` as rough marks for the dust gate — not a live oracle. For tighter FX later, plan for a rate provider (see roadmap).
- Size `DUST_IGNORE_USD` to your product: too low invites spam txs; too high rejects real micropayments.
- One txid confirms one invoice — do not reuse the same on-chain payment across orders.
- When embedding, mount by invoice id after server-side creation rather than putting the API key in public pages for production.

---

## Roadmap

### Near term

- **More cryptocurrencies** — graduate ETH / POL / TRX / XMR stubs to production checkers; add USDT/USDC (and other stables) per chain where memo or amount-matching is reliable.
- **National fiat invoice volume** — accept merchant amounts in local fiat (RUB, EUR, …), convert to crypto at quote time with a clearer rate source, and surface fiat + crypto totals on the pay UI / webhook.

### Messaging adapters

- **Telegram endpoint** — bot API for text bots (create invoice, send pay link / QR as message) and a Mini App surface that reuses the existing pay widget inside Telegram WebApp.
- **Element (Matrix) bots endpoint** — room/DM bot that creates invoices and posts pay links for Element/Matrix communities, same core invoice + webhook model.

### Later

- Live FX / oracle rates instead of static `PRICE_USD_*` marks.
- Stronger multi-tenant merchant keys and per-merchant wallets.
- Optional refund / underpaid / overpaid status hooks beyond simple confirm.

---

## How concurrent invoices are matched (same amount problem)

One shared receive address cannot tell two identical payments apart by amount alone. FreedomPay uses **two identity signals**:

| Chain type | Identity | How |
|---|---|---|
| **Memo chains** (TON, SOL, …) | Unique **memo / comment** | Each invoice gets a random hex memo. The payer must include it; the poller matches `memo` (+ amount). |
| **Amount-only chains** (BTC, EVM natives) | Unique **pay amount** | After merchant amount + service fee, a stable dust suffix from `sha256(invoice_id)` is added. If that total is already used by an open invoice, it bumps by 1 subunit until free. |

Additionally:

- A **txid can confirm only one invoice** (claimed once).
- Transfers below **`DUST_IGNORE_USD` (default `$0.10` ≈ USDT)** are ignored as junk and cannot create invoices.

Customer always pays `amount` = merchant + fee (+ unique dust on amount-only chains). Merchant webhook receives `amount_merchant`, `amount_fee`, and `amount`.

---

## Import into your project

### Option A — Docker Compose (recommended)

```bash
cd FreedomPay
docker compose up --build -d
./scripts/smoke_compose.sh
```

Services: **postgres**, **redis**, **api** (FastAPI), **worker** + **scheduler** (Taskiq), **frontend** (nginx SPA on http://localhost:8127). API also on http://localhost:8117.

Copy `.env.docker` for Compose demo wallets / API key, or override via environment.

### Option B — sibling folder + your own Compose

```text
your-monorepo/
  your-backend/
  FreedomPay/          ← this repo (clone next to your app)
  compose.yml
```

```bash
cd /path/to/parent
git clone https://github.com/mister228orange/FreedomPay.git
cp FreedomPay/.env.example FreedomPay/.env
# fill WALLET_*, API_KEY, MERCHANT_WEBHOOK_*
```

Example Compose service (SQLite + embedded Taskiq):

```yaml
services:
  freedompay:
    build:
      context: ../FreedomPay
      dockerfile: Dockerfile
      target: api
    ports:
      - "8090:8080"
    env_file:
      - ../FreedomPay/.env
    environment:
      - PUBLIC_BASE_URL=https://pay.example.com
      - MERCHANT_WEBHOOK_URL=http://backend:8000/api/v1/payments/webhook/freedompay
      - MERCHANT_WEBHOOK_SECRET=${FREEDOMPAY_WEBHOOK_SECRET}
      - API_KEY=${FREEDOMPAY_API_KEY}
      - NETWORK=testnet
      - DEMO_MODE=true
      - SERVICE_FEE_PERCENT=1.5
      - DUST_IGNORE_USD=0.10
      - TASKIQ_EMBEDDED=true
      - REDIS_URL=
    volumes:
      - freedompay-data:/app/data

volumes:
  freedompay-data:
```

### Option C — HTTP API only (any stack)

1. Run FreedomPay (`uvicorn` or Docker).
2. Create invoice from your backend:

```http
POST /v1/invoices
X-API-Key: <API_KEY>
Content-Type: application/json

{
  "chain": "ton",
  "amount": "12.50",
  "external_ref": "<your-payment-id>",
  "callback_url": "https://your.app/webhooks/freedompay"
}
```

3. Show user `pay_url` / `embed_url` / address+memo from the response.
4. On confirm, FreedomPay POSTs to your webhook with header `X-FreedomPay-Secret`.

Minimal webhook handler (pseudo):

```python
# verify X-FreedomPay-Secret
# if status == "confirmed": mark payment external_ref as paid (txid = body.txid)
```

### Option D — Embed widget on any site

```html
<div id="freedompay"></div>
<script src="https://pay.example.com/embed.js"
  data-api-key="YOUR_KEY"
  data-chain="ton"
  data-amount="1.5"
  data-external-ref="order-42"
  data-target="#freedompay"></script>
```

Or mount an existing invoice: `data-invoice="<uuid>"`.

---

## Pay UI endpoints

| Endpoint | Returns |
|---|---|
| `GET /v1/pay/{id}/page?size=sm\|md\|lg` | Full HTML page (QR + copy fields) |
| `GET /v1/pay/{id}/div?size=sm\|md\|lg&width=360` | Only the widget `<div>` fragment |
| `GET /v1/pay/{id}/qr.svg` | QR SVG (BIP21 / ton:// / solana:) |

Invoice amounts are **USD by default** (`amount_unit: "usd"`), rounded **up** to **10¢** (`USD_PRECISION`), then converted to native crypto with **ceil**. Short memos use `MEMO_LENGTH` (default **4**).

```bash
# Embed only the div on any site
curl "http://localhost:8090/v1/pay/<id>/div?size=md"
```

## Quick start (local)

```bash
cd FreedomPay
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
cd frontend && npm install && npm run build && cd ..
uvicorn app.main:app --reload --port 8090
```

- UI: http://localhost:8090  
- Demo: http://localhost:8090/demo  
- API: http://localhost:8090/docs  

On testnet with `DEMO_MODE=true`, use **Simulate** on the pay page without a real chain tx.

```bash
pytest -q
```

---

## Env

| Variable | Meaning |
|---|---|
| `API_KEY` | Merchant API key (`X-API-Key`) |
| `NETWORK` | `testnet` \| `mainnet` |
| `DEMO_MODE` | Allow `/simulate` on testnet |
| `SERVICE_FEE_PERCENT` | Commission on merchant amount |
| `DUST_IGNORE_USD` | Ignore txs / reject invoices below this USD (default `0.10`) |
| `PRICE_USD_*` | Rough marks for dust gate (not a live oracle) |
| `WALLET_BTC` / `WALLET_TON` / `WALLET_SOL` | Watch-only receive addresses |
| `MERCHANT_WEBHOOK_URL` / `MERCHANT_WEBHOOK_SECRET` | Paid callback |
| `INVOICE_TTL_SECONDS` | Default payment await window (seconds) |
| `INVOICE_TTL_BTC` / `_TON` / `_SOL` / … | Per-chain payment await override |
| `POLL_INTERVAL_SECONDS` | Default chain poll cadence (seconds) |
| `POLL_INTERVAL_BTC` / `_TON` / `_SOL` / … | Per-chain poll interval override |
| `TASKIQ_EMBEDDED` | Run Taskiq scheduler inside the API process (`true` only without Redis) |
| `REDIS_URL` | Redis for Taskiq worker/scheduler (empty → InMemoryBroker) |
| `DATABASE_URL` | SQLite or `postgresql+psycopg://…` |

See `.env.example`.

---

## FirstLayer note

FreedomPay lives as a **standalone repo** under `Documents/FreedomPay` (not nested inside FirstLayer). Wire it as a sibling Compose service (`context: ../FreedomPay`) and keep the backend webhook at `POST /api/v1/payments/webhook/freedompay`.
