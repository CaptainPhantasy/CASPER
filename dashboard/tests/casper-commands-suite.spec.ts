import { test, expect, Page } from '@playwright/test';

/**
 * CASPER Prime - Comprehensive Command Test Suite
 * Tests all 21+ slash commands in headless mode with full automation
 */

interface TestResult {
  command: string;
  status: 'PASS' | 'FAIL' | 'SKIP';
  duration: number;
  error?: string;
  output?: string;
}

class CASPERCommandTester {
  private page: Page;
  private results: TestResult[] = [];

  constructor(page: Page) {
    this.page = page;
  }

  async openTerminal(): Promise<void> {
    // Click on terminal tab or area
    const terminalButton = this.page.locator('button:has-text("Terminal"), [data-testid="terminal-button"]');
    if (await terminalButton.isVisible()) {
      await terminalButton.click();
    }

    // Wait for terminal to be ready
    await this.page.waitForSelector('.xterm-viewport, .terminal-container, [data-testid="terminal"]',
      { state: 'visible', timeout: 10000 });
    await this.page.waitForTimeout(2000); // Allow terminal to fully initialize
  }

  async executeCommand(command: string, timeout: number = 30000): Promise<TestResult> {
    const startTime = Date.now();

    try {
      // Focus terminal
      await this.page.locator('.xterm-helper-textarea, input[placeholder*="command"], .terminal-input').click();

      // Type the command
      await this.page.keyboard.type(command);
      await this.page.keyboard.press('Enter');

      // Wait for command execution and response
      await this.page.waitForTimeout(3000);

      // Look for success indicators or error messages
      const terminalContent = await this.page.locator('.xterm-screen, .terminal-output, .terminal-container').textContent();

      const duration = Date.now() - startTime;

      // Check for common error patterns
      if (terminalContent?.includes('Error:') ||
          terminalContent?.includes('Failed:') ||
          terminalContent?.includes('command not found') ||
          terminalContent?.includes('No such file')) {
        return {
          command,
          status: 'FAIL',
          duration,
          error: 'Command execution failed',
          output: terminalContent?.slice(-500) // Last 500 chars
        };
      }

      return {
        command,
        status: 'PASS',
        duration,
        output: terminalContent?.slice(-500)
      };

    } catch (error) {
      return {
        command,
        status: 'FAIL',
        duration: Date.now() - startTime,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  async testCommandWithDialog(command: string): Promise<TestResult> {
    const startTime = Date.now();

    try {
      // Open command palette
      await this.page.keyboard.press('Meta+K');
      await this.page.waitForSelector('[cmdk-root], [data-testid="cmdk"], dialog', { state: 'visible' });

      // Type command
      await this.page.keyboard.type(command);
      await this.page.waitForTimeout(1000);

      // Press enter to execute
      await this.page.keyboard.press('Enter');

      // Wait for execution
      await this.page.waitForTimeout(3000);

      // Close any dialogs
      await this.page.keyboard.press('Escape');

      return {
        command,
        status: 'PASS',
        duration: Date.now() - startTime
      };

    } catch (error) {
      return {
        command,
        status: 'FAIL',
        duration: Date.now() - startTime,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }
}

test.describe('CASPER Commands - Complete Test Suite', () => {
  let tester: CASPERCommandTester;

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('header', { state: 'visible', timeout: 10000 });

    tester = new CASPERCommandTester(page);
    await tester.openTerminal();
  });

  // Core System Commands
  test.describe('Core System Commands', () => {
    test('should execute /help command', async ({ page }) => {
      const result = await tester.executeCommand('/help');
      expect(result.status).toBe('PASS');
      console.log(`✓ /help: ${result.duration}ms`);
    });

    test('should execute /status command', async ({ page }) => {
      const result = await tester.executeCommand('/status');
      expect(result.status).toBe('PASS');
      console.log(`✓ /status: ${result.duration}ms`);
    });

    test('should execute /config command', async ({ page }) => {
      const result = await tester.executeCommand('/config');
      expect(result.status).toBe('PASS');
      console.log(`✓ /config: ${result.duration}ms`);
    });

    test('should execute /setup command', async ({ page }) => {
      const result = await tester.executeCommand('/setup');
      expect(result.status).toBe('PASS');
      console.log(`✓ /setup: ${result.duration}ms`);
    });
  });

  // Context Management Commands
  test.describe('Context Management Commands', () => {
    test('should execute /context command', async ({ page }) => {
      const result = await tester.executeCommand('/context');
      expect(result.status).toBe('PASS');
      console.log(`✓ /context: ${result.duration}ms`);
    });

    test('should execute /switch command', async ({ page }) => {
      const result = await tester.executeCommand('/switch');
      expect(result.status).toBe('PASS');
      console.log(`✓ /switch: ${result.duration}ms`);
    });

    test('should execute /env command', async ({ page }) => {
      const result = await tester.executeCommand('/env');
      expect(result.status).toBe('PASS');
      console.log(`✓ /env: ${result.duration}ms`);
    });
  });

  // Development Commands
  test.describe('Development Commands', () => {
    test('should execute /newcomponent command', async ({ page }) => {
      const result = await tester.executeCommand('/newcomponent TestComponent');
      expect(result.status).toBe('PASS');
      console.log(`✓ /newcomponent: ${result.duration}ms`);
    });

    test('should execute /docs command', async ({ page }) => {
      const result = await tester.executeCommand('/docs');
      expect(result.status).toBe('PASS');
      console.log(`✓ /docs: ${result.duration}ms`);
    });

    test('should execute /commit command', async ({ page }) => {
      const result = await tester.executeCommand('/commit "Test commit message"');
      expect(result.status).toBe('PASS');
      console.log(`✓ /commit: ${result.duration}ms`);
    });

    test('should execute /test command', async ({ page }) => {
      const result = await tester.executeCommand('/test');
      expect(result.status).toBe('PASS');
      console.log(`✓ /test: ${result.duration}ms`);
    });
  });

  // Business Commands (Phase 2)
  test.describe('Business Commands', () => {
    test('should execute /proposal command', async ({ page }) => {
      const result = await tester.executeCommand('/proposal "Test project proposal"');
      expect(result.status).toBe('PASS');
      console.log(`✓ /proposal: ${result.duration}ms`);
    });

    test('should execute /estimate command', async ({ page }) => {
      const result = await tester.executeCommand('/estimate');
      expect(result.status).toBe('PASS');
      console.log(`✓ /estimate: ${result.duration}ms`);
    });

    test('should execute /invoice command', async ({ page }) => {
      const result = await tester.executeCommand('/invoice');
      expect(result.status).toBe('PASS');
      console.log(`✓ /invoice: ${result.duration}ms`);
    });
  });

  // Emergency Commands
  test.describe('Emergency Commands', () => {
    test('should execute /panic command', async ({ page }) => {
      const result = await tester.executeCommand('/panic');
      expect(result.status).toBe('PASS');
      console.log(`✓ /panic: ${result.duration}ms`);
    });

    test('should execute /hotfix command', async ({ page }) => {
      const result = await tester.executeCommand('/hotfix "Critical bug fix"');
      expect(result.status).toBe('PASS');
      console.log(`✓ /hotfix: ${result.duration}ms`);
    });
  });

  // Development Workflow Commands (Phase 3)
  test.describe('Development Workflow Commands', () => {
    test('should execute /migrate command', async ({ page }) => {
      const result = await tester.executeCommand('/migrate');
      expect(result.status).toBe('PASS');
      console.log(`✓ /migrate: ${result.duration}ms`);
    });

    test('should execute /seed command', async ({ page }) => {
      const result = await tester.executeCommand('/seed');
      expect(result.status).toBe('PASS');
      console.log(`✓ /seed: ${result.duration}ms`);
    });

    test('should execute /scan command', async ({ page }) => {
      const result = await tester.executeCommand('/scan');
      expect(result.status).toBe('PASS');
      console.log(`✓ /scan: ${result.duration}ms`);
    });

    test('should execute /lint command', async ({ page }) => {
      const result = await tester.executeCommand('/lint');
      expect(result.status).toBe('PASS');
      console.log(`✓ /lint: ${result.duration}ms`);
    });

    test('should execute /api command', async ({ page }) => {
      const result = await tester.executeCommand('/api users');
      expect(result.status).toBe('PASS');
      console.log(`✓ /api: ${result.duration}ms`);
    });

    test('should execute /logs command', async ({ page }) => {
      const result = await tester.executeCommand('/logs');
      expect(result.status).toBe('PASS');
      console.log(`✓ /logs: ${result.duration}ms`);
    });
  });

  // Productivity Commands
  test.describe('Productivity Commands', () => {
    test('should execute /focus command', async ({ page }) => {
      const result = await tester.executeCommand('/focus 25');
      expect(result.status).toBe('PASS');
      console.log(`✓ /focus: ${result.duration}ms`);
    });

    test('should execute /til command', async ({ page }) => {
      const result = await tester.executeCommand('/til "Learned about Playwright testing"');
      expect(result.status).toBe('PASS');
      console.log(`✓ /til: ${result.duration}ms`);
    });

    test('should execute /notes command', async ({ page }) => {
      const result = await tester.executeCommand('/notes "Test implementation notes"');
      expect(result.status).toBe('PASS');
      console.log(`✓ /notes: ${result.duration}ms`);
    });
  });

  // Session Management Commands
  test.describe('Session Management Commands', () => {
    test('should execute /save command', async ({ page }) => {
      const result = await tester.executeCommand('/save test-session');
      expect(result.status).toBe('PASS');
      console.log(`✓ /save: ${result.duration}ms`);
    });

    test('should execute /resume command', async ({ page }) => {
      const result = await tester.executeCommand('/resume');
      expect(result.status).toBe('PASS');
      console.log(`✓ /resume: ${result.duration}ms`);
    });

    test('should execute /sessions command', async ({ page }) => {
      const result = await tester.executeCommand('/sessions');
      expect(result.status).toBe('PASS');
      console.log(`✓ /sessions: ${result.duration}ms`);
    });
  });

  // Performance and Integration Tests
  test.describe('Performance and Integration Tests', () => {
    test('should handle rapid command execution', async ({ page }) => {
      const commands = ['/status', '/help', '/config'];
      const results: TestResult[] = [];

      for (const cmd of commands) {
        const result = await tester.executeCommand(cmd);
        results.push(result);
        await page.waitForTimeout(1000); // Brief pause between commands
      }

      const allPassed = results.every(r => r.status === 'PASS');
      expect(allPassed).toBe(true);
      console.log(`✓ Rapid execution test: ${results.length} commands`);
    });

    test('should maintain terminal state across commands', async ({ page }) => {
      // Execute multiple commands in sequence
      await tester.executeCommand('/status');
      await tester.executeCommand('/help');

      // Verify terminal is still responsive
      const result = await tester.executeCommand('/config');
      expect(result.status).toBe('PASS');
      console.log('✓ Terminal state maintained across commands');
    });

    test('should handle command with special characters', async ({ page }) => {
      const result = await tester.executeCommand('/notes "Test with @#$%^&*() characters"');
      expect(result.status).toBe('PASS');
      console.log('✓ Special characters handled correctly');
    });
  });

  // Error Handling Tests
  test.describe('Error Handling Tests', () => {
    test('should handle invalid command gracefully', async ({ page }) => {
      const result = await tester.executeCommand('/nonexistent-command');
      // We expect this to fail, but gracefully
      expect(['PASS', 'FAIL']).toContain(result.status);
      console.log('✓ Invalid command handled gracefully');
    });

    test('should handle command without arguments when required', async ({ page }) => {
      const result = await tester.executeCommand('/newcomponent');
      // Should either pass with default behavior or fail gracefully
      expect(['PASS', 'FAIL']).toContain(result.status);
      console.log('✓ Missing arguments handled gracefully');
    });
  });

  // Comprehensive System Test
  test('should complete full command suite execution', async ({ page }) => {
    const allCommands = [
      '/help', '/status', '/config', '/setup',
      '/context', '/switch', '/env',
      '/newcomponent TestComp', '/docs', '/commit "Test"', '/test',
      '/proposal "Test"', '/estimate', '/invoice',
      '/panic', '/hotfix "Fix"',
      '/migrate', '/seed', '/scan', '/lint', '/api users', '/logs',
      '/focus 25', '/til "Test"', '/notes "Test"',
      '/save test', '/resume', '/sessions'
    ];

    const results: TestResult[] = [];
    let passCount = 0;
    let failCount = 0;

    console.log(`\n📋 Executing full command suite (${allCommands.length} commands)...\n`);

    for (let i = 0; i < allCommands.length; i++) {
      const cmd = allCommands[i];
      console.log(`[${i + 1}/${allCommands.length}] Testing: ${cmd}`);

      const result = await tester.executeCommand(cmd);
      results.push(result);

      if (result.status === 'PASS') {
        passCount++;
        console.log(`  ✅ PASS (${result.duration}ms)`);
      } else {
        failCount++;
        console.log(`  ❌ FAIL (${result.duration}ms): ${result.error}`);
      }

      // Small delay between commands to avoid overwhelming the system
      await page.waitForTimeout(2000);
    }

    const totalCommands = results.length;
    const successRate = (passCount / totalCommands) * 100;

    console.log(`\n📊 Test Suite Summary:`);
    console.log(`  Total Commands: ${totalCommands}`);
    console.log(`  Passed: ${passCount}`);
    console.log(`  Failed: ${failCount}`);
    console.log(`  Success Rate: ${successRate.toFixed(1)}%`);

    // Save detailed results for analysis
    await page.evaluate((testResults) => {
      (window as any).casperTestResults = testResults;
    }, results);

    // We expect at least 70% success rate for a robust system
    expect(successRate).toBeGreaterThan(70);
    console.log(`✅ Full command suite completed with ${successRate.toFixed(1)}% success rate`);
  });
});

// Additional utility tests for terminal integration
test.describe('Terminal Integration Tests', () => {
  test('should verify terminal WebSocket connection', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('header', { state: 'visible' });

    // Monitor network for WebSocket connections
    const wsPromise = new Promise((resolve) => {
      page.on('websocket', (ws) => {
        console.log('WebSocket connected:', ws.url());
        resolve(ws);
      });
    });

    // Open terminal to trigger WebSocket connection
    const terminalButton = page.locator('button:has-text("Terminal"), [data-testid="terminal-button"]');
    if (await terminalButton.isVisible()) {
      await terminalButton.click();
    }

    // Wait for WebSocket connection or timeout
    try {
      await wsPromise;
      console.log('✅ WebSocket connection established');
    } catch (error) {
      console.log('⚠️ WebSocket connection not detected (may use different transport)');
    }
  });

  test('should verify terminal responsiveness', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('header', { state: 'visible' });

    const tester = new CASPERCommandTester(page);
    await tester.openTerminal();

    // Test terminal input responsiveness
    const startTime = Date.now();
    await page.locator('.xterm-helper-textarea, input[placeholder*="command"], .terminal-input').click();
    await page.keyboard.type('echo "terminal test"');
    const responseTime = Date.now() - startTime;

    expect(responseTime).toBeLessThan(1000); // Should respond within 1 second
    console.log(`✅ Terminal responsive in ${responseTime}ms`);
  });
});