export type Role = 'SUPER_ADMIN' | 'ADMIN' | 'PLANT_MANAGER' | 'EHS_MANAGER' | 'AUDITOR' | 'VIEWER';

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: Role;
  tenantId: string;
  tenantName?: string;
  plantIds: string[];
}

export interface Plant {
  id: string;
  name: string;
  code: string;
  jurisdiction: string;
  district: string;
  pincode: string;
}

export interface PlantProfile {
  id: string;
  plantId: string;
  industryCategory: 'RED' | 'ORANGE' | 'GREEN' | 'WHITE';
  sector: string;
  employeeCount: number;
  contractLabourCount: number;
  builtUpAreaSqm: number;
  capitalInvestmentInr: number;
  connectedPowerKw: number;
  dgSetCapacityKva: number;
  hazardousWasteTpa: number;
  effluentDischargeKld: number;
  boilerCount: number;
  steamCapacityTph: number;
  version?: number | string;
  activities?: string[];
  rawAttributes?: Record<string, unknown>;
}

export type ApplicabilityStatus = 'APPLICABLE' | 'CONDITIONALLY_APPLICABLE' | 'EXEMPTED' | 'NOT_APPLICABLE';
export type EvidenceStatus = 'VALID' | 'EXPIRING_SOON' | 'MISSING' | 'EXPIRED' | 'UNDER_REVIEW' | 'NOT_REQUIRED';

export interface RequirementItem {
  id: string;
  code: string;
  title: string;
  authority: string;
  obligationType: string;
  applicability: ApplicabilityStatus;
  evidenceStatus: EvidenceStatus;
  dueDate: string | null;
  ownerName: string;
  ownerRole: string;
  ownerInitials: string;
}

export interface NeedsAttentionItem {
  id: string;
  title: string;
  authority: string;
  type: string;
  dueDate: string;
  status: 'OVERDUE' | 'DUE_SOON';
  ownerName: string;
  ownerRole: string;
  ownerInitials: string;
}

export interface DashboardSummary {
  totalRequirements: number;
  applicableCount: number;
  notApplicableCount: number;
  dueSoonCount: number;
  evidenceGapsCount: number;
  regulatoryChangesCount: number;
  regulatoryChangesRequireReview: number;
  complianceRatePercentage: number;
  statusBreakdown: {
    compliant: number;
    dueSoon: number;
    overdue: number;
    notApplicable: number;
  };
  upcomingDeadlines: Array<{
    month: string;
    count: number;
  }>;
  needsAttention: NeedsAttentionItem[];
}

export interface RegulatorySource {
  id: string;
  code: string;
  name: string;
  authority_name: string;
  jurisdiction: string;
  adapter_type: string;
  adapter_mode?: 'FIXTURE' | 'LIVE_HTTP' | 'DISABLED' | 'FAILED';
  url: string;
  update_frequency: string;
  expected_format: string;
  terms_limitations: string;
  health_status: 'HEALTHY' | 'DEGRADED' | 'UNAVAILABLE' | 'STALE';
  last_checked_at: string | null;
  last_successful_check_at: string | null;
  consecutive_failures: number;
  error_message: string | null;
  error_category?: string | null;
  is_active: boolean;
}

export interface EvidenceSnippet {
  section?: string;
  page?: number;
  text: string;
  clause?: string;
}

export interface RegulatoryChangeReview {
  id: string;
  source_id: string;
  source_name?: string;
  source_adapter_mode?: 'FIXTURE' | 'LIVE_HTTP' | 'DISABLED' | 'FAILED';
  document_id: string | null;
  target_requirement_code: string | null;
  notification_number: string;
  title: string;
  published_date: string | null;
  effective_date: string | null;
  summary_plain_language: string;
  key_changes_summary: string[];
  who_may_be_affected: string[];
  evidence_snippets: EvidenceSnippet[];
  proposed_categories: string[];
  confidence_score: number;
  confidence_band: 'HIGH' | 'MEDIUM' | 'LOW';
  detected_change_type: string;
  old_text: string | null;
  new_text: string | null;
  diff_summary: string | null;
  status: 'detected' | 'extraction_failed' | 'draft_analysis' | 'needs_review' | 'approved' | 'rejected' | 'published' | 'superseded';
  review_decision: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  published_rule_id: string | null;
  superseded_rule_id: string | null;
}


export interface RegulatoryChangeImpact {
  id: string;
  change_review_id: string;
  plant_id: string;
  plant_name: string;
  plant_code: string;
  tenant_name: string;
  impact_status: 'POTENTIALLY_APPLICABLE' | 'REQUIRES_REVIEW' | 'NOT_APPLICABLE';
  matched_facts: Record<string, any>;
  missing_facts: string[];
  explanation: string;
}

export interface RegulatoryAuditLog {
  id: string;
  action: string;
  performed_by: string;
  details: Record<string, any>;
  created_at: string;
}

