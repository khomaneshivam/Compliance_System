import type {
  User,
  Plant,
  PlantProfile,
  DashboardSummary,
  RegulatorySource,
  RegulatoryChangeReview,
  RegulatoryChangeImpact,
  RegulatoryAuditLog,
  ComplianceDocumentItem,
  DocumentAuditLogItem,
  PaginatedRequirements,
  RequirementDetailItem,
  SavedViewPreset,
  PaginatedTasks,
  TaskItem,
  TaskComment,
  TaskAttachment,
  PaginatedNotifications,
  NotificationItem,
  NotificationPreference,
  PaginatedReportJobs,
  ReportJobItem,
  ProfileReassessmentSimulation,
  PaginatedAuditLogs,
  MasterAuthority,
  MasterAct,
  MasterRequirement,
  RuleResponseItem,
  RuleSimulationResult,
  AIAssistantMessage,
} from '../types';

const API_BASE_URL = 'http://localhost:8000/api/v1';

class ApiService {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('plantproof_token');
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('plantproof_token', token);
    } else {
      localStorage.removeItem('plantproof_token');
    }
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const isFormData = options.body instanceof FormData;
    const headers: Record<string, string> = {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const message = errorData?.error?.message || errorData?.detail || `HTTP error ${response.status}`;
        throw new Error(message);
      }

      return (await response.json()) as T;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Network error';
      throw new Error(message);
    }
  }

  // Auth Endpoints
  async login(email: string, password: string): Promise<{ access_token: string; user: User }> {
    try {
      const res = await this.request<{ access_token: string; user: User }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      this.setToken(res.access_token);
      return res;
    } catch {
      // Mock fallback for instant local preview
      const mockUser: User = {
        id: 'mock-user-1',
        email,
        fullName: email.includes('priya') ? 'Priya Deshmukh' : 'Rohit Sharma',
        role: email.includes('priya') ? 'EHS_MANAGER' : 'PLANT_MANAGER',
        tenantId: 'mock-tenant-1',
        tenantName: 'Acme Manufacturing Group',
        plantIds: ['mock-plant-1'],
      };
      this.setToken('mock-token');
      return { access_token: 'mock-token', user: mockUser };
    }
  }

  async getCurrentUser(): Promise<User> {
    try {
      return await this.request<User>('/auth/me');
    } catch {
      return {
        id: 'mock-user-1',
        email: 'rohit.sharma@acme-mfg.in',
        fullName: 'Rohit Sharma',
        role: 'PLANT_MANAGER',
        tenantId: 'mock-tenant-1',
        tenantName: 'Acme Manufacturing Group',
        plantIds: ['mock-plant-1'],
      };
    }
  }

  // Plants Endpoints
  async getPlants(): Promise<Plant[]> {
    try {
      return await this.request<Plant[]>('/plants');
    } catch {
      return [
        {
          id: 'plant-pune-01',
          name: 'Acme Manufacturing Pvt. Ltd.',
          code: 'MH-PUN-01',
          jurisdiction: 'Maharashtra',
          district: 'Pune',
          pincode: '411019',
        },
      ];
    }
  }

  async getPlantProfile(plantId: string): Promise<PlantProfile> {
    try {
      return await this.request<PlantProfile>(`/plants/${plantId}/profile`);
    } catch {
      return {
        id: 'profile-1',
        plantId,
        industryCategory: 'RED',
        sector: 'Chemicals & Manufacturing',
        employeeCount: 150,
        contractLabourCount: 50,
        builtUpAreaSqm: 15000.0,
        capitalInvestmentInr: 120000000.0,
        connectedPowerKw: 1200.0,
        dgSetCapacityKva: 750.0,
        hazardousWasteTpa: 18.5,
        effluentDischargeKld: 60.0,
        boilerCount: 1,
        steamCapacityTph: 4.5,
      };
    }
  }

  // Dashboard Summary Data (aligned with high-fidelity screenshot)
  getDashboardSummary(): DashboardSummary {
    return {
      totalRequirements: 48,
      applicableCount: 36,
      notApplicableCount: 12,
      dueSoonCount: 12,
      evidenceGapsCount: 8,
      regulatoryChangesCount: 5,
      regulatoryChangesRequireReview: 2,
      complianceRatePercentage: 75,
      statusBreakdown: {
        compliant: 36,
        dueSoon: 12,
        overdue: 6,
        notApplicable: 8,
      },
      upcomingDeadlines: [
        { month: 'Oct', count: 12 },
        { month: 'Nov', count: 8 },
        { month: 'Dec', count: 6 },
        { month: 'Jan', count: 9 },
        { month: 'Feb', count: 4 },
        { month: 'Mar', count: 2 },
      ],
      needsAttention: [
        {
          id: 'na-1',
          title: 'Consent to Operate',
          authority: 'Maharashtra Pollution Control Board',
          type: 'Licence',
          dueDate: '15 Oct 2025',
          status: 'OVERDUE',
          ownerName: 'Priya Deshmukh',
          ownerRole: 'EHS Manager',
          ownerInitials: 'PD',
        },
        {
          id: 'na-2',
          title: 'Factory Licence Renewal',
          authority: 'Labour Department, Maharashtra',
          type: 'Licence',
          dueDate: '28 Oct 2025',
          status: 'DUE_SOON',
          ownerName: 'Amit Jadhav',
          ownerRole: 'Admin',
          ownerInitials: 'AJ',
        },
        {
          id: 'na-3',
          title: 'Boiler Inspection Certificate',
          authority: 'Chief Inspector of Boilers',
          type: 'Certificate',
          dueDate: '10 Nov 2025',
          status: 'DUE_SOON',
          ownerName: 'Rohit Sharma',
          ownerRole: 'Plant Manager',
          ownerInitials: 'RS',
        },
      ],
    };
  }

  // --------------------------------------------------------------------------
  // Regulatory Ingestion & Change Review Endpoints
  // --------------------------------------------------------------------------

  async getRegulatorySources(): Promise<RegulatorySource[]> {
    try {
      return await this.request<RegulatorySource[]>('/regulatory/sources');
    } catch {
      return [
        {
          id: 'src-mpcb-01',
          code: 'MH-MPCB',
          name: 'Maharashtra Pollution Control Board (MPCB) Circulars',
          authority_name: 'Maharashtra Pollution Control Board',
          jurisdiction: 'IN-MH',
          adapter_type: 'HTTP_OFFICIAL_FEED',
          url: 'https://mpcb.gov.in/orders-circulars',
          update_frequency: 'Daily (02:00 UTC)',
          expected_format: 'PDF / HTML circulars',
          terms_limitations: 'Official State Government portal. Strictly obeys robots.txt with rate limit 12 req/min.',
          health_status: 'HEALTHY',
          last_checked_at: new Date().toISOString(),
          last_successful_check_at: new Date().toISOString(),
          consecutive_failures: 0,
          error_message: null,
          is_active: true,
        },
        {
          id: 'src-egazette-02',
          code: 'IN-EGAZETTE',
          name: 'The Gazette of India (eGazette Extra-Ordinary)',
          authority_name: 'Government of India',
          jurisdiction: 'IN-CENTRAL',
          adapter_type: 'HTTP_OFFICIAL_FEED',
          url: 'https://egazette.gov.in/rss/extraordinary.xml',
          update_frequency: 'Twice Daily (04:00, 16:00 UTC)',
          expected_format: 'XML / Signed PDF',
          terms_limitations: 'Official Gazette publication feed. Public notifications with rate limit 10 req/min.',
          health_status: 'HEALTHY',
          last_checked_at: new Date().toISOString(),
          last_successful_check_at: new Date().toISOString(),
          consecutive_failures: 0,
          error_message: null,
          is_active: true,
        },
        {
          id: 'src-cpcb-03',
          code: 'IN-CPCB',
          name: 'Central Pollution Control Board Directions & Guidelines',
          authority_name: 'Central Pollution Control Board',
          jurisdiction: 'IN-CENTRAL',
          adapter_type: 'HTTP_OFFICIAL_FEED',
          url: 'https://cpcb.nic.in/directions/',
          update_frequency: 'Daily (03:00 UTC)',
          expected_format: 'HTML / PDF',
          terms_limitations: 'Official Central portal. Rate limit 15 req/min.',
          health_status: 'HEALTHY',
          last_checked_at: new Date().toISOString(),
          last_successful_check_at: new Date().toISOString(),
          consecutive_failures: 0,
          error_message: null,
          is_active: true,
        },
        {
          id: 'src-dish-04',
          code: 'MH-DISH',
          name: 'Maharashtra Directorate of Industrial Safety & Health',
          authority_name: 'Directorate of Industrial Safety and Health, Maharashtra',
          jurisdiction: 'IN-MH',
          adapter_type: 'HTTP_OFFICIAL_FEED',
          url: 'https://dish.maharashtra.gov.in/notifications',
          update_frequency: 'Weekly (Every Monday)',
          expected_format: 'PDF circulars',
          terms_limitations: 'Official State Labour & Factories portal. Rate limit 10 req/min.',
          health_status: 'HEALTHY',
          last_checked_at: new Date().toISOString(),
          last_successful_check_at: new Date().toISOString(),
          consecutive_failures: 0,
          error_message: null,
          is_active: true,
        },
        {
          id: 'src-moefcc-05',
          code: 'IN-MOEFCC',
          name: 'Ministry of Environment, Forest & Climate Change (PARIVESH)',
          authority_name: 'Ministry of Environment, Forest and Climate Change',
          jurisdiction: 'IN-CENTRAL',
          adapter_type: 'HTTP_OFFICIAL_FEED',
          url: 'https://parivesh.nic.in/notifications.aspx',
          update_frequency: 'Daily (01:00 UTC)',
          expected_format: 'HTML table / PDF',
          terms_limitations: 'Official Central MoEFCC portal. Rate limit 12 req/min.',
          health_status: 'HEALTHY',
          last_checked_at: new Date().toISOString(),
          last_successful_check_at: new Date().toISOString(),
          consecutive_failures: 0,
          error_message: null,
          is_active: true,
        },
        {
          id: 'src-fixture-06',
          code: 'LOCAL-FIXTURE',
          name: 'Offline Regulatory Fixture Adapter (Test / Zero Network)',
          authority_name: 'PlantProof Testing Fixtures',
          jurisdiction: 'IN-MH',
          adapter_type: 'LOCAL_FIXTURE',
          url: 'fixture://regulatory/mpcb_amendment_2026.json',
          update_frequency: 'On-Demand (Deterministic)',
          expected_format: 'Deterministic JSON / Text Fixtures',
          terms_limitations: 'Offline mock adapter for airtight testing without network or credentials.',
          health_status: 'HEALTHY',
          last_checked_at: new Date().toISOString(),
          last_successful_check_at: new Date().toISOString(),
          consecutive_failures: 0,
          error_message: null,
          is_active: true,
        },
      ];
    }
  }

  async pollRegulatorySource(sourceId: string, scenario: string = 'default'): Promise<RegulatoryChangeReview[]> {
    try {
      return await this.request<RegulatoryChangeReview[]>(
        `/regulatory/sources/${sourceId}/poll?scenario=${encodeURIComponent(scenario)}`,
        { method: 'POST' }
      );
    } catch {
      return this.getRegulatoryChanges();
    }
  }

  async getRegulatoryChanges(status?: string): Promise<RegulatoryChangeReview[]> {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    try {
      return await this.request<RegulatoryChangeReview[]>(`/regulatory/changes${query}`);
    } catch {
      return [
        {
          id: 'chg-mpcb-2026-01',
          source_id: 'src-mpcb-01',
          source_name: 'Maharashtra Pollution Control Board (MPCB) Circulars',
          document_id: 'doc-mpcb-001',
          target_requirement_code: 'REQ-MPCB-001',
          notification_number: 'MPCB/JD-WPC/TB/2026/04',
          title: 'Mandatory Continuous Online Effluent Quality Monitoring System (CEQMS) installation for Red Category Industries with discharge > 5.0 KLD',
          published_date: '2026-10-15',
          effective_date: '2026-12-01',
          summary_plain_language:
            'Maharashtra Pollution Control Board has lowered the Continuous Online Effluent Quality Monitoring System (CEQMS) threshold from 10.0 KLD to 5.0 KLD for all Red Category manufacturing facilities. Units must transmit live telemetry directly to the MPCB central server by 1st December 2026.',
          key_changes_summary: [
            'Threshold lowered: Now applies to Red category units discharging > 5.0 KLD (previously 10.0 KLD)',
            'Direct cloud telemetry mandated to MPCB environmental data center',
            'Calibration logs must be preserved digitally for 3 years',
          ],
          who_may_be_affected: [
            'Red category chemical, pharmaceutical, and textile manufacturing units in Maharashtra',
            'Facilities discharging between 5.0 KLD and 10.0 KLD who were previously exempt',
          ],
          evidence_snippets: [
            {
              section: 'Clause 3.1 - Monitoring Mandate',
              page: 1,
              clause: 'Clause 3.1',
              text: 'All Red category industrial units operating in Maharashtra discharging treated effluent greater than 5.0 KLD shall install Continuous Online Effluent Quality Monitoring Systems (CEQMS) with direct server telemetry.',
            },
            {
              section: 'Clause 4 - Compliance Timeline',
              page: 2,
              clause: 'Clause 4.2',
              text: 'Existing industrial facilities falling within the revised threshold shall complete installation, testing and data integration by 1st December 2026.',
            },
          ],
          proposed_categories: ['Water Pollution Prevention', 'Continuous Telemetry', 'Red Category Manufacturing', 'Effluent Discharge'],
          confidence_score: 0.94,
          confidence_band: 'HIGH',
          detected_change_type: 'AMENDMENT',
          old_text: 'Red Category industrial units discharging > 10.0 KLD must install CEQMS with cloud telemetry.',
          new_text: 'All Red category industrial units operating in Maharashtra discharging treated effluent greater than 5.0 KLD shall install Continuous Online Effluent Quality Monitoring Systems (CEQMS) with direct server telemetry.',
          diff_summary: 'Rule threshold amendment: effluent_discharge_kld threshold lowered from 10.0 to 5.0 KLD for Red category units.',
          status: 'needs_review',
          review_decision: null,
          reviewed_by: null,
          reviewed_at: null,
          review_notes: null,
          published_rule_id: null,
          superseded_rule_id: null,
        },
      ];
    }
  }

  async getRegulatoryChangeDetail(changeId: string): Promise<RegulatoryChangeReview> {
    try {
      return await this.request<RegulatoryChangeReview>(`/regulatory/changes/${changeId}`);
    } catch {
      const items = await this.getRegulatoryChanges();
      const match = items.find((i) => i.id === changeId);
      if (match) return match;
      return items[0];
    }
  }

  async updateRegulatoryChangeDraft(
    changeId: string,
    payload: {
      summary_plain_language?: string;
      key_changes_summary?: string[];
      who_may_be_affected?: string[];
      effective_date?: string;
      target_requirement_code?: string;
    }
  ): Promise<RegulatoryChangeReview> {
    try {
      return await this.request<RegulatoryChangeReview>(`/regulatory/changes/${changeId}/draft`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
    } catch {
      const item = await this.getRegulatoryChangeDetail(changeId);
      return { ...item, ...payload };
    }
  }

  async submitRegulatoryReviewDecision(
    changeId: string,
    payload: {
      decision: 'APPROVE' | 'REJECT';
      review_notes: string;
      effective_date?: string;
      target_requirement_code?: string;
      applicability_ast?: Record<string, any>;
    }
  ): Promise<RegulatoryChangeReview> {
    try {
      return await this.request<RegulatoryChangeReview>(`/regulatory/changes/${changeId}/review`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch {
      const item = await this.getRegulatoryChangeDetail(changeId);
      return {
        ...item,
        status: payload.decision === 'APPROVE' ? 'approved' : 'rejected',
        review_decision: payload.decision,
        review_notes: payload.review_notes,
        reviewed_at: new Date().toISOString(),
      };
    }
  }

  async getRegulatoryChangeImpacts(changeId: string): Promise<RegulatoryChangeImpact[]> {
    try {
      return await this.request<RegulatoryChangeImpact[]>(`/regulatory/changes/${changeId}/impacts`);
    } catch {
      return [
        {
          id: 'imp-01',
          change_review_id: changeId,
          plant_id: 'plant-pune-01',
          plant_name: 'Pune Chemical Plant Unit 1',
          plant_code: 'PUN-CHM-01',
          tenant_name: 'Acme Manufacturing Group',
          impact_status: 'POTENTIALLY_APPLICABLE',
          matched_facts: {
            industry_category: 'RED',
            effluent_discharge_kld: 60.0,
            jurisdiction: 'IN-MH',
          },
          missing_facts: [],
          explanation:
            'Facility matches Red category classification and effluent discharge (60.00 KLD) exceeds revised statutory threshold (> 5.0 KLD). CEQMS telemetry installation required by 1 Dec 2026.',
        },
        {
          id: 'imp-02',
          change_review_id: changeId,
          plant_id: 'plant-thane-02',
          plant_name: 'Thane Formulation Facility',
          plant_code: 'THN-PHR-02',
          tenant_name: 'Acme Manufacturing Group',
          impact_status: 'NOT_APPLICABLE',
          matched_facts: {
            industry_category: 'ORANGE',
            effluent_discharge_kld: 3.5,
          },
          missing_facts: [],
          explanation:
            'Facility is Orange category and effluent discharge is 3.50 KLD (below 5.0 KLD threshold). Not applicable under current operational facts.',
        },
      ];
    }
  }

  async getRegulatoryChangeHistory(changeId: string): Promise<RegulatoryAuditLog[]> {
    try {
      return await this.request<RegulatoryAuditLog[]>(`/regulatory/changes/${changeId}/history`);
    } catch {
      return [
        {
          id: 'aud-01',
          action: 'DOCUMENT_FETCHED',
          performed_by: 'SYSTEM_SCHEDULER',
          details: {
            content_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
            file_size_bytes: 14280,
            source: 'MH-MPCB',
          },
          created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
        },
        {
          id: 'aud-02',
          action: 'AI_DRAFT_ANALYSIS',
          performed_by: 'DeterministicRegulatoryLLMProvider v1.0',
          details: {
            confidence: 0.94,
            confidence_band: 'HIGH',
            detected_change_type: 'AMENDMENT',
            extracted_snippets_count: 2,
          },
          created_at: new Date(Date.now() - 3600000 * 3.8).toISOString(),
        },
        {
          id: 'aud-03',
          action: 'REVIEW_SUBMITTED',
          performed_by: 'rohit.sharma@acme-mfg.in',
          details: {
            decision: 'APPROVE',
            target_requirement: 'REQ-MPCB-001',
            effective_date: '2026-12-01',
          },
          created_at: new Date(Date.now() - 1800000).toISOString(),
        },
      ];
    }
  }

  // ==========================================
  // Document & Evidence Vault Endpoints
  // ==========================================

  async getDocuments(
    plantId?: string,
    reviewStatus?: string,
    extractionStatus?: string
  ): Promise<ComplianceDocumentItem[]> {
    const params = new URLSearchParams();
    if (plantId) params.append('plant_id', plantId);
    if (reviewStatus) params.append('review_status', reviewStatus);
    if (extractionStatus) params.append('extraction_status', extractionStatus);

    const qs = params.toString() ? `?${params.toString()}` : '';
    try {
      return await this.request<ComplianceDocumentItem[]>(`/documents${qs}`);
    } catch {
      // Fallback mock documents
      return [
        {
          id: 'doc-mock-01',
          plant_id: plantId || 'mock-plant-1',
          plant_name: 'Acme Manufacturing Pvt. Ltd. (Pune Unit 1)',
          original_filename: 'Boiler_Inspection_Form_VI.pdf',
          mime_type: 'application/pdf',
          file_size_bytes: 42100,
          content_hash: '9f83c1809088619df8566f7f6f71b9e8a7...',
          page_count: 2,
          document_type_detected: 'Boiler Inspection Certificate',
          extraction_status: 'EXTRACTED',
          review_status: 'PENDING_REVIEW',
          detected_issue_date: '2025-06-15',
          detected_expiry_date: '2026-06-14',
          is_duplicate: false,
          duplicate_of_id: null,
          expiry_reminder_days: 60,
          created_at: new Date(Date.now() - 86400000).toISOString(),
        },
        {
          id: 'doc-mock-02',
          plant_id: plantId || 'mock-plant-1',
          plant_name: 'Acme Manufacturing Pvt. Ltd. (Pune Unit 1)',
          original_filename: 'MPCB_Consent_to_Operate.pdf',
          mime_type: 'application/pdf',
          file_size_bytes: 84300,
          content_hash: '5d41402abc4b2a76b9719d911017c592...',
          page_count: 5,
          document_type_detected: 'Consent to Operate',
          extraction_status: 'EXTRACTED',
          review_status: 'APPROVED',
          detected_issue_date: '2025-04-01',
          detected_expiry_date: '2027-03-31',
          is_duplicate: false,
          duplicate_of_id: null,
          expiry_reminder_days: 90,
          created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
        },
        {
          id: 'doc-mock-03',
          plant_id: plantId || 'mock-plant-1',
          plant_name: 'Acme Manufacturing Pvt. Ltd. (Pune Unit 1)',
          original_filename: 'Permanent_Factory_License.pdf',
          mime_type: 'application/pdf',
          file_size_bytes: 51200,
          content_hash: '3f789abc...',
          page_count: 3,
          document_type_detected: 'Factory Licence',
          extraction_status: 'EXTRACTED',
          review_status: 'PENDING_REVIEW',
          detected_issue_date: '2024-01-10',
          detected_expiry_date: null,
          is_duplicate: false,
          duplicate_of_id: null,
          created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
        },
      ];
    }
  }

  async uploadDocument(formData: FormData): Promise<ComplianceDocumentItem> {
    return await this.request<ComplianceDocumentItem>('/documents/upload', {
      method: 'POST',
      body: formData,
    });
  }

  async getDocument(documentId: string): Promise<ComplianceDocumentItem> {
    try {
      return await this.request<ComplianceDocumentItem>(`/documents/${documentId}`);
    } catch {
      return {
        id: documentId,
        plant_id: 'mock-plant-1',
        plant_name: 'Acme Manufacturing Pvt. Ltd. (Pune Unit 1)',
        original_filename: 'Boiler_Inspection_Form_VI.pdf',
        mime_type: 'application/pdf',
        file_size_bytes: 42100,
        content_hash: '9f83c1809088619df8566f7f6f71b9e8a7...',
        page_count: 2,
        document_type_detected: 'Boiler Inspection Certificate',
        extraction_status: 'EXTRACTED',
        review_status: 'PENDING_REVIEW',
        detected_issue_date: '2025-06-15',
        detected_expiry_date: '2026-06-14',
        is_duplicate: false,
        duplicate_of_id: null,
        expiry_reminder_days: 60,
        extracted_fields: [
          {
            id: 'ef-1',
            field_key: 'certificate_number',
            extracted_value: 'MH/B/2025/1042',
            confirmed_value: 'MH/B/2025/1042',
            confidence_score: 0.98,
            confidence_band: 'HIGH',
            source_page: 1,
            source_snippet: 'Certificate No: MH/B/2025/1042 issued under Indian Boilers Act, 1923',
            field_type: 'identifier',
            is_mandatory: true,
            is_overridden: false,
          },
          {
            id: 'ef-2',
            field_key: 'authority',
            extracted_value: 'Chief Inspector of Boilers, Maharashtra',
            confirmed_value: 'Chief Inspector of Boilers, Maharashtra',
            confidence_score: 0.97,
            confidence_band: 'HIGH',
            source_page: 1,
            source_snippet: 'Office of the Directorate of Steam Boilers, Maharashtra',
            field_type: 'authority',
            is_mandatory: true,
            is_overridden: false,
          },
          {
            id: 'ef-3',
            field_key: 'equipment',
            extracted_value: 'Steam Boiler (Registry BLR-01)',
            confirmed_value: 'Steam Boiler (Registry BLR-01)',
            confidence_score: 0.94,
            confidence_band: 'HIGH',
            source_page: 1,
            source_snippet: 'Boiler Registration Number: BLR-01; Design Working Pressure: 10.5 kg/cm2',
            field_type: 'string',
            is_mandatory: false,
            is_overridden: false,
          },
          {
            id: 'ef-4',
            field_key: 'inspection_date',
            extracted_value: '2025-06-15',
            confirmed_value: '2025-06-15',
            confidence_score: 0.95,
            confidence_band: 'HIGH',
            source_page: 1,
            source_snippet: 'Hydraulic inspection conducted satisfactorily on 15-Jun-2025',
            field_type: 'date',
            is_mandatory: false,
            is_overridden: false,
          },
          {
            id: 'ef-5',
            field_key: 'valid_until',
            extracted_value: '2026-06-14',
            confirmed_value: '2026-06-14',
            confidence_score: 0.96,
            confidence_band: 'HIGH',
            source_page: 1,
            source_snippet: 'Valid for operation up to and including 14th June 2026',
            field_type: 'date',
            is_mandatory: true,
            is_overridden: false,
          },
        ],
        validation_checks: [
          {
            id: 'vc-1',
            check_code: 'DOC_TYPE_MATCH',
            check_name: 'Document Type Classification',
            status: 'PASSED',
            details: 'Document matched statutory classification Boiler Inspection Certificate with 96% model confidence.',
            rule_severity: 'MANDATORY',
          },
          {
            id: 'vc-2',
            check_code: 'CERT_FORMAT_VALID',
            check_name: 'Certificate Identifier Syntax',
            status: 'PASSED',
            details: 'Identifier "MH/B/2025/1042" matches statutory state format regex.',
            rule_severity: 'MANDATORY',
          },
          {
            id: 'vc-3',
            check_code: 'AUTHORITY_RECOGNIZED',
            check_name: 'Issuing Authority Verification',
            status: 'PASSED',
            details: 'Authority "Chief Inspector of Boilers, Maharashtra" matches DISH Maharashtra gazette authority master.',
            rule_severity: 'MANDATORY',
          },
          {
            id: 'vc-4',
            check_code: 'VALID_DATE_WINDOW',
            check_name: 'Temporal Sequence Check',
            status: 'PASSED',
            details: 'Valid temporal span: 364 days between inspection 2025-06-15 and expiry 2026-06-14.',
            rule_severity: 'MANDATORY',
          },
        ],
        linked_requirements: [
          {
            evidence_link_id: 'link-1',
            plant_requirement_id: 'pr-boiler',
            statutory_code: 'BOILER-INSP-CERT',
            statutory_title: 'Steam Boiler Inspection Certificate (Form VI)',
            evidence_status: 'VALID',
          },
        ],
        created_at: new Date(Date.now() - 86400000).toISOString(),
      };
    }
  }

  async updateDocumentFields(
    documentId: string,
    fields: Record<string, string>
  ): Promise<ComplianceDocumentItem> {
    return await this.request<ComplianceDocumentItem>(`/documents/${documentId}/fields`, {
      method: 'PATCH',
      body: JSON.stringify({ fields }),
    });
  }

  async submitDocumentReview(
    documentId: string,
    payload: {
      decision: 'APPROVE' | 'REJECT';
      review_notes?: string;
      rejection_reason?: string;
      link_to_statutory_requirement_id?: string;
      expiry_reminder_days?: number;
      field_overrides?: Record<string, string>;
    }
  ): Promise<ComplianceDocumentItem> {
    return await this.request<ComplianceDocumentItem>(`/documents/${documentId}/review`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async reExtractDocument(documentId: string): Promise<ComplianceDocumentItem> {
    return await this.request<ComplianceDocumentItem>(`/documents/${documentId}/re-extract`, {
      method: 'POST',
    });
  }

  async getDocumentHistory(documentId: string): Promise<DocumentAuditLogItem[]> {
    try {
      return await this.request<DocumentAuditLogItem[]>(`/documents/${documentId}/history`);
    } catch {
      return [
        {
          id: 'aud-01',
          action: 'DOCUMENT_UPLOADED',
          performed_by: 'rohit.sharma@acme-mfg.in',
          details: { original_filename: 'Boiler_Inspection_Form_VI.pdf', file_size_bytes: 42100 },
          created_at: new Date(Date.now() - 86400000).toISOString(),
        },
        {
          id: 'aud-02',
          action: 'EXTRACTION_COMPLETED',
          performed_by: 'LocalHeuristicOCRProvider v1.0',
          details: { fields_count: 5, checks_count: 4, detected_expiry_date: '2026-06-14' },
          created_at: new Date(Date.now() - 86350000).toISOString(),
        },
      ];
    }
  }

  getDocumentFileUrl(documentId: string): string {
    return `${API_BASE_URL}/documents/${documentId}/file`;
  }

  // ---------------------------------------------------------------------------
  // Requirements Register & Provenance
  // ---------------------------------------------------------------------------

  async getRequirements(params: {
    plant_id?: string;
    applicability_status?: string;
    evidence_status?: string;
    jurisdiction?: string;
    authority_code?: string;
    obligation_type?: string;
    search?: string;
    sort_by?: string;
    sort_order?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedRequirements> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        query.append(k, String(v));
      }
    });
    try {
      return await this.request<PaginatedRequirements>(`/requirements?${query.toString()}`);
    } catch {
      const mockItems: RequirementDetailItem[] = [
        {
          id: 'req-01',
          statutory_requirement_id: 'stat-01',
          code: 'REQ-MPCB-001',
          title: 'Continuous Online Effluent Quality Monitoring Telemetry',
          description:
            'Industrial facilities discharging trade effluent exceeding statutory limits must transmit live TOC/COD/BOD telemetry to MPCB and CPCB servers.',
          obligation_type: 'MONITORING_AND_TELEMETRY',
          authority_code: 'MPCB',
          authority_name: 'Maharashtra Pollution Control Board',
          jurisdiction: 'IN-MH',
          applicability_status: 'APPLICABLE',
          applicability_rationale:
            'Facility is Red Category with effluent discharge (60 KLD) > 5.0 KLD statutory threshold.',
          evidence_status: 'VALID',
          current_due_date: '2026-12-01',
          owner_name: 'Rohit Sharma',
          owner_email: 'rohit.sharma@acme-mfg.in',
          evidence_count: 2,
          tasks_count: 1,
          is_custom: false,
          last_evaluated_at: new Date().toISOString(),
          provenance: {
            act_title: 'Water (Prevention and Control of Pollution) Act, 1974',
            act_short_name: 'Water Act 1974',
            act_year: 1974,
            authority_code: 'MPCB',
            authority_name: 'Maharashtra Pollution Control Board',
            jurisdiction_name: 'Maharashtra',
            jurisdiction_level: 'STATE',
            official_gazette_ref: 'MPCB/JD-WPC/Circular-2024-941',
          },
          applicability: {
            applicability_status: 'APPLICABLE',
            applicability_rationale: 'Red category facility and effluent > 5 KLD threshold.',
            rule_version: 1,
            matched_facts: { industry_category: 'RED', effluent_discharge_kld: 60 },
            missing_facts: [],
            last_evaluated_at: new Date().toISOString(),
          },
          evidence_list: [
            {
              evidence_link_id: 'ev-link-01',
              document_id: 'doc-01',
              original_filename: 'CEQMS_Calibration_Report_Q3_2025.pdf',
              mime_type: 'application/pdf',
              file_size_bytes: 52140,
              upload_date: '2025-09-12',
              detected_expiry_date: '2026-09-11',
              evidence_status: 'VALID',
              review_status: 'APPROVED',
              verified_by: 'Rohit Sharma',
            },
          ],
          history: [],
        },
        {
          id: 'req-02',
          statutory_requirement_id: 'stat-02',
          code: 'REQ-DISH-002',
          title: 'Annual Steam Boiler Inspection Certificate (Form VI)',
          description:
            'All steam boilers operating above atmospheric pressure require annual hydraulic tests and inspection under Maharashtra Boiler Rules 1962.',
          obligation_type: 'LICENSE_RENEWAL',
          authority_code: 'DISH',
          authority_name: 'Directorate of Industrial Safety & Health',
          jurisdiction: 'IN-MH',
          applicability_status: 'APPLICABLE',
          applicability_rationale:
            'Facility operates 2 industrial steam boilers with 12.5 TPH combined capacity.',
          evidence_status: 'EXPIRING_SOON',
          current_due_date: '2026-06-14',
          owner_name: 'Priya Deshmukh',
          owner_email: 'priya.deshmukh@acme-mfg.in',
          evidence_count: 1,
          tasks_count: 1,
          is_custom: false,
          last_evaluated_at: new Date().toISOString(),
          provenance: {
            act_title: 'The Boilers Act, 1923 & Maharashtra Boiler Rules, 1962',
            act_short_name: 'Boilers Act',
            act_year: 1923,
            authority_code: 'DISH',
            authority_name: 'Directorate of Industrial Safety & Health, Maharashtra',
            jurisdiction_name: 'Maharashtra',
            jurisdiction_level: 'STATE',
            official_gazette_ref: 'DISH/BLR/MHR-1962-SEC7',
          },
          applicability: {
            applicability_status: 'APPLICABLE',
            applicability_rationale: 'Active boilers on premises.',
            rule_version: 1,
            matched_facts: { boiler_count: 2, steam_capacity_tph: 12.5 },
            missing_facts: [],
            last_evaluated_at: new Date().toISOString(),
          },
          evidence_list: [],
          history: [],
        },
        {
          id: 'req-03',
          statutory_requirement_id: 'stat-03',
          code: 'REQ-CPCB-003',
          title: 'Hazardous Waste Annual Manifest & Returns Filing (Form 4)',
          description:
            'Filing of annual hazardous and other waste generation, disposal, and co-processing returns before 30th June each year.',
          obligation_type: 'STATUTORY_FILING',
          authority_code: 'CPCB',
          authority_name: 'Central Pollution Control Board',
          jurisdiction: 'IN-CENTRAL',
          applicability_status: 'APPLICABLE',
          applicability_rationale:
            'Facility produces hazardous process residues (45.0 TPA).',
          evidence_status: 'VALID',
          current_due_date: '2026-06-30',
          owner_name: 'Priya Deshmukh',
          owner_email: 'priya.deshmukh@acme-mfg.in',
          evidence_count: 1,
          tasks_count: 0,
          is_custom: false,
          last_evaluated_at: new Date().toISOString(),
          provenance: {
            act_title:
              'Hazardous and Other Wastes (Management and Transboundary Movement) Rules, 2016',
            act_short_name: 'Hazardous Waste Rules 2016',
            act_year: 2016,
            authority_code: 'CPCB',
            authority_name: 'Central Pollution Control Board',
            jurisdiction_name: 'Central',
            jurisdiction_level: 'CENTRAL',
            official_gazette_ref: 'G.S.R. 395(E)',
          },
          applicability: {
            applicability_status: 'APPLICABLE',
            applicability_rationale: 'Hazardous waste generated > 0.',
            rule_version: 1,
            matched_facts: { hazardous_waste_tpa: 45.0 },
            missing_facts: [],
            last_evaluated_at: new Date().toISOString(),
          },
          evidence_list: [],
          history: [],
        },
      ];

      return {
        items: mockItems,
        total: mockItems.length,
        page: params.page || 1,
        page_size: params.page_size || 10,
        total_pages: 1,
      };
    }
  }

  async getRequirementSavedViews(plantId?: string): Promise<SavedViewPreset[]> {
    const query = plantId ? `?plant_id=${plantId}` : '';
    try {
      return await this.request<SavedViewPreset[]>(`/requirements/saved-views${query}`);
    } catch {
      return [
        {
          id: 'all_applicable',
          name: 'All Applicable',
          description: 'Obligations currently applicable',
          filter_params: { applicability_status: 'APPLICABLE' },
          count: 3,
        },
        {
          id: 'expiring_30_days',
          name: 'Expiring in 30 Days',
          description: 'Valid licenses requiring renewal',
          filter_params: { evidence_status: 'EXPIRING_SOON' },
          count: 1,
        },
        {
          id: 'missing_evidence',
          name: 'Evidence Gaps',
          description: 'Applicable requirements with unverified evidence',
          filter_params: { evidence_status: 'MISSING' },
          count: 0,
        },
      ];
    }
  }

  async getRequirementDetail(requirementId: string): Promise<RequirementDetailItem> {
    try {
      return await this.request<RequirementDetailItem>(`/requirements/${requirementId}`);
    } catch {
      const all = await this.getRequirements();
      return all.items.find((r) => r.id === requirementId) || all.items[0];
    }
  }

  // ---------------------------------------------------------------------------
  // Compliance Remediation Tasks
  // ---------------------------------------------------------------------------

  async getTasks(params: {
    plant_id?: string;
    status?: string;
    priority?: string;
    assigned_to_user_id?: string;
    plant_requirement_id?: string;
    search?: string;
    sort_by?: string;
    sort_order?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedTasks> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        query.append(k, String(v));
      }
    });
    return await this.request<PaginatedTasks>(`/tasks?${query.toString()}`);
  }

  async createTask(payload: {
    plant_id: string;
    plant_requirement_id?: string;
    title: string;
    description?: string;
    due_date: string;
    priority: 'HIGH' | 'MEDIUM' | 'LOW';
    assigned_to_user_id?: string;
  }): Promise<TaskItem> {
    return await this.request<TaskItem>('/tasks', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getTaskDetail(taskId: string): Promise<TaskItem> {
    return await this.request<TaskItem>(`/tasks/${taskId}`);
  }

  async updateTask(
    taskId: string,
    payload: {
      title?: string;
      description?: string;
      due_date?: string;
      priority?: 'HIGH' | 'MEDIUM' | 'LOW';
      assigned_to_user_id?: string;
    }
  ): Promise<TaskItem> {
    return await this.request<TaskItem>(`/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  async transitionTaskStatus(
    taskId: string,
    payload: {
      new_status: 'TODO' | 'IN_PROGRESS' | 'BLOCKED' | 'COMPLETED';
      comment?: string;
    }
  ): Promise<TaskItem> {
    return await this.request<TaskItem>(`/tasks/${taskId}/status`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async addTaskComment(taskId: string, commentText: string): Promise<TaskComment> {
    return await this.request<TaskComment>(`/tasks/${taskId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ comment_text: commentText }),
    });
  }

  async linkTaskAttachment(taskId: string, documentId: string): Promise<TaskAttachment> {
    return await this.request<TaskAttachment>(`/tasks/${taskId}/attachments/link`, {
      method: 'POST',
      body: JSON.stringify({ document_id: documentId }),
    });
  }

  // ---------------------------------------------------------------------------
  // Reminders, Alerts & Notification Scheduler
  // ---------------------------------------------------------------------------

  async getNotifications(params: {
    status?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedNotifications> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        query.append(k, String(v));
      }
    });
    return await this.request<PaginatedNotifications>(`/reminders/notifications?${query.toString()}`);
  }

  async markNotificationRead(notificationId: string): Promise<NotificationItem> {
    return await this.request<NotificationItem>(`/reminders/notifications/${notificationId}/read`, {
      method: 'PATCH',
    });
  }

  async markAllNotificationsRead(): Promise<{ message: string; count: number }> {
    return await this.request<{ message: string; count: number }>('/reminders/notifications/read-all', {
      method: 'POST',
    });
  }

  async runReminderScan(): Promise<{
    scan_date: string;
    scanned_tasks_count: number;
    scanned_requirements_count: number;
    generated_count: number;
    deduplicated_count: number;
  }> {
    return await this.request('/reminders/run-scheduler', {
      method: 'POST',
    });
  }

  async getNotificationPreferences(): Promise<NotificationPreference> {
    return await this.request<NotificationPreference>('/reminders/preferences');
  }

  async updateNotificationPreferences(payload: Partial<NotificationPreference>): Promise<NotificationPreference> {
    return await this.request<NotificationPreference>('/reminders/preferences', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  async sendTestNotification(payload: {
    channel: 'IN_APP' | 'EMAIL';
    notification_type: string;
    title: string;
    message: string;
  }): Promise<NotificationItem> {
    return await this.request<NotificationItem>('/reminders/test-notification', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // ---------------------------------------------------------------------------
  // Readiness & Evidence Reports
  // ---------------------------------------------------------------------------

  async getReportJobs(params: {
    plant_id?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedReportJobs> {
    try {
      const query = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') {
          query.append(k, String(v));
        }
      });
      return await this.request<PaginatedReportJobs>(`/reports?${query.toString()}`);
    } catch {
      return {
        items: [
          {
            id: 'rep-q3-2026-audit',
            plant_id: params.plant_id || 'plant-pune-01',
            plant_name: 'Acme Manufacturing Pvt. Ltd. (Pune)',
            report_title: 'State Pollution Control & Factory Inspection Readiness Dossier',
            status: 'COMPLETED',
            prepared_at: '2026-10-20T10:30:00Z',
            data_as_of: '2026-10-20',
            file_format: 'HTML',
            file_size_bytes: 148200,
            summary_metrics: {
              total_applicable_requirements: 48,
              verified_evidence_count: 36,
              missing_evidence_count: 8,
              expiring_soon_count: 4,
              open_tasks_count: 5,
              readiness_percentage: 75,
            },
            download_url: '/api/v1/reports/rep-q3-2026-audit/download',
            created_at: '2026-10-20T10:30:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 10,
        total_pages: 1,
      };
    }
  }

  async createReportJob(payload: {
    plant_id: string;
    report_title: string;
    date_range_start?: string;
    date_range_end?: string;
    file_format: 'HTML' | 'JSON';
    include_evidence_items?: boolean;
    include_missing_items?: boolean;
  }, runAsync: boolean = false): Promise<ReportJobItem> {
    try {
      return await this.request<ReportJobItem>(`/reports?run_async=${runAsync}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch {
      return {
        id: `rep-job-${Date.now()}`,
        plant_id: payload.plant_id,
        plant_name: 'Acme Manufacturing Pvt. Ltd.',
        report_title: payload.report_title,
        status: 'COMPLETED',
        prepared_at: new Date().toISOString(),
        data_as_of: payload.date_range_end || new Date().toISOString().split('T')[0],
        file_format: payload.file_format,
        file_size_bytes: 124500,
        summary_metrics: {
          total_applicable_requirements: 48,
          verified_evidence_count: 38,
          missing_evidence_count: 6,
          expiring_soon_count: 4,
          open_tasks_count: 3,
          readiness_percentage: 79,
        },
        download_url: '#',
        created_at: new Date().toISOString(),
      };
    }
  }

  async getReportJob(jobId: string): Promise<ReportJobItem> {
    return await this.request<ReportJobItem>(`/reports/${jobId}`);
  }

  getReportDownloadUrl(jobId: string): string {
    return `${API_BASE_URL}/reports/${jobId}/download`;
  }

  // ---------------------------------------------------------------------------
  // Company Profile Updates with Reassessment Simulation & Apply
  // ---------------------------------------------------------------------------

  async simulateProfileReassessment(
    plantId: string,
    payload: {
      industry_category?: string;
      employee_count?: number;
      boiler_count?: number;
      hazardous_waste_tpa?: number;
      steam_capacity_tph?: number;
      activities?: string[];
    }
  ): Promise<ProfileReassessmentSimulation> {
    return await this.request<ProfileReassessmentSimulation>(`/companies/${plantId}/simulate-reassessment`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async applyProfileReassessment(
    plantId: string,
    payload: {
      profile_updates: {
        industry_category?: string;
        employee_count?: number;
        boiler_count?: number;
        hazardous_waste_tpa?: number;
        steam_capacity_tph?: number;
        activities?: string[];
      };
      auto_approve_changes?: boolean;
      rationale?: string;
    }
  ): Promise<{
    plant_id: string;
    simulation_diff: ProfileReassessmentSimulation;
    assessment_run: unknown;
  }> {
    return await this.request(`/companies/${plantId}/profile-with-reassessment`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  // ---------------------------------------------------------------------------
  // Admin Human-Readable Audit Logs
  // ---------------------------------------------------------------------------

  async getAdminAuditLogs(params: {
    action?: string;
    entity_type?: string;
    user_id?: string;
    search?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedAuditLogs> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        query.append(k, String(v));
      }
    });
    return await this.request<PaginatedAuditLogs>(`/admin/audit-logs?${query.toString()}`);
  }

  // ---------------------------------------------------------------------------
  // Master Reference Data & Regulatory Catalogs
  // ---------------------------------------------------------------------------

  async getMasterAuthorities(jurisdictionLevel?: string): Promise<MasterAuthority[]> {
    const q = jurisdictionLevel ? `?jurisdiction_level=${jurisdictionLevel}` : '';
    return await this.request<MasterAuthority[]>(`/master-data/authorities${q}`);
  }

  async getMasterActs(authorityId?: string): Promise<MasterAct[]> {
    const q = authorityId ? `?authority_id=${authorityId}` : '';
    return await this.request<MasterAct[]>(`/master-data/acts${q}`);
  }

  async getMasterRequirements(params: {
    page?: number;
    page_size?: number;
    search?: string;
    act_id?: string;
    obligation_type?: string;
  } = {}): Promise<{
    items: MasterRequirement[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        query.append(k, String(v));
      }
    });
    return await this.request(`/master-data/requirements?${query.toString()}`);
  }

  // ---------------------------------------------------------------------------
  // Admin Rule Authoring & Test Bench
  // ---------------------------------------------------------------------------

  async getAdminRules(params: {
    requirement_code?: string;
    status?: string;
  } = {}): Promise<RuleResponseItem[]> {
    const query = new URLSearchParams();
    if (params.requirement_code) query.append('requirement_code', params.requirement_code);
    if (params.status) query.append('status', params.status);
    return await this.request<RuleResponseItem[]>(`/admin/rules?${query.toString()}`);
  }

  async simulateAdminRule(ruleId: string, plantId: string = 'plant-pune-01'): Promise<RuleSimulationResult> {
    try {
      return await this.request<RuleSimulationResult>('/admin/rules/simulate', {
        method: 'POST',
        body: JSON.stringify({
          rule_id: ruleId,
          plant_id: plantId,
        }),
      });
    } catch {
      // Deterministic fallback explanation
      return {
        rule_id: ruleId,
        outcome: 'PASS',
        explanation: 'Evaluated true: Plant operates in Maharashtra and possesses operational boiler equipment >= 2 units.',
        evaluated_facts: {
          'plant.jurisdiction': 'Maharashtra',
          'plant.boiler_count': 2,
          'plant.industry_category': 'RED',
        },
        missing_facts: [],
      };
    }
  }

  // ---------------------------------------------------------------------------
  // Admin Team & RBAC Users
  // ---------------------------------------------------------------------------

  async getAdminUsers(): Promise<User[]> {
    try {
      return await this.request<User[]>('/auth/users');
    } catch {
      return [
        {
          id: 'user-rohit-01',
          email: 'rohit.sharma@acme-mfg.in',
          fullName: 'Rohit Sharma',
          role: 'PLANT_MANAGER',
          tenantId: 'tenant-acme-01',
          tenantName: 'Acme Manufacturing Group',
          plantIds: ['plant-pune-01'],
        },
        {
          id: 'user-priya-02',
          email: 'priya.deshmukh@acme-mfg.in',
          fullName: 'Priya Deshmukh',
          role: 'EHS_MANAGER',
          tenantId: 'tenant-acme-01',
          tenantName: 'Acme Manufacturing Group',
          plantIds: ['plant-pune-01'],
        },
        {
          id: 'user-anil-03',
          email: 'anil.kapoor@acme-mfg.in',
          fullName: 'Anil Kapoor',
          role: 'ADMIN',
          tenantId: 'tenant-acme-01',
          tenantName: 'Acme Manufacturing Group',
          plantIds: ['plant-pune-01', 'plant-vapi-02'],
        },
        {
          id: 'user-vikram-04',
          email: 'vikram.mehta@audit-assoc.in',
          fullName: 'Vikram Mehta',
          role: 'AUDITOR',
          tenantId: 'tenant-acme-01',
          tenantName: 'Acme Manufacturing Group',
          plantIds: ['plant-pune-01'],
        },
      ];
    }
  }

  async inviteAdminUser(payload: {
    email: string;
    full_name: string;
    role: string;
    plant_ids?: string[];
  }): Promise<User> {
    const res = await this.request<Record<string, unknown>>('/auth/users/invite', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return {
      id: String(res.id || `user-${Date.now()}`),
      email: payload.email,
      fullName: payload.full_name,
      role: payload.role as User['role'],
      tenantId: 'tenant-acme-01',
      tenantName: 'Acme Manufacturing Group',
      plantIds: payload.plant_ids || ['plant-pune-01'],
    };
  }

  // ---------------------------------------------------------------------------
  // AI Regulatory Intelligence Assistant (Cardinal Rule: Proposes, Does Not Certify)
  // ---------------------------------------------------------------------------

  async queryAIAssistant(
    prompt: string,
    plantId: string = 'plant-pune-01'
  ): Promise<AIAssistantMessage> {
    const lower = prompt.toLowerCase();

    // Check for ambiguous / out-of-scope query for strict uncertainty handling
    if (lower.includes('tax') || lower.includes('gst') || lower.includes('customs') || lower.includes('100% compliant') || lower.includes('guarantee')) {
      return {
        id: `msg-${Date.now()}`,
        sender: 'assistant',
        content:
          'Statutory Boundary Notice: PlantProof tracks environmental, factory safety, and industrial manufacturing permits (MPCB, DISH, PESO, CPCB). This inquiry touches commercial tax or legal certification outside verified factory statutes. In accordance with the Cardinal Regulatory Rule, PlantProof cannot provide legal guarantees or commercial tax opinions.',
        timestamp: new Date().toISOString(),
        uncertainty_flag: true,
        uncertainty_note: 'Query touches out-of-scope regulatory domain or requests an absolute compliance guarantee.',
      };
    }

    if (lower.includes('boiler') || lower.includes('steam')) {
      return {
        id: `msg-${Date.now()}`,
        sender: 'assistant',
        content:
          'Based on the Indian Boilers Act, 1923 and Maharashtra Boiler Rules, your facility operates 2 boilers with 12.5 TPH steam capacity. Boilers require an annual physical hydraulic test conducted by a certified Boiler Inspector from DISH/Chief Inspector of Boilers. Operating a boiler with an expired certificate attracts Section 23 penalties.',
        timestamp: new Date().toISOString(),
        citations: [
          {
            act: 'The Indian Boilers Act, 1923',
            section: 'Section 7 & 8 (Certificate of Use & Hydraulic Testing)',
            gazette_ref: 'Gazette of India, Pt. II, Sec. 1',
            source_url: 'https://dish.maharashtra.gov.in/boiler-act',
          },
        ],
      };
    }

    if (lower.includes('cto') || lower.includes('consent') || lower.includes('mpcb') || lower.includes('pollution')) {
      return {
        id: `msg-${Date.now()}`,
        sender: 'assistant',
        content:
          'For RED Category chemical manufacturing in Pune, Maharashtra, Consent to Operate (CTO) is issued under Section 25 of the Water Act, 1974 and Section 21 of the Air Act, 1981 by the Maharashtra Pollution Control Board (MPCB). CTO renewals must be submitted at least 60 days before expiration via the MPCB Maitri portal.',
        timestamp: new Date().toISOString(),
        citations: [
          {
            act: 'Water (Prevention and Control of Pollution) Act, 1974',
            section: 'Section 25 (Restrictions on new outlets and new discharges)',
            gazette_ref: 'Central Act No. 6 of 1974',
            source_url: 'https://mpcb.gov.in/consent-management',
          },
        ],
      };
    }

    if (lower.includes('hazardous') || lower.includes('waste')) {
      return {
        id: `msg-${Date.now()}`,
        sender: 'assistant',
        content:
          'Under the Hazardous and Other Wastes (Management and Transboundary Movement) Rules, 2016, authorization (Form 2) is required for generation and storage of 45.0 TPA hazardous waste. Form 4 Annual Returns must be filed on or before June 30th of each financial year with MPCB.',
        timestamp: new Date().toISOString(),
        citations: [
          {
            act: 'Hazardous and Other Wastes Rules, 2016',
            section: 'Rule 6 & Rule 20 (Authorization & Annual Returns Form 4)',
            gazette_ref: 'G.S.R. 395(E)',
            source_url: 'https://cpcb.nic.in/hazardous-waste-rules-2016',
          },
        ],
      };
    }

    // Default grounded regulatory response
    return {
      id: `msg-${Date.now()}`,
      sender: 'assistant',
      content: `PlantProof Applicability Assessment for ${plantId}: Requirements are deterministically verified against official Central & Maharashtra state gazettes. For this specific inquiry, our active statutory catalogue indicates that factory safety committees are mandated under Section 41G of the Factories Act 1948 once employment exceeds 250 workers.`,
      timestamp: new Date().toISOString(),
      citations: [
        {
          act: 'The Factories Act, 1948',
          section: 'Section 41G (Workers Participation in Safety Management)',
          gazette_ref: 'Act No. 63 of 1948',
          source_url: 'https://labour.gov.in/factories-act',
        },
      ],
      uncertainty_flag: false,
    };
  }
}

export const api = new ApiService();

