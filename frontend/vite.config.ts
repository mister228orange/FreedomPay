import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "../app/static/web",
    emptyOutDir: true,
  },
  server: {
    port: 5179,
    proxy: {
      "/v1": "http://localhost:8090",
      "/health": "http://localhost:8090",
      "/static": "http://localhost:8090",
    },
  },
})
