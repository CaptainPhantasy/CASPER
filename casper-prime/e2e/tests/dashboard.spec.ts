import path from 'path';
import { test, expect } from '@playwright/test';

const WORKSPACE_PATH = process.env.CASPER_E2E_WORKSPACE ?? process.cwd();
const WORKSPACE_NAME = path.basename(WORKSPACE_PATH) || WORKSPACE_PATH;

test.describe('CASPER Prime IDE dashboard', () => {
  test('opens workspace and surfaces live data', async ({ page }) => {
    await page.goto('/');

    // Connection badge should appear and settle on either connecting or connected
    const statusBadge = page.locator('header').locator('text=/connected|connecting/i');
    await expect(statusBadge).toBeVisible({ timeout: 20000 });

    // Open workspace dialog
    await page.getByRole('button', { name: /open workspace/i }).click();
    const dialog = page.getByRole('dialog', { name: /select workspace/i });
    await expect(dialog).toBeVisible();

    const input = dialog.getByLabel(/workspace path/i);
    await input.fill(WORKSPACE_PATH);
    await dialog.getByRole('button', { name: /^open$/i }).click();

    // The dialog should close once the workspace loads
    await expect(dialog).toBeHidden({ timeout: 20000 });

    // Header should reflect the workspace name
    await expect(page.locator('header').getByText(WORKSPACE_NAME)).toBeVisible({ timeout: 20000 });

    // File tree should populate with known file
    await expect(page.locator('aside').getByText('README')).toBeVisible({ timeout: 20000 });

    // Project analysis card should display
    await expect(page.getByText('Project insights')).toBeVisible();

    // Open settings dialog from toolbar
    await page.getByRole('button', { name: /^Settings$/i }).click();
    const settingsDialog = page.getByRole('dialog', { name: /workspace settings/i });
    await expect(settingsDialog).toBeVisible();
    await settingsDialog.getByRole('button', { name: /cancel/i }).click();
    await expect(settingsDialog).toBeHidden();

    // Command palette opens and lists quick actions
    await page.getByRole('button', { name: /palette/i }).click();
    const palette = page.getByRole('dialog', { name: /global command palette/i });
    await expect(palette).toBeVisible();
    await expect(palette.getByText('Quick actions')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(palette).toBeHidden();

    // Agent activity panel should be reachable
    await expect(page.getByText('Agent Activity')).toBeVisible();
  });
});
