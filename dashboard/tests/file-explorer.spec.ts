import { test, expect } from '@playwright/test';

test('opens an explorer file and displays its fetched contents', async ({ page }) => {
  const file = { type: 'file', path: 'review-example.txt', name: 'review-example.txt' };
  const fileRequests: unknown[] = [];

  await page.routeWebSocket('**/*', () => {});
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    let response: unknown = {};
    if (path === '/api/workspace/info') {
      response = { workspace: { path: '/workspace', language: 'Text' } };
    } else if (path === '/api/workspace/filetree') {
      response = { file_tree: [file] };
    } else if (path === '/api/workspace/file') {
      fileRequests.push(route.request().postDataJSON());
      response = { content: 'Explorer content loaded successfully.' };
    } else if (path === '/api/approvals/mode') {
      response = { mode: 'STRICT' };
    }
    await route.fulfill({ json: response });
  });

  await page.goto('/');
  await page.getByText(file.name, { exact: true }).click();
  await page.getByRole('menuitem', { name: 'Open', exact: true }).click();
  await expect(page.getByRole('tab', { name: file.name })).toBeVisible();
  await expect(page.getByRole('tabpanel').getByText('Explorer content loaded successfully.')).toBeVisible();
  expect(fileRequests).toEqual([{ path: file.path }]);
});
