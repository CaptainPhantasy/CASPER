import { chromium, FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Global setup for CASPER command testing
 * Prepares test environment and validates system readiness
 */
async function globalSetup(config: FullConfig) {
  console.log('🚀 CASPER Command Test Suite - Global Setup');

  // Ensure test results directory exists
  const testResultsDir = path.join(__dirname, '../test-results');
  if (!fs.existsSync(testResultsDir)) {
    fs.mkdirSync(testResultsDir, { recursive: true });
  }

  // Create browser for initial system check
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('📡 Checking dashboard availability...');
    await page.goto('http://localhost:4173', { timeout: 30000 });
    await page.waitForSelector('header', { state: 'visible', timeout: 10000 });
    console.log('✅ Dashboard is accessible');

    console.log('🔌 Checking backend connectivity...');
    const response = await page.request.get('http://localhost:8742/docs').catch(() => null);
    if (response?.ok()) {
      console.log('✅ Backend server is running');
    } else {
      console.log('⚠️ Backend server may not be available (some tests may fail)');
    }

    console.log('🖥️ Verifying terminal capabilities...');
    const terminalSupported = await page.evaluate(() => {
      // Check for WebSocket support and other terminal requirements
      return !!(window.WebSocket && document.createElement('canvas').getContext);
    });

    if (terminalSupported) {
      console.log('✅ Terminal capabilities verified');
    } else {
      console.log('⚠️ Terminal capabilities limited in this environment');
    }

    // Create test session storage
    const testDataDir = path.join(__dirname, '../test-data');
    if (!fs.existsSync(testDataDir)) {
      fs.mkdirSync(testDataDir, { recursive: true });
    }

    // Write system info for test context
    const systemInfo = {
      timestamp: new Date().toISOString(),
      dashboardUrl: 'http://localhost:4173',
      backendUrl: 'http://localhost:8742',
      terminalSupported,
      setupComplete: true
    };

    fs.writeFileSync(
      path.join(testDataDir, 'setup-info.json'),
      JSON.stringify(systemInfo, null, 2)
    );

    console.log('✅ Global setup completed successfully');

  } catch (error) {
    console.error('❌ Global setup failed:', error);
    throw error;
  } finally {
    await context.close();
    await browser.close();
  }
}

export default globalSetup;