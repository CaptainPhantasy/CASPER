import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 9318,
    proxy: {
      '/api': {
        target: 'http://localhost:8742',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8742',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
