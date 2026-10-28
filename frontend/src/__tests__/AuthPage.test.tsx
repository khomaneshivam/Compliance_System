import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { AuthPage } from '../pages/AuthPage';

describe('AuthPage Component', () => {
  it('renders sign in screen with email, password fields and demo persona switcher', () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <AuthPage />
        </AuthProvider>
      </BrowserRouter>
    );

    expect(screen.getAllByText(/PlantProof/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/Enterprise Regulatory Intelligence/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Work Email Address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Password$/i)).toBeInTheDocument();
    expect(screen.getByText(/Select Demo Role to Sign In Directly/i)).toBeInTheDocument();
    expect(screen.getByText(/Rohit Sharma/i)).toBeInTheDocument();
    expect(screen.getByText(/Anil Kapoor/i)).toBeInTheDocument();
  });

  it('switches between Sign In, Accept Invite, and Password Reset tabs', () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <AuthPage />
        </AuthProvider>
      </BrowserRouter>
    );

    // Click Accept Invite tab
    const inviteTab = screen.getByRole('button', { name: /Accept Invite/i });
    fireEvent.click(inviteTab);
    expect(screen.getByText(/Invitation \/ Token Code/i)).toBeInTheDocument();
    expect(screen.getByText(/Set Account Password/i)).toBeInTheDocument();

    // Click Password Reset tab
    const resetTab = screen.getByRole('button', { name: /Password Reset/i });
    fireEvent.click(resetTab);
    expect(screen.getByText(/Your Registered Email Address/i)).toBeInTheDocument();
  });

  it('populates demo credentials when clicking a persona button', async () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <AuthPage />
        </AuthProvider>
      </BrowserRouter>
    );

    const rohitBtn = screen.getByText(/Rohit Sharma/i);
    fireEvent.click(rohitBtn);

    const emailInput = screen.getByLabelText(/Work Email Address/i) as HTMLInputElement;
    expect(emailInput.value).toBe('rohit.sharma@acme-mfg.in');
  });
});
