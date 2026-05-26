import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Vite config for @dar/web.
//
// `base` is configurable via DAR_MOUNT env (e.g. "/admin-react/"); the
// default keeps the dev server self-contained. In production we build
// with relative asset URLs so the wheel can be served from any mount.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === "build" ? "./" : "/",
  resolve: {
    alias: {
      "@dar/api": path.resolve(__dirname, "../../packages/api/src/index.ts"),
      "@dar/data": path.resolve(__dirname, "../../packages/data/src/index.ts"),
      "@dar/ui": path.resolve(__dirname, "../../packages/ui/src/index.ts"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Forward API calls to the Django dev server.
      "/admin-react/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: path.resolve(__dirname, "../../../django_admin_react/static/admin_react"),
    emptyOutDir: true,
    sourcemap: true,
    // Emit `.vite/manifest.json` so Django's SpaIndexView can map
    // the entry to its hashed JS / CSS filenames at render time.
    manifest: true,
    rollupOptions: {
      // Listing `index.html` as input makes Vite treat it as the
      // entry — this is what triggers `manifest.json` to include
      // an `index.html` record, which our Django view looks up.
      input: path.resolve(__dirname, "index.html"),
      output: {
        // Hashed filenames so Django's collectstatic can serve them
        // with long Cache-Control. The wheel ships the manifest and
        // the bundle in lockstep.
        entryFileNames: "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
}));
