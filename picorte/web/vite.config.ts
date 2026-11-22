/// <reference types="vitest/config" />
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const raizRepo = fileURLToPath(new URL("../..", import.meta.url));
const backend = "http://127.0.0.1:8770";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    assetsInlineLimit: 0, // a CSP do backend não aceita data: em imagem nem fonte
    modulePreload: { polyfill: false }, // sem script inline
  },
  server: {
    port: 5173,
    strictPort: true,
    fs: { allow: [raizRepo] }, // assets/fonts e design/brand ficam fora de picorte/web
    proxy: {
      "/api": { target: backend, changeOrigin: true },
      "/media": { target: backend, changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/testes/preparar.ts"],
    css: false,
  },
});
