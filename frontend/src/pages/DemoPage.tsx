import { useEffect, useMemo, useState, type FormEvent } from "react"
import { Link } from "react-router-dom"
import {
  createInvoice,
  fetchConfig,
  fetchGateways,
  getStoredApiKey,
  setStoredApiKey,
  type Gateway,
  type GatewayGroup,
  type PublicConfig,
} from "../api"

export default function DemoPage() {
  const [groups, setGroups] = useState<GatewayGroup[]>([])
  const [gateways, setGateways] = useState<Gateway[]>([])
  const [cfg, setCfg] = useState<PublicConfig | null>(null)
  const [apiKey, setApiKey] = useState(getStoredApiKey())
  const [chain, setChain] = useState("ton")
  const [amount, setAmount] = useState("5.00")
  const [externalRef, setExternalRef] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    void fetchGateways().then((g) => {
      setGateways(g.data)
      setGroups(g.groups || [])
      if (g.data.length && !g.data.some((x) => x.chain === chain)) {
        setChain(g.data[0].chain)
      }
    })
    void fetchConfig().then(setCfg)
  }, [chain])

  const selected = useMemo(
    () => gateways.find((g) => g.chain === chain),
    [gateways, chain],
  )

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError("")
    setStoredApiKey(apiKey)
    try {
      const inv = await createInvoice({
        chain,
        amount,
        external_ref: externalRef || undefined,
        apiKey,
      })
      window.location.href = inv.page_url || `/v1/pay/${inv.id}/page`
    } catch (err) {
      setError(err instanceof Error ? err.message : "create failed")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="shell">
      <header className="brand-row">
        <Link to="/">
          <img className="brand-mark" src="/logo.png" alt="FreedomPay" />
        </Link>
        <div>
          <h1 className="brand-name">Demo</h1>
          <p className="brand-tag">
            Amount in USD · fee {cfg?.service_fee_percent ?? "…"}% · memo{" "}
            {cfg?.memo_length ?? 4} digits
          </p>
        </div>
      </header>

      <form className="panel" onSubmit={(e) => void onSubmit(e)}>
        <label>
          API key
          <input
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="X-API-Key"
            required
          />
        </label>

        <div style={{ marginBottom: "0.95rem" }}>
          <span className="hint" style={{ display: "block", marginBottom: 8 }}>
            Network & currency
          </span>
          <div className="chain-groups">
            {groups.map((g) => (
              <div key={g.id} className="chain-group">
                <div className="chain-group-head">
                  <img className="chain-logo" src={g.logo_url} alt="" />
                  <span className="chain-group-title">{g.name}</span>
                  <span className="chain-group-net">{g.network}</span>
                </div>
                <div className="chips">
                  {g.currencies.map((c) => (
                    <button
                      key={c.chain}
                      type="button"
                      className={`chip${c.chain === chain ? " active" : ""}`}
                      onClick={() => setChain(c.chain)}
                    >
                      {c.currency}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <label>
          Amount USD → {selected?.currency || "…"}
          <input
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            inputMode="decimal"
            required
          />
        </label>

        <label>
          External ref (optional)
          <input
            value={externalRef}
            onChange={(e) => setExternalRef(e.target.value)}
            placeholder="order / payment id"
          />
        </label>

        <div className="btn-row">
          <button className="btn btn-gold" type="submit" disabled={busy}>
            {busy ? "Creating…" : "Create invoice"}
          </button>
          <Link className="btn btn-ghost" to="/">
            Back
          </Link>
        </div>
        {error && <p className="error">{error}</p>}
        <p className="hint">
          Customer pays merchant + fee. On testnet with DEMO_MODE use Simulate
          without an on-chain tx.
        </p>
      </form>
    </div>
  )
}