export interface ExtractedFieldItem {
  id: string;
  field_key: string;
  extracted_value: string;
  confirmed_value: string | null;
  confidence_score: number;
  confidence_band: 'HIGH' | 'MEDIUM' | 'LOW';
  source_page: number;
  source_snippet: string | null;
  field_type: string;
  is_mandatory: boolean;
  is_overridden: boolean;
}

export interface ValidationCheckItem {
  id: string;
  check_code: string;
  check_name: string;
  status: 'PASSED' | 'FAILED' | 'WARNING' | 'SKIPPED';
  details: string;
  rule_severity: 'MANDATORY' | 'WARNING' | 'INFO';
}

export interface LinkedRequirementItem {
  evidence_link_id: string;
  plant_requirement_id: string;
  statutory_code: string;
  statutory_title: string;
  evidence_status: string;
}

export interface ComplianceDocumentItem {
  id: string;
  plant_id: string;
  plant_name: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  content_hash: string;
  page_count: number;
  storage_key?: string;
  document_type_detected: string | null;
  extraction_status: 'QUEUED' | 'EXTRACTING' | 'EXTRACTED' | 'EXTRACTION_FAILED';
  extraction_provider_mode?: 'FIXTURE' | 'LIVE_OCR' | 'DISABLED' | 'FAILED';
  extraction_error?: string | null;
  error_category?: string | null;
  review_status: 'PENDING_REVIEW' | 'APPROVED' | 'EDITED_AND_APPROVED' | 'REJECTED';
  detected_issue_date: string | null;
  detected_expiry_date: string | null;
  is_duplicate: boolean;
  duplicate_of_id: string | null;
  expiry_reminder_days?: number;
  uploaded_by?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  rejection_reason?: string | null;
  extracted_fields?: ExtractedFieldItem[];
  validation_checks?: ValidationCheckItem[];
  linked_requirements?: LinkedRequirementItem[];
  created_at: string;
}


export interface DocumentAuditLogItem {
  id: string;
  action: string;
  performed_by: string;
  details: Record<string, any>;
  created_at: string;
}

// -----------------------------------------------------------------------------
// Operational Workflows: Requirements, Tasks, Reminders, Reports, Audit
// -----------------------------------------------------------------------------

export interface StatutoryProvenance {
  act_title: string | null;
  act_short_name: string | null;
  act_year: number | null;
  authority_code: string | null;
  authority_name: string | null;
  jurisdiction_name: string | null;
  jurisdiction_level: string | null;
  section_clause?: string | null;
  gazette_reference?: string | null;
  official_gazette_ref?: string | null;
  official_source_url?: string | null;
  publication_date?: string | null;
  source_verification_status?: string | null;
  source_fingerprint?: string | null;
  instrument_identifier?: string | null;
  is_verified?: boolean;
}

export interface EvidenceSummaryItem {
  evidence_link_id: string;
  document_id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  upload_date: string;
  detected_expiry_date?: string | null;
  evidence_status: string;
  review_status: string;
  verified_by?: string | null;
}

export interface ApplicabilityProvenance {
  applicability_status: string;
  applicability_rationale: string;
  rule_version: number;
  matched_facts: Record<string, unknown>;
  missing_facts: string[];
  condition_trace?: Record<string, unknown>;
  last_evaluated_at: string;
}

export interface RequirementHistoryItem {
  id: string;
  action: string;
  performed_by: string;
  timestamp: string;
  details: Record<string, unknown>;
  summary_text: string;
}

export interface RequirementDetailItem {
  id: string;
  statutory_requirement_id: string;
  code: string;
  title: string;
  description: string | null;
  obligation_type: string;
  authority_code: string | null;
  authority_name: string | null;
  jurisdiction: string;
  applicability_status: string;
  applicability_rationale: string;
  evidence_status: string;
  current_due_date: string | null;
  owner_name: string | null;
  owner_email: string | null;
  evidence_count: number;
  tasks_count: number;
  is_custom: boolean;
  last_evaluated_at: string;
  provenance: StatutoryProvenance;
  applicability: ApplicabilityProvenance;
  evidence_list: EvidenceSummaryItem[];
  history: RequirementHistoryItem[];
}

