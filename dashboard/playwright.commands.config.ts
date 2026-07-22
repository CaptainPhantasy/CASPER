import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration specifically for CASPER command testing
 * Optimized for headless execution and comprehensive logging
 */
export default defineConfig({
  testDir: './tests',
  testMatch: '**/casper-commands-suite.spec.ts',

  /* Run tests in sequence for terminal stability */
  fullyParallel: false,
  workers: 1,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry failed tests */
  retries: 2,

  /* Extended timeout for command execution */
  timeout: 120000, // 2 minutes per test

  /* Reporter with detailed output */
  reporter: [
    ['html', { outputFolder: 'playwright-report/commands-report' }],
    ['json', { outputFile: 'test-results/commands-results.json' }],
    ['list'],
  ],

  /* Global test settings */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost:4173',

    /* Headless mode for CI/automated testing */
    headless: true,

    /* Collect trace on failure for debugging */
    trace: 'retain-on-failure',

    /* Record video on failure */
    video: 'retain-on-failure',

    /* Take screenshot on failure */
    screenshot: 'only-on-failure',

    /* Extended action timeout for slower commands */
    actionTimeout: 30000,

    /* Extended navigation timeout */
    navigationTimeout: 30000,
  },

  /* Projects for different browsers (focusing on Chromium for commands) */
  projects: [
    {
      name: 'chromium-commands',
      use: {
        ...devices['Desktop Chrome'],
        // Additional Chrome flags for terminal support
        launchOptions: {
          args: [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--remote-debugging-port=9222'
          ]
        }
      },
    },
  ],

  /* Web server configuration - using existing running servers */
  webServer: {
    command: 'echo "Using existing servers"',
    port: 4173,
    reuseExistingServer: true,
    timeout: 5000,
  },

  /* Global setup and teardown */
  globalSetup: './tests/global-setup.ts',
  globalTeardown: './tests/global-teardown.ts',
});