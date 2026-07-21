import { defineConfig } from "vitest/config";
import path from "path";

/**
 * Minimal Vitest config for pure-function unit tests.
 *
 * - environment: "node"  — no jsdom; pure modules only.
 * - No component tests, no @testing-library — keep it lightweight.
 * - Alias @/* mirrors tsconfig paths so imports in lib files resolve correctly.
 */
export default defineConfig({
  test: {
    environment: "node",
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
