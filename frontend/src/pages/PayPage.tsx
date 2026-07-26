import { Link, useParams } from "react-router-dom"
import { useEffect, useState } from "react"
import { fetchConfig } from "../api"
import PayPanel from "../components/PayPanel"

export default function PayPage() {
  const { invoiceId = "" } = useParams()
  const [demo, setDemo] = useState(false)

  useEffect(() => {
    void fetchConfig().then((c) => setDemo(c.demo_mode))
  }, [])

  return (
    <div className="shell">
      <header className="brand-row">
        <Link to="/">
          <img className="brand-mark" src="/logo.png" alt="FreedomPay" />
        </Link>
        <div>
          <h1 className="brand-name">Оплата</h1>
          <p className="brand-tag">Отправьте точную сумму на адрес ниже</p>
        </div>
      </header>
      <PayPanel invoiceId={invoiceId} showSimulate={demo} />
    </div>
  )
}
