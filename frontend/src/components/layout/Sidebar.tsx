import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FileCheck,
  FileText,
  Scale,
  CheckSquare,
  BarChart3,
  Building2,
  Database,
  GitBranch,
  Users,
  ShieldAlert,
  Sparkles,
  Leaf,
  Compass,
  Lock,
  Bot,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import type { Role } from '../../types';

interface SidebarProps {
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ mobileOpen, onCloseMobile }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { hasRole, activePlantId, switchPlant } = useAuth();

  const handleNavClick = (path: string) => {
    navigate(path);
    if (onCloseMobile) onCloseMobile();
  };

  const mainNavItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/setup-wizard', label: 'Setup Wizard', icon: Compass },
    { path: '/requirements', label: 'Requirements', icon: FileCheck },
    { path: '/documents', label: 'Documents', icon: FileText },
    { path: '/regulatory-changes', label: 'Regulatory Changes', icon: Scale },
    { path: '/tasks', label: 'Tasks & Deadlines', icon: CheckSquare },
    { path: '/reports', label: 'Audits & Reports', icon: BarChart3 },
    { path: '/company-profile', label: 'Facility Profile', icon: Building2 },
    { path: '/assistant', label: 'AI Compliance Intel', icon: Bot },
  ];

  const adminNavItems: { path: string; label: string; icon: React.FC<{ size?: number }>; roles: Role[] }[] = [
    { path: '/admin/master-data', label: 'Master Data', icon: Database, roles: ['ADMIN', 'SUPER_ADMIN'] },
    { path: '/admin/rules', label: 'Rule Review Bench', icon: GitBranch, roles: ['ADMIN', 'SUPER_ADMIN'] },
    { path: '/admin/users', label: 'Users & Roles', icon: Users, roles: ['ADMIN', 'SUPER_ADMIN'] },
    { path: '/admin/audit-log', label: 'Audit Log', icon: ShieldAlert, roles: ['ADMIN', 'SUPER_ADMIN'] },
  ];

  const isCurrent = (path: string) => {
    if (path === '/dashboard' && location.pathname === '/') return true;
    return location.pathname.startsWith(path);
  };

  const handlePlantToggle = () => {
    const nextPlant = activePlantId === 'plant-pune-01' ? 'plant-vapi-02' : 'plant-pune-01';
    switchPlant(nextPlant);
  };

  return (
    <>
      <div
        className={`sidebar-backdrop ${mobileOpen ? 'active' : ''}`}
        onClick={onCloseMobile}
        aria-hidden="true"
      />
      <aside className={`sidebar ${mobileOpen ? 'mobile-open' : ''}`}>
      {/* Brand Header */}
      <div
        className="sidebar-header"
        onClick={() => navigate('/dashboard')}
        style={{ cursor: 'pointer' }}
        title="PlantProof - Factory Compliance Platform"
      >
        <div style={{ color: '#10b981', display: 'flex', alignItems: 'center' }}>
          <Leaf size={24} strokeWidth={2.4} />
        </div>
        <span className="sidebar-brand-name">PlantProof</span>
      </div>

      {/* Navigation Links */}
      <nav className="sidebar-nav">
        <div className="sidebar-section-label">Operations</div>
        {mainNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = isCurrent(item.path);
          return (
            <div
              key={item.path}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => handleNavClick(item.path)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') handleNavClick(item.path);
              }}
            >
              <Icon size={16} />
              <span>{item.label}</span>
            </div>
          );
        })}

        <div className="sidebar-section-label" style={{ marginTop: '12px' }}>
          Governance & Admin
        </div>
        {adminNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = isCurrent(item.path);
          const isPermitted = hasRole(item.roles);

          return (
            <div
              key={item.path}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => handleNavClick(item.path)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                opacity: isPermitted ? 1 : 0.65,
              }}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') handleNavClick(item.path);
              }}
              title={
                isPermitted
                  ? item.label
                  : `${item.label} (Restricted to ${item.roles.join(', ')})`
              }
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Icon size={16} />
                <span>{item.label}</span>
              </div>
              {!isPermitted && <Lock size={12} style={{ color: '#94a3b8' }} />}
            </div>
          );
        })}

        <div className="sidebar-section-label" style={{ marginTop: '12px' }}>
          Design System
        </div>
        <div
          className={`nav-item ${isCurrent('/design-playground') ? 'active' : ''}`}
          onClick={() => handleNavClick('/design-playground')}
          style={{ color: '#34d399' }}
          role="button"
          tabIndex={0}
        >
          <Sparkles size={16} />
          <span>Interactive Playground</span>
        </div>
      </nav>

      {/* Facility Context Card Footer */}
      <div className="sidebar-footer">
        <div
          className="plant-pill"
          onClick={handlePlantToggle}
          style={{ cursor: 'pointer' }}
          title="Click to toggle active facility context"
        >
          <div className="plant-pill-icon">
            <Building2 size={18} />
          </div>
          <div style={{ minWidth: 0 }}>
            <div className="plant-pill-title">
              {activePlantId === 'plant-pune-01' ? 'Acme Pune Plant' : 'Acme Vapi Chemical'}
            </div>
            <div className="plant-pill-sub">
              {activePlantId === 'plant-pune-01' ? 'Maharashtra (MIDC)' : 'Gujarat (GIDC)'} • Switch
            </div>
          </div>
        </div>
      </div>
    </aside>
    </>
  );
};
