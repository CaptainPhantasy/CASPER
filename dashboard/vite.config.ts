import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: 'monaco',
              test: /node_modules[\\/](?:monaco-editor|@monaco-editor)/,
              priority: 40,
            },
            {
              name: 'charts',
              test: /node_modules[\\/](?:recharts|d3-|victory-vendor)/,
              priority: 30,
            },
            {
              name: 'terminal',
              test: /node_modules[\\/]@xterm/,
              priority: 30,
            },
            {
              name: 'ui',
              test: /node_modules[\\/](?:@radix-ui|framer-motion|lucide-react|@tabler)/,
              maxSize: 450_000,
              priority: 20,
            },
            {
              name: 'vendor',
              test: /node_modules/,
              maxSize: 450_000,
              priority: 10,
            },
          ],
        },
      },
    },
  },
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
  // Mirror the dev proxy for `vite preview` so the production build served
  // during E2E tests can reach the backend on :8742 (API + WebSocket).
  preview: {
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
