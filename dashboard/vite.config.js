import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Every API path is proxied to the FastAPI app, so the dashboard is same-origin
// in development and needs no base-URL configuration.
const API_PATHS = ["/alerts", "/health", "/metrics", "/admin", "/orders", "/products", "/notifications"];

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      API_PATHS.map((p) => [p, { target: "http://127.0.0.1:8000", changeOrigin: true }])
    ),
  },
});
