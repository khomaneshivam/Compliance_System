import React, { useState, useEffect, useCallback } from 'react';
import {
  Scale,
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Search,
  Filter,
  ArrowLeft,
  ExternalLink,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Building2,
  Check,
  GitCompare,
  History,
  Tag,
  ChevronRight,
  Sparkles,
  Server,
  Activity,
  Edit3,
  FileCheck,
} from 'lucide-react';
import { api } from '../services/api';
import type {
  RegulatorySource,
  RegulatoryChangeReview,
  RegulatoryChangeImpact,
  RegulatoryAuditLog,
} from '../types';

export const RegulatoryChangeDetailPage: React.FC = () => {
  // Navigation / View State
  const [activeMainView, setActiveMainView] = useState<'inbox' | 'sources' | 'detail'>('inbox');
  const [selectedChangeId, setSelectedChangeId] = useState<string | null>(null);
  
  // Data State
  const [sources, setSources] = useState<RegulatorySource[]>([]);
  const [changes, setChanges] = useState<RegulatoryChangeReview[]>([]);
  const [currentChange, setCurrentChange] = useState<RegulatoryChangeReview | null>(null);
  const [impacts, setImpacts] = useState<RegulatoryChangeImpact[]>([]);
  const [historyLogs, setHistoryLogs] = useState<RegulatoryAuditLog[]>([]);
  
  // UI State
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [detailTab, setDetailTab] = useState<'proposal' | 'diff' | 'impacts' | 'history'>('proposal');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [pollingSourceId, setPollingSourceId] = useState<string | null>(null);
  const [pollScenario, setPollScenario] = useState<string>('default');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  
  // Reviewer Form State
  const [editableSummary, setEditableSummary] = useState<string>('');
  const [editableEffectiveDate, setEditableEffectiveDate] = useState<string>('');
  const [editableRequirementCode, setEditableRequirementCode] = useState<string>('REQ-MPCB-001');
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [isSubmittingReview, setIsSubmittingReview] = useState<boolean>(false);

  // Load Initial Data
  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [srcList, chgList] = await Promise.all([
        api.getRegulatorySources(),
        api.getRegulatoryChanges(),
      ]);
      setSources(srcList);
      setChanges(chgList);
      
      // Auto-select first change review if available
      if (chgList.length > 0 && !selectedChangeId) {
        setSelectedChangeId(chgList[0].id);
      }
    } catch {
      // Handled by api fallback
    } finally {
      setIsLoading(false);
    }
  }, [selectedChangeId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load details whenever selectedChangeId changes
  useEffect(() => {
    if (!selectedChangeId) return;
    
    api.getRegulatoryChangeDetail(selectedChangeId).then((item) => {
      setCurrentChange(item);
      setEditableSummary(item.summary_plain_language);
      setEditableEffectiveDate(item.effective_date || '2026-12-01');
      setEditableRequirementCode(item.target_requirement_code || 'MPCB-CTO');
    });

    api.getRegulatoryChangeImpacts(selectedChangeId).then((impList) => {
      setImpacts(impList);
    });

    api.getRegulatoryChangeHistory(selectedChangeId).then((logs) => {
      setHistoryLogs(logs);
    });
  }, [selectedChangeId]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Trigger Source Poll
  const handlePollSource = async (sourceId: string) => {
    setPollingSourceId(sourceId);
    try {
      const newChanges = await api.pollRegulatorySource(sourceId, pollScenario);
      showToast(`Source poll completed successfully. ${newChanges.length} review item(s) processed.`);
      // Refresh source list and changes
      const [updatedSources, updatedChanges] = await Promise.all([
        api.getRegulatorySources(),
        api.getRegulatoryChanges(),
      ]);
      setSources(updatedSources);
      setChanges(updatedChanges);
    } catch (err: any) {
      showToast(`Polling alert: ${err.message || 'Source check reported issues'}`);
    } finally {
      setPollingSourceId(null);
    }
  };

  // Save Draft Changes
  const handleSaveDraft = async () => {
    if (!currentChange) return;
    try {
      const updated = await api.updateRegulatoryChangeDraft(currentChange.id, {
        summary_plain_language: editableSummary,
        effective_date: editableEffectiveDate,
        target_requirement_code: editableRequirementCode,
      });
      setCurrentChange(updated);
      showToast('Draft edits saved to change review item.');
    } catch {
      showToast('Error saving draft edits.');
    }
  };

  // Submit Review Decision (Approve / Reject)
  const handleReviewDecision = async (decision: 'APPROVE' | 'REJECT') => {
    if (!currentChange) return;
    if (!reviewNotes.trim()) {
      alert('Review rationale / notes are required for regulatory provenance audit.');
      return;
    }

    setIsSubmittingReview(true);
    try {
      const updated = await api.submitRegulatoryReviewDecision(currentChange.id, {
        decision,
        review_notes: reviewNotes,
        effective_date: editableEffectiveDate,
        target_requirement_code: editableRequirementCode,
      });
      setCurrentChange(updated);
      
      // Refresh impact list and audit history
      const [updatedImpacts, updatedLogs] = await Promise.all([
        api.getRegulatoryChangeImpacts(currentChange.id),
        api.getRegulatoryChangeHistory(currentChange.id),
      ]);
      setImpacts(updatedImpacts);
      setHistoryLogs(updatedLogs);

      showToast(
        decision === 'APPROVE'
          ? 'Regulatory change APPROVED: Immutable rule version published and facility impacts evaluated.'
          : 'Proposal REJECTED: Reason stamped in audit trail.'
      );
    } catch (err: any) {
      showToast(`Review submission error: ${err.message || 'Check inputs'}`);
    } finally {
      setIsSubmittingReview(false);
    }
  };

  // Filtered Changes
  const filteredChanges = changes.filter((c) => {
    const matchesStatus = statusFilter === 'all' || c.status === statusFilter;
    const matchesSearch =
      searchQuery === '' ||
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.notification_number.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div
          style={{
            position: 'fixed',
            top: '80px',
            right: '28px',
            zIndex: 999,
            backgroundColor: '#064e3b',
            color: '#ecfdf5',
            padding: '12px 20px',
            borderRadius: '6px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            fontSize: '0.88rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            border: '1px solid #059669',
          }}
        >
          <CheckCircle2 size={18} />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Header & Sub-Navigation */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '1.45rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
              Regulatory Intelligence & Change Review
            </h1>
            <span className="badge badge-info" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <ShieldCheck size={12} />
              <span>Auditable Pipeline</span>
            </span>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Multi-stage ingestion pipeline with content hash deduplication, AI drafting with confidence bands, and human review gates.
          </p>
        </div>

        {/* View Switcher Tabs */}
        <div style={{ display: 'flex', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '6px', padding: '3px' }}>
          <button
            onClick={() => setActiveMainView('inbox')}
            style={{
              padding: '6px 14px',
              fontSize: '0.82rem',
              fontWeight: 600,
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              background: activeMainView === 'inbox' ? 'var(--brand-primary)' : 'transparent',
              color: activeMainView === 'inbox' ? '#ffffff' : 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Scale size={14} />
            <span>Detected Changes ({changes.length})</span>
          </button>

          <button
            onClick={() => setActiveMainView('sources')}
            style={{
              padding: '6px 14px',
              fontSize: '0.82rem',
              fontWeight: 600,
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              background: activeMainView === 'sources' ? 'var(--brand-primary)' : 'transparent',
              color: activeMainView === 'sources' ? '#ffffff' : 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Server size={14} />
            <span>Source Registry & Health ({sources.length})</span>
          </button>
        </div>
      </div>

      {/* Cardinal Rule Safeguard Banner */}
      <div
        style={{
          backgroundColor: '#eff6ff',
          border: '1px solid #bfdbfe',
          borderRadius: '6px',
          padding: '12px 18px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          color: '#1e3a8a',
          fontSize: '0.84rem',
        }}
      >
        <ShieldAlert size={20} style={{ color: '#2563eb', flexShrink: 0 }} />
        <div>
          <strong>The Cardinal Regulatory Rule: "AI Proposes, Humans Dispose."</strong>
          <div style={{ color: '#1e40af', marginTop: '2px', fontSize: '0.80rem' }}>
            Machine learning extractions and category mappings are strictly proposals. No legal obligation is altered and no enterprise register is updated until confirmed by an authorized compliance reviewer.
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* VIEW 1: DETECTED CHANGES INBOX                                            */}
      {/* ========================================================================= */}
      {activeMainView === 'inbox' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Controls Bar */}
          <div className="card" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: '280px' }}>
              <div style={{ position: 'relative', flex: 1, maxWidth: '380px' }}>
                <Search size={15} style={{ position: 'absolute', left: '10px', top: '9px', color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Filter by notification number, authority, or title..."
                  className="form-input"
                  style={{ paddingLeft: '32px' }}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Filter size={15} style={{ color: 'var(--text-muted)' }} />
                <select
                  className="form-select"
                  style={{ width: '170px' }}
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="all">All Statuses</option>
                  <option value="needs_review">Needs Review</option>
                  <option value="approved">Approved & Published</option>
                  <option value="rejected">Rejected</option>
                  <option value="extraction_failed">Extraction Failed</option>
                </select>
              </div>
            </div>

            <button
              className="btn-secondary"
              onClick={loadData}
              disabled={isLoading}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <RefreshCw size={14} className={isLoading ? 'spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>

          {/* Changes Table */}
          <div className="data-table-container">
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ background: 'var(--bg-canvas)', borderBottom: '1px solid var(--border-default)', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Notification & Authority</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Change Type</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>AI Confidence</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Effective Date</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>Status</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredChanges.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ padding: '40px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No regulatory changes found matching the selected filter.
                    </td>
                  </tr>
                ) : (
                  filteredChanges.map((change) => {
                    const isSelected = selectedChangeId === change.id;
                    return (
                      <tr
                        key={change.id}
                        style={{
                          borderBottom: '1px solid var(--border-default)',
                          backgroundColor: isSelected ? 'var(--brand-tint)' : 'transparent',
                          transition: 'background 0.15s ease',
                        }}
                      >
                        <td style={{ padding: '14px 16px', maxWidth: '380px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                            <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.82rem' }}>
                              {change.notification_number}
                            </span>
                            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>•</span>
                            <span style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                              {change.published_date || 'Recent'}
                            </span>
                            <span
                              className="badge badge-neutral"
                              style={{
                                fontSize: '0.66rem',
                                padding: '1px 5px',
                                background: change.source_adapter_mode === 'LIVE_HTTP' ? '#eff6ff' : '#f8fafc',
                                color: change.source_adapter_mode === 'LIVE_HTTP' ? '#1d4ed8' : '#64748b',
                                border: '1px solid var(--border-default)',
                              }}
                            >
                              {change.source_adapter_mode === 'LIVE_HTTP' ? '🌐 Live Portal' : '🧪 Fixture Feed'}
                            </span>
                          </div>
                          <div
                            style={{
                              fontSize: '0.86rem',
                              color: 'var(--text-primary)',
                              fontWeight: 500,
                              marginTop: '3px',
                              lineHeight: 1.4,
                            }}
                          >
                            {change.title}
                          </div>
                        </td>


                        <td style={{ padding: '14px 16px' }}>
                          <span
                            className="badge badge-neutral"
                            style={{
                              fontSize: '0.70rem',
                              backgroundColor: change.detected_change_type === 'AMENDMENT' ? '#fef3c7' : '#ecfdf5',
                              color: change.detected_change_type === 'AMENDMENT' ? '#92400e' : '#065f46',
                              border: '1px solid var(--border-default)',
                            }}
                          >
                            {change.detected_change_type}
                          </span>
                        </td>

                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span
                              className={`badge ${
                                change.confidence_band === 'HIGH'
                                  ? 'badge-valid'
                                  : change.confidence_band === 'MEDIUM'
                                  ? 'badge-warning'
                                  : 'badge-danger'
                              }`}
                            >
                              <Sparkles size={11} />
                              <span>{change.confidence_band} ({Math.round(change.confidence_score * 100)}%)</span>
                            </span>
                          </div>
                        </td>

                        <td style={{ padding: '14px 16px', color: 'var(--text-secondary)' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <Clock size={13} style={{ color: 'var(--text-muted)' }} />
                            <span>{change.effective_date || 'Immediate'}</span>
                          </div>
                        </td>

                        <td style={{ padding: '14px 16px' }}>
                          {change.status === 'approved' || change.status === 'published' ? (
                            <span className="badge badge-valid">
                              <CheckCircle2 size={12} /> Approved & Published
                            </span>
                          ) : change.status === 'rejected' ? (
                            <span className="badge badge-danger">
                              <XCircle size={12} /> Rejected
                            </span>
                          ) : change.status === 'extraction_failed' ? (
                            <span className="badge badge-danger">
                              <AlertTriangle size={12} /> Extraction Failed
                            </span>
                          ) : (
                            <span className="badge badge-warning">
                              <Clock size={12} /> Needs Review
                            </span>
                          )}
                        </td>

                        <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                          <button
                            className="btn-primary"
                            style={{ padding: '5px 12px', fontSize: '0.78rem' }}
                            onClick={() => {
                              setSelectedChangeId(change.id);
                              setActiveMainView('detail');
                            }}
                          >
                            <span>Review Change</span>
                            <ChevronRight size={13} />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW 2: SOURCE REGISTRY & HEALTH                                          */}
      {/* ========================================================================= */}
      {activeMainView === 'sources' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="card" style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Official Regulatory Source Registry
              </h2>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Monitors government gazettes and statutory portals with strict timeouts, rate limiting, and fallback fixture adapters.
              </p>
            </div>

            {/* Test Scenario Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '0.80rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                Test Scenario:
              </span>
              <select
                className="form-select"
                style={{ width: '190px', fontSize: '0.80rem' }}
                value={pollScenario}
                onChange={(e) => setPollScenario(e.target.value)}
              >
                <option value="default">Default Official Feed</option>
                <option value="amendment_revised_hash">Revised Hash Amendment</option>
                <option value="corrupt_pdf">Corrupted File Test</option>
                <option value="oversized">Oversized File (Exceeds 25MB)</option>
                <option value="prompt_injection">Prompt Injection Test</option>
                <option value="offline">Offline / Unavailable</option>
              </select>
            </div>
          </div>

          {/* Sources Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))', gap: '16px' }}>
            {sources.map((src) => {
              const isPolling = pollingSourceId === src.id;
              const isHealthy = src.health_status === 'HEALTHY';
              const isUnavailable = src.health_status === 'UNAVAILABLE';

              return (
                <div key={src.id} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div>
                    {/* Header */}
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px', marginBottom: '10px' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.92rem', color: 'var(--text-primary)' }}>
                            {src.name}
                          </span>
                        </div>
                        <span style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                          {src.authority_name} ({src.jurisdiction})
                        </span>
                      </div>

                      {/* Health Status & Mode Badges */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                        <span
                          className={`badge ${
                            src.adapter_mode === 'LIVE_HTTP'
                              ? 'badge-info'
                              : src.adapter_mode === 'FAILED'
                              ? 'badge-danger'
                              : 'badge-neutral'
                          }`}
                          style={{ fontSize: '0.70rem' }}
                        >
                          {src.adapter_mode === 'LIVE_HTTP'
                            ? '🌐 Live Portal'
                            : src.adapter_mode === 'FAILED'
                            ? 'Connection Failed'
                            : src.adapter_mode === 'DISABLED'
                            ? 'Disabled'
                            : '🧪 Fixture Feed'}
                        </span>
                        <span
                          className={`badge ${
                            isHealthy
                              ? 'badge-valid'
                              : isUnavailable
                              ? 'badge-danger'
                              : 'badge-warning'
                          }`}
                        >
                          <Activity size={12} />
                          <span>{src.health_status}</span>
                        </span>
                      </div>
                    </div>

                    {/* Sanitized Error & Remediation Banner */}
                    {src.error_message && (
                      <div
                        style={{
                          backgroundColor: '#fff1f2',
                          border: '1px solid #fecdd3',
                          borderRadius: '6px',
                          padding: '8px 12px',
                          fontSize: '0.75rem',
                          color: '#9f1239',
                          marginBottom: '10px',
                        }}
                      >
                        <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '5px' }}>
                          <AlertTriangle size={13} />
                          <span>{src.error_category || 'Ingestion Alert'}: {src.error_message}</span>
                        </div>
                        <div style={{ fontSize: '0.70rem', color: '#be123c', marginTop: '2px' }}>
                          Remediation: Verify public portal availability or retry during normal scheduled maintenance windows.
                        </div>
                      </div>
                    )}

                    {/* Meta Specs */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.78rem', color: 'var(--text-secondary)', margin: '12px 0' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Adapter Type:</span>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{src.adapter_type}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Check Frequency:</span>
                        <span>{src.update_frequency}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Expected Format:</span>
                        <span>{src.expected_format}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Last Successful:</span>
                        <span>{src.last_successful_check_at ? new Date(src.last_successful_check_at).toLocaleTimeString() : 'Never'}</span>
                      </div>
                    </div>


                    {/* URL & Terms */}
                    <div
                      style={{
                        backgroundColor: 'var(--bg-canvas)',
                        padding: '8px 10px',
                        borderRadius: '4px',
                        border: '1px solid var(--border-default)',
                        fontSize: '0.74rem',
                        color: 'var(--text-secondary)',
                        marginBottom: '14px',
                      }}
                    >
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <ExternalLink size={12} />
                        <span>Source Endpoint:</span>
                      </div>
                      <div style={{ fontFamily: 'monospace', wordBreak: 'break-all', color: 'var(--text-muted)' }}>
                        {src.url}
                      </div>
                      <div style={{ marginTop: '6px', fontSize: '0.71rem', color: 'var(--text-secondary)', borderTop: '1px solid var(--border-default)', paddingTop: '4px' }}>
                        <strong>Governance:</strong> {src.terms_limitations}
                      </div>
                    </div>
                  </div>

                  {/* Action Bar */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-default)', paddingTop: '12px' }}>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                      Failures: <strong>{src.consecutive_failures}</strong>
                    </div>

                    <button
                      className="btn-primary"
                      style={{ padding: '6px 14px', fontSize: '0.78rem' }}
                      onClick={() => handlePollSource(src.id)}
                      disabled={isPolling}
                    >
                      <RefreshCw size={13} className={isPolling ? 'spin' : ''} />
                      <span>{isPolling ? 'Polling...' : 'Poll Source Now'}</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW 3: CHANGE REVIEW DETAIL SCREEN                                       */}
      {/* ========================================================================= */}
      {activeMainView === 'detail' && currentChange && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {/* Back Button & Header */}
          <div>
            <button
              className="btn-secondary"
              style={{ padding: '4px 10px', fontSize: '0.78rem', marginBottom: '12px' }}
              onClick={() => setActiveMainView('inbox')}
            >
              <ArrowLeft size={13} />
              <span>Back to Detected Changes Inbox</span>
            </button>

            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
                    {currentChange.title}
                  </h2>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px', fontSize: '0.82rem', color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
                  <span>Notification: <strong>{currentChange.notification_number}</strong></span>
                  <span>•</span>
                  <span>Published: <strong>{currentChange.published_date || 'October 2026'}</strong></span>
                  <span>•</span>
                  <span>Effective: <strong>{currentChange.effective_date || '1 Dec 2026'}</strong></span>
                  <span>•</span>
                  <span
                    className={`badge ${
                      currentChange.confidence_band === 'HIGH'
                        ? 'badge-valid'
                        : currentChange.confidence_band === 'MEDIUM'
                        ? 'badge-warning'
                        : 'badge-danger'
                    }`}
                  >
                    <Sparkles size={11} />
                    <span>AI Confidence: {currentChange.confidence_band} ({Math.round(currentChange.confidence_score * 100)}%)</span>
                  </span>
                  <span>•</span>
                  <span
                    className="badge badge-neutral"
                    style={{
                      fontSize: '0.72rem',
                      background: currentChange.source_adapter_mode === 'LIVE_HTTP' ? '#eff6ff' : '#f8fafc',
                      color: currentChange.source_adapter_mode === 'LIVE_HTTP' ? '#1d4ed8' : '#64748b',
                      border: '1px solid var(--border-default)',
                    }}
                  >
                    Origin: {currentChange.source_adapter_mode === 'LIVE_HTTP' ? '🌐 Live Official Portal' : '🧪 Fixture Test Feed'}
                  </span>
                </div>
              </div>


              {/* Status Indicator */}
              <div>
                {currentChange.status === 'approved' || currentChange.status === 'published' ? (
                  <span className="badge badge-valid" style={{ padding: '6px 14px', fontSize: '0.82rem' }}>
                    <CheckCircle2 size={15} /> Approved & Published
                  </span>
                ) : currentChange.status === 'rejected' ? (
                  <span className="badge badge-danger" style={{ padding: '6px 14px', fontSize: '0.82rem' }}>
                    <XCircle size={15} /> Proposal Rejected
                  </span>
                ) : (
                  <span className="badge badge-warning" style={{ padding: '6px 14px', fontSize: '0.82rem' }}>
                    <Clock size={15} /> Awaiting Human Review
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Sub-Tabs for Change Review */}
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border-default)', gap: '20px' }}>
            {[
              { id: 'proposal', label: 'Proposal & Evidence', icon: FileCheck },
              { id: 'diff', label: 'Readable Old vs New Diff', icon: GitCompare },
              { id: 'impacts', label: `Affected Facilities (${impacts.length})`, icon: Building2 },
              { id: 'history', label: 'Audit Trail & Provenance', icon: History },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = detailTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setDetailTab(tab.id as any)}
                  style={{
                    padding: '10px 4px',
                    background: 'transparent',
                    border: 'none',
                    borderBottom: isActive ? '2px solid var(--brand-primary)' : '2px solid transparent',
                    color: isActive ? 'var(--brand-primary)' : 'var(--text-secondary)',
                    fontWeight: isActive ? 600 : 500,
                    fontSize: '0.86rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <Icon size={15} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* TAB 1: PROPOSAL & EVIDENCE */}
          {detailTab === 'proposal' && (
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
              {/* Left Column: Summary and Grounding */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* Plain-Language Summary Box */}
                <div className="card">
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Sparkles size={16} style={{ color: 'var(--brand-primary)' }} />
                      <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        Plain-Language Executive Summary
                      </h3>
                    </div>
                    <span className="badge badge-neutral" style={{ fontSize: '0.70rem' }}>
                      Editable Draft
                    </span>
                  </div>

                  <textarea
                    rows={4}
                    className="form-input"
                    style={{ lineHeight: 1.6, resize: 'vertical' }}
                    value={editableSummary}
                    onChange={(e) => setEditableSummary(e.target.value)}
                    placeholder="Enter or refine plain-language legal explanation..."
                  />

                  {/* Key Changes List */}
                  <div style={{ marginTop: '16px' }}>
                    <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                      Key Changes Identified:
                    </div>
                    <ul style={{ paddingLeft: '20px', fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                      {currentChange.key_changes_summary.map((item, idx) => (
                        <li key={idx} style={{ marginBottom: '4px' }}>{item}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Who May Be Affected */}
                  <div style={{ marginTop: '16px' }}>
                    <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                      Who May Be Affected:
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {currentChange.who_may_be_affected.map((aff, idx) => (
                        <span key={idx} className="badge badge-neutral" style={{ fontSize: '0.74rem' }}>
                          {aff}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Evidence Snippets & Grounding */}
                <div className="card">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <FileText size={16} style={{ color: 'var(--brand-primary)' }} />
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      Extracted Evidence Snippets & Official Grounding
                    </h3>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {currentChange.evidence_snippets.length === 0 ? (
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                        No specific clause snippets extracted.
                      </div>
                    ) : (
                      currentChange.evidence_snippets.map((snip, idx) => (
                        <div
                          key={idx}
                          style={{
                            backgroundColor: 'var(--bg-canvas)',
                            border: '1px solid var(--border-default)',
                            borderRadius: '6px',
                            padding: '12px 14px',
                            fontSize: '0.82rem',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                              {snip.clause || snip.section || `Snippet #${idx + 1}`}
                            </span>
                            {snip.page && (
                              <span className="badge badge-neutral" style={{ fontSize: '0.68rem' }}>
                                Page {snip.page}
                              </span>
                            )}
                          </div>
                          <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', lineHeight: 1.5 }}>
                            "{snip.text}"
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Right Column: Reviewer Action Panel & Proposed Categories */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* Proposed Categories */}
                <div className="card">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                    <Tag size={16} style={{ color: 'var(--brand-primary)' }} />
                    <h3 style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      Proposed Impact Categories
                    </h3>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {currentChange.proposed_categories.map((cat, idx) => (
                      <span
                        key={idx}
                        className="badge badge-info"
                        style={{ fontSize: '0.74rem', padding: '4px 9px' }}
                      >
                        {cat}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Reviewer Gate Panel */}
                <div className="card" style={{ border: '2px solid var(--brand-border)', backgroundColor: '#ffffff' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <ShieldCheck size={18} style={{ color: 'var(--brand-primary)' }} />
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      Reviewer Decision Gate
                    </h3>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div>
                      <label style={{ fontSize: '0.76rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                        Target Statutory Requirement Code:
                      </label>
                      <input
                        type="text"
                        className="form-input"
                        value={editableRequirementCode}
                        onChange={(e) => setEditableRequirementCode(e.target.value)}
                        placeholder="e.g. REQ-MPCB-001"
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: '0.76rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                        Confirmed Effective Date:
                      </label>
                      <input
                        type="date"
                        className="form-input"
                        value={editableEffectiveDate}
                        onChange={(e) => setEditableEffectiveDate(e.target.value)}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: '0.76rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                        Reviewer Rationale / Audit Notes: <span style={{ color: '#dc2626' }}>*</span>
                      </label>
                      <textarea
                        rows={3}
                        className="form-input"
                        placeholder="State legal justification for approving or rejecting this change..."
                        value={reviewNotes}
                        onChange={(e) => setReviewNotes(e.target.value)}
                      />
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '6px' }}>
                      <button
                        className="btn-primary"
                        style={{ justifyContent: 'center', width: '100%', padding: '10px' }}
                        onClick={() => handleReviewDecision('APPROVE')}
                        disabled={isSubmittingReview || currentChange.status === 'approved'}
                      >
                        <Check size={16} />
                        <span>Approve & Publish Version (N+1)</span>
                      </button>

                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          className="btn-danger"
                          style={{ flex: 1, justifyContent: 'center' }}
                          onClick={() => handleReviewDecision('REJECT')}
                          disabled={isSubmittingReview || currentChange.status === 'rejected'}
                        >
                          <XCircle size={15} />
                          <span>Reject</span>
                        </button>

                        <button
                          className="btn-secondary"
                          style={{ flex: 1, justifyContent: 'center' }}
                          onClick={handleSaveDraft}
                        >
                          <Edit3 size={14} />
                          <span>Save Draft</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: READABLE OLD VS NEW DIFF */}
          {detailTab === 'diff' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="card" style={{ padding: '14px 18px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <GitCompare size={18} style={{ color: 'var(--brand-primary)' }} />
                  <div>
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      Statutory Text Difference Analysis
                    </h3>
                    <div style={{ fontSize: '0.80rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      {currentChange.diff_summary || 'Threshold lowering and telemetry mandate detected.'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Side-by-Side Diff Panels */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                {/* Prior Baseline (Old) */}
                <div className="card" style={{ backgroundColor: '#fffaf0', border: '1px solid #fed7aa' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#9a3412' }}>
                      Prior Statutory Baseline (Active Version)
                    </span>
                    <span className="badge badge-warning" style={{ fontSize: '0.68rem' }}>
                      Version 1.0
                    </span>
                  </div>
                  <div
                    style={{
                      fontFamily: 'monospace',
                      fontSize: '0.82rem',
                      lineHeight: 1.6,
                      color: '#7c2d12',
                      whiteSpace: 'pre-wrap',
                      backgroundColor: '#fff7ed',
                      padding: '12px',
                      borderRadius: '4px',
                      border: '1px solid #ffedd5',
                    }}
                  >
                    {currentChange.old_text ||
                      'Red Category industrial units discharging > 10.0 KLD must install CEQMS with cloud telemetry.'}
                  </div>
                </div>

                {/* Incoming Notification (New) */}
                <div className="card" style={{ backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#166534' }}>
                      Incoming Notification Text (Proposed N+1)
                    </span>
                    <span className="badge badge-valid" style={{ fontSize: '0.68rem' }}>
                      Proposed Amendment
                    </span>
                  </div>
                  <div
                    style={{
                      fontFamily: 'monospace',
                      fontSize: '0.82rem',
                      lineHeight: 1.6,
                      color: '#14532d',
                      whiteSpace: 'pre-wrap',
                      backgroundColor: '#dcfce7',
                      padding: '12px',
                      borderRadius: '4px',
                      border: '1px solid #bbf7d0',
                    }}
                  >
                    {currentChange.new_text ||
                      'All Red category industrial units operating in Maharashtra discharging treated effluent greater than 5.0 KLD shall install Continuous Online Effluent Quality Monitoring Systems (CEQMS) with direct server telemetry.'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: AFFECTED FACILITIES REVIEW */}
          {detailTab === 'impacts' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div
                style={{
                  backgroundColor: '#ecfdf5',
                  border: '1px solid #a7f3d0',
                  borderRadius: '6px',
                  padding: '12px 16px',
                  fontSize: '0.84rem',
                  color: '#065f46',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                }}
              >
                <ShieldCheck size={18} />
                <span>
                  <strong>Tenant Safeguard Active:</strong> Identified impacts are staged in the human review queue as <em>Proposed Requirement Changes</em>. No customer obligations or deadlines are altered without site reviewer confirmation.
                </span>
              </div>

              {/* Impacts Table */}
              <div className="data-table-container">
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ background: 'var(--bg-canvas)', borderBottom: '1px solid var(--border-default)', color: 'var(--text-secondary)' }}>
                      <th style={{ padding: '12px 16px', fontWeight: 600 }}>Facility Name & Code</th>
                      <th style={{ padding: '12px 16px', fontWeight: 600 }}>Company Tenant</th>
                      <th style={{ padding: '12px 16px', fontWeight: 600 }}>Impact Status</th>
                      <th style={{ padding: '12px 16px', fontWeight: 600 }}>Matched Facts</th>
                      <th style={{ padding: '12px 16px', fontWeight: 600 }}>Legal Explainability</th>
                    </tr>
                  </thead>
                  <tbody>
                    {impacts.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ padding: '40px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
                          No company facilities impacted by this change yet. (Approve change to trigger impact evaluation).
                        </td>
                      </tr>
                    ) : (
                      impacts.map((imp) => (
                        <tr key={imp.id} style={{ borderBottom: '1px solid var(--border-default)' }}>
                          <td style={{ padding: '12px 16px' }}>
                            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{imp.plant_name}</div>
                            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>{imp.plant_code}</div>
                          </td>
                          <td style={{ padding: '12px 16px', color: 'var(--text-secondary)' }}>
                            {imp.tenant_name}
                          </td>
                          <td style={{ padding: '12px 16px' }}>
                            {imp.impact_status === 'POTENTIALLY_APPLICABLE' ? (
                              <span className="badge badge-danger">
                                <AlertTriangle size={12} /> Potentially Applicable
                              </span>
                            ) : imp.impact_status === 'REQUIRES_REVIEW' ? (
                              <span className="badge badge-warning">
                                <Clock size={12} /> Requires Review
                              </span>
                            ) : (
                              <span className="badge badge-neutral">
                                <Check size={12} /> Not Applicable
                              </span>
                            )}
                          </td>
                          <td style={{ padding: '12px 16px' }}>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                              {Object.entries(imp.matched_facts).map(([k, v]) => (
                                <span key={k} className="badge badge-neutral" style={{ fontSize: '0.68rem' }}>
                                  {k}: {String(v)}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td style={{ padding: '12px 16px', color: 'var(--text-secondary)', maxWidth: '320px', lineHeight: 1.4 }}>
                            {imp.explanation}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 4: AUDIT TRAIL & PROVENANCE */}
          {detailTab === 'history' && (
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <History size={18} style={{ color: 'var(--brand-primary)' }} />
                <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Immutable Audit Trail & Provenance History
                </h3>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {historyLogs.length === 0 ? (
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                    No audit records recorded yet.
                  </div>
                ) : (
                  historyLogs.map((log) => (
                    <div
                      key={log.id}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '12px',
                        borderLeft: '2px solid var(--brand-primary)',
                        paddingLeft: '14px',
                        paddingBottom: '8px',
                      }}
                    >
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                            {log.action}
                          </span>
                          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>•</span>
                          <span style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                            {log.performed_by}
                          </span>
                          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>•</span>
                          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                            {new Date(log.created_at).toLocaleString()}
                          </span>
                        </div>

                        {/* Clean formatted parameters (no raw JSON) */}
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                          {Object.entries(log.details).map(([k, v]) => (
                            <span
                              key={k}
                              className="badge badge-neutral"
                              style={{ fontSize: '0.70rem', background: '#f8fafc' }}
                            >
                              <strong>{k}:</strong> {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
