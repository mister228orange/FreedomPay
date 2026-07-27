import { Link } from "react-router-dom"
import { useEffect, useState } from "react"
import {
  fetchConfig,
  fetchGateways,
  type GatewayGroup,
  type PublicConfig,
} from "../api"

export default function HomePage() {
  const [groups, setGroups] = useState<GatewayGroup[]>([])
  const [cfg, setCfg] = useState<PublicConfig | null>(null)

  useEffect(() => {
    void fetchGateways().then((g) => setGroups(g.groups || []))
    void fetchConfig().then(setCfg)
  }, [])

  const snippet = `<div id="freedompay"></div>
<script src="${cfg?.public_base_url || ""}/embed.js"
  data-api-key="YOUR_KEY"
  data-chain="ton-usdt"
  data-amount="10"
  data-target="#freedompay"></script>`

  return (
    <div className="shell">
      <header className="brand-row">
        <img className="brand-mark" src="/logo.png" alt="FreedomPay" />
        <div>
          <h1 className="brand-name">FreedomPay</h1>
          <p className="brand-tag">
            Non-custodial crypto payments · grey / yellow checkout
          </p>
        </div>
      </header>

      <div className="grid two">
        <section className="panel">
          <h2>Currencies</h2>
          {groups.length === 0 ? (
            <p className="hint">
              No wallets configured. Set WALLET_BTC / WALLET_TON / WALLET_SOL in
              `.env`.
            </p>
          ) : (
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
                      <span key={c.chain} className="chip active">
                        {c.currency}
                        {c.is_token ? " · token" : ""}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
          <p className="hint">
            Network: <strong>{cfg?.network ?? "…"}</strong>
            {" · "}
            fee: <strong>{cfg?.service_fee_percent ?? "…"}%</strong>
            {cfg?.demo_mode ? " · demo simulate on" : ""}
          </p>
          <div className="btn-row">
            <Link className="btn btn-gold" to="/demo">
              Open demo
            </Link>
            <a className="btn btn-ghost" href="/docs">
              API docs
            </a>
          </div>
        </section>

        <section className="panel">
          <h2>Embed</h2>
          <p className="hint">
            Drop-in script creates an invoice and mounts checkout on any site.
          </p>
          <pre className="snippet">{snippet}</pre>
        </section>
      </div>
    </div>
  )
}
