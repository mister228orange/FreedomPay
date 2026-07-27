import { useEffect, useState } from "react"
import {
  checkInvoice,
  fetchInvoicePublic,
  formatUnixLocal,
  getStoredApiKey,
  simulateInvoice,
  type Invoice,
} from "../api"

type Props = {
  invoiceId: string
  compact?: boolean
  showSimulate?: boolean
}

export default function PayPanel({
  invoiceId,
  compact = false,
  showSimulate = false,
}: Props) {
  const [invoice, setInvoice] = useState<Invoice | null>(null)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState("")
  const apiKey = getStoredApiKey()

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const inv = await fetchInvoicePublic(invoiceId)
        if (alive) setInvoice(inv)
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : "Ошибка загрузки")
      }
    }
    void load()
    const t = window.setInterval(() => {
      void load()
    }, 8000)
    return () => {
      alive = false
      window.clearInterval(t)
    }
  }, [invoiceId])

  async function onCheck() {
    if (!apiKey) {
      setError("Нужен API key (страница Demo)")
      return
    }
    setBusy(true)
    setError("")
    try {
      setInvoice(await checkInvoice(invoiceId, apiKey))
    } catch (e) {
      setError(e instanceof Error ? e.message : "check failed")
    } finally {
      setBusy(false)
    }
  }

  async function onSimulate() {
    if (!apiKey) {
      setError("Нужен API key (страница Demo)")
      return
    }
    setBusy(true)
    setError("")
    try {
      setInvoice(await simulateInvoice(invoiceId, apiKey))
    } catch (e) {
      setError(e instanceof Error ? e.message : "simulate failed")
    } finally {
      setBusy(false)
    }
  }

  async function copy(label: string, text: string) {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(label)
      window.setTimeout(() => setCopied(""), 900)
    } catch {
      /* ignore */
    }
  }

  if (!invoice) {
    return (
      <div className="panel pay-card">
        <p className="hint">{error || "Загрузка счёта…"}</p>
      </div>
    )
  }

  const row = (label: string, value: string, copyKey: string) => (
    <div key={copyKey}>
      <span>{label}</span>
      <div style={{ display: "flex", gap: "0.5rem", alignItems: "flex-start" }}>
        <code style={{ flex: 1 }}>{value}</code>
        <button
          type="button"
          className="btn btn-ghost"
          style={{ padding: "0.4rem 0.65rem", fontSize: "0.75rem" }}
          onClick={() => void copy(copyKey, value)}
        >
          {copied === copyKey ? "OK" : "Copy"}
        </button>
      </div>
    </div>
  )

  return (
    <div className={`panel pay-card${compact ? " compact" : ""}`}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          marginBottom: "1rem",
        }}
      >
        <img
          className={`logo-mini${invoice.status === "pending" ? " live" : ""}`}
          src="/logo.png"
          alt=""
        />
        <div>
          <strong style={{ color: "var(--yellow-dim)", letterSpacing: "0.02em" }}>
            FreedomPay
          </strong>
          <div className={`status ${invoice.status}`}>{invoice.status}</div>
        </div>
      </div>

      <div style={{ textAlign: "center", marginBottom: "1rem" }}>
        <img
          src={invoice.qr_url || `/v1/pay/${invoice.id}/qr.svg`}
          alt="Payment QR"
          width={compact ? 140 : 180}
          height={compact ? 140 : 180}
          style={{
            background: "#fff",
            borderRadius: 6,
            padding: 8,
            border: "1px solid #333",
          }}
        />
        <p className="hint">Scan QR or copy fields into your wallet</p>
      </div>

      <div className="meta">
        {row(
          "USD (ceil 10¢, fee included)",
          `${invoice.amount_usd} USD`,
          "usd",
        )}
        {row(
          `Send exactly · ${invoice.currency}`,
          invoice.amount,
          "amount",
        )}
        {row(`Address · ${invoice.chain}`, invoice.address, "address")}
        {invoice.memo &&
          row("Memo / comment (обязательно)", invoice.memo, "memo")}
        {!compact &&
          row("Service fee (USD)", `${invoice.amount_usd_fee} USD`, "fee")}
        <div>
          <span>Created</span>
          <code>{formatUnixLocal(invoice.created_at)}</code>
        </div>
        <div>
          <span>Expires</span>
          <code>{formatUnixLocal(invoice.expires_at)}</code>
        </div>
        {invoice.paid_at != null && (
          <div>
            <span>Paid</span>
            <code>{formatUnixLocal(invoice.paid_at)}</code>
          </div>
        )}
        {invoice.txid && (
          <div>
            <span>Tx</span>
            <code>{invoice.txid}</code>
          </div>
        )}
      </div>

      <div className="btn-row">
        <a className="btn btn-gold" href={invoice.page_url || `/v1/pay/${invoice.id}/page`}>
          Full page
        </a>
        <button
          type="button"
          className="btn btn-ghost"
          disabled={busy}
          onClick={() => void onCheck()}
        >
          Проверить
        </button>
        {showSimulate && (
          <button
            type="button"
            className="btn btn-ghost"
            disabled={busy || invoice.status === "confirmed"}
            onClick={() => void onSimulate()}
          >
            Simulate (testnet)
          </button>
        )}
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  )
}
