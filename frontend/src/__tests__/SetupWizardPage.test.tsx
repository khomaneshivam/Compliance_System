import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { SetupWizardPage } from '../pages/SetupWizardPage';

describe('SetupWizardPage Component', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders onboarding stepper with all 5 compliance steps', () => {
    render(
      <BrowserRouter>
        <SetupWizardPage />
      </BrowserRouter>
    );

    expect(screen.getByText(/First-Run Facility Onboarding Wizard/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Legal Entity/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Site & Facility/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/CPCB Category/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Operational Facts/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Review & Engine/i).length).toBeGreaterThanOrEqual(1);
  });

  it('allows saving draft to localStorage', () => {
    render(
      <BrowserRouter>
        <SetupWizardPage />
      </BrowserRouter>
    );

    const saveDraftBtn = screen.getByRole('button', { name: /Save Draft/i });
    expect(saveDraftBtn).toBeInTheDocument();
    fireEvent.click(saveDraftBtn);

    const draft = localStorage.getItem('plantproof_onboarding_draft');
    expect(draft).not.toBeNull();
  });

  it('navigates to step 2 when clicking Save & Continue', async () => {
    render(
      <BrowserRouter>
        <SetupWizardPage />
      </BrowserRouter>
    );

    const nextBtn = screen.getByRole('button', { name: /Save & Continue/i });
    fireEvent.click(nextBtn);

    await waitFor(() => {
      expect(screen.getByText(/Step 2: Manufacturing Site & Facility Identification/i)).toBeInTheDocument();
    });
  });
});
