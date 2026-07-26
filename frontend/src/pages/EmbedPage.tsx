import { useSearchParams } from "react-router-dom"
import { useEffect, useState } from "react"
import { fetchConfig } from "../api"
import PayPanel from "../components/PayPanel"

export default function EmbedPage() {
  const [params] = useSearchParams()
  const invoiceId = params.get("invoice") || ""
  const [demo, setDemo] = useState(false)

  useEffect(() => {
    void fetchConfig().then((c) => setDemo(c.demo_mode))
  }, [])

  if (!invoiceId) {
    return (
      <div className="embed-body">
        <div className="panel pay-card">
          <p className="hint">Укажите ?invoice=UUID</p>
        </div>
      </div>
    )
  }

  return (
    <div className="embed-body">
      <PayPanel invoiceId={invoiceId} compact showSimulate={demo} />
    </div>
  )
}
