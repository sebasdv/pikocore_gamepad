import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(() => ({
  // GitHub Pages serves a project repo at /<repo>/, not at the domain root.
  // Vite's `command` can't tell "building for GH Pages" apart from a local
  // `vite preview` of that same build (both report the same value, confirmed
  // by testing -- `vite preview` served the app at "/" even though the
  // command-based conditional this replaced expected "build"), so an explicit
  // env var is the only thing that actually disambiguates the two. The
  // GitHub Actions deploy workflow sets GH_PAGES_BASE; everything else
  // (npm run dev, npm run preview) defaults to "/".
  // This also feeds import.meta.env.BASE_URL, which App.tsx uses to fetch the
  // bundled firmware .uf2 files from public/ -- get this wrong and that
  // download 404s once deployed, even though everything works locally.
  base: process.env.GH_PAGES_BASE ?? '/',
  plugins: [react()],
  build: {
    emptyOutDir: true,
    manifest: true,
  },
}));
