import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "/dataqual/",
  plugins: [react()],
  server: { proxy: { "/api": process.env.DATAQUAL_DEV_API_URL || "http://127.0.0.1:8000" } },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    exclude: ["e2e/**", "node_modules/**"],
    coverage: { provider: "v8", reporter: ["text", "json", "html"] },
  },
});
