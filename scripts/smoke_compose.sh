#!/usr/bin/env bash
# Smoke-test a running FreedomPay Compose stack (frontend :8127, api :8117).
set -euo pipefail

BASE="${FREEDOMPAY_BASE:-http://localhost:8127}"
API_KEY="${FREEDOMPAY_API_KEY:-dev-freedompay}"

echo "== health =="
curl -fsS "$BASE/health" | tee /tmp/fp-health.json
echo

echo "== gateways =="
curl -fsS "$BASE/v1/gateways" | tee /tmp/fp-gateways.json
python3 - <<'PY'
import json
g = json.load(open("/tmp/fp-gateways.json"))
assert g["count"] >= 1, g
print(f"ok: {g['count']} gateway(s): {[x['chain'] for x in g['data']]}")
PY

echo "== create invoice (ton) =="
curl -fsS -X POST "$BASE/v1/invoices" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"chain":"ton","amount":"10","external_ref":"compose-smoke"}' \
  | tee /tmp/fp-invoice.json
python3 - <<'PY'
import json
inv = json.load(open("/tmp/fp-invoice.json"))
assert inv["status"] == "pending", inv
assert inv["memo"], inv
print(f"ok: invoice {inv['id']} memo={inv['memo']}")
open("/tmp/fp-invoice-id.txt","w").write(inv["id"])
PY

INV_ID="$(cat /tmp/fp-invoice-id.txt)"

echo "== pay page =="
curl -fsS -o /dev/null -w "HTTP %{http_code}\n" "$BASE/v1/pay/$INV_ID/page"

echo "== frontend SPA =="
curl -fsS -o /dev/null -w "HTTP %{http_code}\n" "$BASE/"
curl -fsS -o /dev/null -w "HTTP %{http_code}\n" "$BASE/demo"

echo "== simulate pay =="
curl -fsS -X POST "$BASE/v1/invoices/$INV_ID/simulate" \
  -H "X-API-Key: $API_KEY" \
  | tee /tmp/fp-sim.json
python3 - <<'PY'
import json
inv = json.load(open("/tmp/fp-sim.json"))
assert inv["status"] == "confirmed", inv
print(f"ok: confirmed txid={inv['txid']}")
PY

echo
echo "Compose stack looks workable."
