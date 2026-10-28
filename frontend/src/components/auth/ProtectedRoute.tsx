import React from 'react';
import { Navigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import type { Role } from '../../types';
import { ShieldAlert, ArrowLeft, UserCheck } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: Role[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { user, isAuthenticated, hasRole, switchRole } = useAuth();
  const location = useLocation();

  if (!isAuthenticated || !user) {
    return <Navigate to="/auth/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !hasRole(allowedRoles)) {
    return (
      <div style={{ padding: '60px 24px', maxWidth: '640px', margin: '40px auto', textAlign: 'center' }}>
        <div
          style={{
            width: '56px',
            height: '56px',
            borderRadius: '50%',
            backgroundColor: '#fef2f2',
            color: '#dc2626',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px',
          }}
        >
          <ShieldAlert size={28} />
        </div>
        <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#0f172a', marginBottom: '8px' }}>
          Access Restricted / Permission Denied
        </h1>
        <p style={{ color: '#64748b', fontSize: '13.5px', lineHeight: 1.6, marginBottom: '20px' }}>
          Your active role (<strong>{user.role}</strong>) does not have authorization to access this administrative or governance module. This area is restricted to: {allowedRoles.join(', ')}.
        </p>

        <div
          style={{
            backgroundColor: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '24px',
            textAlign: 'left',
            fontSize: '12.5px',
            color: '#334155',
          }}
        >
          <strong>Need Access?</strong>
          <div style={{ marginTop: '4px', color: '#64748b' }}>
            Contact your enterprise tenant administrator (e.g. Anil Kapoor) to request role elevation or permissions assignment.
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <Link
            to="/dashboard"
            className="btn btn-secondary"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <ArrowLeft size={14} />
            <span>Return to Dashboard</span>
          </Link>

          {/* Quick Demo Switcher helper */}
          <button
            onClick={() => switchRole(allowedRoles[0])}
            className="btn btn-primary"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#059669',
              borderColor: '#059669',
            }}
          >
            <UserCheck size={14} />
            <span>Switch Role to {allowedRoles[0]} (Demo)</span>
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};
