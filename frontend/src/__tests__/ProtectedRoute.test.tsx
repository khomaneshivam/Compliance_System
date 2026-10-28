import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';

describe('ProtectedRoute Component & RBAC', () => {
  it('renders children when user role matches allowedRoles', () => {
    render(
      <MemoryRouter initialEntries={['/admin/users']}>
        <AuthProvider>
          <Routes>
            <Route
              path="/admin/users"
              element={
                <ProtectedRoute allowedRoles={['PLANT_MANAGER', 'ADMIN']}>
                  <div>Protected Admin Content</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    // Default demo user is Rohit Sharma (PLANT_MANAGER)
    expect(screen.getByText('Protected Admin Content')).toBeInTheDocument();
  });

  it('renders Screen 18 Permission Denied when user role is not authorized', () => {
    render(
      <MemoryRouter initialEntries={['/admin/rules']}>
        <AuthProvider>
          <Routes>
            <Route
              path="/admin/rules"
              element={
                <ProtectedRoute allowedRoles={['SUPER_ADMIN']}>
                  <div>Super Admin Secret Area</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    // Rohit Sharma (PLANT_MANAGER) does not have SUPER_ADMIN
    expect(screen.getByText(/Access Restricted \/ Permission Denied/i)).toBeInTheDocument();
    expect(screen.getByText(/Your active role/i)).toBeInTheDocument();
    expect(screen.queryByText('Super Admin Secret Area')).not.toBeInTheDocument();
  });
});
