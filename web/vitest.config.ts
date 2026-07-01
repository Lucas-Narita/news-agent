import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Mirrors tsconfig.json's "@/*": ["./*"] so vitest (Vite's resolver)
    // understands the same alias Next.js already resolves at build time.
    alias: {
      "@": fileURLToPath(new URL(".", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    // Playwright owns e2e/**; vitest's default glob would otherwise pick up
    // home.spec.ts and crash trying to run Playwright's test() outside its runner.
    exclude: ["node_modules/**", "e2e/**"],
  },
});
