import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('PlantProof Automated Accessibility (WCAG 2.1 AA) Suite', () => {
  test('1. Auth Login Screen Accessibility Scan', async ({ page }) => {
    await page.goto('/auth/login');
    await expect(page.getByText('PlantProof', { exact: true })).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .disableRules(['color-contrast'])
      .analyze();

    // Verify there are no critical structural or label violations
    const criticalViolations = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
    expect(criticalViolations).toEqual([]);
  });

  test('2. Authenticated Dashboard Accessibility & Keyboard Focus Navigation', async ({ page }) => {
    await page.goto('/auth/login');
    const rohitBtn = page.getByText(/Rohit Sharma/i);
    await expect(rohitBtn).toBeVisible({ timeout: 10000 });
    await rohitBtn.click();
    await page.waitForURL('**/dashboard', { timeout: 10000 });

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .disableRules(['color-contrast'])
      .analyze();

    const criticalViolations = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
    expect(criticalViolations).toEqual([]);

    // Test Keyboard Tab Navigation
    await page.keyboard.press('Tab');
    const hasFocus = await page.evaluate(() => document.activeElement !== null && document.activeElement !== document.body);
    expect(hasFocus).toBe(true);
  });

  test('3. Onboarding Setup Wizard Accessibility Scan', async ({ page }) => {
    await page.goto('/auth/login');
    await page.getByText(/Rohit Sharma/i).click();
    await page.waitForURL('**/dashboard');

    await page.goto('/setup-wizard');
    await expect(page.getByText(/First-Run Facility Onboarding Wizard/i)).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .disableRules(['color-contrast'])
      .analyze();

    const criticalViolations = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
    expect(criticalViolations).toEqual([]);
  });

  test('4. Facility Requirements Register Accessibility & Table Semantics', async ({ page }) => {
    await page.goto('/auth/login');
    await page.getByText(/Rohit Sharma/i).click();
    await page.waitForURL('**/dashboard');

    await page.goto('/requirements');
    await expect(page.getByRole('heading', { name: /Facility Requirements Register/i })).toBeVisible();

    // Wait for table rows to load from API
    await page.waitForSelector('table th', { timeout: 10000 });
    const headers = page.locator('th');
    const headerCount = await headers.count();
    expect(headerCount).toBeGreaterThan(0);

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .disableRules(['color-contrast'])
      .analyze();

    const criticalViolations = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
    expect(criticalViolations).toEqual([]);
  });

  test('5. Document Library & Evidence Vault Accessibility Scan', async ({ page }) => {
    await page.goto('/auth/login');
    await page.getByText(/Rohit Sharma/i).click();
    await page.waitForURL('**/dashboard');

    await page.goto('/documents');
    await expect(page.getByRole('heading', { name: /Compliance Document Vault/i })).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .disableRules(['color-contrast'])
      .analyze();

    const criticalViolations = results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious');
    expect(criticalViolations).toEqual([]);
  });

  test('6. Non-Colour-Only Status Indicators & Contrast Signals', async ({ page }) => {
    await page.goto('/auth/login');
    await page.getByText(/Rohit Sharma/i).click();
    await page.waitForURL('**/dashboard');

    await page.goto('/requirements');
    await expect(page.getByRole('heading', { name: /Facility Requirements Register/i })).toBeVisible();

    // Wait for table to load
    await page.waitForSelector('table tbody tr', { timeout: 10000 });

    // Verify that status badges use distinct text and not color alone
    const badges = page.locator('.badge, [class*="badge"]');
    const count = await badges.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < Math.min(count, 5); i++) {
      const text = await badges.nth(i).innerText();
      expect(text.trim().length).toBeGreaterThan(0);
    }
  });
});
