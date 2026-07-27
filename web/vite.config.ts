import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(() => ({
  base: process.env.GH_PAGES_BASE ?? '/',
  plugins: [react()],
  build: {
    emptyOutDir: true,
    manifest: true,
  },
}));