export interface PaginatedRequirements {
  items: RequirementDetailItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SavedViewPreset {
  id: string;
  name: string;
  description: string;
  filter_params: Record<string, unknown>;
  count: number;
}

export interface TaskComment {
  id: string;
  user_name: string | null;
  user_email: string | null;
  comment_text: string;
  created_at: string;
}

export interface TaskAttachment {
  id: string;
  document_id: string | null;
  filename: string;
  file_size_bytes: number;
  storage_key?: string | null;
  uploaded_by_email?: string | null;
  created_at: string;
}

export interface TaskItem {
  id: string;
  plant_id: string;
  plant_name?: string | null;
  plant_requirement_id?: string | null;
  requirement_code?: string | null;
  requirement_title?: string | null;
  title: string;
  description?: string | null;
  due_date: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'TODO' | 'IN_PROGRESS' | 'BLOCKED' | 'COMPLETED';
  assigned_to_id?: string | null;
  assigned_to_name?: string | null;
  assigned_to_email?: string | null;
  completed_at?: string | null;
  blocked_reason?: string | null;
  comments_count: number;
  attachments_count: number;
  created_at: string;
  comments?: TaskComment[];
  attachments?: TaskAttachment[];
}

export interface PaginatedTasks {
  items: TaskItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface NotificationItem {
  id: string;
  plant_id: string;
  notification_type: 'DUE_SOON' | 'OVERDUE' | 'STATUS_CHANGE' | 'SYSTEM_TEST' | string;
  entity_type: string;
  entity_id: string;
  title: string;
  message: string;
  channel: 'IN_APP' | 'EMAIL';
  status: 'UNREAD' | 'READ' | 'DISMISSED';
  sent_at: string;
  read_at?: string | null;
  metadata_payload?: Record<string, unknown>;
}

export interface PaginatedNotifications {
  items: NotificationItem[];
  total: number;
  page: number;
  page_size: number;
  unread_count: number;
}

export interface NotificationPreference {
  email_enabled: boolean;
  in_app_enabled: boolean;
  lead_time_days: number;
  notify_on_overdue: boolean;
  frequency: 'IMMEDIATE' | 'DAILY_DIGEST';
}

export interface ReportJobItem {
  id: string;
  plant_id: string;
  plant_name?: string | null;
  report_title: string;
  status: 'QUEUED' | 'GENERATING' | 'COMPLETED' | 'FAILED';
  error_message?: string | null;
  prepared_at: string;
  data_as_of: string;
  file_format: 'HTML' | 'JSON';
  file_size_bytes: number;
  summary_metrics: {
    total_applicable_requirements?: number;
    verified_evidence_count?: number;
    missing_evidence_count?: number;
    expiring_soon_count?: number;
    open_tasks_count?: number;
    readiness_percentage?: number;
  };
  download_url?: string | null;
  created_at: string;
}

export interface PaginatedReportJobs {
  items: ReportJobItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ProfileAttributeDiff {
  field_name: string;
  previous_value: unknown;
  proposed_value: unknown;
}

export interface ProposedRequirementDiffItem {
  requirement_code: string;
  requirement_title: string;
  authority_code?: string | null;
  obligation_type: string;
  previous_status: string;
  projected_status: string;
  reason: string;
  impact_type: 'NEWLY_APPLICABLE' | 'NO_LONGER_APPLICABLE' | 'STATUS_CHANGE' | 'UNCHANGED';
}

export interface ProfileReassessmentSimulation {
  plant_id: string;
  attribute_changes: ProfileAttributeDiff[];
  newly_applicable_count: number;
  no_longer_applicable_count: number;
  unchanged_applicable_count: number;
  needs_review_count: number;
  impacted_requirements: ProposedRequirementDiffItem[];
  summary_guidance: string;
}

export interface AuditLogEntry {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  user_name: string | null;
  user_email: string | null;
  readable_description: string;
  description?: string;
  changes_summary: string[];
  timestamp: string;
  client_ip?: string | null;
  previous_state?: Record<string, unknown> | null;
  new_state: Record<string, unknown>;
}

export interface PaginatedAuditLogs {
  items: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  available_actions: string[];
  available_entity_types: string[];
}

export interface MasterAuthority {
  id: string;
  code: string;
  name: string;
  jurisdiction_level: string;
  jurisdiction_name: string;
  website_url?: string | null;
}

export interface MasterAct {
  id: string;
  authority_id: string;
  authority_code?: string;
  code: string;
  title: string;
  enacted_year?: number;
  jurisdiction_scope: string;
}

export interface MasterRequirement {
  id: string;
  act_id: string;
  act_title?: string;
  authority_code?: string;
  code: string;
  title: string;
  description: string;
  obligation_type: string;
  validity_period_months?: number;
  grace_period_days?: number;
}

export interface RuleResponseItem {
  id: string;
  statutory_requirement_id: string;
  statutory_requirement_code?: string | null;
  rule_version: string;
  status: 'PROPOSED' | 'ACTIVE' | 'SUPERSEDED' | 'REJECTED';
  expression_ast: Record<string, unknown>;
  pass_explanation_template?: string | null;
  fail_explanation_template?: string | null;
  is_immutable: boolean;
  effective_from: string;
  effective_to?: string | null;
  change_rationale?: string | null;
  approved_at?: string | null;
}

export interface RuleSimulationResult {
  rule_id?: string;
  outcome: 'PASS' | 'FAIL' | 'UNKNOWN';
  explanation: string;
  evaluated_facts: Record<string, unknown>;
  missing_facts: string[];
}

export interface AIAssistantMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  timestamp: string;
  citations?: Array<{
    act: string;
    section: string;
    gazette_ref?: string;
    source_url?: string;
  }>;
  uncertainty_flag?: boolean;
  uncertainty_note?: string;
}


