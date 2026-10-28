import React, { useState, useEffect, useCallback } from 'react';
import {
  ArrowLeft,
  ZoomIn,
  ZoomOut,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  FileText,
  Upload,
  Check,
  Edit2,
  Save,
  RotateCcw,
  ShieldCheck,
  ExternalLink,
  FileCheck,
  X,
  FileWarning,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import type {
  ComplianceDocumentItem,
  DocumentAuditLogItem,
  Plant,
} from '../types';

export const DocumentReviewPage: React.FC = () => {
  // Navigation & View Mode
  const [viewMode, setViewMode] = useState<'vault' | 'review'>('vault');

  // Document Vault State
  const [documents, setDocuments] = useState<ComplianceDocumentItem[]>([]);
  const [plants, setPlants] = useState<Plant[]>([]);
  const [selectedPlantId, setSelectedPlantId] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [actionNotice, setActionNotice] = useState<{ type: 'success' | 'error' | 'warning'; message: string } | null>(null);

  // Upload Modal State
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadPlantId, setUploadPlantId] = useState<string>('');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  // Review Dual-Pane State
  const [currentDoc, setCurrentDoc] = useState<ComplianceDocumentItem | null>(null);
  const [auditLogs, setAuditLogs] = useState<DocumentAuditLogItem[]>([]);
  const [activeReviewTab, setActiveReviewTab] = useState<'parameters' | 'history'>('parameters');
  const [zoomLevel, setZoomLevel] = useState(100);
  const [editableFields, setEditableFields] = useState<Record<string, string>>({});
  const [isEditingFields, setIsEditingFields] = useState(false);
  const [linkRequirementCode, setLinkRequirementCode] = useState('BOILER-INSP-CERT');
  const [expiryReminderDays, setExpiryReminderDays] = useState<number>(60);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');

  // Load plants and document list
  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const plantsRes = await api.getPlants();
      setPlants(plantsRes);
      if (!uploadPlantId && plantsRes.length > 0) {
        setUploadPlantId(plantsRes[0].id);
      }

      const reviewStatusParam = statusFilter !== 'ALL' ? statusFilter : undefined;
      const docsRes = await api.getDocuments(selectedPlantId || undefined, reviewStatusParam);
      setDocuments(docsRes);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch documents';
      setActionNotice({ type: 'error', message: msg });
    } finally {
      setIsLoading(false);
    }
  }, [selectedPlantId, statusFilter, uploadPlantId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Open review for a specific document
  const handleOpenReview = async (docId: string) => {
    setIsLoading(true);
    try {
      const doc = await api.getDocument(docId);
      setCurrentDoc(doc);

      // Prepopulate editable fields
      const fieldMap: Record<string, string> = {};
      if (doc.extracted_fields) {
        doc.extracted_fields.forEach((f) => {
          fieldMap[f.field_key] = f.confirmed_value || f.extracted_value;
        });
      }
      setEditableFields(fieldMap);

      if (doc.expiry_reminder_days) {
        setExpiryReminderDays(doc.expiry_reminder_days);
      }

      // Preselect linked requirement if already linked
      if (doc.linked_requirements && doc.linked_requirements.length > 0) {
        setLinkRequirementCode(doc.linked_requirements[0].statutory_code);
      }

      const logs = await api.getDocumentHistory(docId);
      setAuditLogs(logs);

      setViewMode('review');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load document details';
      setActionNotice({ type: 'error', message: msg });
    } finally {
      setIsLoading(false);
    }
  };

  // Upload handler with client-side safeguards
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploadError(null);

    if (!uploadFile) {
      setUploadError('Please select a document file to upload.');
      return;
    }

    if (!uploadPlantId) {
      setUploadError('Please select a facility/plant for this document.');
      return;
    }

    // Client-side extension check
    const allowedExts = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif'];
    const lowerName = uploadFile.name.toLowerCase();
    const hasValidExt = allowedExts.some((ext) => lowerName.endsWith(ext));
    if (!hasValidExt) {
      setUploadError('Prohibited format. Allowed file formats are PDF, PNG, JPG, and TIFF.');
      return;
    }

    // Client-side size boundary (25MB)
    const MAX_SIZE = 25 * 1024 * 1024;
    if (uploadFile.size > MAX_SIZE) {
      setUploadError(`File size ${(uploadFile.size / 1024 / 1024).toFixed(1)}MB exceeds maximum allowed boundary of 25MB.`);
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append('plant_id', uploadPlantId);
    formData.append('file', uploadFile);

    try {
      const uploadedDoc = await api.uploadDocument(formData);
      setUploadModalOpen(false);
      setUploadFile(null);
      setActionNotice({
        type: 'success',
        message: `Document "${uploadedDoc.original_filename}" safely uploaded to private vault and extraction completed.`,
      });
      await loadData();
      // Directly open review for uploaded document
      handleOpenReview(uploadedDoc.id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed. File rejected.';
      setUploadError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  // Save edited fields
  const handleSaveFieldOverrides = async () => {
    if (!currentDoc) return;
    try {
      const updated = await api.updateDocumentFields(currentDoc.id, editableFields);
      setCurrentDoc(updated);
      setIsEditingFields(false);
      setActionNotice({ type: 'success', message: 'Extracted fields updated and marked as reviewer overrides.' });
      const logs = await api.getDocumentHistory(currentDoc.id);
      setAuditLogs(logs);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update fields';
      setActionNotice({ type: 'error', message: msg });
    }
  };

  // Approve Document as Evidence
  const handleApproveDocument = async () => {
    if (!currentDoc) return;
    try {
      const updated = await api.submitDocumentReview(currentDoc.id, {
        decision: 'APPROVE',
        review_notes: 'Document parameters verified against physical certificate and official authority registry.',
        link_to_statutory_requirement_id: linkRequirementCode,
        expiry_reminder_days: currentDoc.detected_expiry_date ? expiryReminderDays : undefined,
        field_overrides: editableFields,
      });
      setCurrentDoc(updated);
      setActionNotice({
        type: 'success',
        message: `Document approved! Linked as evidence to statutory requirement ${linkRequirementCode} with status VALID.`,
      });
      const logs = await api.getDocumentHistory(currentDoc.id);
      setAuditLogs(logs);
      loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Approval failed';
      setActionNotice({ type: 'error', message: msg });
    }
  };

  // Reject Document
  const handleRejectSubmit = async () => {
    if (!currentDoc) return;
    if (!rejectionReason.trim()) {
      alert('Please enter a rejection reason.');
      return;
    }
    try {
      const updated = await api.submitDocumentReview(currentDoc.id, {
        decision: 'REJECT',
        rejection_reason: rejectionReason,
      });
      setCurrentDoc(updated);
      setRejectModalOpen(false);
      setRejectionReason('');
      setActionNotice({
        type: 'warning',
        message: `Document rejected. Evidence obligation remains UNMET in the legal register.`,
      });
      const logs = await api.getDocumentHistory(currentDoc.id);
      setAuditLogs(logs);
      loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Rejection failed';
      setActionNotice({ type: 'error', message: msg });
    }
  };

  // Re-run extraction
  const handleReExtract = async () => {
    if (!currentDoc) return;
    try {
      const updated = await api.reExtractDocument(currentDoc.id);
      setCurrentDoc(updated);
      setActionNotice({ type: 'success', message: 'Re-extraction completed successfully.' });
      const logs = await api.getDocumentHistory(currentDoc.id);
      setAuditLogs(logs);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Re-extraction failed';
      setActionNotice({ type: 'error', message: msg });
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', minHeight: 'calc(100vh - 110px)' }}>
      {/* Toast Notice Banner */}
      {actionNotice && (
        <div
          style={{
            padding: '10px 16px',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.86rem',
            backgroundColor:
              actionNotice.type === 'success'
                ? 'var(--status-valid-bg)'
                : actionNotice.type === 'error'
                ? 'var(--status-danger-bg)'
                : 'var(--status-warning-bg)',
            color:
              actionNotice.type === 'success'
                ? 'var(--status-valid-text)'
                : actionNotice.type === 'error'
                ? 'var(--status-danger-text)'
                : 'var(--status-warning-text)',
            border: `1px solid ${
              actionNotice.type === 'success'
                ? 'var(--status-valid-border)'
                : actionNotice.type === 'error'
                ? 'var(--status-danger-border)'
                : 'var(--status-warning-border)'
            }`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {actionNotice.type === 'success' && <CheckCircle2 size={16} />}
            {actionNotice.type === 'error' && <XCircle size={16} />}
            {actionNotice.type === 'warning' && <AlertTriangle size={16} />}
            <span>{actionNotice.message}</span>
          </div>
          <button
            onClick={() => setActionNotice(null)}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'inherit' }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* =================================================================== */}
      {/* VIEW MODE 1: DOCUMENT VAULT & UPLOAD INVENTORY                      */}
      {/* =================================================================== */}
      {viewMode === 'vault' && (
        <>
          {/* Header Controls */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Compliance Document Vault
              </h1>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Secure, isolated evidence management with deterministic verification and AI-assisted extraction.
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <button
                className="btn-primary"
                onClick={() => setUploadModalOpen(true)}
                style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <Upload size={15} />
                <span>Upload Document</span>
              </button>
            </div>
          </div>

          {/* Filter Bar */}
          <div
            style={{
              backgroundColor: '#ffffff',
              border: '1px solid var(--border-default)',
              borderRadius: '8px',
              padding: '12px 16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '14px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Plant / Site:</span>
                <select
                  aria-label="Filter by Plant or Site"
                  className="form-input"
                  style={{ width: '220px', padding: '6px 10px', fontSize: '0.82rem' }}
                  value={selectedPlantId}
                  onChange={(e) => setSelectedPlantId(e.target.value)}
                >
                  <option value="">All Facilities</option>
                  {plants.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.code})
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Review Status:</span>
                <select
                  aria-label="Filter by Review Status"
                  className="form-input"
                  style={{ width: '160px', padding: '6px 10px', fontSize: '0.82rem' }}
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="ALL">All Statuses</option>
                  <option value="PENDING_REVIEW">Pending Review</option>
                  <option value="APPROVED">Approved</option>
                  <option value="EDITED_AND_APPROVED">Edited & Approved</option>
                  <option value="REJECTED">Rejected</option>
                </select>
              </div>
            </div>

            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Showing <strong>{documents.length}</strong> vault items
            </div>
          </div>

          {/* Document Inventory Table */}
          <div
            style={{
              backgroundColor: '#ffffff',
              border: '1px solid var(--border-default)',
              borderRadius: '8px',
              overflow: 'hidden',
            }}
          >
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.84rem' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--bg-surface-subtle)', borderBottom: '1px solid var(--border-default)' }}>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Document File</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Facility</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Detected Classification</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Extraction Status</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Statutory Expiry</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Review State</th>
                  <th style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--text-secondary)', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={7} style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      <Clock size={28} style={{ margin: '0 auto 8px', display: 'block', opacity: 0.6 }} />
                      <p style={{ fontWeight: 600 }}>Loading compliance vault documents...</p>
                    </td>
                  </tr>
                ) : documents.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      <FileText size={32} style={{ margin: '0 auto 10px', display: 'block', opacity: 0.5 }} />
                      <p style={{ fontWeight: 600 }}>No compliance documents found</p>
                      <p style={{ fontSize: '0.8rem' }}>Upload a PDF or scan to initiate secure vault storage and AI extraction.</p>
                    </td>
                  </tr>
                ) : (
                  documents.map((doc) => (
                    <tr
                      key={doc.id}
                      style={{ borderBottom: '1px solid var(--border-default)', transition: 'background-color 0.15s' }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-surface-hover)')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      {/* Document File & Hash */}
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <FileText size={18} color="var(--brand-primary)" />
                          <div>
                            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{doc.original_filename}</div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span>{(doc.file_size_bytes / 1024).toFixed(1)} KB</span>
                              <span>•</span>
                              <span>{doc.page_count} page(s)</span>
                              {doc.is_duplicate && (
                                <span
                                  className="badge badge-warning"
                                  style={{ padding: '2px 6px', fontSize: '0.7rem' }}
                                  title="Duplicate document detected via SHA-256 hash. Preserved separately without silent merging."
                                >
                                  Duplicate Hash
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Facility */}
                      <td style={{ padding: '12px 16px', color: 'var(--text-secondary)' }}>
                        {doc.plant_name}
                      </td>

                      {/* Detected Classification */}
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          {doc.document_type_detected || 'Detecting...'}
                        </span>
                      </td>

                      {/* Extraction Status */}
                      <td style={{ padding: '12px 16px' }}>
                        {doc.extraction_status === 'EXTRACTED' && (
                          <span className="badge badge-valid" style={{ gap: '4px' }}>
                            <CheckCircle2 size={12} />
                            <span>Extracted</span>
                          </span>
                        )}
                        {doc.extraction_status === 'QUEUED' && (
                          <span className="badge badge-info" style={{ gap: '4px' }}>
                            <Clock size={12} />
                            <span>Queued</span>
                          </span>
                        )}
                        {doc.extraction_status === 'EXTRACTION_FAILED' && (
                          <span className="badge badge-danger" style={{ gap: '4px' }}>
                            <XCircle size={12} />
                            <span>Failed</span>
                          </span>
                        )}
                      </td>

                      {/* Statutory Expiry Date */}
                      <td style={{ padding: '12px 16px' }}>
                        {doc.detected_expiry_date ? (
                          <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                            {doc.detected_expiry_date}
                          </span>
                        ) : (
                          <span className="badge badge-neutral" title="Document has perpetual lifetime validity; no artificial expiry date invented.">
                            Permanent (No Expiry)
                          </span>
                        )}
                      </td>

                      {/* Review State */}
                      <td style={{ padding: '12px 16px' }}>
                        {doc.review_status === 'PENDING_REVIEW' && (
                          <span className="badge badge-warning" style={{ gap: '4px' }}>
                            <Clock size={12} />
                            <span>Pending Review</span>
                          </span>
                        )}
                        {doc.review_status === 'APPROVED' && (
                          <span className="badge badge-valid" style={{ gap: '4px' }}>
                            <CheckCircle2 size={12} />
                            <span>Approved</span>
                          </span>
                        )}
                        {doc.review_status === 'EDITED_AND_APPROVED' && (
                          <span className="badge badge-valid" style={{ gap: '4px' }}>
                            <CheckCircle2 size={12} />
                            <span>Edited & Approved</span>
                          </span>
                        )}
                        {doc.review_status === 'REJECTED' && (
                          <span className="badge badge-danger" style={{ gap: '4px' }}>
                            <XCircle size={12} />
                            <span>Rejected</span>
                          </span>
                        )}
                      </td>

                      {/* Action */}
                      <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                        <button
                          className="btn-secondary"
                          style={{ padding: '5px 10px', fontSize: '0.78rem' }}
                          onClick={() => handleOpenReview(doc.id)}
                        >
                          <FileCheck size={14} style={{ marginRight: '4px' }} />
                          <span>Review & Verify</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* =================================================================== */}
      {/* VIEW MODE 2: DUAL-PANE HUMAN REVIEW & VERIFICATION SCREEN           */}
      {/* =================================================================== */}
      {viewMode === 'review' && currentDoc && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', flex: 1 }}>
          {/* Review Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <button
                className="btn-secondary"
                style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                onClick={() => setViewMode('vault')}
              >
                <ArrowLeft size={14} />
                <span>Back to Vault</span>
              </button>
              <div>
                <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {currentDoc.document_type_detected || 'Compliance Document Review'}
                </h1>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {currentDoc.original_filename} • {currentDoc.plant_name}
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {currentDoc.review_status === 'PENDING_REVIEW' ? (
                <span className="badge badge-warning" style={{ gap: '4px' }}>
                  <Clock size={13} />
                  <span>Pending Human Review</span>
                </span>
              ) : currentDoc.review_status === 'REJECTED' ? (
                <span className="badge badge-danger" style={{ gap: '4px' }}>
                  <XCircle size={13} />
                  <span>Rejected by Reviewer</span>
                </span>
              ) : (
                <span className="badge badge-valid" style={{ gap: '4px' }}>
                  <CheckCircle2 size={13} />
                  <span>Approved as Evidence</span>
                </span>
              )}

              {/* Sub-Tabs: Parameters vs Audit Trail */}
              <div
                style={{
                  display: 'flex',
                  backgroundColor: 'var(--bg-surface-subtle)',
                  borderRadius: '6px',
                  padding: '3px',
                  border: '1px solid var(--border-default)',
                }}
              >
                <button
                  onClick={() => setActiveReviewTab('parameters')}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '4px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    border: 'none',
                    cursor: 'pointer',
                    backgroundColor: activeReviewTab === 'parameters' ? '#ffffff' : 'transparent',
                    color: activeReviewTab === 'parameters' ? 'var(--text-primary)' : 'var(--text-secondary)',
                    boxShadow: activeReviewTab === 'parameters' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
                  }}
                >
                  Extracted Fields & Checks
                </button>
                <button
                  onClick={() => setActiveReviewTab('history')}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '4px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    border: 'none',
                    cursor: 'pointer',
                    backgroundColor: activeReviewTab === 'history' ? '#ffffff' : 'transparent',
                    color: activeReviewTab === 'history' ? 'var(--text-primary)' : 'var(--text-secondary)',
                    boxShadow: activeReviewTab === 'history' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
                  }}
                >
                  Immutable Audit Trail ({auditLogs.length})
                </button>
              </div>
            </div>
          </div>

          {/* Split Dual-Pane Container */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 480px',
              gap: '18px',
              flex: 1,
              minHeight: 0,
            }}
          >
            {/* ------------------------------------------------------------- */}
            {/* LEFT PANE: DOCUMENT PREVIEWER & METADATA                     */}
            {/* ------------------------------------------------------------- */}
            <div
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid var(--border-default)',
                borderRadius: '8px',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
              }}
            >
              {/* Viewer Toolbar */}
              <div
                style={{
                  padding: '8px 14px',
                  borderBottom: '1px solid var(--border-default)',
                  backgroundColor: 'var(--bg-surface-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '0.82rem',
                }}
              >
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                  {currentDoc.original_filename}
                </span>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button
                    className="btn-secondary"
                    style={{ padding: '3px 7px' }}
                    onClick={() => setZoomLevel((z) => Math.max(50, z - 25))}
                  >
                    <ZoomOut size={13} />
                  </button>
                  <span style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', minWidth: '40px', textAlign: 'center' }}>
                    {zoomLevel}%
                  </span>
                  <button
                    className="btn-secondary"
                    style={{ padding: '3px 7px' }}
                    onClick={() => setZoomLevel((z) => Math.min(200, z + 25))}
                  >
                    <ZoomIn size={13} />
                  </button>
                  <span style={{ color: 'var(--border-strong)', margin: '0 4px' }}>|</span>
                  <span style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                    Page 1 of {currentDoc.page_count}
                  </span>
                  <a
                    href={api.getDocumentFileUrl(currentDoc.id)}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-secondary"
                    style={{ padding: '3px 7px', display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    <ExternalLink size={13} />
                    <span>Raw File</span>
                  </a>
                </div>
              </div>

              {/* Document Canvas Preview */}
              <div
                style={{
                  flex: 1,
                  backgroundColor: '#f1f5f9',
                  overflow: 'auto',
                  padding: '24px',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'flex-start',
                }}
              >
                <div
                  style={{
                    backgroundColor: '#ffffff',
                    width: `${Math.round(580 * (zoomLevel / 100))}px`,
                    minHeight: `${Math.round(760 * (zoomLevel / 100))}px`,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                    borderRadius: '4px',
                    padding: `${Math.round(36 * (zoomLevel / 100))}px`,
                    border: '1px solid #cbd5e1',
                    fontSize: `${Math.round(13 * (zoomLevel / 100))}px`,
                    color: '#1e293b',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    {/* Header */}
                    <div style={{ textAlign: 'center', borderBottom: '2px solid #0f172a', paddingBottom: '12px', marginBottom: '18px' }}>
                      <div style={{ fontSize: '0.85em', fontWeight: 600, color: '#475569', letterSpacing: '0.05em' }}>
                        OFFICIAL STATUTORY RECORD / TEST FIXTURE
                      </div>
                      <div style={{ fontSize: '1.2em', fontWeight: 800, color: '#0f172a', marginTop: '4px' }}>
                        {currentDoc.document_type_detected || 'COMPLIANCE CERTIFICATE'}
                      </div>
                      <div style={{ fontSize: '0.8em', color: '#64748b' }}>
                        Original File: {currentDoc.original_filename}
                      </div>
                    </div>

                    {/* Grounded Extracted Fields Callout Sheet */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      <div style={{ fontSize: '0.82em', fontWeight: 700, color: '#334155', textTransform: 'uppercase' }}>
                        Extracted Document Clauses & Values
                      </div>
                      {currentDoc.extracted_fields && currentDoc.extracted_fields.length > 0 ? (
                        currentDoc.extracted_fields.map((field) => (
                          <div
                            key={field.id}
                            style={{
                              backgroundColor: '#f8fafc',
                              borderLeft: '3px solid var(--brand-primary)',
                              padding: '8px 10px',
                              borderRadius: '2px',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75em' }}>
                              <span style={{ fontWeight: 600, color: '#0f172a' }}>{field.field_key.toUpperCase()}</span>
                              <span style={{ color: '#059669', fontWeight: 600 }}>Page {field.source_page}</span>
                            </div>
                            <div style={{ fontSize: '0.9em', fontWeight: 600, color: '#1e293b', marginTop: '2px' }}>
                              {field.confirmed_value || field.extracted_value}
                            </div>
                            {field.source_snippet && (
                              <div style={{ fontSize: '0.74em', color: '#64748b', fontStyle: 'italic', marginTop: '4px' }}>
                                "{field.source_snippet}"
                              </div>
                            )}
                          </div>
                        ))
                      ) : (
                        <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '0.85em' }}>
                          Extraction running or no structured fields found.
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Watermark / Provenance Footer */}
                  <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '10px', marginTop: '24px', fontSize: '0.7em', color: '#94a3b8' }}>
                    <div>PlantProof Private Vault Document Key: {currentDoc.storage_key || 'vault/isolated/random.bin'}</div>
                    <div>SHA-256 Content Hash: {currentDoc.content_hash}</div>
                  </div>
                </div>
              </div>

              {/* Bottom Security Capsule */}
              <div
                style={{
                  padding: '8px 14px',
                  backgroundColor: 'var(--bg-surface)',
                  borderTop: '1px solid var(--border-default)',
                  fontSize: '0.75rem',
                  color: 'var(--text-secondary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <ShieldCheck size={14} color="#059669" />
                  <span>Isolated Tenant Vault • MIME & File Signatures Validated</span>
                </div>
                <div>Storage Key: {currentDoc.storage_key ? currentDoc.storage_key.split('/').pop() : 'random-uuid.bin'}</div>
              </div>
            </div>

            {/* ------------------------------------------------------------- */}
            {/* RIGHT PANE: PARAMETERS, VALIDATION CHECKS & EVIDENCE CONTROLS  */}
            {/* ------------------------------------------------------------- */}
            <div
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid var(--border-default)',
                borderRadius: '8px',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
              }}
            >
              {activeReviewTab === 'parameters' ? (
                <>
                  <div style={{ padding: '16px 20px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '18px' }}>
                    {/* Provenance Banner */}
                    <div
                      style={{
                        padding: '10px 14px',
                        backgroundColor: 'var(--bg-surface-subtle)',
                        borderRadius: '6px',
                        border: '1px solid var(--border-default)',
                        fontSize: '0.8rem',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Sparkles size={14} color="var(--brand-primary)" />
                          <span>Deterministic + AI Extraction</span>
                        </span>
                        <span className="badge badge-valid">High Confidence</span>
                      </div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.74rem', marginTop: '4px' }}>
                        Retains model provenance, timestamp, snippet citations, and schema version.
                      </div>
                    </div>

                    {/* Cardinal Rule Expiry Notice if Permanent */}
                    {!currentDoc.detected_expiry_date && (
                      <div
                        style={{
                          padding: '10px 14px',
                          backgroundColor: '#ecfdf5',
                          borderRadius: '6px',
                          border: '1px solid #a7f3d0',
                          fontSize: '0.8rem',
                          color: '#065f46',
                        }}
                      >
                        <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <ShieldCheck size={14} />
                          <span>Cardinal Rule Enforced: Permanent Certificate</span>
                        </div>
                        <div style={{ fontSize: '0.74rem', marginTop: '2px' }}>
                          No expiration date exists on this permanent registration. System does NOT invent an expiry date.
                        </div>
                      </div>
                    )}

                    {/* Extracted Fields Form */}
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                          Extracted Parameters
                        </span>
                        <button
                          className="btn-secondary"
                          style={{ padding: '3px 8px', fontSize: '0.76rem' }}
                          onClick={() => setIsEditingFields(!isEditingFields)}
                        >
                          <Edit2 size={12} style={{ marginRight: '4px' }} />
                          <span>{isEditingFields ? 'Cancel Edit' : 'Edit Fields'}</span>
                        </button>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {currentDoc.extracted_fields?.map((field) => (
                          <div
                            key={field.id}
                            style={{
                              padding: '10px 12px',
                              backgroundColor: field.is_overridden ? '#fefce8' : '#ffffff',
                              border: `1px solid ${field.is_overridden ? '#fde047' : 'var(--border-default)'}`,
                              borderRadius: '6px',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span style={{ fontSize: '0.76rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                                  {field.field_key.replace('_', ' ').toUpperCase()}
                                </span>
                                {field.is_mandatory && (
                                  <span style={{ color: '#dc2626', fontSize: '0.75rem', fontWeight: 700 }}>*</span>
                                )}
                                {field.is_overridden && (
                                  <span className="badge badge-warning" style={{ fontSize: '0.68rem', padding: '1px 5px' }}>
                                    Edited by Reviewer
                                  </span>
                                )}
                              </div>
                              <span
                                className={`badge ${
                                  field.confidence_band === 'HIGH'
                                    ? 'badge-valid'
                                    : field.confidence_band === 'MEDIUM'
                                    ? 'badge-warning'
                                    : 'badge-danger'
                                }`}
                                style={{ fontSize: '0.68rem', padding: '1px 6px' }}
                              >
                                {Math.round(field.confidence_score * 100)}% {field.confidence_band}
                              </span>
                            </div>

                            {isEditingFields ? (
                              <input
                                type="text"
                                className="form-input"
                                style={{ width: '100%', fontSize: '0.84rem', padding: '6px 8px' }}
                                value={editableFields[field.field_key] || ''}
                                onChange={(e) =>
                                  setEditableFields({ ...editableFields, [field.field_key]: e.target.value })
                                }
                              />
                            ) : (
                              <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                                {editableFields[field.field_key] || field.extracted_value}
                              </div>
                            )}

                            {/* Source citation snippet */}
                            {field.source_snippet && (
                              <div
                                style={{
                                  marginTop: '6px',
                                  padding: '4px 8px',
                                  backgroundColor: 'var(--bg-surface-subtle)',
                                  borderRadius: '4px',
                                  fontSize: '0.73rem',
                                  color: 'var(--text-muted)',
                                }}
                              >
                                <strong>Page {field.source_page}:</strong> "{field.source_snippet}"
                              </div>
                            )}
                          </div>
                        ))}
                      </div>

                      {isEditingFields && (
                        <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'flex-end' }}>
                          <button
                            className="btn-primary"
                            style={{ padding: '6px 14px', fontSize: '0.8rem' }}
                            onClick={handleSaveFieldOverrides}
                          >
                            <Save size={13} style={{ marginRight: '4px' }} />
                            <span>Save Field Overrides</span>
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Deterministic Validation Checks Group */}
                    <div>
                      <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', display: 'block', marginBottom: '8px' }}>
                        Deterministic Rule Checks
                      </span>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {currentDoc.validation_checks?.map((chk) => (
                          <div
                            key={chk.id}
                            style={{
                              display: 'flex',
                              alignItems: 'flex-start',
                              gap: '8px',
                              fontSize: '0.78rem',
                              padding: '8px 10px',
                              borderRadius: '6px',
                              backgroundColor: chk.status === 'PASSED' ? '#f0fdf4' : '#fffbeb',
                              border: `1px solid ${chk.status === 'PASSED' ? '#bbf7d0' : '#fef08a'}`,
                            }}
                          >
                            {chk.status === 'PASSED' ? (
                              <Check size={14} color="#059669" style={{ marginTop: '2px', flexShrink: 0 }} />
                            ) : (
                              <AlertTriangle size={14} color="#d97706" style={{ marginTop: '2px', flexShrink: 0 }} />
                            )}
                            <div>
                              <div style={{ fontWeight: 600, color: '#0f172a' }}>{chk.check_name}</div>
                              <div style={{ color: '#475569', fontSize: '0.73rem', marginTop: '2px' }}>{chk.details}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Evidence Linking & Expiry Reminders */}
                    <div style={{ padding: '12px 14px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: '6px', border: '1px solid var(--border-default)' }}>
                      <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)', display: 'block', marginBottom: '8px' }}>
                        Statutory Evidence Linking & Alerts
                      </span>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <div>
                          <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                            Link to Requirement:
                          </label>
                          <select
                            className="form-input"
                            style={{ width: '100%', fontSize: '0.82rem', padding: '6px 8px' }}
                            value={linkRequirementCode}
                            onChange={(e) => setLinkRequirementCode(e.target.value)}
                          >
                            <option value="BOILER-INSP-CERT">BOILER-INSP-CERT - Steam Boiler Inspection Certificate (Form VI)</option>
                            <option value="MPCB-CTO">MPCB-CTO - Consent to Operate (Air & Water)</option>
                            <option value="DISH-FAC-REG">DISH-FAC-REG - Permanent Factory Registration Licence</option>
                          </select>
                        </div>

                        <div>
                          <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                            Expiry Notification Lead Time:
                          </label>
                          {currentDoc.detected_expiry_date ? (
                            <select
                              className="form-input"
                              style={{ width: '100%', fontSize: '0.82rem', padding: '6px 8px' }}
                              value={expiryReminderDays}
                              onChange={(e) => setExpiryReminderDays(Number(e.target.value))}
                            >
                              <option value={30}>30 days before expiration</option>
                              <option value={60}>60 days before expiration</option>
                              <option value={90}>90 days before expiration</option>
                            </select>
                          ) : (
                            <input
                              type="text"
                              disabled
                              value="None (Permanent document without expiration date)"
                              className="form-input"
                              style={{ width: '100%', fontSize: '0.8rem', backgroundColor: '#f1f5f9', color: '#64748b' }}
                            />
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Action Bar */}
                  <div
                    style={{
                      padding: '12px 18px',
                      borderTop: '1px solid var(--border-default)',
                      backgroundColor: 'var(--bg-surface-subtle)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '8px',
                    }}
                  >
                    <button
                      className="btn-secondary"
                      style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                      onClick={handleReExtract}
                    >
                      <RotateCcw size={13} style={{ marginRight: '4px' }} />
                      <span>Re-Extract</span>
                    </button>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <button
                        className="btn-danger"
                        style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                        onClick={() => setRejectModalOpen(true)}
                      >
                        <XCircle size={14} style={{ marginRight: '4px' }} />
                        <span>Reject</span>
                      </button>
                      <button
                        className="btn-primary"
                        style={{ padding: '6px 16px', fontSize: '0.8rem' }}
                        onClick={handleApproveDocument}
                      >
                        <CheckCircle2 size={14} style={{ marginRight: '4px' }} />
                        <span>Approve as Evidence</span>
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                /* Audit Trail View (No Raw Machine JSON) */
                <div style={{ padding: '16px 20px', overflowY: 'auto', flex: 1 }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '14px' }}>
                    Immutable Compliance Audit Trail
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {auditLogs.map((log) => (
                      <div
                        key={log.id}
                        style={{
                          padding: '10px 14px',
                          border: '1px solid var(--border-default)',
                          borderRadius: '6px',
                          fontSize: '0.8rem',
                          backgroundColor: '#ffffff',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span
                            className="badge badge-neutral"
                            style={{ fontWeight: 600, fontSize: '0.75rem', padding: '2px 8px' }}
                          >
                            {log.action}
                          </span>
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                            {new Date(log.created_at).toLocaleString()}
                          </span>
                        </div>
                        <div style={{ marginTop: '6px', color: 'var(--text-secondary)' }}>
                          Performed by: <strong>{log.performed_by}</strong>
                        </div>
                        {/* Human-readable metadata chips */}
                        {log.details && (
                          <div style={{ marginTop: '6px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                            {Object.entries(log.details).map(([k, v]) => (
                              <span
                                key={k}
                                style={{
                                  padding: '2px 6px',
                                  backgroundColor: 'var(--bg-surface-subtle)',
                                  borderRadius: '4px',
                                  fontSize: '0.72rem',
                                  color: 'var(--text-secondary)',
                                  border: '1px solid var(--border-default)',
                                }}
                              >
                                {k}: {String(v)}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* UPLOAD MODAL                                                        */}
      {/* =================================================================== */}
      {uploadModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.65)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px',
          }}
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '8px',
              width: '100%',
              maxWidth: '520px',
              padding: '24px',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Upload size={18} color="var(--brand-primary)" />
                <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Upload Compliance Evidence
                </h2>
              </div>
              <button
                onClick={() => setUploadModalOpen(false)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            {uploadError && (
              <div
                style={{
                  marginBottom: '14px',
                  padding: '8px 12px',
                  backgroundColor: 'var(--status-danger-bg)',
                  color: 'var(--status-danger-text)',
                  border: '1px solid var(--status-danger-border)',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                }}
              >
                {uploadError}
              </div>
            )}

            <form onSubmit={handleUploadSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Target Facility / Plant:
                </label>
                <select
                  className="form-input"
                  style={{ width: '100%', fontSize: '0.84rem' }}
                  value={uploadPlantId}
                  onChange={(e) => setUploadPlantId(e.target.value)}
                >
                  {plants.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.code})
                    </option>
                  ))}
                </select>
              </div>

              {/* Drag & Drop File Zone */}
              <div
                style={{
                  border: '2px dashed var(--border-strong)',
                  borderRadius: '8px',
                  padding: '24px',
                  textAlign: 'center',
                  backgroundColor: 'var(--bg-surface-subtle)',
                  cursor: 'pointer',
                }}
                onClick={() => document.getElementById('vault-file-picker')?.click()}
              >
                <input
                  id="vault-file-picker"
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,.tiff"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setUploadFile(e.target.files[0]);
                    }
                  }}
                />
                <Upload size={32} color="var(--brand-primary)" style={{ margin: '0 auto 8px', display: 'block' }} />
                <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {uploadFile ? uploadFile.name : 'Click to select or drag and drop document'}
                </div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Allowed formats: PDF, PNG, JPG, TIFF (Max 25MB)
                </div>
              </div>

              <div
                style={{
                  fontSize: '0.74rem',
                  color: 'var(--text-muted)',
                  backgroundColor: '#f8fafc',
                  padding: '8px 10px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-default)',
                }}
              >
                <strong>Security Protection:</strong> Files are stored privately under random internal UUID storage keys. Executables and archives are strictly rejected.
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setUploadModalOpen(false)}
                  disabled={isUploading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={isUploading || !uploadFile}
                >
                  {isUploading ? 'Validating & Uploading...' : 'Upload & Extract'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* REJECTION MODAL                                                     */}
      {/* =================================================================== */}
      {rejectModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.65)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px',
          }}
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '8px',
              width: '100%',
              maxWidth: '460px',
              padding: '24px',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
              <FileWarning size={18} color="#dc2626" />
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Reject Compliance Document
              </h2>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
              Specify the compliance reason for rejecting this document. This decision is immutably logged in the audit trail.
            </p>

            <textarea
              className="form-input"
              rows={3}
              style={{ width: '100%', fontSize: '0.84rem', padding: '8px' }}
              placeholder="e.g., Illegible scan, seal missing, or incorrect boiler registry number..."
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '16px' }}>
              <button className="btn-secondary" onClick={() => setRejectModalOpen(false)}>
                Cancel
              </button>
              <button className="btn-danger" onClick={handleRejectSubmit}>
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
