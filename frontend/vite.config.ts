import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Dev: Vite serves frontend at 5173 and proxies /api to the FastAPI backend
//      at 8765 so the SPA can call the API without CORS/origin friction.
// Build: emits to ../backend/fonliman/static so the Docker image's Python
//      stage can serve it directly without copying.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: path.resolve(__dirname, "../backend/fonliman/static"),
    emptyOutDir: true,
  },
});
