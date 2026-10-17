/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    // Allow arbitrary hostnames so public tunnels (trycloudflare, loca.lt,
    // ngrok, serveo, LAN IP) can reach the dev server without a 403.
    allowedHosts: true,
    // Proxy /api/v1 to the FastAPI backend so the browser only ever talks to
    // the Vite origin. Tunneling just port 5173 is then sufficient.
    proxy: {
      '/api/v1': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
