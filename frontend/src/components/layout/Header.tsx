import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import {
  Search,
  Bell,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sparkles,
  RefreshCw,
  Send,
  Building2,
  ChevronDown,
  UserCheck,
  LogOut,
  Menu,
  Sliders,
  X,
} from 'lucide-react';
import type { User, NotificationItem, NotificationPreference } from '../../types';
import { api } from '../../services/api';
import { useAuth, DEMO_USERS } from '../../context/AuthContext';

interface HeaderProps {
  user: User;
  onOpenAiAssistant?: () => void;
  onToggleMobileMenu?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ user, onOpenAiAssistant, onToggleMobileMenu }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { activePlantId, switchPlant, switchUser, logout } = useAuth();

  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [showNotifications, setShowNotifications] = useState<boolean>(false);
  const [showUserDropdown, setShowUserDropdown] = useState<boolean>(false);
  const [showPlantDropdown, setShowPlantDropdown] = useState<boolean>(false);
  const [scanning, setScanning] = useState<boolean>(false);
  const [showPreferencesModal, setShowPreferencesModal] = useState<boolean>(false);
  const [preferences, setPreferences] = useState<NotificationPreference | null>(null);
  const [savingPreferences, setSavingPreferences] = useState<boolean>(false);
  const [prefMessage, setPrefMessage] = useState<string | null>(null);

  const notifRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const plantMenuRef = useRef<HTMLDivElement>(null);

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase();
  };

  const fetchNotifications = useCallback(async () => {
    try {
      const data = await api.getNotifications({ page: 1, page_size: 10 });
      setNotifications(data.items);
      setUnreadCount(data.unread_count);
    } catch {
      // Local fallback
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 12000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  // Global click outside listener
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setShowUserDropdown(false);
      }
      if (plantMenuRef.current && !plantMenuRef.current.contains(e.target as Node)) {
        setShowPlantDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Global keyboard shortcut: Ctrl+K / Cmd+K triggers AI Assistant
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        onOpenAiAssistant?.();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onOpenAiAssistant]);

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setUnreadCount(0);
      setNotifications((prev) => prev.map((n) => ({ ...n, status: 'READ' })));
    } catch (err) {
      console.error('Failed to mark all read', err);
    }
  };

  const handleMarkSingleRead = async (id: string) => {
    try {
      await api.markNotificationRead(id);
      setUnreadCount((c) => Math.max(0, c - 1));
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, status: 'READ' } : n))
      );
    } catch (err) {
      console.error('Failed to mark read', err);
    }
  };

  const handleRunScan = async () => {
    setScanning(true);
    try {
      const res = await api.runReminderScan();
      alert(
        `Reminder Scan Completed Successfully!\nScanned Tasks: ${res.scanned_tasks_count}\nScanned Requirements: ${res.scanned_requirements_count}\nNew Notifications: ${res.generated_count}\nDeduplicated: ${res.deduplicated_count}`
      );
      fetchNotifications();
    } catch (err: unknown) {
      alert((err as Error).message || 'Failed to execute reminder scan.');
    } finally {
      setScanning(false);
    }
  };

  const handleSendTest = async () => {
    try {
      await api.sendTestNotification({
        channel: 'IN_APP',
        notification_type: 'SYSTEM_TEST',
        title: 'Factory Safety Test Reminder',
        message: 'This is a test notification generated via the Test Notification Adapter.',
      });
      fetchNotifications();
    } catch (err: unknown) {
      alert((err as Error).message || 'Failed to dispatch test notification.');
    }
  };

  const fetchPreferences = useCallback(async () => {
    try {
      const data = await api.getNotificationPreferences();
      setPreferences(data);
    } catch (err) {
      console.error('Failed to load notification preferences', err);
    }
  }, []);

  const handleOpenPreferences = () => {
    fetchPreferences();
    setShowPreferencesModal(true);
    setShowNotifications(false);
  };

  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!preferences) return;
    setSavingPreferences(true);
    setPrefMessage(null);
    try {
      const updated = await api.updateNotificationPreferences(preferences);
      setPreferences(updated);
      setPrefMessage('Notification preferences updated successfully.');
      setTimeout(() => setPrefMessage(null), 3000);
    } catch (err) {
      alert((err as Error).message || 'Failed to update preferences.');
    } finally {
      setSavingPreferences(false);
    }
  };

  const handleNotificationClick = async (item: NotificationItem) => {
    if (item.status === 'UNREAD') {
      await handleMarkSingleRead(item.id);
    }
    setShowNotifications(false);
    if (item.entity_type === 'TASK') {
      navigate('/tasks');
    } else if (item.entity_type === 'REQUIREMENT') {
      navigate('/requirements');
    } else if (item.entity_type === 'DOCUMENT') {
      navigate('/documents');
    } else if (item.entity_type === 'REGULATORY_CHANGE') {
      navigate('/regulatory-changes');
    }
  };

  // Human readable breadcrumb title generator
  const getBreadcrumbs = () => {
    const path = location.pathname;
    if (path.startsWith('/dashboard') || path === '/') {
      return [{ label: 'PlantProof', href: '/dashboard' }, { label: 'Executive Dashboard' }];
    }
    if (path.startsWith('/setup-wizard')) {
      return [{ label: 'PlantProof', href: '/dashboard' }, { label: 'Facility Onboarding Wizard' }];
    }
    if (path.startsWith('/requirements')) {
      return [{ label: 'Operations', href: '/dashboard' }, { label: 'Requirements Register' }];
    }
    if (path.startsWith('/documents')) {
      return [{ label: 'Operations', href: '/dashboard' }, { label: 'Document Library & OCR Workbench' }];
    }
    if (path.startsWith('/regulatory-changes')) {
      return [{ label: 'Operations', href: '/dashboard' }, { label: 'Gazette Changes & Impact Review' }];
    }
    if (path.startsWith('/tasks')) {
      return [{ label: 'Operations', href: '/dashboard' }, { label: 'Tasks & Remediation Calendar' }];
    }
    if (path.startsWith('/reports')) {
      return [{ label: 'Operations', href: '/dashboard' }, { label: 'Audit Readiness & Report Generator' }];
    }
    if (path.startsWith('/company-profile')) {
      return [{ label: 'Operations', href: '/dashboard' }, { label: 'Facility Profile & Operational Facts' }];
    }
    if (path.startsWith('/admin/master-data')) {
      return [{ label: 'Governance', href: '/admin/users' }, { label: 'Statutory Master Data' }];
    }
    if (path.startsWith('/admin/rules')) {
      return [{ label: 'Governance', href: '/admin/users' }, { label: 'Rule Review & Test Bench' }];
    }
    if (path.startsWith('/admin/users')) {
      return [{ label: 'Governance', href: '/admin/users' }, { label: 'Team, Roles & RBAC Matrix' }];
    }
    if (path.startsWith('/admin/audit-log')) {
      return [{ label: 'Governance', href: '/admin/users' }, { label: 'Enterprise Audit Trail' }];
    }
    if (path.startsWith('/assistant')) {
      return [{ label: 'Intelligence', href: '/dashboard' }, { label: 'AI Statutory Assistant' }];
    }
    return [{ label: 'PlantProof', href: '/dashboard' }, { label: 'Compliance Workspace' }];
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <header className="top-header" style={{ position: 'relative' }}>
      {/* Left: Breadcrumbs & Page Context */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
        <button
          type="button"
          className="mobile-menu-toggle"
          onClick={onToggleMobileMenu}
          aria-label="Toggle navigation menu"
        >
          <Menu size={20} />
        </button>
        <nav
          className="breadcrumb-nav"
          aria-label="Breadcrumbs"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '13px',
            color: '#64748b',
          }}
        >
          {breadcrumbs.map((crumb, idx) => (
            <React.Fragment key={idx}>
              {idx > 0 && <span style={{ color: '#cbd5e1' }}>/</span>}
              {crumb.href ? (
                <Link
                  to={crumb.href}
                  style={{ color: '#475569', textDecoration: 'none', fontWeight: 500 }}
                  className="hover-underline"
                >
                  {crumb.label}
                </Link>
              ) : (
                <span style={{ color: '#0f172a', fontWeight: 600 }}>{crumb.label}</span>
              )}
            </React.Fragment>
          ))}
        </nav>
      </div>

      {/* Center: Global Search */}
      <div className="search-bar" style={{ maxWidth: '340px' }}>
        <Search size={16} color="var(--text-muted)" />
        <input
          type="text"
          className="search-input"
          placeholder="Search obligations, rules, gazettes..."
        />
      </div>

      {/* Right: Header Actions */}
      <div className="header-actions">
        {/* Plant / Facility Context Switcher */}
        <div style={{ position: 'relative' }} ref={plantMenuRef}>
          <button
            onClick={() => setShowPlantDropdown((v) => !v)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#f1f5f9',
              border: '1px solid #cbd5e1',
              borderRadius: '6px',
              padding: '6px 10px',
              fontSize: '12px',
              fontWeight: 600,
              color: '#334155',
              cursor: 'pointer',
            }}
            title="Switch Active Manufacturing Facility"
          >
            <Building2 size={14} color="#059669" />
            <span>
              {activePlantId === 'plant-pune-01' ? 'Pune MIDC Plant' : 'Vapi GIDC Plant'}
            </span>
            <ChevronDown size={13} color="#64748b" />
          </button>

          {showPlantDropdown && (
            <div
              style={{
                position: 'absolute',
                top: '36px',
                right: '0',
                width: '240px',
                backgroundColor: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
                zIndex: 1100,
                padding: '6px 0',
              }}
            >
              <div
                style={{
                  padding: '6px 12px',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: '#94a3b8',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Select Active Facility
              </div>
              <button
                onClick={() => {
                  switchPlant('plant-pune-01');
                  setShowPlantDropdown(false);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  width: '100%',
                  padding: '8px 12px',
                  border: 'none',
                  background: activePlantId === 'plant-pune-01' ? '#f0fdf4' : 'transparent',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '12.5px',
                  color: activePlantId === 'plant-pune-01' ? '#059669' : '#1e293b',
                  fontWeight: activePlantId === 'plant-pune-01' ? 600 : 500,
                }}
              >
                <div>
                  <div>Acme Pune Plant</div>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>Maharashtra (MIDC)</div>
                </div>
                {activePlantId === 'plant-pune-01' && <CheckCircle2 size={14} />}
              </button>
              <button
                onClick={() => {
                  switchPlant('plant-vapi-02');
                  setShowPlantDropdown(false);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  width: '100%',
                  padding: '8px 12px',
                  border: 'none',
                  background: activePlantId === 'plant-vapi-02' ? '#f0fdf4' : 'transparent',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '12.5px',
                  color: activePlantId === 'plant-vapi-02' ? '#059669' : '#1e293b',
                  fontWeight: activePlantId === 'plant-vapi-02' ? 600 : 500,
                }}
              >
                <div>
                  <div>Acme Vapi Works</div>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>Gujarat (GIDC)</div>
                </div>
                {activePlantId === 'plant-vapi-02' && <CheckCircle2 size={14} />}
              </button>
            </div>
          )}
        </div>

        {/* AI Assistant Quick Trigger */}
        <button
          onClick={onOpenAiAssistant}
          className="btn btn-secondary btn-sm"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#f0fdf4',
            color: '#059669',
            borderColor: '#a7f3d0',
            fontWeight: 600,
          }}
          title="Open AI Compliance Assistant (Ctrl+K)"
        >
          <Sparkles size={14} />
          <span>Ask AI</span>
          <kbd
            style={{
              backgroundColor: '#dcfce7',
              borderRadius: '3px',
              padding: '1px 4px',
              fontSize: '10px',
              color: '#047857',
            }}
          >
            Ctrl+K
          </kbd>
        </button>

        {/* Notifications Bell */}
        <div style={{ position: 'relative' }} ref={notifRef}>
          <button
            className="notification-btn"
            aria-label="Notifications"
            onClick={() => setShowNotifications((v) => !v)}
            style={{ position: 'relative' }}
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span
                style={{
                  position: 'absolute',
                  top: '-3px',
                  right: '-3px',
                  backgroundColor: '#dc2626',
                  color: '#ffffff',
                  fontSize: '10px',
                  fontWeight: 700,
                  borderRadius: '10px',
                  minWidth: '16px',
                  height: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '0 4px',
                  border: '2px solid #ffffff',
                }}
              >
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Dropdown Drawer */}
          {showNotifications && (
            <div
              style={{
                position: 'absolute',
                top: '42px',
                right: '0',
                width: '380px',
                backgroundColor: '#ffffff',
                borderRadius: '12px',
                border: '1px solid #e2e8f0',
                boxShadow: '0 12px 28px rgba(0,0,0,0.15)',
                zIndex: 1100,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <div
                style={{
                  padding: '14px 18px',
                  backgroundColor: '#06281e',
                  color: '#ffffff',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Bell size={16} color="#34d399" />
                  <span style={{ fontWeight: 600, fontSize: '13.5px' }}>
                    Notifications & Reminders
                  </span>
                  {unreadCount > 0 && (
                    <span
                      style={{
                        backgroundColor: '#059669',
                        color: '#ffffff',
                        fontSize: '10px',
                        fontWeight: 700,
                        padding: '1px 6px',
                        borderRadius: '9999px',
                      }}
                    >
                      {unreadCount} new
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {unreadCount > 0 && (
                    <button
                      onClick={handleMarkAllRead}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#a7f3d0',
                        fontSize: '11px',
                        fontWeight: 500,
                        cursor: 'pointer',
                        padding: 0,
                      }}
                    >
                      Mark all read
                    </button>
                  )}
                  <button
                    onClick={handleOpenPreferences}
                    title="Configure notification preferences"
                    style={{
                      background: 'rgba(255, 255, 255, 0.12)',
                      border: '1px solid rgba(255, 255, 255, 0.25)',
                      borderRadius: '4px',
                      color: '#ffffff',
                      fontSize: '11px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      padding: '3px 8px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <Sliders size={11} />
                    <span>Preferences</span>
                  </button>
                </div>
              </div>

              <div
                style={{
                  padding: '8px 14px',
                  backgroundColor: '#f8fafc',
                  borderBottom: '1px solid #e2e8f0',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <button
                  onClick={handleRunScan}
                  disabled={scanning}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11.5px',
                    color: '#059669',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  <RefreshCw size={12} className={scanning ? 'spin-slow' : ''} />
                  <span>{scanning ? 'Scanning...' : 'Scan Due-Soon Work'}</span>
                </button>
                <button
                  onClick={handleSendTest}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11.5px',
                    color: '#64748b',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                  }}
                >
                  <Send size={11} />
                  <span>Send Test Alert</span>
                </button>
              </div>

              <div style={{ maxHeight: '360px', overflowY: 'auto' }}>
                {notifications.length === 0 ? (
                  <div style={{ padding: '36px 20px', textAlign: 'center', color: '#64748b' }}>
                    <CheckCircle2 size={24} color="#059669" style={{ margin: '0 auto 8px' }} />
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>
                      All caught up!
                    </div>
                    <div style={{ fontSize: '12px', marginTop: '2px' }}>
                      No due-soon or overdue compliance reminders pending.
                    </div>
                  </div>
                ) : (
                  notifications.map((item) => {
                    const isUnread = item.status === 'UNREAD';
                    return (
                      <div
                        key={item.id}
                        onClick={() => handleNotificationClick(item)}
                        title={item.entity_type ? `Navigate to ${item.entity_type.toLowerCase()}` : undefined}
                        style={{
                          padding: '12px 16px',
                          borderBottom: '1px solid #f1f5f9',
                          backgroundColor: isUnread ? '#f0fdf4' : '#ffffff',
                          cursor: 'pointer',
                          display: 'flex',
                          gap: '12px',
                          alignItems: 'flex-start',
                          transition: 'background-color 0.15s ease',
                        }}
                      >
                        <div style={{ flexShrink: 0, marginTop: '2px' }}>
                          {item.notification_type === 'OVERDUE' ? (
                            <AlertTriangle size={16} color="#dc2626" />
                          ) : item.notification_type === 'DUE_SOON' ? (
                            <Clock size={16} color="#d97706" />
                          ) : item.notification_type === 'STATUS_CHANGE' ? (
                            <CheckCircle2 size={16} color="#059669" />
                          ) : (
                            <Sparkles size={16} color="#7c3aed" />
                          )}
                        </div>

                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div
                            style={{
                              fontSize: '12.5px',
                              fontWeight: isUnread ? 600 : 500,
                              color: '#0f172a',
                              marginBottom: '2px',
                            }}
                          >
                            {item.title}
                          </div>
                          <div
                            style={{
                              fontSize: '11.5px',
                              color: '#475569',
                              lineHeight: 1.45,
                              marginBottom: '4px',
                            }}
                          >
                            {item.message}
                          </div>
                          <div
                            style={{
                              fontSize: '10.5px',
                              color: '#94a3b8',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px',
                            }}
                          >
                            <span>
                              {new Date(item.sent_at).toLocaleTimeString('en-IN', {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                            <span>•</span>
                            <span style={{ textTransform: 'capitalize' }}>
                              {item.channel.toLowerCase()}
                            </span>
                            {isUnread && (
                              <span style={{ color: '#059669', fontWeight: 600, marginLeft: 'auto' }}>
                                Unread
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Profile Pill & Demo Persona Switcher */}
        <div style={{ position: 'relative' }} ref={userMenuRef}>
          <div
            className="user-profile-pill"
            onClick={() => setShowUserDropdown((v) => !v)}
            style={{ cursor: 'pointer' }}
            title="Click to switch persona or sign out"
          >
            <div className="user-avatar">{getInitials(user.fullName)}</div>
            <div>
              <div className="user-meta-name" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span>{user.fullName}</span>
                <ChevronDown size={12} color="#64748b" />
              </div>
              <div className="user-meta-role">
                {user.role === 'PLANT_MANAGER'
                  ? 'Plant Manager'
                  : user.role === 'EHS_MANAGER'
                  ? 'EHS Manager'
                  : user.role === 'AUDITOR'
                  ? 'External Auditor'
                  : user.role}
              </div>
            </div>
          </div>

          {/* User & Role Switcher Dropdown */}
          {showUserDropdown && (
            <div
              style={{
                position: 'absolute',
                top: '46px',
                right: '0',
                width: '260px',
                backgroundColor: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                boxShadow: '0 10px 25px rgba(0,0,0,0.12)',
                zIndex: 1100,
                padding: '6px 0',
              }}
            >
              <div
                style={{
                  padding: '8px 14px',
                  borderBottom: '1px solid #f1f5f9',
                  background: '#f8fafc',
                }}
              >
                <div style={{ fontSize: '11px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>
                  Active Persona & RBAC Role
                </div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a', marginTop: '2px' }}>
                  {user.fullName}
                </div>
                <div style={{ fontSize: '11.5px', color: '#64748b' }}>{user.email}</div>
              </div>

              <div style={{ padding: '6px 12px', fontSize: '11px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>
                Switch Persona (Demo Testing)
              </div>
              {DEMO_USERS.map((demo) => (
                <button
                  key={demo.id}
                  onClick={() => {
                    switchUser(demo.id);
                    setShowUserDropdown(false);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    width: '100%',
                    padding: '7px 14px',
                    border: 'none',
                    background: user.id === demo.id ? '#f0fdf4' : 'transparent',
                    cursor: 'pointer',
                    textAlign: 'left',
                    fontSize: '12px',
                    color: user.id === demo.id ? '#059669' : '#334155',
                    fontWeight: user.id === demo.id ? 600 : 500,
                  }}
                >
                  <div>
                    <div>{demo.fullName}</div>
                    <div style={{ fontSize: '10.5px', color: '#64748b' }}>{demo.role}</div>
                  </div>
                  {user.id === demo.id && <UserCheck size={14} color="#059669" />}
                </button>
              ))}

              <div style={{ borderTop: '1px solid #f1f5f9', marginTop: '6px', paddingTop: '6px' }}>
                <button
                  onClick={() => {
                    logout();
                    navigate('/auth/login');
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    width: '100%',
                    padding: '8px 14px',
                    border: 'none',
                    background: 'transparent',
                    cursor: 'pointer',
                    color: '#dc2626',
                    fontSize: '12px',
                    fontWeight: 500,
                  }}
                >
                  <LogOut size={14} />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Alert & Notification Preferences Modal */}
      {showPreferencesModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="notif-pref-modal-title"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.65)',
            backdropFilter: 'blur(4px)',
            zIndex: 1300,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px',
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowPreferencesModal(false);
          }}
        >
          <div
            style={{
              width: '480px',
              maxWidth: '100%',
              backgroundColor: '#ffffff',
              borderRadius: '12px',
              border: '1px solid #e2e8f0',
              boxShadow: '0 20px 45px rgba(0,0,0,0.2)',
              overflow: 'hidden',
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                backgroundColor: '#06281e',
                color: '#ffffff',
                padding: '16px 20px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sliders size={18} color="#34d399" />
                <h3
                  id="notif-pref-modal-title"
                  style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#ffffff' }}
                >
                  Compliance Notification Preferences
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowPreferencesModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  padding: '4px',
                }}
                aria-label="Close preferences modal"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body / Form */}
            {preferences ? (
              <form onSubmit={handleSavePreferences} style={{ padding: '20px' }}>
                {prefMessage && (
                  <div
                    style={{
                      marginBottom: '16px',
                      padding: '10px 14px',
                      backgroundColor: '#f0fdf4',
                      border: '1px solid #bbf7d0',
                      borderRadius: '8px',
                      color: '#166534',
                      fontSize: '12.5px',
                      fontWeight: 500,
                    }}
                  >
                    {prefMessage}
                  </div>
                )}

                {/* Lead time */}
                <div style={{ marginBottom: '18px' }}>
                  <label
                    style={{
                      display: 'block',
                      fontSize: '12.5px',
                      fontWeight: 600,
                      color: '#0f172a',
                      marginBottom: '6px',
                    }}
                  >
                    Reminder Lead Time (Days Before Expiry/Due Date)
                  </label>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    {[7, 15, 30, 60].map((days) => (
                      <button
                        key={days}
                        type="button"
                        onClick={() =>
                          setPreferences((prev) => (prev ? { ...prev, lead_time_days: days } : null))
                        }
                        style={{
                          padding: '6px 12px',
                          borderRadius: '6px',
                          border:
                            preferences.lead_time_days === days
                              ? '1.5px solid #059669'
                              : '1px solid #cbd5e1',
                          backgroundColor:
                            preferences.lead_time_days === days ? '#f0fdf4' : '#ffffff',
                          color: preferences.lead_time_days === days ? '#059669' : '#475569',
                          fontWeight: preferences.lead_time_days === days ? 700 : 500,
                          fontSize: '12px',
                          cursor: 'pointer',
                        }}
                      >
                        {days} Days
                      </button>
                    ))}
                    <input
                      type="number"
                      min={1}
                      max={180}
                      value={preferences.lead_time_days}
                      onChange={(e) =>
                        setPreferences((prev) =>
                          prev ? { ...prev, lead_time_days: parseInt(e.target.value, 10) || 1 } : null
                        )
                      }
                      style={{
                        width: '70px',
                        padding: '6px 8px',
                        borderRadius: '6px',
                        border: '1px solid #cbd5e1',
                        fontSize: '12px',
                        textAlign: 'center',
                      }}
                      aria-label="Custom lead time in days"
                    />
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
                    Advance warning window for upcoming tasks, consents, and permits.
                  </div>
                </div>

                {/* Channel Toggles */}
                <div
                  style={{
                    backgroundColor: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    padding: '14px',
                    marginBottom: '18px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  <div style={{ fontSize: '11px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>
                    Alert Channels & Triggers
                  </div>

                  <label
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      fontSize: '12.5px',
                      color: '#1e293b',
                      cursor: 'pointer',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={preferences.in_app_enabled}
                      onChange={(e) =>
                        setPreferences((prev) =>
                          prev ? { ...prev, in_app_enabled: e.target.checked } : null
                        )
                      }
                      style={{ accentColor: '#059669', width: '16px', height: '16px' }}
                    />
                    <div>
                      <div style={{ fontWeight: 600 }}>In-App Notifications</div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>
                        Display reminders in top-bar bell and facility operations banner
                      </div>
                    </div>
                  </label>

                  <label
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      fontSize: '12.5px',
                      color: '#1e293b',
                      cursor: 'pointer',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={preferences.email_enabled}
                      onChange={(e) =>
                        setPreferences((prev) =>
                          prev ? { ...prev, email_enabled: e.target.checked } : null
                        )
                      }
                      style={{ accentColor: '#059669', width: '16px', height: '16px' }}
                    />
                    <div>
                      <div style={{ fontWeight: 600 }}>Email Notifications</div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>
                        Dispatch notification emails via configured compliance SMTP adapter
                      </div>
                    </div>
                  </label>

                  <label
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      fontSize: '12.5px',
                      color: '#1e293b',
                      cursor: 'pointer',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={preferences.notify_on_overdue}
                      onChange={(e) =>
                        setPreferences((prev) =>
                          prev ? { ...prev, notify_on_overdue: e.target.checked } : null
                        )
                      }
                      style={{ accentColor: '#dc2626', width: '16px', height: '16px' }}
                    />
                    <div>
                      <div style={{ fontWeight: 600 }}>Notify on Overdue Items</div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>
                        Raise immediate critical alert once statutory due date has elapsed
                      </div>
                    </div>
                  </label>
                </div>

                {/* Dispatch Frequency */}
                <div style={{ marginBottom: '20px' }}>
                  <label
                    style={{
                      display: 'block',
                      fontSize: '12.5px',
                      fontWeight: 600,
                      color: '#0f172a',
                      marginBottom: '6px',
                    }}
                  >
                    Alert Delivery Cadence
                  </label>
                  <select
                    value={preferences.frequency}
                    onChange={(e) =>
                      setPreferences((prev) =>
                        prev
                          ? { ...prev, frequency: e.target.value as 'IMMEDIATE' | 'DAILY_DIGEST' }
                          : null
                      )
                    }
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      border: '1px solid #cbd5e1',
                      fontSize: '12.5px',
                      color: '#1e293b',
                      backgroundColor: '#ffffff',
                    }}
                  >
                    <option value="IMMEDIATE">Immediate (Real-Time Dispatch per Scan)</option>
                    <option value="DAILY_DIGEST">Daily Morning Compliance Digest (08:00 AM IST)</option>
                  </select>
                </div>

                {/* Modal Footer */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'flex-end',
                    gap: '10px',
                    borderTop: '1px solid #f1f5f9',
                    paddingTop: '16px',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => setShowPreferencesModal(false)}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '6px',
                      border: '1px solid #cbd5e1',
                      backgroundColor: '#ffffff',
                      color: '#475569',
                      fontSize: '12.5px',
                      fontWeight: 500,
                      cursor: 'pointer',
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={savingPreferences}
                    style={{
                      padding: '8px 18px',
                      borderRadius: '6px',
                      border: 'none',
                      backgroundColor: '#059669',
                      color: '#ffffff',
                      fontSize: '12.5px',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    {savingPreferences ? 'Saving...' : 'Save Preferences'}
                  </button>
                </div>
              </form>
            ) : (
              <div style={{ padding: '30px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
                Loading notification preferences...
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
