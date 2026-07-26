import { Link } from "react-router-dom"
import { useEffect, useState } from "react"
import { fetchConfig, fetchGateways, type Gateway, type PublicConfig } from "../api"

export default function HomePage() {
  const [gateways, setGateways] = useState<Gateway[]>([])
  const [cfg, setCfg] = useState<PublicConfig | null>(null)

  useEffect(() => {
    void fetchGateways().then((g) => setGateways(g.data))
    void fetchConfig().then(setCfg)
  }, [])

  const snippet = `<div id="freedompay"></div>
<script src="${cfg?.public_base_url || "http://localhost:8090"}/embed.js"
  data-api-key="YOUR_KEY"
  data-chain="ton"
  data-amount="1.5"
  data-target="#freedompay"></script>`

  return (
    <div className="shell">
      <header className="brand-row">
        <img className="brand-mark live" src="/logo.png" alt="FreedomPay" />
        <div>
          <h1 className="brand-name">FreedomPay</h1>
          <p className="brand-tag">
            Crypto acceptor · BTC / TON / SOL · commission-aware invoices
          </p>
        </div>
      </header>

      <div className="grid two">
        <section className="panel">
          <h2>Доступные шлюзы</h2>
          {gateways.length === 0 ? (
            <p className="hint">
              Нет настроенных кошельков. Заполните WALLET_BTC / WALLET_TON /
              WALLET_SOL в `.env` (testnet).
            </p>
          ) : (
            <div className="chips">
              {gateways.map((g) => (
                <span key={g.chain} className="chip active">
                  {g.currency} · {g.network}
                </span>
              ))}
            </div>
          )}
          <p className="hint">
            Сеть: <strong>{cfg?.network ?? "…"}</strong>
            {" · "}
            комиссия сервиса:{" "}
            <strong>{cfg?.service_fee_percent ?? "…"}%</strong>
            {cfg?.demo_mode ? " · DEMO simulate включён" : ""}
          </p>
          <div className="btn-row">
            <Link className="btn btn-gold" to="/demo">
              Открыть demo
            </Link>
            <a className="btn btn-ghost" href="/docs">
              API docs
            </a>
          </div>
        </section>

        <section className="panel">
          <h2>Встраиваемый виджет</h2>
          <p className="hint">
            Один скрипт вставляет iframe-checkout на любой сайт и создаёт счёт
            через API.
          </p>
          <pre className="snippet">{snippet}</pre>
        </section>
      </div>
    </div>
  )
}
