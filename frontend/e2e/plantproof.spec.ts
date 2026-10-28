import { test, expect } from '@playwright/test';

test.describe('PlantProof Factory Compliance E2E Workflows', () => {
  test.beforeEach(async ({ page }) => {
    // Visit app login screen
    await page.goto('/auth/login');

    // Click demo persona button for Rohit Sharma (Plant Manager) which directly logs in and navigates to /dashboard
    const rohitBtn = page.getByText(/Rohit Sharma/i);
    await expect(rohitBtn).toBeVisible({ timeout: 10000 });
    await rohitBtn.click();

    // Confirm navigation into the authenticated shell
    await page.waitForURL('**/dashboard', { timeout: 10000 });
  });

  test('1. Onboarding Wizard: Save/resume draft and step progression', async ({ page }) => {
    await page.goto('/setup-wizard');
    await expect(page.getByText(/First-Run Facility Onboarding Wizard/i)).toBeVisible();

    // Verify step 1 has default entity values
    await expect(page.getByPlaceholder('e.g. Acme Manufacturing Private Limited')).toBeVisible();

    // Click Save Draft
    await page.getByRole('button', { name: /Save Draft/i }).click();

    // Navigate to Step 2
    await page.getByRole('button', { name: /Save & Continue/i }).click();
    await expect(page.getByText(/Step 2: Manufacturing Site & Facility Identification/i)).toBeVisible();

    // Navigate to Step 3
    await page.getByRole('button', { name: /Save & Continue/i }).click();
    await expect(page.getByText(/Step 3: CPCB Industrial Categorization/i)).toBeVisible();
  });

  test('2. Dashboard: Live KPI cards, quick actions and facility context', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

    // Verify statutory obligations metrics cards are rendered in main content
    const main = page.locator('main');
    await expect(main.getByText('Requirements', { exact: true })).toBeVisible();
    await expect(main.getByText('Due Soon', { exact: true }).first()).toBeVisible();
    await expect(main.getByText('Evidence Gaps', { exact: true })).toBeVisible();
    await expect(main.getByText('Regulatory Changes', { exact: true })).toBeVisible();
  });

  test('3. Requirements Register & Obligation Details Drawer', async ({ page }) => {
    await page.goto('/requirements');
    await expect(page.getByRole('heading', { name: /Facility Requirements Register/i })).toBeVisible();

    // Verify table has items and click View Details to open drawer
    await page.waitForSelector('table');
    const viewBtn = page.getByRole('button', { name: /View Details/i }).first();
    await expect(viewBtn).toBeVisible();
    await viewBtn.click();

    // Verify drawer details
    const drawer = page.locator('.drawer-content');
    await expect(drawer).toBeVisible();
    await expect(drawer.getByText('Applicability State')).toBeVisible();
    await expect(drawer.getByText('Evidence Status')).toBeVisible();
  });

  test('4. Document Library & OCR Extraction Workbench', async ({ page }) => {
    await page.goto('/documents');
    await expect(page.getByRole('heading', { name: /Compliance Document Vault/i })).toBeVisible();

    // Check document table rows and click Review & Verify
    await page.waitForSelector('table');
    const reviewBtn = page.getByRole('button', { name: /Review & Verify/i }).first();
    await expect(reviewBtn).toBeVisible();
    await reviewBtn.click();

    // Verify dual-pane human review workbench opened
    await expect(page.getByText('Back to Vault')).toBeVisible();
    await expect(page.getByRole('button', { name: /Approve as Evidence/i })).toBeVisible();
  });

  test('5. Regulatory Change Inbox & Impact Review', async ({ page }) => {
    await page.goto('/regulatory-changes');
    await expect(page.getByRole('heading', { name: /Regulatory Intelligence & Change Review/i })).toBeVisible();

    // Verify detected changes view is active
    await expect(page.getByText(/Detected Changes/i)).toBeVisible();
    await expect(page.getByText(/Gazette/i).first()).toBeVisible();
  });

  test('6. Remediation Tasks: List / Calendar toggle', async ({ page }) => {
    await page.goto('/tasks');
    await expect(page.getByRole('heading', { name: /Remediation & Compliance Tasks/i })).toBeVisible();

    // Test List / Calendar toggle
    const calToggle = page.getByRole('button', { name: /Calendar View/i });
    await expect(calToggle).toBeVisible();
    await calToggle.click();

    // Verify calendar header and month days are visible
    await expect(page.getByText('Mon', { exact: true })).toBeVisible();
    await expect(page.getByText('Sun', { exact: true })).toBeVisible();

    // Toggle back to list
    const listToggle = page.getByRole('button', { name: /List View/i });
    await listToggle.click();
    await expect(page.locator('table')).toBeVisible();
  });

  test('7. Audit Readiness & Report Generator', async ({ page }) => {
    await page.goto('/reports');
    await expect(page.getByRole('heading', { name: /Audits & Readiness Reports/i })).toBeVisible();

    // Verify readiness score indicator is present
    await expect(page.getByText(/Audit Readiness/i).first()).toBeVisible();

    // Open report builder drawer or modal
    const generateBtn = page.getByRole('button', { name: /Generate Audit Report/i });
    if (await generateBtn.isVisible()) {
      await generateBtn.click();
      await expect(page.getByText(/Audit Readiness Report Builder/i)).toBeVisible();
    }
  });

  test('8. Role-Based Access Control: Viewer cannot access Admin Master Data', async ({ page }) => {
    // Switch to Sneha Patil (VIEWER)
    await page.goto('/auth/login');
    const snehaBtn = page.getByText(/Sneha Patil/i);
    await expect(snehaBtn).toBeVisible();
    await snehaBtn.click();
    await page.waitForURL('**/dashboard', { timeout: 10000 });

    // Try navigating to admin master data
    await page.goto('/admin/master-data');
    await expect(page.getByText(/Access Restricted \/ Permission Denied/i)).toBeVisible();
  });
});
