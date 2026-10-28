import { test, expect } from '@playwright/test';
import path from 'path';

const BASE_URL = 'http://localhost:5173';
const SCREENSHOT_DIR = path.resolve(process.cwd(), '../artifacts/ui-review');

test.describe('PlantProof Real-User Visual QA & Route Inspection Suite', () => {

  test('01. Public Auth & Error States: Inspect visual hierarchy and error messages', async ({ page }) => {
    // 1. Visit Auth Screen
    await page.goto(`${BASE_URL}/auth/login`);
    await page.waitForLoadState('networkidle');

    // Verify visual branding and layout
    await expect(page.locator('h1')).toContainText(/PlantProof/i);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/01_auth_login.png`, fullPage: true });

    // 2. Test Invalid Credentials Error State (friendly error banner, no raw payload)
    await page.fill('input[type="email"]', 'invalid.user@acme-mfg.in');
    await page.fill('input[type="password"]', 'WrongPassword123!');
    await page.click('button[type="submit"]');

    // Wait for error feedback banner
    await page.waitForTimeout(600);
    const errorBanner = page.locator('[role="alert"]').first();
    if (await errorBanner.isVisible()) {
      const errorText = await errorBanner.innerText();
      expect(errorText).not.toContain('Traceback');
      expect(errorText).not.toContain('sqlite3');
      expect(errorText).not.toContain('SQLAlchemy');
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/02_auth_error_state.png` });

    // 3. Test Demo Persona Switcher Chips
    const personaButton = page.locator('button:has-text("Rohit Sharma"), button:has-text("Plant Manager")').first();
    if (await personaButton.isVisible()) {
      await personaButton.click();
      await page.waitForURL('**/dashboard', { timeout: 8000 });
      expect(page.url()).toContain('/dashboard');
    }
  });

  test('02. Company Admin Journey: Dashboard, Master Data, Rules, Users, Audit Logs', async ({ page }) => {
    // 1. Login as Company Admin
    await page.goto(`${BASE_URL}/auth/login`);
    await page.fill('input[type="email"]', 'amit.jadhav@acme-mfg.in');
    await page.fill('input[type="password"]', 'DemoPass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });

    // 2. Inspect Executive Dashboard
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Dashboard');
    await expect(page.locator('text=Requirements').first()).toBeVisible();
    await page.screenshot({ path: `${SCREENSHOT_DIR}/03_admin_dashboard.png`, fullPage: true });

    // 3. Inspect Onboarding Setup Wizard
    await page.goto(`${BASE_URL}/setup-wizard`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1, h2, .stepper').first()).toBeVisible();
    // Test Save Draft button
    const saveDraftBtn = page.locator('button:has-text("Save Draft")').first();
    if (await saveDraftBtn.isVisible()) {
      await saveDraftBtn.click();
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/04_setup_wizard_admin.png`, fullPage: true });

    // 4. Inspect Admin Master Data Catalog
    await page.goto(`${BASE_URL}/admin/master-data`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Master Data');
    // Verify tabs exist and can be clicked
    const actsTab = page.locator('button:has-text("Acts & Statutes"), button:has-text("Acts")').first();
    if (await actsTab.isVisible()) {
      await actsTab.click();
      await page.waitForTimeout(400);
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/05_admin_master_data.png`, fullPage: true });

    // 5. Inspect Admin Rule Review Bench
    await page.goto(`${BASE_URL}/admin/rules`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1, h2').first()).toBeVisible();
    // Click simulate evaluation if button present
    const simulateBtn = page.locator('button:has-text("Simulate"), button:has-text("Test Rule")').first();
    if (await simulateBtn.isVisible()) {
      await simulateBtn.click();
      await page.waitForTimeout(500);
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/06_admin_rules_bench.png`, fullPage: true });

    // 6. Inspect Admin Users & Roles
    await page.goto(`${BASE_URL}/admin/users`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toBeVisible();
    await page.screenshot({ path: `${SCREENSHOT_DIR}/07_admin_users.png`, fullPage: true });

    // 7. Inspect Admin Audit Trail
    await page.goto(`${BASE_URL}/admin/audit-log`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toBeVisible();
    // Test expanding an event row if present
    const firstLogRow = page.locator('tbody tr, .audit-card').first();
    if (await firstLogRow.isVisible()) {
      await firstLogRow.click();
      await page.waitForTimeout(300);
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/08_admin_audit_log.png`, fullPage: true });
  });

  test('03. Compliance Manager Journey: Requirements, Vault, Changes, Tasks, Reports, AI Intel', async ({ page }) => {
    // 1. Login as Compliance Manager (Priya Deshmukh)
    await page.goto(`${BASE_URL}/auth/login`);
    await page.fill('input[type="email"]', 'priya.deshmukh@acme-mfg.in');
    await page.fill('input[type="password"]', 'DemoPass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });

    // 2. Requirements Register
    await page.goto(`${BASE_URL}/requirements`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Requirements');
    // Test Search input
    const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('Boiler');
      await page.waitForTimeout(500);
      await searchInput.fill('');
    }
    // Click first requirement to open details drawer
    const firstReqRow = page.locator('tbody tr, .requirement-card').first();
    if (await firstReqRow.isVisible()) {
      await firstReqRow.click();
      await page.waitForTimeout(500);
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/09_requirements_manager.png`, fullPage: true });

    // 3. Document Library & OCR Review Workbench
    await page.goto(`${BASE_URL}/documents`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Compliance Document Vault');
    // Click Upload Document button to verify modal
    const uploadBtn = page.locator('button:has-text("Upload"), button:has-text("Add Evidence")').first();
    if (await uploadBtn.isVisible()) {
      await uploadBtn.click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: `${SCREENSHOT_DIR}/10_document_upload_modal.png` });
      // Close modal
      const closeBtn = page.locator('button[aria-label="Close"], button:has-text("Cancel")').first();
      if (await closeBtn.isVisible()) await closeBtn.click();
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/11_documents_manager.png`, fullPage: true });

    // 4. Regulatory Changes Inbox
    await page.goto(`${BASE_URL}/regulatory-changes`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toBeVisible();
    await page.screenshot({ path: `${SCREENSHOT_DIR}/12_regulatory_changes_manager.png`, fullPage: true });

    // 5. Tasks & Remediation Workbench
    await page.goto(`${BASE_URL}/tasks`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toBeVisible();
    // Test Calendar toggle if available
    const calendarToggle = page.locator('button:has-text("Calendar")').first();
    if (await calendarToggle.isVisible()) {
      await calendarToggle.click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: `${SCREENSHOT_DIR}/13_tasks_calendar_view.png`, fullPage: true });
      const listToggle = page.locator('button:has-text("List")').first();
      if (await listToggle.isVisible()) await listToggle.click();
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/14_tasks_manager.png`, fullPage: true });

    // 6. Audits & Readiness Reports
    await page.goto(`${BASE_URL}/reports`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toBeVisible();
    await page.screenshot({ path: `${SCREENSHOT_DIR}/15_reports_manager.png`, fullPage: true });

    // 7. Facility Operational Profile
    await page.goto(`${BASE_URL}/company-profile`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1, h2').first()).toBeVisible();
    await page.screenshot({ path: `${SCREENSHOT_DIR}/16_company_profile_manager.png`, fullPage: true });

    // 8. AI Regulatory Intel Q&A Bench
    await page.goto(`${BASE_URL}/assistant`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Regulatory Intelligence Assistant');
    // Type sample query
    const chatInput = page.locator('input[placeholder*="Ask"], textarea').first();
    if (await chatInput.isVisible()) {
      await chatInput.fill('What are the hazardous waste storage limits under 2016 rules?');
      const sendBtn = page.locator('button:has-text("Send"), button[aria-label="Send query"]').first();
      if (await sendBtn.isVisible()) {
        await sendBtn.click();
        await page.waitForTimeout(1000);
      }
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/17_ai_assistant.png`, fullPage: true });
  });

  test('04. Read-Only Viewer / Auditor Journey: Restricted Access Verification', async ({ page }) => {
    // 1. Login as Read-Only Auditor (Sneha Patil)
    await page.goto(`${BASE_URL}/auth/login`);
    await page.fill('input[type="email"]', 'sneha.patil@acme-mfg.in');
    await page.fill('input[type="password"]', 'DemoPass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });

    // 2. Verify Viewer can view Dashboard
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Dashboard');
    await page.screenshot({ path: `${SCREENSHOT_DIR}/18_viewer_dashboard.png`, fullPage: true });

    // 3. Verify Admin Navigation Links are hidden from Viewer in Sidebar
    const adminLink = page.locator('a[href="/admin/master-data"], button:has-text("Master Data")');
    expect(await adminLink.count()).toBe(0);

    // 4. Attempt Direct Access to Admin Route: /admin/master-data -> Must show Access Restricted screen
    await page.goto(`${BASE_URL}/admin/master-data`);
    await page.waitForTimeout(800);
    const accessDenied = page.locator('h1:has-text("Access Restricted")');
    await expect(accessDenied).toBeVisible();
    await page.screenshot({ path: `${SCREENSHOT_DIR}/19_viewer_admin_blocked.png` });
  });

  test('05. Responsive Mobile & Tablet Layout Inspection', async ({ page }) => {
    // Login as Compliance Manager
    await page.goto(`${BASE_URL}/auth/login`);
    await page.fill('input[type="email"]', 'priya.deshmukh@acme-mfg.in');
    await page.fill('input[type="password"]', 'DemoPass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });

    // Set Tablet Viewport (768 x 1024)
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/20_responsive_tablet_dashboard.png`, fullPage: true });

    // Set Mobile Viewport (390 x 844 - iPhone)
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/21_responsive_mobile_dashboard.png`, fullPage: true });

    // Requirements Table on Mobile
    await page.goto(`${BASE_URL}/requirements`);
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/22_responsive_mobile_requirements.png`, fullPage: true });
  });

  test('06. System Reviewer Journey: Super Admin / System Audit Verification', async ({ page }) => {
    // Login as Compliance Auditor
    await page.goto(`${BASE_URL}/auth/login`);
    await page.fill('input[type="email"]', 'auditor@external-audit.in');
    await page.fill('input[type="password"]', 'DemoPass123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 10000 });

    // Inspect readiness reports
    await page.goto(`${BASE_URL}/reports`);
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: `${SCREENSHOT_DIR}/23_system_auditor_reports.png`, fullPage: true });
  });

  test('07. Catch-All Route: 404 Page Verification', async ({ page }) => {
    // Visit nonexistent route
    await page.goto(`${BASE_URL}/nonexistent-regulatory-route`);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Page Not Found (404)');
    await page.screenshot({ path: `${SCREENSHOT_DIR}/24_not_found_404.png` });
  });

});
