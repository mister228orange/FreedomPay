export type Gateway = {
  chain: string
  currency: string
  name: string
  decimals: number
  min_confirmations: number
  supports_memo: boolean
  network: string
  exits: string[]
}

export type Invoice = {
  id: string
  chain: string
  currency: string
  network: string
  fiat: string
  amount_usd: string
  amount_usd_fee: string
  amount_merchant: string
  amount_fee: string
  amount: string
  address: string
  memo: string | null
  status: string
  external_ref: string | null
  txid: string | null
  confirmations: number
  created_at: number
  expires_at: number
  paid_at: number | null
  exits: Record<string, string>
  pay_url: string
  embed_url: string
  page_url: string
  div_url: string
  qr_url: string
  qr_payload: string
}

export type PublicConfig = {
  network: string
  demo_mode: boolean
  service_fee_percent: string
  dust_ignore_usd?: string
  default_fiat?: string
  usd_precision?: string
  memo_length?: number
  public_base_url: string
}

const API_KEY_STORAGE = "fp_api_key"

export function getStoredApiKey(): string {
  return localStorage.getItem(API_KEY_STORAGE) || ""
}

export function setStoredApiKey(key: string) {
  localStorage.setItem(API_KEY_STORAGE, key)
}

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) {
    const text = await r.text()
    throw new Error(text || `HTTP ${r.status}`)
  }
  return r.json() as Promise<T>
}

export function fetchGateways() {
  return json<{
    data: Gateway[]
    count: number
    network: string
    service_fee_percent: string
    default_fiat?: string
    usd_precision?: string
    memo_length?: number
  }>("/v1/gateways")
}

export function fetchConfig() {
  return json<PublicConfig>("/v1/config/public")
}

export function fetchInvoicePublic(id: string) {
  return json<Invoice>(`/v1/public/invoices/${id}`)
}

export function createInvoice(body: {
  chain: string
  amount: string
  external_ref?: string
  apiKey: string
}) {
  return json<Invoice>("/v1/invoices", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": body.apiKey,
    },
    body: JSON.stringify({
      chain: body.chain,
      amount: body.amount,
      amount_unit: "usd",
      external_ref: body.external_ref || null,
    }),
  })
}

export function simulateInvoice(id: string, apiKey: string) {
  return json<Invoice>(`/v1/invoices/${id}/simulate`, {
    method: "POST",
    headers: { "X-API-Key": apiKey },
  })
}

export function checkInvoice(id: string, apiKey: string) {
  return json<Invoice>(`/v1/invoices/${id}/check`, {
    method: "POST",
    headers: { "X-API-Key": apiKey },
  })
}

/** Russian locale: дд.мм.гггг, чч:мм */
export function formatUnixRu(ts: number | null | undefined): string {
  if (!ts) return "—"
  return new Date(ts * 1000).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}
