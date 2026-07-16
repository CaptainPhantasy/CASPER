// @ts-check
const path = require('path');
const { defineConfig } = require('@playwright/test');

const repoRoot = path.resolve(__dirname, '..', '..');
const dashboardDir = path.join(repoRoot, 'dashboard');
const pythonExecutable = process.platform === 'win32'
  ? path.join(repoRoot, 'venv', 'Scripts', 'python.exe')
  : path.join(repoRoot, 'venv', 'bin', 'python');
const pythonCommand = `${JSON.stringify(pythonExecutable)} -m uvicorn core.server:app --host 127.0.0.1 --port 8742`;

process.env.CASPER_E2E_WORKSPACE = repoRoot;

module.exports = defineConfig({
  testDir: path.resolve(__dirname, 'tests'),
  timeout: 120000,
  expect: { timeout: 20000 },
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    launchOptions: {
      args: process.platform === 'linux' ? ['--disable-dev-shm-usage'] : [],
    },
  },
  webServer: [
    {
      command: pythonCommand,
      cwd: repoRoot,
      port: 8742,
      reuseExistingServer: true,
      timeout: 120000,
      env: {
        PORT: '8742',
        CASPER_PROJECT_ROOT: repoRoot,
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173',
      cwd: dashboardDir,
      port: 5173,
      reuseExistingServer: true,
      timeout: 120000,
    },
  ],
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
});
