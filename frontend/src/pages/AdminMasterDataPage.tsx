import React, { useState, useEffect, useCallback } from 'react';
import {
  Database,
  Building,
  Scale,
  FileCheck,
  Search,
  Plus,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  X,
} from 'lucide-react';
import { api } from '../services/api';
import type { MasterAuthority, MasterAct, MasterRequirement } from '../types';

export const AdminMasterDataPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'authorities' | 'acts' | 'requirements'>('authorities');
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>('');

  const [authorities, setAuthorities] = useState<MasterAuthority[]>([]);
  const [acts, setActs] = useState<MasterAct[]>([]);
  const [requirements, setRequirements] = useState<MasterRequirement[]>([]);

  // Add Item Modal
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [modalTitle, setModalTitle] = useState<string>('');
  const [modalCode, setModalCode] = useState<string>('');
  const [modalDesc, setModalDesc] = useState<string>('');
  const [feedback, setFeedback] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      if (activeTab === 'authorities') {
        const data = await api.getMasterAuthorities();
        setAuthorities(data);
      } else if (activeTab === 'acts') {
        const data = await api.getMasterActs();
        setActs(data);
      } else if (activeTab === 'requirements') {
        const data = await api.getMasterRequirements({ search: search.trim() || undefined });
        setRequirements(data.items);
      }
    } catch (err: unknown) {
      console.error('Failed to load master data', err);
    } finally {
      setLoading(false);
    }
  }, [activeTab, search]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreateMock = (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalCode.trim() || !modalTitle.trim()) {
      alert('Code and title are mandatory.');
      return;
    }

    if (activeTab === 'authorities') {
      const newAuth: MasterAuthority = {
        id: `auth-${Date.now()}`,
        code: modalCode.trim().toUpperCase(),
        name: modalTitle.trim(),
        jurisdiction_level: 'STATE',
        jurisdiction_name: 'Maharashtra',
      };
      setAuthorities((prev) => [newAuth, ...prev]);
    } else if (activeTab === 'acts') {
      const newAct: MasterAct = {
        id: `act-${Date.now()}`,
        authority_id: 'auth-mpcb',
        authority_code: 'MPCB',
        code: modalCode.trim().toUpperCase(),
        title: modalTitle.trim(),
        enacted_year: 2025,
        jurisdiction_scope: 'STATE',
      };
      setActs((prev) => [newAct, ...prev]);
    } else {
      const newReq: MasterRequirement = {
        id: `req-${Date.now()}`,
        act_id: 'act-water-1974',
        act_title: 'Water Act 1974',
        authority_code: 'MPCB',
        code: modalCode.trim().toUpperCase(),
        title: modalTitle.trim(),
        description: modalDesc.trim() || 'Statutory requirement catalog entry.',
        obligation_type: 'CONSENT',
        validity_period_months: 60,
        grace_period_days: 30,
      };
      setRequirements((prev) => [newReq, ...prev]);
    }

    setFeedback(`New ${activeTab.slice(0, -1)} '${modalTitle}' registered in master catalog.`);
    setTimeout(() => setFeedback(null), 3000);
    setShowAddModal(false);
    setModalCode('');
    setModalTitle('');
    setModalDesc('');
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
              <Database size={18} />
            </div>
            <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
              Master Data & Regulatory Catalogs
            </h1>
          </div>
          <p style={{ color: '#64748b', fontSize: '13px', margin: 0 }}>
            Authoritative national & state regulatory reference registers, governing bodies, acts, and statutory obligation templates.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => fetchData()}
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} className={loading ? 'spin-slow' : ''} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="btn btn-primary"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#059669',
              borderColor: '#059669',
            }}
          >
            <Plus size={16} />
            <span>Add Catalog Reference</span>
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
          <strong>Statutory Governance Tenet: </strong>
          Master data catalogs serve as the single source of truth across all enterprise plants. Modifying an authority, act code, or validity template carries strict provenance tracking and version immutability.
        </div>
      </div>

      {/* Feedback banner */}
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

      {/* Tabs navigation */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '20px',
          borderBottom: '1px solid #e2e8f0',
          paddingBottom: '12px',
        }}
      >
        {[
          { key: 'authorities', label: 'Regulatory Authorities', icon: Building, count: authorities.length },
          { key: 'acts', label: 'Statutory Acts & Rules', icon: Scale, count: acts.length },
          { key: 'requirements', label: 'Obligation Templates', icon: FileCheck, count: requirements.length },
        ].map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key as typeof activeTab)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                borderRadius: '8px',
                border: 'none',
                backgroundColor: isActive ? '#06281e' : '#f1f5f9',
                color: isActive ? '#ffffff' : '#475569',
                fontSize: '13px',
                fontWeight: isActive ? 600 : 500,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <Icon size={15} color={isActive ? '#34d399' : '#64748b'} />
              <span>{t.label}</span>
              {t.count > 0 && (
                <span
                  style={{
                    backgroundColor: isActive ? '#059669' : '#e2e8f0',
                    color: isActive ? '#ffffff' : '#475569',
                    fontSize: '11px',
                    padding: '1px 6px',
                    borderRadius: '10px',
                  }}
                >
                  {t.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Main Table Container */}
      <div
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '12px',
          border: '1px solid #e2e8f0',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          overflow: 'hidden',
        }}
      >
        {/* Search header */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ position: 'relative', width: '320px' }}>
            <Search size={15} color="#94a3b8" style={{ position: 'absolute', left: '10px', top: '10px' }} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by code, title, or jurisdiction..."
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
          <span style={{ fontSize: '12px', color: '#64748b' }}>
            Central & State Statutory Catalog v1.2
          </span>
        </div>

        {/* AUTHORITIES TAB */}
        {activeTab === 'authorities' && (
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Authority Code</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Governing Body Name</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Jurisdiction Level</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Territory Scope</th>
                <th style={{ padding: '12px 18px', fontWeight: 600, textAlign: 'right' }}>Official Portal</th>
              </tr>
            </thead>
            <tbody>
              {authorities.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ padding: '36px', textAlign: 'center', color: '#64748b' }}>
                    No regulatory authorities loaded in catalog.
                  </td>
                </tr>
              ) : (
                authorities.map((auth) => (
                  <tr key={auth.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '14px 18px' }}>
                      <span
                        style={{
                          padding: '3px 8px',
                          borderRadius: '4px',
                          backgroundColor: '#ecfdf5',
                          color: '#059669',
                          fontWeight: 700,
                          fontSize: '12px',
                        }}
                      >
                        {auth.code}
                      </span>
                    </td>
                    <td style={{ padding: '14px 18px', fontWeight: 600, color: '#0f172a' }}>
                      {auth.name}
                    </td>
                    <td style={{ padding: '14px 18px', color: '#475569' }}>
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '11.5px',
                          backgroundColor: auth.jurisdiction_level === 'STATE' ? '#eff6ff' : '#f1f5f9',
                          color: auth.jurisdiction_level === 'STATE' ? '#1e40af' : '#334155',
                          fontWeight: 500,
                        }}
                      >
                        {auth.jurisdiction_level}
                      </span>
                    </td>
                    <td style={{ padding: '14px 18px', color: '#334155' }}>
                      {auth.jurisdiction_name}
                    </td>
                    <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                      <a
                        href={auth.website_url || '#'}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          color: '#059669',
                          textDecoration: 'none',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontSize: '12px',
                        }}
                      >
                        <span>Official Portal</span>
                        <ExternalLink size={12} />
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}

        {/* ACTS TAB */}
        {activeTab === 'acts' && (
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Act Code</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Statutory Act Title</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Authority</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Enacted Year</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Scope</th>
              </tr>
            </thead>
            <tbody>
              {acts.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ padding: '36px', textAlign: 'center', color: '#64748b' }}>
                    No statutory acts listed.
                  </td>
                </tr>
              ) : (
                acts.map((act) => (
                  <tr key={act.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '14px 18px', fontWeight: 700, color: '#0f172a' }}>
                      {act.code}
                    </td>
                    <td style={{ padding: '14px 18px', fontWeight: 600, color: '#334155' }}>
                      {act.title}
                    </td>
                    <td style={{ padding: '14px 18px' }}>
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          backgroundColor: '#ecfdf5',
                          color: '#059669',
                          fontSize: '11px',
                          fontWeight: 600,
                        }}
                      >
                        {act.authority_code || 'Central'}
                      </span>
                    </td>
                    <td style={{ padding: '14px 18px', color: '#64748b' }}>
                      {act.enacted_year || 'Central Statute'}
                    </td>
                    <td style={{ padding: '14px 18px', color: '#475569' }}>
                      {act.jurisdiction_scope}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}

        {/* REQUIREMENTS TAB */}
        {activeTab === 'requirements' && (
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Obligation Code</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Requirement Title & Description</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Act Reference</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Type</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Validity</th>
              </tr>
            </thead>
            <tbody>
              {requirements.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ padding: '36px', textAlign: 'center', color: '#64748b' }}>
                    No standard requirement templates found.
                  </td>
                </tr>
              ) : (
                requirements.map((req) => (
                  <tr key={req.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '14px 18px' }}>
                      <span style={{ fontWeight: 700, color: '#0f172a' }}>{req.code}</span>
                    </td>
                    <td style={{ padding: '14px 18px' }}>
                      <div style={{ fontWeight: 600, color: '#0f172a' }}>{req.title}</div>
                      <div style={{ fontSize: '11.5px', color: '#64748b', marginTop: '2px' }}>
                        {req.description}
                      </div>
                    </td>
                    <td style={{ padding: '14px 18px', color: '#334155' }}>
                      {req.act_title || 'General'}
                    </td>
                    <td style={{ padding: '14px 18px' }}>
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: 600,
                          backgroundColor: '#f1f5f9',
                          color: '#334155',
                        }}
                      >
                        {req.obligation_type}
                      </span>
                    </td>
                    <td style={{ padding: '14px 18px', color: '#64748b', fontSize: '12px' }}>
                      {req.validity_period_months ? `${req.validity_period_months} months` : 'Permanent / Periodic'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Add Modal */}
      {showAddModal && (
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
          onClick={() => setShowAddModal(false)}
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '12px',
              maxWidth: '500px',
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
                Register New {activeTab.slice(0, -1).toUpperCase()}
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                style={{ background: 'none', border: 'none', color: '#ffffff', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateMock} style={{ padding: '24px' }}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Unique Code *
                </label>
                <input
                  type="text"
                  value={modalCode}
                  onChange={(e) => setModalCode(e.target.value)}
                  placeholder="e.g. CPCB-EPR-PLASTIC"
                  required
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

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Full Title / Name *
                </label>
                <input
                  type="text"
                  value={modalTitle}
                  onChange={(e) => setModalTitle(e.target.value)}
                  placeholder="e.g. Extended Producer Responsibility (EPR) Certificate"
                  required
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

              {activeTab === 'requirements' && (
                <div style={{ marginBottom: '14px' }}>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                    Description & Scope
                  </label>
                  <textarea
                    value={modalDesc}
                    onChange={(e) => setModalDesc(e.target.value)}
                    placeholder="Enter compliance scope, return frequency, or threshold triggers..."
                    rows={3}
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
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ backgroundColor: '#059669', borderColor: '#059669' }}
                >
                  Save to Catalog
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
