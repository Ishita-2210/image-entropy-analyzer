import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { copyFileSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: 'offline-api-reference',
      closeBundle() {
        const target = resolve(import.meta.dirname, 'dist/docs-assets');
        mkdirSync(target, { recursive: true });
        for (const filename of ['swagger-ui-bundle.js', 'swagger-ui.css', 'favicon-32x32.png']) {
          copyFileSync(
            resolve(import.meta.dirname, 'node_modules/swagger-ui-dist', filename),
            resolve(target, filename),
          );
        }
      },
    },
  ],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test-setup.ts',
    include: ['src/**/*.test.{ts,tsx}'],
  },
  build: {
    rollupOptions: {
      output: { manualChunks: (id) => (/echarts|zrender/.test(id) ? 'charts' : undefined) },
    },
  },
});
