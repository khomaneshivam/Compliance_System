import React, { useState, useEffect, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Users,
  UserPlus,
  ShieldCheck,
  Search,
  CheckCircle2,
  X,
  RefreshCw,
} from 'lucide-react';
import { api } from '../services/api';
import type { User, Role } from '../types';

const inviteSchema = z.object({
  fullName: z.string().min(2, 'Full name must be at least 2 characters'),
  email: z.string().email('Please enter a valid work email address'),
  role: z.enum(['SUPER_ADMIN', 'ADMIN', 'PLANT_MANAGER', 'EHS_MANAGER', 'AUDITOR', 'VIEWER']),
  plantScope: z.string().min(1, 'Please select plant scope'),
});

type InviteFormData = z.infer<typeof inviteSchema>;

export const AdminUsersPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [showInviteModal, setShowInviteModal] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<InviteFormData>({
    resolver: zodResolver(inviteSchema),
    defaultValues: {
      fullName: '',
      email: '',
      role: 'EHS_MANAGER',
      plantScope: 'plant-pune-01',
    },
  });

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getAdminUsers();
      setUsers(data);
    } catch (err: unknown) {
      console.error('Failed to load users', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const onInviteSubmit = async (data: InviteFormData) => {
    try {
      const created = await api.inviteAdminUser({
        full_name: data.fullName,
        email: data.email,
        role: data.role,
        plant_ids: [data.plantScope],
      });
      setUsers((prev) => [created, ...prev]);
      setFeedback(`Invitation dispatched to ${data.email} with ${data.role} permissions.`);
      setTimeout(() => setFeedback(null), 3500);
      setShowInviteModal(false);
      reset();
    } catch (err: unknown) {
      alert((err as Error).message || 'Failed to dispatch user invitation.');
    }
  };

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      !search.trim() ||
      u.fullName.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase());
    const matchesRole = !roleFilter || u.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const renderRoleBadge = (role: Role) => {
    let bg = '#f1f5f9';
    let color = '#334155';
    let border = '#cbd5e1';

    if (role === 'SUPER_ADMIN' || role === 'ADMIN') {
      bg = '#f5f3ff';
      color = '#7c3aed';
      border = '#ddd6fe';
    } else if (role === 'PLANT_MANAGER') {
      bg = '#eff6ff';
      color = '#1e40af';
      border = '#bfdbfe';
    } else if (role === 'EHS_MANAGER') {
      bg = '#ecfdf5';
      color = '#059669';
      border = '#a7f3d0';
    } else if (role === 'AUDITOR') {
      bg = '#fffbeb';
      color = '#92400e';
      border = '#fde68a';
    }

    return (
      <span
        style={{
          display: 'inline-block',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '11px',
          fontWeight: 600,
          backgroundColor: bg,
          color,
          border: `1px solid ${border}`,
        }}
      >
        {role.replace(/_/g, ' ')}
      </span>
    );
  };

  return (
    <div style={{ padding: '24px 32px', maxWidth: '1440px', margin: '0 auto' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: '20px',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: '#ecfdf5',
                color: '#059669',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Users size={18} />
            </div>
            <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
              Enterprise Users, Roles & Permissions
            </h1>
          </div>
          <p style={{ color: '#64748b', fontSize: '13px', margin: 0 }}>
            Manage facility team member seats, role-based access control (RBAC), and multi-plant operational scopes.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => fetchUsers()}
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} className={loading ? 'spin-slow' : ''} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setShowInviteModal(true)}
            className="btn btn-primary"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#059669',
              borderColor: '#059669',
            }}
          >
            <UserPlus size={16} />
            <span>Invite Team Member</span>
          </button>
        </div>
      </div>

      {/* Tenet Alert Banner */}
      <div
        style={{
          backgroundColor: '#f8fafc',
          border: '1px solid #cbd5e1',
          borderLeft: '4px solid #059669',
          borderRadius: '8px',
          padding: '12px 18px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          fontSize: '12.5px',
          color: '#334155',
        }}
      >
        <ShieldCheck size={20} color="#059669" style={{ flexShrink: 0 }} />
        <div>
          <strong>Role-Based Access Enforcement: </strong>
          EHS Managers and Plant Managers possess review and sign-off authority for statutory evidence and tasks. Auditors operate with read-only inspection scopes. Rule authoring is strictly restricted to Admins.
        </div>
      </div>

      {/* Feedback Toast */}
      {feedback && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: '8px',
            marginBottom: '20px',
            backgroundColor: '#ecfdf5',
            color: '#065f46',
            border: '1px solid #a7f3d0',
            fontSize: '13px',
          }}
        >
          ✓ {feedback}
        </div>
      )}

      {/* Filter and Search Bar */}
      <div
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '10px',
          border: '1px solid #e2e8f0',
          padding: '14px 18px',
          marginBottom: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ position: 'relative', width: '300px' }}>
          <Search size={15} color="#94a3b8" style={{ position: 'absolute', left: '10px', top: '10px' }} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search team member by name or email..."
            style={{
              width: '100%',
              padding: '8px 12px 8px 32px',
              borderRadius: '6px',
              border: '1px solid #cbd5e1',
              fontSize: '13px',
              boxSizing: 'border-box',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: '#64748b' }}>Role Scope:</span>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            style={{
              padding: '7px 12px',
              borderRadius: '6px',
              border: '1px solid #cbd5e1',
              fontSize: '12.5px',
            }}
          >
            <option value="">All Roles ({users.length})</option>
            <option value="PLANT_MANAGER">Plant Manager</option>
            <option value="EHS_MANAGER">EHS Manager</option>
            <option value="ADMIN">Tenant Admin</option>
            <option value="AUDITOR">Auditor</option>
            <option value="VIEWER">Viewer</option>
          </select>
        </div>
      </div>

      {/* Users Table */}
      <div
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '12px',
          border: '1px solid #e2e8f0',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          overflow: 'hidden',
          marginBottom: '28px',
        }}
      >
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
          <thead>
            <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
              <th style={{ padding: '12px 18px', fontWeight: 600 }}>Team Member</th>
              <th style={{ padding: '12px 18px', fontWeight: 600 }}>Role</th>
              <th style={{ padding: '12px 18px', fontWeight: 600 }}>Enterprise Tenant</th>
              <th style={{ padding: '12px 18px', fontWeight: 600 }}>Facility Scopes</th>
              <th style={{ padding: '12px 18px', fontWeight: 600 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: '36px', textAlign: 'center', color: '#64748b' }}>
                  No team members match your active filter.
                </td>
              </tr>
            ) : (
              filteredUsers.map((u) => (
                <tr key={u.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '14px 18px' }}>
                    <div style={{ fontWeight: 600, color: '#0f172a' }}>{u.fullName}</div>
                    <div style={{ fontSize: '11.5px', color: '#64748b' }}>{u.email}</div>
                  </td>
                  <td style={{ padding: '14px 18px' }}>{renderRoleBadge(u.role)}</td>
                  <td style={{ padding: '14px 18px', color: '#334155' }}>
                    {u.tenantName || 'Acme Manufacturing Group'}
                  </td>
                  <td style={{ padding: '14px 18px', color: '#475569' }}>
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        backgroundColor: '#f1f5f9',
                        fontSize: '11px',
                        fontWeight: 600,
                      }}
                    >
                      {u.plantIds?.length ? `${u.plantIds.length} plant(s)` : 'All Plants'}
                    </span>
                  </td>
                  <td style={{ padding: '14px 18px' }}>
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '11.5px',
                        fontWeight: 600,
                        color: '#059669',
                      }}
                    >
                      <CheckCircle2 size={13} /> Active
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Permissions Matrix Reference Card */}
      <div
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '12px',
          border: '1px solid #e2e8f0',
          padding: '20px 24px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
        }}
      >
        <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', marginBottom: '12px' }}>
          Role-Based Access Control (RBAC) Permission Matrix
        </h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
            <thead>
              <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                <th style={{ padding: '10px 14px' }}>System Permission</th>
                <th style={{ padding: '10px 14px', textAlign: 'center' }}>Admin</th>
                <th style={{ padding: '10px 14px', textAlign: 'center' }}>Plant Manager</th>
                <th style={{ padding: '10px 14px', textAlign: 'center' }}>EHS Manager</th>
                <th style={{ padding: '10px 14px', textAlign: 'center' }}>Auditor</th>
                <th style={{ padding: '10px 14px', textAlign: 'center' }}>Viewer</th>
              </tr>
            </thead>
            <tbody>
              {[
                { perm: 'View Requirements Register & Dashboards', roles: [true, true, true, true, true] },
                { perm: 'Upload Evidence Documents', roles: [true, true, true, false, false] },
                { perm: 'Approve AI Extractions & Link Evidence', roles: [true, true, true, false, false] },
                { perm: 'Perform State Machine Task Transitions', roles: [true, true, true, false, false] },
                { perm: 'Run Reassessment Simulations & Commit Facts', roles: [true, true, false, false, false] },
                { perm: 'Generate Readiness Reports & Download Dossiers', roles: [true, true, true, true, false] },
                { perm: 'Author Rules & Manage Master Catalog', roles: [true, false, false, false, false] },
              ].map((row, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '10px 14px', fontWeight: 500, color: '#334155' }}>{row.perm}</td>
                  {row.roles.map((has, i) => (
                    <td key={i} style={{ padding: '10px 14px', textAlign: 'center' }}>
                      {has ? (
                        <span style={{ color: '#059669', fontWeight: 700 }}>✓</span>
                      ) : (
                        <span style={{ color: '#cbd5e1' }}>—</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.45)',
            backdropFilter: 'blur(2px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px',
          }}
          onClick={() => setShowInviteModal(false)}
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '12px',
              maxWidth: '480px',
              width: '100%',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
              overflow: 'hidden',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                padding: '18px 24px',
                borderBottom: '1px solid #e2e8f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                backgroundColor: '#06281e',
                color: '#ffffff',
              }}
            >
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#ffffff' }}>
                Invite New Enterprise Team Member
              </h3>
              <button
                onClick={() => setShowInviteModal(false)}
                style={{ background: 'none', border: 'none', color: '#ffffff', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmit(onInviteSubmit)} style={{ padding: '24px' }}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Full Name *
                </label>
                <input
                  type="text"
                  {...register('fullName')}
                  placeholder="e.g. Ramesh Iyer"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: errors.fullName ? '1px solid #dc2626' : '1px solid #cbd5e1',
                    fontSize: '13px',
                    boxSizing: 'border-box',
                  }}
                />
                {errors.fullName && (
                  <span style={{ fontSize: '11px', color: '#dc2626', marginTop: '3px', display: 'block' }}>
                    {errors.fullName.message}
                  </span>
                )}
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Work Email Address *
                </label>
                <input
                  type="email"
                  {...register('email')}
                  placeholder="e.g. ramesh.iyer@acme-mfg.in"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: errors.email ? '1px solid #dc2626' : '1px solid #cbd5e1',
                    fontSize: '13px',
                    boxSizing: 'border-box',
                  }}
                />
                {errors.email && (
                  <span style={{ fontSize: '11px', color: '#dc2626', marginTop: '3px', display: 'block' }}>
                    {errors.email.message}
                  </span>
                )}
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Enterprise Role *
                </label>
                <select
                  {...register('role')}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '13px',
                    backgroundColor: '#ffffff',
                  }}
                >
                  <option value="PLANT_MANAGER">Plant Manager</option>
                  <option value="EHS_MANAGER">EHS Manager (Compliance Officer)</option>
                  <option value="ADMIN">Tenant Administrator</option>
                  <option value="AUDITOR">Compliance Auditor (Read-Only Audit)</option>
                  <option value="VIEWER">Viewer (Department Read-Only)</option>
                </select>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Facility Scope *
                </label>
                <select
                  {...register('plantScope')}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '13px',
                    backgroundColor: '#ffffff',
                  }}
                >
                  <option value="plant-pune-01">Acme Pune Manufacturing Unit (Maharashtra)</option>
                  <option value="plant-vapi-02">Acme Vapi Chemical Plant (Gujarat)</option>
                  <option value="all-plants">All Corporate Facilities</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="btn btn-secondary"
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="btn btn-primary"
                  style={{ backgroundColor: '#059669', borderColor: '#059669' }}
                >
                  {isSubmitting ? 'Dispatching Invite...' : 'Send Invitation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
