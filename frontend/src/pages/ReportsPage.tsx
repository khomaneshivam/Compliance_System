import React, { useState, useEffect, useCallback } from 'react';
import {
  BarChart3,
  FileText,
  Download,
  AlertTriangle,
  CheckCircle2,
  Clock,
  RefreshCw,
  Plus,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  Calendar,
  Layers,
  Sparkles,
  X,
} from 'lucide-react';
import { api } from '../services/api';
import type { ReportJobItem, PaginatedReportJobs } from '../types';

export const ReportsPage: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [reportsData, setReportsData] = useState<PaginatedReportJobs | null>(null);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(10);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Report Generation Modal State
  const [showGenerateModal, setShowGenerateModal] = useState<boolean>(false);
  const [reportTitle, setReportTitle] = useState<string>('Comprehensive Facility Readiness & Evidence Audit');
  const [plantId, setPlantId] = useState<string>('plant-pune-01');
  const [format, setFormat] = useState<'HTML' | 'JSON'>('HTML');
  const [dateStart, setDateStart] = useState<string>('');
  const [dateEnd, setDateEnd] = useState<string>('');
  const [includeEvidence, setIncludeEvidence] = useState<boolean>(true);
  const [includeMissing, setIncludeMissing] = useState<boolean>(true);
  const [runAsync, setRunAsync] = useState<boolean>(false);
  const [generating, setGenerating] = useState<boolean>(false);

  // Selected Report for Preview Modal
  const [selectedReport, setSelectedReport] = useState<ReportJobItem | null>(null);

  const fetchReports = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getReportJobs({
        plant_id: plantId || undefined,
        page,
        page_size: pageSize,
      });
      setReportsData(data);
    } catch (err: unknown) {
      console.error('Failed to load reports', err);
      setFeedback({ type: 'error', message: 'Could not load readiness reports. Please try again.' });
    } finally {
      setLoading(false);
    }
  }, [plantId, page, pageSize]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  // Polling for generating jobs
  useEffect(() => {
    const hasGeneratingJobs = reportsData?.items.some(
      (j) => j.status === 'QUEUED' || j.status === 'GENERATING'
    );
    if (!hasGeneratingJobs) return;

    const interval = setInterval(() => {
      fetchReports();
    }, 3000);

    return () => clearInterval(interval);
  }, [reportsData, fetchReports]);

  const handleGenerateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reportTitle.trim()) {
      alert('Please enter a descriptive report title.');
      return;
    }

    setGenerating(true);
    setFeedback(null);
    try {
      const job = await api.createReportJob(
        {
          plant_id: plantId,
          report_title: reportTitle.trim(),
          file_format: format,
          date_range_start: dateStart || undefined,
          date_range_end: dateEnd || undefined,
          include_evidence_items: includeEvidence,
          include_missing_items: includeMissing,
        },
        runAsync
      );

      setShowGenerateModal(false);
      setFeedback({
        type: 'success',
        message:
          job.status === 'COMPLETED'
            ? 'Readiness report generated successfully and ready for download.'
            : 'Readiness report job queued in background. Status will update automatically.',
      });
      fetchReports();
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        message: (err as Error).message || 'Failed to start report generation job.',
      });
    } finally {
      setGenerating(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const renderStatusBadge = (status: ReportJobItem['status']) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 10px',
              borderRadius: '9999px',
              fontSize: '12px',
              fontWeight: 500,
              backgroundColor: '#ecfdf5',
              color: '#059669',
              border: '1px solid #a7f3d0',
            }}
          >
            <CheckCircle2 size={13} />
            Completed
          </span>
        );
      case 'GENERATING':
        return (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 10px',
              borderRadius: '9999px',
              fontSize: '12px',
              fontWeight: 500,
              backgroundColor: '#eff6ff',
              color: '#2563eb',
              border: '1px solid #bfdbfe',
            }}
          >
            <RefreshCw size={13} className="spin-slow" />
            Generating
          </span>
        );
      case 'QUEUED':
        return (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 10px',
              borderRadius: '9999px',
              fontSize: '12px',
              fontWeight: 500,
              backgroundColor: '#fef3c7',
              color: '#d97706',
              border: '1px solid #fde68a',
            }}
          >
            <Clock size={13} />
            Queued
          </span>
        );
      case 'FAILED':
        return (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 10px',
              borderRadius: '9999px',
              fontSize: '12px',
              fontWeight: 500,
              backgroundColor: '#fef2f2',
              color: '#dc2626',
              border: '1px solid #fecaca',
            }}
          >
            <AlertTriangle size={13} />
            Failed
          </span>
        );
      default:
        return <span>{status}</span>;
    }
  };

  return (
    <div style={{ padding: '24px 32px', maxWidth: '1440px', margin: '0 auto' }}>
      {/* Header Bar */}
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
              <BarChart3 size={18} />
            </div>
            <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
              Audits & Readiness Reports
            </h1>
          </div>
          <p style={{ color: '#64748b', fontSize: '13px', margin: 0 }}>
            Generate and export auditable compliance-readiness records with verified evidence, missing gap analyses, and statutory provenance.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => fetchReports()}
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            title="Refresh list"
          >
            <RefreshCw size={14} className={loading ? 'spin-slow' : ''} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setShowGenerateModal(true)}
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
            <span>Build Readiness Report</span>
          </button>
        </div>
      </div>

      {/* Cardinal Legal Tenet Banner */}
      <div
        style={{
          backgroundColor: '#f8fafc',
          border: '1px solid #cbd5e1',
          borderLeft: '4px solid #0284c7',
          borderRadius: '8px',
          padding: '14px 18px',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
        }}
      >
        <ShieldAlert size={20} color="#0284c7" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '12.5px', color: '#334155', lineHeight: '1.55' }}>
          <strong style={{ color: '#0f172a' }}>Statutory Boundary & Disclaimer: </strong>
          PlantProof reports represent <em>operational readiness and evidence-assembly assessments</em> based on currently loaded enterprise profiles, verified records, and gazette rules. They do <strong>not</strong> constitute legal advice, regulatory certifications, or formal legal opinions. Statutory compliance determinations remain under the exclusive jurisdiction of regulatory authorities (e.g. MPCB, DISH, CPCB).
        </div>
      </div>

      {/* Feedback Toast */}
      {feedback && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: '8px',
            marginBottom: '20px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: feedback.type === 'success' ? '#ecfdf5' : '#fef2f2',
            color: feedback.type === 'success' ? '#065f46' : '#991b1b',
            border: `1px solid ${feedback.type === 'success' ? '#a7f3d0' : '#fecaca'}`,
            fontSize: '13px',
          }}
        >
          <span>{feedback.message}</span>
          <button
            onClick={() => setFeedback(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Reports Table / Card Container */}
      <div
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '12px',
          border: '1px solid #e2e8f0',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid #f1f5f9',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
            backgroundColor: '#fafbfc',
          }}
        >
          <div style={{ fontSize: '14px', fontWeight: 600, color: '#1e293b' }}>
            Generated Readiness Reports Archive
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#64748b' }}>
            <span>Facility:</span>
            <span style={{ fontWeight: 600, color: '#0f172a', background: '#e2e8f0', padding: '2px 8px', borderRadius: '4px' }}>
              Acme Manufacturing Pune Plant
            </span>
          </div>
        </div>

        {/* Content Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e2e8f0', backgroundColor: '#f8fafc', color: '#475569' }}>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Report Title & Metadata</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Data As Of</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Format & Size</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Status</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Readiness Score</th>
                <th style={{ padding: '12px 18px', fontWeight: 600 }}>Evidence / Gaps</th>
                <th style={{ padding: '12px 18px', fontWeight: 600, textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && (!reportsData || reportsData.items.length === 0) ? (
                <tr>
                  <td colSpan={7} style={{ padding: '48px 24px', textAlign: 'center', color: '#64748b' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px' }}>
                      <RefreshCw size={18} className="spin-slow" />
                      <span>Loading readiness reports...</span>
                    </div>
                  </td>
                </tr>
              ) : !reportsData || reportsData.items.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: '60px 24px', textAlign: 'center' }}>
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
                      <FileText size={24} />
                    </div>
                    <div style={{ fontSize: '15px', fontWeight: 600, color: '#1e293b', marginBottom: '6px' }}>
                      No Readiness Reports Generated Yet
                    </div>
                    <p style={{ color: '#64748b', fontSize: '13px', maxWidth: '420px', margin: '0 auto 20px' }}>
                      Generate an executive readiness report to review all applicable statutory obligations, verified certificates, and missing gap documents before an audit.
                    </p>
                    <button
                      onClick={() => setShowGenerateModal(true)}
                      className="btn btn-primary"
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                    >
                      <Plus size={16} />
                      <span>Build First Report</span>
                    </button>
                  </td>
                </tr>
              ) : (
                reportsData.items.map((job) => {
                  const metrics = job.summary_metrics || {};
                  const readiness = metrics.readiness_percentage ?? 0;
                  return (
                    <tr
                      key={job.id}
                      style={{
                        borderBottom: '1px solid #f1f5f9',
                        transition: 'background-color 0.15s ease',
                      }}
                      className="table-row-hover"
                    >
                      <td style={{ padding: '14px 18px' }}>
                        <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: '2px' }}>
                          {job.report_title}
                        </div>
                        <div style={{ fontSize: '11px', color: '#64748b', display: 'flex', gap: '10px' }}>
                          <span>Job ID: {job.id.slice(0, 8)}...</span>
                          <span>•</span>
                          <span>Prepared: {new Date(job.prepared_at).toLocaleString('en-IN')}</span>
                        </div>
                      </td>

                      <td style={{ padding: '14px 18px', color: '#334155', fontSize: '12px' }}>
                        {new Date(job.data_as_of).toLocaleDateString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </td>

                      <td style={{ padding: '14px 18px', fontSize: '12px' }}>
                        <span
                          style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            background: '#f1f5f9',
                            color: '#334155',
                            fontWeight: 600,
                            marginRight: '6px',
                          }}
                        >
                          {job.file_format}
                        </span>
                        <span style={{ color: '#64748b' }}>{formatBytes(job.file_size_bytes)}</span>
                      </td>

                      <td style={{ padding: '14px 18px' }}>{renderStatusBadge(job.status)}</td>

                      <td style={{ padding: '14px 18px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div
                            style={{
                              width: '42px',
                              height: '42px',
                              borderRadius: '50%',
                              background:
                                readiness >= 80
                                  ? '#ecfdf5'
                                  : readiness >= 50
                                  ? '#fef3c7'
                                  : '#fef2f2',
                              color:
                                readiness >= 80
                                  ? '#059669'
                                  : readiness >= 50
                                  ? '#d97706'
                                  : '#dc2626',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontWeight: 700,
                              fontSize: '12px',
                            }}
                          >
                            {Math.round(readiness)}%
                          </div>
                          <span style={{ fontSize: '11px', color: '#64748b' }}>readiness score</span>
                        </div>
                      </td>

                      <td style={{ padding: '14px 18px', fontSize: '12px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                          <span style={{ color: '#059669', fontWeight: 500 }}>
                            ✓ {metrics.verified_evidence_count ?? 0} verified records
                          </span>
                          <span style={{ color: (metrics.missing_evidence_count ?? 0) > 0 ? '#d97706' : '#64748b' }}>
                            ⚠ {metrics.missing_evidence_count ?? 0} missing / unverified
                          </span>
                        </div>
                      </td>

                      <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '8px' }}>
                          <button
                            onClick={() => setSelectedReport(job)}
                            className="btn btn-secondary btn-sm"
                            title="Preview metrics summary"
                          >
                            Summary
                          </button>
                          {job.status === 'COMPLETED' ? (
                            <a
                              href={api.getReportDownloadUrl(job.id)}
                              target="_blank"
                              rel="noreferrer"
                              className="btn btn-primary btn-sm"
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                                textDecoration: 'none',
                                backgroundColor: '#059669',
                                borderColor: '#059669',
                              }}
                            >
                              <Download size={13} />
                              <span>Download</span>
                            </a>
                          ) : (
                            <button
                              className="btn btn-secondary btn-sm"
                              disabled
                              title="File is generating..."
                            >
                              <Clock size={13} />
                              <span>Pending</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {reportsData && reportsData.total_pages > 1 && (
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
              Showing {reportsData.items.length} of {reportsData.total} reports
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
                Page {page} of {reportsData.total_pages}
              </span>
              <button
                className="btn btn-secondary btn-sm"
                disabled={page >= reportsData.total_pages}
                onClick={() => setPage((p) => Math.min(reportsData.total_pages, p + 1))}
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Information / Glossary Help Cards */}
      <div
        style={{
          marginTop: '28px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '16px',
        }}
      >
        <div style={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#0f172a', fontWeight: 600, fontSize: '13px' }}>
            <Calendar size={16} color="#059669" />
            <span>Understanding "Data As Of" Timestamp</span>
          </div>
          <p style={{ margin: 0, fontSize: '12px', color: '#64748b', lineHeight: 1.5 }}>
            Regulatory obligations change over time. Every report captures the precise state of company attributes and gazette notifications on that date, preventing anachronistic audit failures.
          </p>
        </div>

        <div style={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#0f172a', fontWeight: 600, fontSize: '13px' }}>
            <Layers size={16} color="#0284c7" />
            <span>Readiness Score Formula</span>
          </div>
          <p style={{ margin: 0, fontSize: '12px', color: '#64748b', lineHeight: 1.5 }}>
            Calculated as the ratio of verified, active evidence documents against all applicable statutory mandates. Unverified AI extractions and expired consents are counted as missing gaps.
          </p>
        </div>

        <div style={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#0f172a', fontWeight: 600, fontSize: '13px' }}>
            <Sparkles size={16} color="#d97706" />
            <span>Auditor Provenance Trail</span>
          </div>
          <p style={{ margin: 0, fontSize: '12px', color: '#64748b', lineHeight: 1.5 }}>
            Every included requirement item cites the originating gazette notification, governing section/rule, issuing authority (MPCB, DISH, CPCB), and human review sign-off.
          </p>
        </div>
      </div>

      {/* Generate Report Modal */}
      {showGenerateModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.5)',
            backdropFilter: 'blur(3px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px',
          }}
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
          >
            <div
              style={{
                padding: '20px 24px',
                borderBottom: '1px solid #e2e8f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                backgroundColor: '#06281e',
                color: '#ffffff',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <BarChart3 size={20} color="#34d399" />
                <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#ffffff' }}>
                  Build Readiness & Evidence Report
                </h3>
              </div>
              <button
                onClick={() => setShowGenerateModal(false)}
                style={{ background: 'none', border: 'none', color: '#ffffff', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleGenerateReport} style={{ padding: '24px' }}>
              {/* Plant selection */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Target Facility / Plant *
                </label>
                <select
                  value={plantId}
                  onChange={(e) => setPlantId(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '13px',
                    backgroundColor: '#ffffff',
                  }}
                  required
                >
                  <option value="plant-pune-01">Acme Manufacturing - Pune Plant (Maharashtra)</option>
                </select>
              </div>

              {/* Title */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  Report Title *
                </label>
                <input
                  type="text"
                  value={reportTitle}
                  onChange={(e) => setReportTitle(e.target.value)}
                  placeholder="e.g. Annual MPCB & Factory Act Statutory Audit Preparation"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '13px',
                    boxSizing: 'border-box',
                  }}
                  required
                />
              </div>

              {/* Format & Background Execution */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                    Output Format
                  </label>
                  <select
                    value={format}
                    onChange={(e) => setFormat(e.target.value as 'HTML' | 'JSON')}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      border: '1px solid #cbd5e1',
                      fontSize: '13px',
                    }}
                  >
                    <option value="HTML">Interactive HTML Dossier</option>
                    <option value="JSON">Auditable JSON Archive</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                    Execution Mode
                  </label>
                  <select
                    value={runAsync ? 'ASYNC' : 'SYNC'}
                    onChange={(e) => setRunAsync(e.target.value === 'ASYNC')}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      border: '1px solid #cbd5e1',
                      fontSize: '13px',
                    }}
                  >
                    <option value="SYNC">Synchronous (Instant)</option>
                    <option value="ASYNC">Background Job (Large Facilities)</option>
                  </select>
                </div>
              </div>

              {/* Date Scope */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                    Due Date Start (Optional)
                  </label>
                  <input
                    type="date"
                    value={dateStart}
                    onChange={(e) => setDateStart(e.target.value)}
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
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                    Due Date End (Optional)
                  </label>
                  <input
                    type="date"
                    value={dateEnd}
                    onChange={(e) => setDateEnd(e.target.value)}
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
              </div>

              {/* Checkboxes */}
              <div style={{ backgroundColor: '#f8fafc', padding: '12px', borderRadius: '6px', marginBottom: '20px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#334155', marginBottom: '8px', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={includeEvidence}
                    onChange={(e) => setIncludeEvidence(e.target.checked)}
                  />
                  <span>Include verified certificate and consent evidence references</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#334155', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={includeMissing}
                    onChange={(e) => setIncludeMissing(e.target.checked)}
                  />
                  <span>Include missing / gap requirements list</span>
                </label>
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setShowGenerateModal(false)}
                  className="btn btn-secondary"
                  disabled={generating}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={generating}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    backgroundColor: '#059669',
                    borderColor: '#059669',
                  }}
                >
                  {generating ? (
                    <>
                      <RefreshCw size={14} className="spin-slow" />
                      <span>Generating Report...</span>
                    </>
                  ) : (
                    <>
                      <BarChart3 size={14} />
                      <span>Generate Report</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Report Summary Preview Modal */}
      {selectedReport && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.5)',
            backdropFilter: 'blur(3px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px',
          }}
          onClick={() => setSelectedReport(null)}
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '12px',
              maxWidth: '600px',
              width: '100%',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
              overflow: 'hidden',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                padding: '20px 24px',
                borderBottom: '1px solid #e2e8f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
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
                  Readiness Dossier Metadata
                </span>
                <h3 style={{ margin: '4px 0 0 0', fontSize: '17px', fontWeight: 600, color: '#ffffff' }}>
                  {selectedReport.report_title}
                </h3>
              </div>
              <button
                onClick={() => setSelectedReport(null)}
                style={{ background: 'none', border: 'none', color: '#ffffff', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ padding: '24px' }}>
              {/* Metrics Grid */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '12px',
                  marginBottom: '20px',
                }}
              >
                <div style={{ backgroundColor: '#f8fafc', padding: '14px', borderRadius: '8px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                  <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>READINESS SCORE</div>
                  <div style={{ fontSize: '24px', fontWeight: 700, color: '#059669', marginTop: '4px' }}>
                    {Math.round(selectedReport.summary_metrics?.readiness_percentage ?? 0)}%
                  </div>
                </div>

                <div style={{ backgroundColor: '#f8fafc', padding: '14px', borderRadius: '8px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                  <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>VERIFIED RECORDS</div>
                  <div style={{ fontSize: '24px', fontWeight: 700, color: '#0f172a', marginTop: '4px' }}>
                    {selectedReport.summary_metrics?.verified_evidence_count ?? 0}
                  </div>
                </div>

                <div style={{ backgroundColor: '#f8fafc', padding: '14px', borderRadius: '8px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                  <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>MISSING GAPS</div>
                  <div style={{ fontSize: '24px', fontWeight: 700, color: '#dc2626', marginTop: '4px' }}>
                    {selectedReport.summary_metrics?.missing_evidence_count ?? 0}
                  </div>
                </div>
              </div>

              {/* Provenance Metadata Table */}
              <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden', marginBottom: '20px' }}>
                <div style={{ backgroundColor: '#f8fafc', padding: '10px 14px', borderBottom: '1px solid #e2e8f0', fontSize: '12px', fontWeight: 600, color: '#475569' }}>
                  Audit Trail & Provenance Reference
                </div>
                <div style={{ padding: '12px 14px', fontSize: '12.5px', color: '#334155', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>Report Job ID:</span>
                    <span style={{ fontFamily: 'monospace' }}>{selectedReport.id}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>Data As Of Date:</span>
                    <span>{new Date(selectedReport.data_as_of).toLocaleString('en-IN')}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>Prepared On:</span>
                    <span>{new Date(selectedReport.prepared_at).toLocaleString('en-IN')}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>File Package:</span>
                    <span>{selectedReport.file_format} ({formatBytes(selectedReport.file_size_bytes)})</span>
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <button
                  type="button"
                  onClick={() => setSelectedReport(null)}
                  className="btn btn-secondary"
                >
                  Close
                </button>
                {selectedReport.status === 'COMPLETED' && (
                  <a
                    href={api.getReportDownloadUrl(selectedReport.id)}
                    target="_blank"
                    rel="noreferrer"
                    className="btn btn-primary"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      textDecoration: 'none',
                      backgroundColor: '#059669',
                      borderColor: '#059669',
                    }}
                  >
                    <Download size={14} />
                    <span>Download Complete Dossier</span>
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
