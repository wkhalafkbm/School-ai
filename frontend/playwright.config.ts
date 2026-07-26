import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3001",
    trace: "on-first-retry",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  webServer: [
    {
      // A port of its own, never the real backend's (8001). Sharing that port
      // meant reuseExistingServer silently bound the suite to a running dev
      // backend, which allows origin :3000 only — every streamed page then sat
      // in its loading state and a dozen tests failed for the wrong reason.
      command: "node e2e/api-server.mjs",
      port: 8010,
      // Always start ours: a stale mock left over from an earlier run would
      // serve whatever routes it was written with, not the ones on disk.
      reuseExistingServer: false,
      env: { MOCK_API_PORT: "8010" },
    },
    {
      command: "npm run dev -- -p 3001",
      port: 3001,
      reuseExistingServer: !process.env.CI,
      env: { NEXT_PUBLIC_API_URL: "http://localhost:8010" },
      timeout: 120_000,
    },
  ],
});
