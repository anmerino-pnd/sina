import { defineConfig } from "vite";
import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// SINA SPA — servida por FastAPI en el mismo origen (base "/").
// En dev, Vite corre en :5173 y proxya /api al backend FastAPI en :8000,
// espejando el setup de producción (mismo origen, sin CORS).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      output: {
        // Aísla el vendor pesado para mantener el chunk de la landing liviano.
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (id.includes("@tanstack")) return "query";
            if (/[\\/](react|react-dom|react-router|scheduler)[\\/]/.test(id))
              return "vendor";
          }
        },
      },
    },
  },
});
