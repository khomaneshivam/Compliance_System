import React, { useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../services/api';

export const ResetPasswordPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const initialToken = useMemo(
    () => new URLSearchParams(location.hash.replace(/^#/, '')).get('token') || '',
    [location.hash],
  );
  const [token, setToken] = useState(initialToken);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [complete, setComplete] = useState(false);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (newPassword.length < 12) {
      setError('Use a password with at least 12 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('The passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      await api.completePasswordReset(token.trim(), newPassword);
      // Reset increments the server-side credential version. Remove any local
      // access token so this browser must authenticate again with the new password.
      api.setToken(null);
      setComplete(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Password reset failed.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main
      style={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        padding: '24px 16px',
        background: '#f8fafc',
      }}
    >
      <section
        style={{
          width: '100%',
          maxWidth: '440px',
          padding: '28px',
          background: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: '12px',
          boxShadow: '0 4px 12px rgba(15, 23, 42, 0.05)',
        }}
      >
        <h1 style={{ margin: '0 0 8px', color: '#0f172a', fontSize: '22px' }}>
          Reset your PlantProof password
        </h1>
        <p style={{ margin: '0 0 22px', color: '#64748b', fontSize: '13px', lineHeight: 1.6 }}>
          Password reset links are single-use and expire after one hour. Completing a reset revokes the account’s existing access tokens.
        </p>

        {complete ? (
          <div role="status" aria-live="polite">
            <h2 style={{ margin: '0 0 8px', color: '#166534', fontSize: '16px' }}>Password updated</h2>
            <p style={{ color: '#475569', fontSize: '13px', lineHeight: 1.6 }}>
              Your password has been changed. Sign in again with your new password.
            </p>
            <button
              type="button"
              onClick={() => navigate('/auth/login', { replace: true })}
              className="btn btn-primary"
              style={{ width: '100%' }}
            >
              Continue to sign in
            </button>
          </div>
        ) : (
          <form onSubmit={submit}>
            <label htmlFor="reset-token" style={{ display: 'block', marginBottom: '6px', fontSize: '12px', fontWeight: 600, color: '#334155' }}>
              Reset token
            </label>
            <input
              id="reset-token"
              autoComplete="off"
              required
              minLength={32}
              value={token}
              onChange={(event) => setToken(event.target.value)}
              style={{
                width: '100%',
                boxSizing: 'border-box',
                marginBottom: '16px',
                padding: '10px 12px',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                fontSize: '13px',
              }}
            />

            <label htmlFor="new-password" style={{ display: 'block', marginBottom: '6px', fontSize: '12px', fontWeight: 600, color: '#334155' }}>
              New password
            </label>
            <input
              id="new-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={12}
              maxLength={128}
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              style={{
                width: '100%',
                boxSizing: 'border-box',
                marginBottom: '16px',
                padding: '10px 12px',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                fontSize: '13px',
              }}
            />

            <label htmlFor="confirm-password" style={{ display: 'block', marginBottom: '6px', fontSize: '12px', fontWeight: 600, color: '#334155' }}>
              Confirm new password
            </label>
            <input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={12}
              maxLength={128}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              style={{
                width: '100%',
                boxSizing: 'border-box',
                marginBottom: '16px',
                padding: '10px 12px',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                fontSize: '13px',
              }}
            />

            {error && (
              <div role="alert" style={{ marginBottom: '16px', padding: '10px 12px', border: '1px solid #fecaca', borderRadius: '6px', background: '#fef2f2', color: '#991b1b', fontSize: '12px' }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={submitting} className="btn btn-primary" style={{ width: '100%' }}>
              {submitting ? 'Updating password…' : 'Update password'}
            </button>
          </form>
        )}

        {!complete && (
          <p style={{ margin: '18px 0 0', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
            Need another reset link? <Link to="/auth/login" style={{ color: '#047857' }}>Request a new one</Link>
          </p>
        )}
      </section>
    </main>
  );
};
