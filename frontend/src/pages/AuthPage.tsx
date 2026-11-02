import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Leaf,
  Lock,
  Mail,
  Eye,
  EyeOff,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  UserCheck,
  ShieldCheck,
} from 'lucide-react';
import { useAuth, DEMO_USERS } from '../context/AuthContext';
import { api } from '../services/api';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid work email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  rememberMe: z.boolean().optional(),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const AuthPage: React.FC = () => {
  const { login, switchUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/dashboard';

  const [mode, setMode] = useState<'signin' | 'invite' | 'reset'>('signin');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [resetSuccess, setResetSuccess] = useState<boolean>(false);
  const [resetEmail, setResetEmail] = useState<string>('');
  const [resetMessage, setResetMessage] = useState<string>('');
  const [resetDebugToken, setResetDebugToken] = useState<string | null>(null);
  const [resetSubmitting, setResetSubmitting] = useState<boolean>(false);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: import.meta.env.DEV
      ? {
          email: 'rohit.sharma@acme-mfg.in',
          password: 'Password123!',
          rememberMe: true,
        }
      : {
          email: '',
          password: '',
          rememberMe: false,
        },
  });

  const onSubmit = async (data: LoginFormData) => {
    setAuthError(null);
    try {
      await login(data.email, data.password);
      navigate(from, { replace: true });
    } catch (err: unknown) {
      setAuthError((err as Error).message || 'Invalid credentials. Please verify your email and password.');
    }
  };

  const onResetRequest = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthError(null);
    setResetSubmitting(true);
    try {
      const result = await api.requestPasswordReset(resetEmail.trim());
      setResetMessage(result.message);
      setResetDebugToken(result.debug_token || null);
      setResetSuccess(true);
    } catch (err: unknown) {
      setAuthError((err as Error).message || 'Unable to request password reset.');
    } finally {
      setResetSubmitting(false);
    }
  };

  const handleDemoSelect = (userId: string, email: string) => {
    setValue('email', email);
    setValue('password', 'Password123!');
    switchUser(userId);
    navigate(from, { replace: true });
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#f8fafc',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '24px 16px',
      }}
    >
      {/* Brand Header */}
      <div style={{ textAlign: 'center', marginBottom: '24px' }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            color: '#059669',
            marginBottom: '8px',
          }}
        >
          <Leaf size={32} strokeWidth={2.4} />
          <h1 style={{ fontSize: '26px', fontWeight: 800, color: '#0f172a', letterSpacing: '-0.02em', margin: 0 }}>
            PlantProof
          </h1>
        </div>
        <p style={{ color: '#64748b', fontSize: '13.5px', margin: 0 }}>
          Enterprise Regulatory Intelligence & Compliance-Evidence Platform
        </p>
      </div>

      {/* Main Authentication Card */}
      <div
        style={{
          width: '100%',
          maxWidth: '440px',
          backgroundColor: '#ffffff',
          borderRadius: '12px',
          border: '1px solid #e2e8f0',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)',
          overflow: 'hidden',
        }}
      >
        {/* Mode Navigation Tabs */}
        <div style={{ display: 'flex', borderBottom: '1px solid #e2e8f0', backgroundColor: '#f8fafc' }}>
          <button
            type="button"
            onClick={() => {
              setMode('signin');
              setAuthError(null);
            }}
            style={{
              flex: 1,
              padding: '12px',
              fontSize: '13px',
              fontWeight: mode === 'signin' ? 600 : 500,
              color: mode === 'signin' ? '#059669' : '#64748b',
              border: 'none',
              borderBottom: mode === 'signin' ? '2px solid #059669' : '2px solid transparent',
              backgroundColor: mode === 'signin' ? '#ffffff' : 'transparent',
              cursor: 'pointer',
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('invite');
              setAuthError(null);
            }}
            style={{
              flex: 1,
              padding: '12px',
              fontSize: '13px',
              fontWeight: mode === 'invite' ? 600 : 500,
              color: mode === 'invite' ? '#059669' : '#64748b',
              border: 'none',
              borderBottom: mode === 'invite' ? '2px solid #059669' : '2px solid transparent',
              backgroundColor: mode === 'invite' ? '#ffffff' : 'transparent',
              cursor: 'pointer',
            }}
          >
            Accept Invite
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('reset');
              setAuthError(null);
            }}
            style={{
              flex: 1,
              padding: '12px',
              fontSize: '13px',
              fontWeight: mode === 'reset' ? 600 : 500,
              color: mode === 'reset' ? '#059669' : '#64748b',
              border: 'none',
              borderBottom: mode === 'reset' ? '2px solid #059669' : '2px solid transparent',
              backgroundColor: mode === 'reset' ? '#ffffff' : 'transparent',
              cursor: 'pointer',
            }}
          >
            Password Reset
          </button>
        </div>

        {/* Form Body */}
        <div style={{ padding: '28px 24px' }}>
          {authError && (
            <div
              style={{
                padding: '10px 14px',
                borderRadius: '6px',
                backgroundColor: '#fef2f2',
                border: '1px solid #fecaca',
                color: '#991b1b',
                fontSize: '12.5px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '16px',
              }}
            >
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{authError}</span>
            </div>
          )}

          {mode === 'signin' && (
            <form onSubmit={handleSubmit(onSubmit)}>
              <div style={{ marginBottom: '16px' }}>
                <label
                  htmlFor="email-input"
                  style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}
                >
                  Work Email Address
                </label>
                <div style={{ position: 'relative' }}>
                  <Mail size={16} color="#94a3b8" style={{ position: 'absolute', left: '10px', top: '11px' }} />
                  <input
                    id="email-input"
                    type="email"
                    {...register('email')}
                    placeholder="name@company.com"
                    style={{
                      width: '100%',
                      padding: '8px 12px 8px 34px',
                      borderRadius: '6px',
                      border: errors.email ? '1px solid #dc2626' : '1px solid #cbd5e1',
                      fontSize: '13px',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>
                {errors.email && (
                  <span style={{ fontSize: '11.5px', color: '#dc2626', marginTop: '4px', display: 'block' }}>
                    {errors.email.message}
                  </span>
                )}
              </div>

              <div style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label
                    htmlFor="password-input"
                    style={{ fontSize: '12.5px', fontWeight: 600, color: '#334155' }}
                  >
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => setMode('reset')}
                    style={{ background: 'none', border: 'none', color: '#059669', fontSize: '11.5px', cursor: 'pointer' }}
                  >
                    Forgot password?
                  </button>
                </div>
                <div style={{ position: 'relative' }}>
                  <Lock size={16} color="#94a3b8" style={{ position: 'absolute', left: '10px', top: '11px' }} />
                  <input
                    id="password-input"
                    type={showPassword ? 'text' : 'password'}
                    {...register('password')}
                    placeholder="Enter your account password"
                    style={{
                      width: '100%',
                      padding: '8px 36px 8px 34px',
                      borderRadius: '6px',
                      border: errors.password ? '1px solid #dc2626' : '1px solid #cbd5e1',
                      fontSize: '13px',
                      boxSizing: 'border-box',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    style={{
                      position: 'absolute',
                      right: '10px',
                      top: '10px',
                      background: 'none',
                      border: 'none',
                      color: '#94a3b8',
                      cursor: 'pointer',
                    }}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {errors.password && (
                  <span style={{ fontSize: '11.5px', color: '#dc2626', marginTop: '4px', display: 'block' }}>
                    {errors.password.message}
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
                <input type="checkbox" id="remember-me" {...register('rememberMe')} />
                <label htmlFor="remember-me" style={{ fontSize: '12.5px', color: '#475569', cursor: 'pointer' }}>
                  Keep me signed in on this computer
                </label>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="btn btn-primary"
                style={{
                  width: '100%',
                  padding: '10px',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '13.5px',
                  backgroundColor: '#059669',
                  borderColor: '#059669',
                }}
              >
                <span>{isSubmitting ? 'Authenticating...' : 'Sign In to PlantProof'}</span>
                <ArrowRight size={15} />
              </button>
            </form>
          )}

          {mode === 'invite' && (
            <div style={{ textAlign: 'center', padding: '16px 0' }}>
              <p style={{ fontSize: '13px', color: '#475569', lineHeight: 1.6, marginBottom: '18px' }}>
                Invitations are single-use and expire after 24 hours. Open the secure link sent to your work email, or enter the invitation token on the acceptance page.
              </p>
              <button
                type="button"
                onClick={() => navigate('/accept-invitation')}
                className="btn btn-primary"
                style={{ width: '100%', backgroundColor: '#059669', borderColor: '#059669' }}
              >
                Enter Invitation Token
              </button>
            </div>
          )}

          {mode === 'reset' && (
            <div>
              {resetSuccess ? (
                <div style={{ textAlign: 'center', padding: '16px 0' }}>
                  <CheckCircle2 size={36} color="#059669" style={{ margin: '0 auto 12px' }} />
                  <h3 style={{ fontSize: '15px', color: '#0f172a', marginBottom: '6px' }}>Check your email</h3>
                  <p style={{ fontSize: '12.5px', color: '#64748b', marginBottom: '16px' }}>
                    {resetMessage}
                  </p>
                  {resetDebugToken && (
                    <button
                      type="button"
                      onClick={() => navigate(`/reset-password?token=${encodeURIComponent(resetDebugToken)}`)}
                      className="btn btn-secondary"
                      style={{ width: '100%', marginBottom: '10px' }}
                    >
                      Open development reset link
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      setMode('signin');
                      setResetSuccess(false);
                      setResetDebugToken(null);
                      setResetMessage('');
                    }}
                    className="btn btn-secondary"
                    style={{ width: '100%' }}
                  >
                    Return to Sign In
                  </button>
                </div>
              ) : (
                <form onSubmit={onResetRequest}>
                  <div style={{ marginBottom: '16px' }}>
                    <label htmlFor="reset-email" style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                      Your Registered Email Address
                    </label>
                    <input
                      id="reset-email"
                      type="email"
                      placeholder="name@company.com"
                      autoComplete="email"
                      required
                      value={resetEmail}
                      onChange={(event) => setResetEmail(event.target.value)}
                      style={{
                        width: '100%',
                        padding: '8px 12px',
                        borderRadius: '6px',
                        border: '1px solid #cbd5e1',
                        fontSize: '13px',
                        boxSizing: 'border-box',
                      }}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={resetSubmitting}
                    className="btn btn-primary"
                    style={{ width: '100%', backgroundColor: '#059669', borderColor: '#059669' }}
                  >
                    {resetSubmitting ? 'Requesting reset…' : 'Send Password Reset Instructions'}
                  </button>
                </form>
              )}
            </div>
          )}
        </div>

        {import.meta.env.DEV && (
          <>
          {/* Demo Fast-Switch Section */}
          <div
            style={{
              padding: '16px 24px',
              backgroundColor: '#f8fafc',
              borderTop: '1px solid #e2e8f0',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11.5px', fontWeight: 600, color: '#475569', marginBottom: '10px' }}>
              <UserCheck size={14} color="#059669" />
              <span>Select Demo Role to Sign In Directly:</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {DEMO_USERS.map((u) => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => handleDemoSelect(u.id, u.email)}
                  style={{
                    padding: '7px 10px',
                    borderRadius: '6px',
                    border: '1px solid #e2e8f0',
                    backgroundColor: '#ffffff',
                    textAlign: 'left',
                    fontSize: '12px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    cursor: 'pointer',
                    transition: 'background-color 0.15s ease',
                  }}
                  className="table-row-hover"
                >
                  <div>
                    <span style={{ fontWeight: 600, color: '#0f172a' }}>{u.fullName}</span>
                    <span style={{ color: '#64748b', marginLeft: '6px' }}>({u.email})</span>
                  </div>
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      backgroundColor: '#ecfdf5',
                      color: '#059669',
                    }}
                  >
                    {u.role.replace(/_/g, ' ')}
                  </span>
                </button>
              ))}
            </div>
          </div>
          </>
        )}
      </div>

      {/* Security & Regulatory Note */}
      <div style={{ marginTop: '20px', display: 'flex', alignItems: 'center', gap: '6px', color: '#94a3b8', fontSize: '11.5px' }}>
        <ShieldCheck size={14} />
        <span>Multi-Tenant Enterprise Isolation • JWT Session Authentication</span>
      </div>
    </div>
  );
};
