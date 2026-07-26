import { Navigate, Route, Routes } from "react-router-dom"
import DemoPage from "./pages/DemoPage"
import EmbedPage from "./pages/EmbedPage"
import HomePage from "./pages/HomePage"
import PayPage from "./pages/PayPage"

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/demo" element={<DemoPage />} />
      <Route path="/pay/:invoiceId" element={<PayPage />} />
      <Route path="/embed" element={<EmbedPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
