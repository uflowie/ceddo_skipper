import { defineConfig } from '@playwright/test';

export default defineConfig({
  webServer: {
    command: 'npx serve . -l 3001 --cors',
    port: 3001,
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
  use: {
    baseURL: 'http://localhost:3001',
  },
  testDir: './tests',
  timeout: 180000,
});