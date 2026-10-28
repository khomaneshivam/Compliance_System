import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  CheckCircle2,
  Clock,
  AlertCircle,
  X,
  FileText,
  Calendar,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  History,
  Plus,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import { api } from '../services/api';
import type {
  RequirementDetailItem,
  SavedViewPreset,
  PaginatedRequirements,
} from '../types';

export const RequirementsPage: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [requirementsData, setRequirementsData] = useState<PaginatedRequirements | null>(null);
  const [savedViews, setSavedViews] = useState<SavedViewPreset[]>([]);
  const [activeViewId, setActiveViewId] = useState<string>('all_applicable');

  // Filter & pagination state
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(10);
  const [search, setSearch] = useState<string>('');
  const [applicabilityFilter, setApplicabilityFilter] = useState<string>('APPLICABLE');
  const [evidenceFilter, setEvidenceFilter] = useState<string>('ALL');
  const [obligationFilter, setObligationFilter] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<string>('current_due_date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Selected requirement for detail drawer
  const [selectedReq, setSelectedReq] = useState<RequirementDetailItem | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);

  // Quick Task Creation state from requirement drawer
  const [showTaskModal, setShowTaskModal] = useState<boolean>(false);
  const [taskTitle, setTaskTitle] = useState<string>('');
  const [taskDueDate, setTaskDueDate] = useState<string>('');
  const [taskPriority, setTaskPriority] = useState<'HIGH' | 'MEDIUM' | 'LOW'>('HIGH');
  const [taskSubmitting, setTaskSubmitting] = useState<boolean>(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  const fetchRequirements = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getRequirements({
        applicability_status: applicabilityFilter,
        evidence_status: evidenceFilter,
        obligation_type: obligationFilter,
        search: search.trim() || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page,
        page_size: pageSize,
      });
      setRequirementsData(data);
    } catch (err: unknown) {
      console.error('Failed to load requirements', err);
    } finally {
      setLoading(false);
    }
  }, [applicabilityFilter, evidenceFilter, obligationFilter, search, sortBy, sortOrder, page, pageSize]);

  const fetchSavedViews = useCallback(async () => {
    try {
      const views = await api.getRequirementSavedViews();
      setSavedViews(views);
    } catch (err: unknown) {
      console.error('Failed to load saved views', err);
    }
  }, []);

  useEffect(() => {
    fetchSavedViews();
  }, [fetchSavedViews]);

  useEffect(() => {
    fetchRequirements();
  }, [fetchRequirements]);

  const handleSelectView = (preset: SavedViewPreset) => {
    setActiveViewId(preset.id);
    setPage(1);
    const params = preset.filter_params;
    if (params.applicability_status) setApplicabilityFilter(String(params.applicability_status));
    if (params.evidence_status) setEvidenceFilter(String(params.evidence_status));
    if (params.obligation_type) setObligationFilter(String(params.obligation_type));
    if (params.sort_by) setSortBy(String(params.sort_by));
    if (params.sort_order) setSortOrder(params.sort_order as 'asc' | 'desc');
  };

  const handleOpenDetail = async (item: RequirementDetailItem) => {
    setDetailLoading(true);
    setSelectedReq(item);
    try {
      const fullDetail = await api.getRequirementDetail(item.id);
      setSelectedReq(fullDetail);
    } catch (err: unknown) {
      console.error('Failed to fetch requirement detail', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCreateTaskForReq = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedReq || !taskTitle || !taskDueDate) return;

    setTaskSubmitting(true);
    try {
      await api.createTask({
        plant_id: selectedReq.provenance?.jurisdiction_name || 'plant-default',
        plant_requirement_id: selectedReq.id,
        title: taskTitle,
        due_date: taskDueDate,
        priority: taskPriority,
        description: `Remediation action for obligation ${selectedReq.code}: ${selectedReq.title}.`,
      });
      setActionFeedback(`Task "${taskTitle}" successfully created and scheduled.`);
      setShowTaskModal(false);
      setTaskTitle('');
      setTaskDueDate('');
      setTimeout(() => setActionFeedback(null), 4000);
    } catch (err: unknown) {
      alert((err as Error).message || 'Failed to create task');
    } finally {
      setTaskSubmitting(false);
    }
  };

  const renderEvidenceBadge = (status: string) => {
    switch (status) {
      case 'VALID':
        return <span className="badge badge-success"><CheckCircle2 size={12} /> Valid Evidence</span>;
      case 'EXPIRING_SOON':
        return <span className="badge badge-warning"><Clock size={12} /> Expiring Soon</span>;
      case 'EXPIRED':
        return <span className="badge badge-critical"><AlertCircle size={12} /> Expired</span>;
      case 'MISSING':
        return <span className="badge badge-critical"><AlertCircle size={12} /> Evidence Missing</span>;
      default:
        return <span className="badge badge-neutral">{status}</span>;
    }
  };

  const renderApplicabilityBadge = (status: string) => {
    switch (status) {
      case 'APPLICABLE':
        return <span className="badge badge-success">Applicable</span>;
      case 'CONDITIONALLY_APPLICABLE':
        return <span className="badge badge-warning">Conditional</span>;
      case 'EXEMPTED':
        return <span className="badge badge-neutral">Exempt</span>;
      case 'NOT_APPLICABLE':
        return <span className="badge badge-neutral">Not Applicable</span>;
      default:
        return <span className="badge badge-info">{status}</span>;
    }
  };

  return (
    <div className="requirements-page" style={{ padding: '24px 32px' }}>
      {/* Top Banner / Feedback */}
      {actionFeedback && (
        <div className="banner banner-success" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={16} />
          <span>{actionFeedback}</span>
        </div>
      )}

      {/* Header & Subtitle */}
      <div className="page-header" style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 600, color: '#0f172a', margin: '0 0 4px 0' }}>
            Facility Requirements Register
          </h1>
          <p style={{ color: '#64748b', fontSize: '13px', margin: 0 }}>
            Deterministic statutory register derived from jurisdictional rules, official gazettes, and factory operational parameters.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={() => fetchRequirements()} title="Refresh requirements register">
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Saved Views Preset Pills */}
      {savedViews.length > 0 && (
        <div className="saved-views-bar" style={{ display: 'flex', gap: '8px', marginBottom: '20px', overflowX: 'auto', paddingBottom: '4px' }}>
          {savedViews.map((view) => {
            const isActive = activeViewId === view.id;
            return (
              <button
                key={view.id}
                onClick={() => handleSelectView(view)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '6px 14px',
                  borderRadius: '20px',
                  border: isActive ? '1px solid #059669' : '1px solid #e2e8f0',
                  background: isActive ? '#ecfdf5' : '#ffffff',
                  color: isActive ? '#065f46' : '#475569',
                  fontSize: '13px',
                  fontWeight: isActive ? 600 : 500,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  whiteSpace: 'nowrap',
                }}
              >
                <span>{view.name}</span>
                <span
                  style={{
                    background: isActive ? '#059669' : '#f1f5f9',
                    color: isActive ? '#ffffff' : '#64748b',
                    fontSize: '11px',
                    padding: '2px 6px',
                    borderRadius: '10px',
                    fontWeight: 600,
                  }}
                >
                  {view.count}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Search & Dynamic Filter Controls */}
      <div
        className="controls-card"
        style={{
          background: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: '8px',
          padding: '16px',
          marginBottom: '20px',
          display: 'grid',
          gridTemplateColumns: '1.5fr 1fr 1fr 1fr auto',
          gap: '12px',
          alignItems: 'center',
        }}
      >
        {/* Search */}
        <div style={{ position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: '#94a3b8' }} />
          <input
            type="text"
            className="input-field"
            placeholder="Search code, title, or authority..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            style={{ paddingLeft: '32px', width: '100%', fontSize: '13px' }}
          />
        </div>

        {/* Applicability Filter */}
        <div>
          <select
            aria-label="Filter by applicability status"
            className="input-field"
            value={applicabilityFilter}
            onChange={(e) => {
              setApplicabilityFilter(e.target.value);
              setActiveViewId('');
              setPage(1);
            }}
            style={{ width: '100%', fontSize: '13px' }}
          >
            <option value="ALL">All Applicability Statuses</option>
            <option value="APPLICABLE">Applicable Only</option>
            <option value="CONDITIONALLY_APPLICABLE">Conditionally Applicable</option>
            <option value="EXEMPTED">Exempted</option>
            <option value="NOT_APPLICABLE">Not Applicable</option>
          </select>
        </div>

        {/* Evidence Filter */}
        <div>
          <select
            aria-label="Filter by evidence state"
            className="input-field"
            value={evidenceFilter}
            onChange={(e) => {
              setEvidenceFilter(e.target.value);
              setActiveViewId('');
              setPage(1);
            }}
            style={{ width: '100%', fontSize: '13px' }}
          >
            <option value="ALL">All Evidence States</option>
            <option value="VALID">Valid Evidence</option>
            <option value="EXPIRING_SOON">Expiring Soon (30 Days)</option>
            <option value="MISSING">Missing Evidence Gaps</option>
            <option value="EXPIRED">Expired Evidence</option>
          </select>
        </div>

        {/* Obligation Type */}
        <div>
          <select
            aria-label="Filter by obligation type"
            className="input-field"
            value={obligationFilter}
            onChange={(e) => {
              setObligationFilter(e.target.value);
              setActiveViewId('');
              setPage(1);
            }}
            style={{ width: '100%', fontSize: '13px' }}
          >
            <option value="ALL">All Obligation Types</option>
            <option value="CONSENT">Consent (CTO / CTE)</option>
            <option value="LICENCE">Factory Licence</option>
            <option value="CERTIFICATE">Inspection Certificate</option>
            <option value="PERMIT">Safety Permit</option>
            <option value="RETURN">Statutory Return</option>
          </select>
        </div>

        {/* Sorting Dropdown */}
        <div>
          <select
            aria-label="Sort requirements by"
            className="input-field"
            value={`${sortBy}:${sortOrder}`}
            onChange={(e) => {
              const [sb, so] = e.target.value.split(':');
              setSortBy(sb);
              setSortOrder(so as 'asc' | 'desc');
            }}
            style={{ fontSize: '13px' }}
          >
            <option value="current_due_date:asc">Due Date (Earliest First)</option>
            <option value="current_due_date:desc">Due Date (Latest First)</option>
            <option value="code:asc">Code (A - Z)</option>
            <option value="title:asc">Title (A - Z)</option>
          </select>
        </div>
      </div>

      {/* Main Requirements Table */}
      <div className="table-container" style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
        <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>Code</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>Obligation Title</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>Authority</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>Applicability</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>Evidence Status</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>Due / Renewal Date</th>
              <th style={{ padding: '12px 16px', fontWeight: 600 }}>Owner</th>
              <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                  <RefreshCw className="spin" size={24} style={{ margin: '0 auto 8px auto', display: 'block' }} />
                  Loading server-side requirements register...
                </td>
              </tr>
            ) : !requirementsData || requirementsData.items.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ padding: '48px 24px', textAlign: 'center' }}>
                  <div style={{ maxWidth: '400px', margin: '0 auto' }}>
                    <ShieldCheck size={40} style={{ color: '#94a3b8', margin: '0 auto 12px auto' }} />
                    <h3 style={{ margin: '0 0 6px 0', fontSize: '16px', color: '#1e293b' }}>No Requirements Found</h3>
                    <p style={{ margin: 0, fontSize: '13px', color: '#64748b' }}>
                      No statutory obligations match the selected filter criteria. Try clearing search filters or running an applicability assessment.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              requirementsData.items.map((req) => (
                <tr
                  key={req.id}
                  style={{
                    borderBottom: '1px solid #f1f5f9',
                    cursor: 'pointer',
                    transition: 'background 0.1s ease',
                  }}
                  className="table-row-hover"
                  onClick={() => handleOpenDetail(req)}
                >
                  <td style={{ padding: '14px 16px', fontWeight: 600, color: '#0f172a' }}>
                    {req.code}
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <div style={{ fontWeight: 500, color: '#1e293b' }}>{req.title}</div>
                    <div style={{ fontSize: '12px', color: '#64748b' }}>{req.obligation_type}</div>
                  </td>
                  <td style={{ padding: '14px 16px', color: '#475569' }}>
                    <span title={req.authority_name || req.authority_code || 'Regulator'}>
                      {req.authority_code || 'Regulator'}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    {renderApplicabilityBadge(req.applicability_status)}
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    {renderEvidenceBadge(req.evidence_status)}
                  </td>
                  <td style={{ padding: '14px 16px', color: '#334155' }}>
                    {req.current_due_date ? (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <Calendar size={13} style={{ color: '#64748b' }} />
                        {req.current_due_date}
                      </span>
                    ) : (
                      <span style={{ color: '#94a3b8' }}>N/A</span>
                    )}
                  </td>
                  <td style={{ padding: '14px 16px', color: '#475569' }}>
                    {req.owner_name || 'Unassigned'}
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenDetail(req);
                      }}
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Server-Side Pagination Bar */}
        {requirementsData && requirementsData.total > 0 && (
          <div
            style={{
              padding: '12px 16px',
              borderTop: '1px solid #e2e8f0',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: '#f8fafc',
              fontSize: '13px',
              color: '#64748b',
            }}
          >
            <div>
              Showing <strong>{(page - 1) * pageSize + 1}</strong> to{' '}
              <strong>{Math.min(page * pageSize, requirementsData.total)}</strong> of{' '}
              <strong>{requirementsData.total}</strong> obligations
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button
                className="btn btn-secondary btn-sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft size={14} /> Previous
              </button>
              <span>
                Page <strong>{page}</strong> of <strong>{requirementsData.total_pages}</strong>
              </span>
              <button
                className="btn btn-secondary btn-sm"
                disabled={page >= requirementsData.total_pages}
                onClick={() => setPage((p) => Math.min(requirementsData.total_pages, p + 1))}
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Slide-Over Drawer for Requirement Provenance & Details */}
      {selectedReq && (
        <div
          className="drawer-overlay"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.45)',
            backdropFilter: 'blur(2px)',
            zIndex: 1000,
            display: 'flex',
            justifyContent: 'flex-end',
          }}
          onClick={() => setSelectedReq(null)}
        >
          <div
            className="drawer-content"
            style={{
              width: '560px',
              maxWidth: '90vw',
              background: '#ffffff',
              height: '100%',
              overflowY: 'auto',
              boxShadow: '-4px 0 24px rgba(0,0,0,0.15)',
              display: 'flex',
              flexDirection: 'column',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Drawer Header */}
            <div
              style={{
                padding: '20px 24px',
                borderBottom: '1px solid #e2e8f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                background: '#06281e',
                color: '#ffffff',
              }}
            >
              <div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '12px', background: 'rgba(255,255,255,0.15)', padding: '2px 8px', borderRadius: '4px' }}>
                    {selectedReq.code}
                  </span>
                  <span style={{ fontSize: '12px', color: '#a7f3d0' }}>
                    {selectedReq.obligation_type}
                  </span>
                </div>
                <h2 style={{ fontSize: '18px', fontWeight: 600, margin: 0, color: '#ffffff' }}>
                  {selectedReq.title}
                </h2>
              </div>
              <button
                onClick={() => setSelectedReq(null)}
                style={{ background: 'transparent', border: 'none', color: '#ffffff', cursor: 'pointer', padding: '4px' }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Drawer Body */}
            <div style={{ padding: '24px', flex: 1, display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {detailLoading ? (
                <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                  <RefreshCw className="spin" size={24} style={{ margin: '0 auto 8px auto', display: 'block' }} />
                  Loading provenance trail and linked evidence...
                </div>
              ) : (
                <>
                  {/* Status & Key Dates Banner */}
                  <div
                    style={{
                      background: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      padding: '16px',
                      display: 'grid',
                      gridTemplateColumns: 'repeat(2, 1fr)',
                      gap: '12px',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#64748b', fontWeight: 600, marginBottom: '4px' }}>
                        Applicability State
                      </div>
                      {renderApplicabilityBadge(selectedReq.applicability_status)}
                    </div>
                    <div>
                      <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#64748b', fontWeight: 600, marginBottom: '4px' }}>
                        Evidence Status
                      </div>
                      {renderEvidenceBadge(selectedReq.evidence_status)}
                    </div>
                    <div>
                      <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#64748b', fontWeight: 600, marginBottom: '4px' }}>
                        Due / Renewal Date
                      </div>
                      <div style={{ fontSize: '13px', fontWeight: 500, color: '#1e293b' }}>
                        {selectedReq.current_due_date || 'No fixed expiry'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#64748b', fontWeight: 600, marginBottom: '4px' }}>
                        Responsible Owner
                      </div>
                      <div style={{ fontSize: '13px', fontWeight: 500, color: '#1e293b' }}>
                        {selectedReq.owner_name || 'Unassigned'}
                      </div>
                    </div>
                  </div>

                  {/* Statutory Provenance Box */}
                  <div>
                    <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#1e293b', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <FileText size={15} style={{ color: '#059669' }} /> Statutory Provenance & Legal Basis
                    </h3>
                    <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '6px', padding: '14px', fontSize: '13px' }}>
                      <div style={{ marginBottom: '10px' }}>
                        {selectedReq.provenance?.source_verification_status === 'VERIFIED' ? (
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 600, background: '#dcfce7', color: '#15803d', border: '1px solid #86efac' }}>
                            ✓ Officially Verified Gazette Instrument
                          </span>
                        ) : selectedReq.provenance?.source_verification_status === 'PROPOSED' ? (
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 600, background: '#e0f2fe', color: '#0369a1', border: '1px solid #7dd3fc' }}>
                            ℹ️ Proposed Rule Version (Pending Approval)
                          </span>
                        ) : (
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 600, background: '#fef3c7', color: '#b45309', border: '1px solid #fde68a' }}>
                            ⚠️ Unverified Demo Fixture (Pending Gazette Match)
                          </span>
                        )}
                      </div>
                      <div style={{ marginBottom: '6px' }}>
                        <strong>Governing Act:</strong> {selectedReq.provenance?.act_title || 'N/A'}{' '}
                        {selectedReq.provenance?.act_year ? `(${selectedReq.provenance.act_year})` : ''}
                      </div>
                      <div style={{ marginBottom: '6px' }}>
                        <strong>Issuing Authority:</strong> {selectedReq.provenance?.authority_name || selectedReq.authority_name || 'Regulatory Board'}
                      </div>
                      <div style={{ marginBottom: '6px' }}>
                        <strong>Jurisdiction:</strong> {selectedReq.provenance?.jurisdiction_name || selectedReq.jurisdiction} ({selectedReq.provenance?.jurisdiction_level || 'STATE'})
                      </div>
                      {(selectedReq.provenance?.instrument_identifier || selectedReq.provenance?.official_gazette_ref || selectedReq.provenance?.gazette_reference) && (
                        <div style={{ marginBottom: '6px' }}>
                          <strong>Gazette / Instrument ID:</strong> {selectedReq.provenance.instrument_identifier || selectedReq.provenance.official_gazette_ref || selectedReq.provenance.gazette_reference}
                        </div>
                      )}
                      {selectedReq.provenance?.section_clause && (
                        <div style={{ marginBottom: '6px' }}>
                          <strong>Statutory Clause:</strong> {selectedReq.provenance.section_clause}
                        </div>
                      )}
                      {selectedReq.provenance?.publication_date && (
                        <div style={{ marginBottom: '6px' }}>
                          <strong>Published Date:</strong> {new Date(selectedReq.provenance.publication_date).toLocaleDateString()}
                        </div>
                      )}
                      {selectedReq.provenance?.official_source_url && (
                        <div style={{ marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <strong>Official Source:</strong>{' '}
                          <a
                            href={selectedReq.provenance.official_source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: '#059669', textDecoration: 'underline', display: 'inline-flex', alignItems: 'center', gap: '3px' }}
                          >
                            Official Portal Link <ExternalLink size={12} />
                          </a>
                        </div>
                      )}
                      {selectedReq.provenance?.source_fingerprint && (
                        <div style={{ marginTop: '8px', paddingTop: '6px', borderTop: '1px dashed #bbf7d0', fontSize: '11px', color: '#475569' }}>
                          <strong>SHA-256 Fingerprint:</strong> <code style={{ background: '#f8fafc', padding: '1px 4px', borderRadius: '3px', fontSize: '10px' }}>{selectedReq.provenance.source_fingerprint}</code>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Applicability Explanation */}
                  <div>
                    <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#1e293b', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <ShieldCheck size={15} style={{ color: '#059669' }} /> Deterministic Applicability Explanation
                    </h3>
                    <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '14px', fontSize: '13px', lineHeight: 1.5 }}>
                      <p style={{ margin: '0 0 8px 0', color: '#1e293b' }}>
                        {selectedReq.applicability?.applicability_rationale || selectedReq.applicability_rationale}
                      </p>

                      {selectedReq.applicability?.missing_facts && selectedReq.applicability.missing_facts.length > 0 && (
                        <div style={{ margin: '8px 0', padding: '8px 12px', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '4px', fontSize: '12px', color: '#92400e' }}>
                          <strong>⚠️ Missing Company Facts for Evaluation:</strong>
                          <div style={{ marginTop: '4px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                            {selectedReq.applicability.missing_facts.map((mf: string) => (
                              <span key={mf} style={{ background: '#fef3c7', padding: '2px 6px', borderRadius: '3px', fontSize: '11px', fontFamily: 'monospace' }}>
                                {mf}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {selectedReq.applicability?.matched_facts && Object.keys(selectedReq.applicability.matched_facts).length > 0 && (
                        <div style={{ margin: '8px 0', fontSize: '12px', color: '#475569' }}>
                          <strong>Evaluated Plant Facts:</strong>
                          <div style={{ marginTop: '4px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                            {Object.entries(selectedReq.applicability.matched_facts).map(([k, v]) => (
                              <span key={k} style={{ background: '#f1f5f9', border: '1px solid #e2e8f0', padding: '2px 6px', borderRadius: '3px', fontSize: '11px' }}>
                                <strong>{k}:</strong> {String(v)}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div style={{ fontSize: '11px', color: '#64748b', marginTop: '8px' }}>
                        Rule Engine Version: <strong>v{selectedReq.applicability?.rule_version || 1}</strong> | Evaluated at:{' '}
                        {selectedReq.last_evaluated_at ? new Date(selectedReq.last_evaluated_at).toLocaleDateString() : 'Baseline'}
                      </div>
                    </div>
                  </div>

                  {/* Linked Evidence Files */}
                  <div>
                    <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#1e293b', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CheckCircle2 size={15} style={{ color: '#059669' }} /> Verified Evidence Documents ({selectedReq.evidence_list?.length || 0})
                    </h3>
                    {selectedReq.evidence_list && selectedReq.evidence_list.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {selectedReq.evidence_list.map((ev) => (
                          <div
                            key={ev.evidence_link_id}
                            style={{
                              border: '1px solid #e2e8f0',
                              borderRadius: '6px',
                              padding: '10px 14px',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              fontSize: '13px',
                            }}
                          >
                            <div>
                              <div style={{ fontWeight: 500, color: '#0f172a' }}>{ev.original_filename}</div>
                              <div style={{ fontSize: '11px', color: '#64748b' }}>
                                Uploaded on {new Date(ev.upload_date).toLocaleDateString()} | {(ev.file_size_bytes / 1024).toFixed(1)} KB
                              </div>
                            </div>
                            <span className="badge badge-success">
                              {ev.review_status}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ background: '#fef2f2', border: '1px solid #fee2e2', borderRadius: '6px', padding: '12px 14px', color: '#991b1b', fontSize: '13px' }}>
                        No compliance evidence document currently attached for this obligation.
                      </div>
                    )}
                  </div>

                  {/* Audit & Change History */}
                  {selectedReq.history && selectedReq.history.length > 0 && (
                    <div>
                      <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#1e293b', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <History size={15} style={{ color: '#64748b' }} /> Audit & Version History
                      </h3>
                      <div style={{ borderLeft: '2px solid #e2e8f0', paddingLeft: '14px', marginLeft: '6px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {selectedReq.history.map((hist) => (
                          <div key={hist.id} style={{ fontSize: '12px' }}>
                            <div style={{ color: '#64748b', marginBottom: '2px' }}>
                              {new Date(hist.timestamp).toLocaleDateString()} by <strong>{hist.performed_by}</strong>
                            </div>
                            <div style={{ color: '#1e293b', fontWeight: 500 }}>{hist.summary_text}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Drawer Footer Actions */}
            <div
              style={{
                padding: '16px 24px',
                borderTop: '1px solid #e2e8f0',
                background: '#f8fafc',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <button
                className="btn btn-primary"
                onClick={() => {
                  setTaskTitle(`Fulfill ${selectedReq.code} Evidence`);
                  setTaskDueDate(selectedReq.current_due_date || new Date(Date.now() + 14 * 86400000).toISOString().split('T')[0]);
                  setShowTaskModal(true);
                }}
              >
                <Plus size={14} /> Create Remediation Task
              </button>
              <button className="btn btn-secondary" onClick={() => setSelectedReq(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Quick Task Creation Modal */}
      {showTaskModal && (
        <div
          className="modal-overlay"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1100,
          }}
        >
          <div
            className="card"
            style={{ width: '480px', maxWidth: '95vw', padding: '24px', background: '#ffffff', borderRadius: '8px' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>Create Remediation Task</h3>
              <button onClick={() => setShowTaskModal(false)} style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreateTaskForReq}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                  Task Title
                </label>
                <input
                  type="text"
                  className="input-field"
                  required
                  value={taskTitle}
                  onChange={(e) => setTaskTitle(e.target.value)}
                  style={{ width: '100%', fontSize: '13px' }}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                    Target Due Date
                  </label>
                  <input
                    type="date"
                    className="input-field"
                    required
                    value={taskDueDate}
                    onChange={(e) => setTaskDueDate(e.target.value)}
                    style={{ width: '100%', fontSize: '13px' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                    Priority
                  </label>
                  <select
                    className="input-field"
                    value={taskPriority}
                    onChange={(e) => setTaskPriority(e.target.value as 'HIGH' | 'MEDIUM' | 'LOW')}
                    style={{ width: '100%', fontSize: '13px' }}
                  >
                    <option value="HIGH">High Priority</option>
                    <option value="MEDIUM">Medium Priority</option>
                    <option value="LOW">Low Priority</option>
                  </select>
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowTaskModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={taskSubmitting}>
                  {taskSubmitting ? 'Creating...' : 'Schedule Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
