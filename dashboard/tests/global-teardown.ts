import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Global teardown for CASPER command testing
 * Cleans up test data and generates final reports
 */
async function globalTeardown() {
  console.log('🧹 CASPER Command Test Suite - Global Teardown');

  try {
    const testDataDir = path.join(__dirname, '../test-data');
    const testResultsDir = path.join(__dirname, '../test-results');

    // Clean up temporary test data
    if (fs.existsSync(testDataDir)) {
      console.log('🗑️ Cleaning up test data...');
      fs.rmSync(testDataDir, { recursive: true, force: true });
    }

    // Generate test summary if results exist
    const resultsFile = path.join(testResultsDir, 'commands-results.json');
    if (fs.existsSync(resultsFile)) {
      console.log('📊 Generating test summary...');

      const results = JSON.parse(fs.readFileSync(resultsFile, 'utf8'));
      const summary = {
        timestamp: new Date().toISOString(),
        totalTests: results.suites?.reduce((acc: number, suite: any) =>
          acc + (suite.specs?.length || 0), 0) || 0,
        passed: results.suites?.reduce((acc: number, suite: any) =>
          acc + (suite.specs?.filter((spec: any) => spec.tests?.some((test: any) => test.status === 'passed')).length || 0), 0) || 0,
        failed: results.suites?.reduce((acc: number, suite: any) =>
          acc + (suite.specs?.filter((spec: any) => spec.tests?.some((test: any) => test.status === 'failed')).length || 0), 0) || 0,
        duration: results.stats?.duration || 0
      };

      fs.writeFileSync(
        path.join(testResultsDir, 'test-summary.json'),
        JSON.stringify(summary, null, 2)
      );

      console.log(`✅ Test Summary: ${summary.passed}/${summary.totalTests} passed`);
    }

    console.log('✅ Global teardown completed');

  } catch (error) {
    console.error('❌ Global teardown error:', error);
    // Don't throw - teardown errors shouldn't fail the build
  }
}

export default globalTeardown;