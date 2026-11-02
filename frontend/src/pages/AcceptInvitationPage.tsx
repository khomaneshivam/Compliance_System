import React, { useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../services/api';

export const AcceptInvitationPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const initialToken = useMemo(
    () => new URLSearchParams(location.hash.replace(/^#/, '')).get('token') || '',
    [location.hash],
  );
  const [token, setToken] = useState(initialToken);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [accepted, setAccepted] = useState(false);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (password.length < 12) {
      setError('Use a password with at least 12 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('The passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      await api.acceptInvitation(token.trim(), password);
      setAccepted(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Invitation acceptance failed.');
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
          Accept PlantProof invitation
        </h1>
        <p style={{ margin: '0 0 22px', color: '#64748b', fontSize: '13px', lineHeight: 1.6 }}>
          Redeem your one-time invitation and create your account password. Invitation links expire after 24 hours.
        </p>

        {accepted ? (
          <div role="status" aria-live="polite">
            <h2 style={{ margin: '0 0 8px', color: '#166534', fontSize: '16px' }}>Account activated</h2>
            <p style={{ color: '#475569', fontSize: '13px', lineHeight: 1.6 }}>
              Your invitation has been accepted. Sign in using the email address that received the invitation and the password you just created.
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
            <label htmlFor="invitation-token" style={{ display: 'block', marginBottom: '6px', fontSize: '12px', fontWeight: 600, color: '#334155' }}>
              Invitation token
            </label>
            <input
              id="invitation-token"
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
              Create password
            </label>
            <input
              id="new-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={12}
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
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
              Confirm password
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
              {submitting ? 'Activating account…' : 'Accept invitation and activate account'}
            </button>
          </form>
        )}

        {!accepted && (
          <p style={{ margin: '18px 0 0', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
            Already have an account? <Link to="/auth/login" style={{ color: '#047857' }}>Sign in</Link>
          </p>
        )}
      </section>
    </main>
  );
};
