import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  Search,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Clock,
  Activity,
} from 'lucide-react';
import { api } from '../services/api';
import type { PaginatedAuditLogs, AuditLogEntry } from '../types';

export const AdminAuditLogPage: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [logsData, setLogsData] = useState<PaginatedAuditLogs | null>(null);

  // Filters & Pagination
  const [actionFilter, setActionFilter] = useState<string>('');
  const [entityFilter, setEntityFilter] = useState<string>('');
  const [search, setSearch] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(15);

  // Detail Modal
  const [selectedEntry, setSelectedEntry] = useState<AuditLogEntry | null>(null);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getAdminAuditLogs({
        action: actionFilter || undefined,
        entity_type: entityFilter || undefined,
        search: search.trim() || undefined,
        page,
        page_size: pageSize,
      });
      setLogsData(data);
    } catch (err: unknown) {
      console.error('Failed to load audit logs', err);
    } finally {
      setLoading(false);
    }
  }, [actionFilter, entityFilter, search, page, pageSize]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const renderActionBadge = (action: string) => {
    let color = '#475569';
    let bg = '#f1f5f9';
    let border = '#e2e8f0';

    if (action.includes('CREATE') || action.includes('UPLOAD')) {
      color = '#059669';
      bg = '#ecfdf5';
      border = '#a7f3d0';
    } else if (action.includes('TRANSITION') || action.includes('UPDATE')) {
      color = '#0284c7';
      bg = '#f0f9ff';
      border = '#bae6fd';
    } else if (action.includes('DELETE') || action.includes('BLOCK') || action.includes('REJECT')) {
      color = '#dc2626';
      bg = '#fef2f2';
      border = '#fecaca';
    } else if (action.includes('REPORT')) {
      color = '#7c3aed';
      bg = '#f5f3ff';
      border = '#ddd6fe';
    }

    return (
      <span
        style={{
          display: 'inline-block',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '11px',
          fontWeight: 600,
          color,
          backgroundColor: bg,
          border: `1px solid ${border}`,
        }}
      >
        {action.replace(/_/g, ' ')}
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
              <ShieldAlert size={18} />
            </div>
            <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
              Administrative Governance Audit Log
            </h1>
          </div>
          <p style={{ color: '#64748b', fontSize: '13px', margin: 0 }}>
            Tamper-evident system activity and regulatory changes ledger. All state mutations, user interventions, and task progressions are recorded with plain-language explanations.
          </p>
        </div>

        <button
          onClick={() => fetchLogs()}
          className="btn btn-secondary"
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={14} className={loading ? 'spin-slow' : ''} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '10px',
          border: '1px solid #e2e8f0',
          padding: '16px 20px',
          marginBottom: '20px',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '16px',
          alignItems: 'center',
          boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
        }}
      >
        {/* Search */}
        <div style={{ flex: '1 1 240px', position: 'relative' }}>
          <Search size={16} color="#94a3b8" style={{ position: 'absolute', left: '10px', top: '10px' }} />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search activity descriptions, user emails, or entity IDs..."
            style={{
              width: '100%',
              padding: '8px 12px 8px 34px',
              borderRadius: '6px',
              border: '1px solid #cbd5e1',
              fontSize: '13px',
              boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Action filter */}
        <div style={{ width: '200px' }}>
          <select
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(1);
            }}
            style={{
              width: '100%',
              padding: '8px 12px',
              borderRadius: '6px',
              border: '1px solid #cbd5e1',
              fontSize: '13px',
              backgroundColor: '#ffffff',
            }}
          >
            <option value="">All Actions</option>
            <option value="TASK_CREATED">Task Created</option>
            <option value="TASK_STATUS_TRANSITION">Status Transition</option>
            <option value="TASK_COMMENT_ADDED">Comment Added</option>
            <option value="EVIDENCE_UPLOAD">Evidence Upload</option>
            <option value="REPORT_GENERATION_INITIATED">Report Generated</option>
            <option value="PROFILE_UPDATED">Profile Updated</option>
          </select>
        </div>

        {/* Entity filter */}
        <div style={{ width: '180px' }}>
          <select
            value={entityFilter}
            onChange={(e) => {
              setEntityFilter(e.target.value);
              setPage(1);
            }}
            style={{
              width: '100%',
              padding: '8px 12px',
              borderRadius: '6px',
              border: '1px solid #cbd5e1',
              fontSize: '13px',
              backgroundColor: '#ffffff',
            }}
          >
            <option value="">All Entity Types</option>
            <option value="COMPLIANCE_TASK">Compliance Task</option>
            <option value="COMPLIANCE_EVIDENCE">Evidence Document</option>
            <option value="READINESS_REPORT">Readiness Report</option>
            <option value="PLANT_PROFILE">Plant Profile</option>
          </select>
        </div>

        {(actionFilter || entityFilter || search) && (
          <button
            onClick={() => {
              setActionFilter('');
              setEntityFilter('');
              setSearch('');
              setPage(1);
            }}
            style={{
              background: 'none',
              border: 'none',
              color: '#059669',
              fontSize: '12.5px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Audit Log Table */}
      <div
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '12px',
          border: '1px solid #e2e8f0',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          overflow: 'hidden',
        }}
      >
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Timestamp (IST)</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Actor / User</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Action</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Target Entity</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Human-Readable Event Description</th>
                <th style={{ padding: '12px 18px', fontWeight: 600, textAlign: 'right' }}>Details</th>
              </tr>
            </thead>
            <tbody>
              {loading && (!logsData || logsData.items.length === 0) ? (
                <tr>
                  <td colSpan={6} style={{ padding: '48px 24px', textAlign: 'center', color: '#64748b' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                      <RefreshCw size={16} className="spin-slow" />
                      <span>Loading governance activity ledger...</span>
                    </div>
                  </td>
                </tr>
              ) : !logsData || logsData.items.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: '60px 24px', textAlign: 'center' }}>
                    <div
                      style={{
                        width: '48px',
                        height: '48px',
                        borderRadius: '50%',
                        backgroundColor: '#f1f5f9',
                        color: '#64748b',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        margin: '0 auto 16px',
                      }}
                    >
                      <Activity size={24} />
                    </div>
                    <div style={{ fontSize: '15px', fontWeight: 600, color: '#1e293b', marginBottom: '4px' }}>
                      No Matching Governance Log Entries
                    </div>
                    <p style={{ color: '#64748b', fontSize: '13px', margin: 0 }}>
                      Try adjusting the filter criteria or searching for different keywords.
                    </p>
                  </td>
                </tr>
              ) : (
                logsData.items.map((log) => (
                  <tr
                    key={log.id}
                    style={{
                      borderBottom: '1px solid #f1f5f9',
                      transition: 'background-color 0.15s ease',
                    }}
                    className="table-row-hover"
                  >
                    <td style={{ padding: '14px 18px', color: '#334155', whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Clock size={13} color="#94a3b8" />
                        <span>{new Date(log.timestamp).toLocaleString('en-IN')}</span>
                      </div>
                    </td>

                    <td style={{ padding: '14px 18px' }}>
                      <div style={{ fontWeight: 600, color: '#0f172a' }}>
                        {log.user_name || 'System Service'}
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>
                        {log.user_email || 'automated@plantproof.internal'}
                      </div>
                    </td>

                    <td style={{ padding: '14px 18px' }}>{renderActionBadge(log.action)}</td>

                    <td style={{ padding: '14px 18px', color: '#475569' }}>
                      <div style={{ fontWeight: 500, fontSize: '12px' }}>{log.entity_type}</div>
                      <div style={{ fontSize: '10.5px', color: '#94a3b8', fontFamily: 'monospace' }}>
                        {log.entity_id.slice(0, 12)}...
                      </div>
                    </td>

                    <td style={{ padding: '14px 18px', color: '#1e293b', lineHeight: 1.5 }}>
                      {log.readable_description || log.description}
                    </td>

                    <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                      <button
                        onClick={() => setSelectedEntry(log)}
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: '12px' }}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {logsData && logsData.total_pages > 1 && (
          <div
            style={{
              padding: '12px 20px',
              borderTop: '1px solid #e2e8f0',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: '#fafbfc',
              fontSize: '13px',
              color: '#64748b',
            }}
          >
            <div>
              Showing {logsData.items.length} of {logsData.total} activity records
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                className="btn btn-secondary btn-sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft size={14} /> Previous
              </button>
              <span>
                Page {page} of {logsData.total_pages}
              </span>
              <button
                className="btn btn-secondary btn-sm"
                disabled={page >= logsData.total_pages}
                onClick={() => setPage((p) => Math.min(logsData.total_pages, p + 1))}
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Inspect Modal */}
      {selectedEntry && (
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
          onClick={() => setSelectedEntry(null)}
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '12px',
              maxWidth: '560px',
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
              <div>
                <span
                  style={{
                    fontSize: '11px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    color: '#6ee7b7',
                    fontWeight: 600,
                  }}
                >
                  Audit Record Trace
                </span>
                <h3 style={{ margin: '2px 0 0 0', fontSize: '16px', fontWeight: 600, color: '#ffffff' }}>
                  {selectedEntry.action.replace(/_/g, ' ')}
                </h3>
              </div>
              <button
                onClick={() => setSelectedEntry(null)}
                style={{ background: 'none', border: 'none', color: '#ffffff', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ padding: '24px' }}>
              <div style={{ fontSize: '13px', lineHeight: 1.6, color: '#1e293b', marginBottom: '16px' }}>
                <strong>Description: </strong>
                {selectedEntry.readable_description || selectedEntry.description}
              </div>

              <div style={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '14px', marginBottom: '16px', fontSize: '12.5px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#64748b' }}>Log Record ID:</span>
                  <span style={{ fontFamily: 'monospace' }}>{selectedEntry.id}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#64748b' }}>Actor Email:</span>
                  <span>{selectedEntry.user_email || 'Automated Internal Process'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#64748b' }}>Client IP:</span>
                  <span style={{ fontFamily: 'monospace' }}>{selectedEntry.client_ip || 'Internal'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#64748b' }}>Entity Reference:</span>
                  <span>{selectedEntry.entity_type} ({selectedEntry.entity_id})</span>
                </div>
              </div>

              {selectedEntry.changes_summary && selectedEntry.changes_summary.length > 0 && (
                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '8px' }}>
                    Summary of Mutated Properties
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '12.5px', color: '#334155', lineHeight: 1.6 }}>
                    {selectedEntry.changes_summary.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => setSelectedEntry(null)}
                  className="btn btn-secondary"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
