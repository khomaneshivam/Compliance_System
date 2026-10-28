import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { Header } from '../components/layout/Header';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    getNotifications: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'notif-1',
          plant_id: 'plant-pune-01',
          notification_type: 'OVERDUE',
          entity_type: 'TASK',
          entity_id: 'task-101',
          title: 'Stack Emission Testing Overdue',
          message: 'Stack test was due yesterday.',
          channel: 'IN_APP',
          status: 'UNREAD',
          sent_at: '2026-10-28T10:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 10,
      unread_count: 1,
    }),
    markNotificationRead: vi.fn().mockResolvedValue({ id: 'notif-1', status: 'READ' }),
    markAllNotificationsRead: vi.fn().mockResolvedValue({ message: 'Marked 1 read', count: 1 }),
    runReminderScan: vi.fn().mockResolvedValue({
      scan_date: '2026-10-28',
      scanned_tasks_count: 5,
      scanned_requirements_count: 12,
      generated_count: 2,
      deduplicated_count: 0,
    }),
    getNotificationPreferences: vi.fn().mockResolvedValue({
      email_enabled: true,
      in_app_enabled: true,
      lead_time_days: 30,
      notify_on_overdue: true,
      frequency: 'IMMEDIATE',
    }),
    updateNotificationPreferences: vi.fn().mockResolvedValue({
      email_enabled: true,
      in_app_enabled: true,
      lead_time_days: 60,
      notify_on_overdue: true,
      frequency: 'IMMEDIATE',
    }),
  },
}));

describe('Header Notification & Preferences Component', () => {
  const dummyUser = {
    id: 'user-rohit-01',
    email: 'rohit.sharma@acme-mfg.in',
    fullName: 'Rohit Sharma',
    role: 'PLANT_MANAGER' as const,
    tenantId: 'tenant-acme-01',
    tenantName: 'Acme Manufacturing Group',
    plantIds: ['plant-pune-01'],
  };

  it('renders notification bell and shows unread badge', async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Header user={dummyUser} />
        </AuthProvider>
      </MemoryRouter>
    );

    const bellBtn = screen.getByLabelText(/notifications/i);
    expect(bellBtn).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument();
    });
  });

  it('toggles notification drawer and displays notification items', async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Header user={dummyUser} />
        </AuthProvider>
      </MemoryRouter>
    );

    const bellBtn = screen.getByLabelText(/notifications/i);
    fireEvent.click(bellBtn);

    await waitFor(() => {
      expect(screen.getByText('Notifications & Reminders')).toBeInTheDocument();
      expect(screen.getByText('Stack Emission Testing Overdue')).toBeInTheDocument();
    });
  });

  it('opens notification preferences modal and allows editing alert channels', async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Header user={dummyUser} />
        </AuthProvider>
      </MemoryRouter>
    );

    const bellBtn = screen.getByLabelText(/notifications/i);
    fireEvent.click(bellBtn);

    await waitFor(() => {
      expect(screen.getByText('Preferences')).toBeInTheDocument();
    });

    const prefBtn = screen.getByText('Preferences');
    fireEvent.click(prefBtn);

    await waitFor(() => {
      expect(screen.getByText('Compliance Notification Preferences')).toBeInTheDocument();
      expect(screen.getByText('Reminder Lead Time (Days Before Expiry/Due Date)')).toBeInTheDocument();
      expect(screen.getByText('In-App Notifications')).toBeInTheDocument();
      expect(screen.getByText('Email Notifications')).toBeInTheDocument();
    });
  });
});
