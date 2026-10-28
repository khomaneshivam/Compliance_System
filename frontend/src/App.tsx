import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { AppLayout } from './components/layout/AppLayout';

// Core Pages
import { AuthPage } from './pages/AuthPage';
import { SetupWizardPage } from './pages/SetupWizardPage';
import { DashboardPage } from './pages/DashboardPage';
import { RequirementsPage } from './pages/RequirementsPage';
import { DocumentReviewPage } from './pages/DocumentReviewPage';
import { RegulatoryChangeDetailPage } from './pages/RegulatoryChangeDetailPage';
import { TasksPage } from './pages/TasksPage';
import { ReportsPage } from './pages/ReportsPage';
import { CompanyProfilePage } from './pages/CompanyProfilePage';
import { AIAssistantPage } from './pages/AIAssistantPage';
import { DesignPlaygroundPage } from './pages/DesignPlaygroundPage';

// Governance & Admin Pages
import { AdminMasterDataPage } from './pages/AdminMasterDataPage';
import { AdminRulesPage } from './pages/AdminRulesPage';
import { AdminUsersPage } from './pages/AdminUsersPage';
import { AdminAuditLogPage } from './pages/AdminAuditLogPage';

import { ShieldAlert, ArrowLeft } from 'lucide-react';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public Authentication Screen */}
            <Route path="/auth/login" element={<AuthPage />} />

            {/* Authenticated Application Routes (Protected with Role-Aware AppLayout) */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Navigate to="/dashboard" replace />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <DashboardPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/setup-wizard"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <SetupWizardPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/requirements"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <RequirementsPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/documents"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <DocumentReviewPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/regulatory-changes"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <RegulatoryChangeDetailPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/tasks"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <TasksPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/reports"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <ReportsPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/company-profile"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <CompanyProfilePage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/assistant"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <AIAssistantPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/design-playground"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <DesignPlaygroundPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            {/* Admin & Governance Routes (Restricted to ADMIN / SUPER_ADMIN) */}
            <Route
              path="/admin/master-data"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'SUPER_ADMIN']}>
                  <AppLayout>
                    <AdminMasterDataPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/admin/rules"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'SUPER_ADMIN']}>
                  <AppLayout>
                    <AdminRulesPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/admin/users"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'SUPER_ADMIN']}>
                  <AppLayout>
                    <AdminUsersPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="/admin/audit-log"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'SUPER_ADMIN']}>
                  <AppLayout>
                    <AdminAuditLogPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />

            {/* 404 / Catch-All Route */}
            <Route
              path="*"
              element={
                <div style={{ padding: '60px 24px', textAlign: 'center', maxWidth: '560px', margin: '40px auto' }}>
                  <div
                    style={{
                      width: '56px',
                      height: '56px',
                      borderRadius: '50%',
                      backgroundColor: '#f1f5f9',
                      color: '#475569',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto 16px',
                    }}
                  >
                    <ShieldAlert size={28} />
                  </div>
                  <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#0f172a', marginBottom: '8px' }}>
                    Page Not Found (404)
                  </h1>
                  <p style={{ color: '#64748b', fontSize: '13.5px', lineHeight: 1.6, marginBottom: '24px' }}>
                    The requested compliance route does not exist or has been relocated within the PlantProof regulatory navigation.
                  </p>
                  <Link
                    to="/dashboard"
                    className="btn btn-primary"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
                  >
                    <ArrowLeft size={14} />
                    <span>Return to Executive Dashboard</span>
                  </Link>
                </div>
              }
            />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
