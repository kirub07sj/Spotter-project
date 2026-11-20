/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // MapLibre supplies a WebGL context; omit deck.gl's unused WebGPU implementation.
  resolve: { conditions: ['visgl:webgl-only', 'module', 'browser', 'development|production'] },
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } },
  },
  worker: { format: 'es' },
  build: { target: 'es2022', sourcemap: true, manifest: true, chunkSizeWarningLimit: 1600 },
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
