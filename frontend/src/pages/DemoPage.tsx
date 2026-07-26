import { useEffect, useMemo, useState, type FormEvent } from "react"
import { Link } from "react-router-dom"
import {
  createInvoice,
  fetchConfig,
  fetchGateways,
  getStoredApiKey,
  setStoredApiKey,
  type Gateway,
  type PublicConfig,
} from "../api"

export default function DemoPage() {
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
            Сумма в USD (ceil 10¢) · fee {cfg?.service_fee_percent ?? "…"}% ·
            memo {cfg?.memo_length ?? 4} chars
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

        <div style={{ marginBottom: "0.85rem" }}>
          <span className="hint" style={{ display: "block", marginBottom: 8 }}>
            Цепочка
          </span>
          <div className="chips">
            {gateways.map((g) => (
              <button
                key={g.chain}
                type="button"
                className={`chip${g.chain === chain ? " active" : ""}`}
                onClick={() => setChain(g.chain)}
              >
                {g.name} ({g.currency})
              </button>
            ))}
          </div>
        </div>

        <label>
          Сумма в USD (конвертация → {selected?.currency || "…"}, округление вверх)
          <input
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            inputMode="decimal"
            required
          />
        </label>

        <label>
          External ref (опционально, payment id в FirstLayer)
          <input
            value={externalRef}
            onChange={(e) => setExternalRef(e.target.value)}
            placeholder="uuid платежа"
          />
        </label>

        <div className="btn-row">
          <button className="btn btn-gold" type="submit" disabled={busy}>
            {busy ? "Создание…" : "Создать счёт"}
          </button>
          <Link className="btn btn-ghost" to="/">
            Назад
          </Link>
        </div>
        {error && <p className="error">{error}</p>}
        <p className="hint">
          Клиент платит merchant + комиссия. На testnet с DEMO_MODE можно
          подтвердить через Simulate без реальной транзакции.
        </p>
      </form>
    </div>
  )
}
