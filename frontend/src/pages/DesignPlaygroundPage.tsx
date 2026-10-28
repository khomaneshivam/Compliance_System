import React, { useState } from 'react';
import {
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Shield,
  FileText,
  Search,
  Lock,
} from 'lucide-react';
import { DashboardPage } from './DashboardPage';
import { RequirementsPage } from './RequirementsPage';
import { DocumentReviewPage } from './DocumentReviewPage';
import { RegulatoryChangeDetailPage } from './RegulatoryChangeDetailPage';
import { api } from '../services/api';

export const DesignPlaygroundPage: React.FC = () => {
  const [selectedScreen, setSelectedScreen] = useState<string>('screen-03');
  const [wizardStep, setWizardStep] = useState(1);
  const [globalState, setGlobalState] = useState<'normal' | 'loading' | 'empty' | 'error' | 'forbidden'>('normal');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Playground Control Header */}
      <div
        className="card"
        style={{
          padding: '16px 20px',
          backgroundColor: '#0f172a',
          color: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Sparkles size={20} color="#34d399" />
          <div>
            <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>
              PlantProof Screen Specification & Design Playground
            </h2>
            <p style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
              Interactive test bench previewing all 18 application screens, dual-pane workflows, and global states.
            </p>
          </div>
        </div>

        {/* Screen Picker */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Active Screen:</span>
          <select
            className="form-select"
            style={{ width: '280px', backgroundColor: '#1e293b', color: '#ffffff', borderColor: '#334155' }}
            value={selectedScreen}
            onChange={(e) => {
              setSelectedScreen(e.target.value);
              setGlobalState('normal');
            }}
          >
            <optgroup label="Authentication & Setup">
              <option value="screen-01">01. Sign In / Reset / Invite Acceptance</option>
              <option value="screen-02">02. First-Run Company Setup Wizard</option>
            </optgroup>
            <optgroup label="Core Factory Operations">
              <option value="screen-03">03. Executive Dashboard</option>
              <option value="screen-04">04. Master Requirements Register</option>
              <option value="screen-07">07. Dual-Pane Document Review Workspace</option>
              <option value="screen-09">09. Regulatory Change Detail & Legal Diff</option>
              <option value="screen-11">11. Remediation Tasks & Deadlines</option>
              <option value="screen-12">12. Audit Readiness Report Builder</option>
              <option value="screen-13">13. Company Operational Profile</option>
            </optgroup>
            <optgroup label="Admin & Governance">
              <option value="screen-14">14. Master Data Administration</option>
              <option value="screen-15">15. Rule Authoring & Test Bench</option>
              <option value="screen-16">16. Users, Roles & Permissions</option>
              <option value="screen-17">17. Compliance Intelligence Search</option>
            </optgroup>
            <optgroup label="Resilience & System States">
              <option value="screen-18">18. Global Application States (Skeleton, Empty, Error)</option>
            </optgroup>
          </select>
        </div>
      </div>

      {/* RENDER SCREEN SELECTED */}

      {/* Screen 01: Sign In Preview */}
      {selectedScreen === 'screen-01' && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '40px 0' }}>
          <div className="card" style={{ width: '420px', maxWidth: '100%', padding: '32px' }}>
            <div style={{ textAlign: 'center', marginBottom: '24px' }}>
              <div style={{ display: 'inline-flex', padding: '8px', borderRadius: '8px', backgroundColor: '#ecfdf5', color: '#059669', marginBottom: '8px' }}>
                <Shield size={24} />
              </div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>Sign In to PlantProof</h2>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Enterprise regulatory compliance for manufacturing</p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)', display: 'block', marginBottom: '4px' }}>Work Email</label>
                <input type="email" className="form-input" defaultValue="rohit.sharma@acme-mfg.in" />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)' }}>Password</label>
                  <span style={{ fontSize: '0.75rem', color: 'var(--brand-primary)', cursor: 'pointer' }}>Forgot password?</span>
                </div>
                <input type="password" className="form-input" defaultValue="DemoPass123!" />
              </div>

              <button className="btn-primary" style={{ justifyContent: 'center', marginTop: '6px' }}>
                <span>Sign In to PlantProof</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Screen 02: Setup Wizard */}
      {selectedScreen === 'screen-02' && (
        <div className="card" style={{ maxWidth: '800px', margin: '0 auto', padding: '28px' }}>
          {/* Stepper Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '28px', borderBottom: '1px solid var(--border-default)', paddingBottom: '16px' }}>
            {['1. Legal Entity', '2. Sites & Location', '3. Category & Sector', '4. Operational Facts', '5. Confirm'].map((step, idx) => (
              <span
                key={step}
                style={{
                  fontSize: '0.82rem',
                  fontWeight: wizardStep === idx + 1 ? 700 : 500,
                  color: wizardStep === idx + 1 ? 'var(--brand-primary)' : 'var(--text-muted)',
                  borderBottom: wizardStep === idx + 1 ? '2px solid var(--brand-primary)' : 'none',
                  paddingBottom: '4px',
                  cursor: 'pointer',
                }}
                onClick={() => setWizardStep(idx + 1)}
              >
                {step}
              </span>
            ))}
          </div>

          {/* Wizard Step Body */}
          {wizardStep === 1 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Step 1: Legal Entity & Jurisdiction</h3>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 500 }}>Registered Corporate Name</label>
                <input type="text" className="form-input" defaultValue="Acme Manufacturing Pvt. Ltd." />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 500 }}>Primary State Jurisdiction</label>
                <select className="form-select" defaultValue="Maharashtra">
                  <option value="Maharashtra">Maharashtra (MPCB & DISH)</option>
                  <option value="Gujarat">Gujarat (GPCB)</option>
                  <option value="Central">Central / National Only</option>
                </select>
              </div>
            </div>
          )}

          {wizardStep === 2 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Step 2: Manufacturing Sites</h3>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 500 }}>Primary Facility Name</label>
                <input type="text" className="form-input" defaultValue="Pune Facility Unit 1" />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 500 }}>District</label>
                  <input type="text" className="form-input" defaultValue="Pune" />
                </div>
                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 500 }}>MIDC / Industrial Zone</label>
                  <input type="text" className="form-input" defaultValue="Chakan Phase II" />
                </div>
              </div>
            </div>
          )}

          {wizardStep >= 3 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Step {wizardStep}: Process Facts & Capacities</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 500 }}>Steam Boiler Capacity (TPH)</label>
                  <input type="number" className="form-input" defaultValue={4.5} />
                </div>
                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 500 }}>Hazardous Waste Generated (TPA)</label>
                  <input type="number" className="form-input" defaultValue={18.5} />
                </div>
                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 500 }}>Connected Electricity Load (kW)</label>
                  <input type="number" className="form-input" defaultValue={1200} />
                </div>
                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 500 }}>Total Workers on Site</label>
                  <input type="number" className="form-input" defaultValue={200} />
                </div>
              </div>
            </div>
          )}

          {/* Stepper Buttons */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '28px', borderTop: '1px solid var(--border-default)', paddingTop: '16px' }}>
            <button className="btn-secondary" disabled={wizardStep === 1} onClick={() => setWizardStep(wizardStep - 1)}>
              Back
            </button>
            <button className="btn-primary" onClick={() => setWizardStep(Math.min(5, wizardStep + 1))}>
              {wizardStep === 5 ? 'Finish & Generate Register' : 'Continue'}
            </button>
          </div>
        </div>
      )}

      {/* Screen 03: Executive Dashboard */}
      {selectedScreen === 'screen-03' && <DashboardPage summary={api.getDashboardSummary()} />}

      {/* Screen 04: Requirements Register */}
      {selectedScreen === 'screen-04' && <RequirementsPage />}

      {/* Screen 07: Document Review Workspace */}
      {selectedScreen === 'screen-07' && <DocumentReviewPage />}

      {/* Screen 09: Regulatory Change Detail */}
      {selectedScreen === 'screen-09' && <RegulatoryChangeDetailPage />}

      {/* Screen 11: Remediation Tasks */}
      {selectedScreen === 'screen-11' && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Compliance Remediation Tasks</h2>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Track renewal filings, sampling reports, and corrective actions</p>
            </div>
            <button className="btn-primary">+ Create Task</button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {[
              { title: 'Submit MPCB Annual Hazardous Waste Return (Form 4)', due: '30 Jun 2026', prio: 'HIGH', status: 'IN_PROGRESS', assignee: 'Priya Deshmukh' },
              { title: 'Renew Maharashtra Factory Licence under Section 6', due: '28 Oct 2025', prio: 'HIGH', status: 'TODO', assignee: 'Amit Jadhav' },
              { title: 'Conduct Annual Boiler Hydraulic Test (BLR-01)', due: '15 May 2026', prio: 'MEDIUM', status: 'TODO', assignee: 'Rohit Sharma' },
              { title: 'Update ETP Effluent Discharge Online Monitoring Log', due: '05 Nov 2025', prio: 'MEDIUM', status: 'COMPLETED', assignee: 'Priya Deshmukh' },
            ].map((task) => (
              <div key={task.title} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', border: '1px solid var(--border-default)', borderRadius: '6px' }}>
                <div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>{task.title}</div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Assigned to: {task.assignee} &bull; Target: {task.due}</div>
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span className={`badge ${task.prio === 'HIGH' ? 'badge-danger' : 'badge-warning'}`}>{task.prio} Priority</span>
                  <span className={`badge ${task.status === 'COMPLETED' ? 'badge-valid' : 'badge-neutral'}`}>{task.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Screen 12: Audit Readiness Report Builder */}
      {selectedScreen === 'screen-12' && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Audit & Readiness Report Builder</h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Generate traceable compliance dossiers with verified evidence attachments</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '14px' }}>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Scope</label>
              <select className="form-select" defaultValue="pune"><option value="pune">Acme Manufacturing - Pune Unit</option></select>
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Category</label>
              <select className="form-select" defaultValue="all"><option value="all">All Statutory Obligations (48)</option><option value="env">Environmental (MPCB/MoEFCC)</option></select>
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Reporting Period</label>
              <select className="form-select" defaultValue="current"><option value="current">Current Active FY (2025-2026)</option></select>
            </div>
          </div>

          <div style={{ padding: '16px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border-default)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--brand-primary)' }}>75% Readiness Score</div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>36 of 48 applicable requirements verified with active certificates</div>
            </div>
            <button className="btn-primary">
              <FileText size={16} />
              <span>Export Audit Dossier (PDF)</span>
            </button>
          </div>
        </div>
      )}

      {/* Screen 13: Company Operational Profile */}
      {selectedScreen === 'screen-13' && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Plant Operational Profile & Master Facts</h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>These factual parameters feed the deterministic applicability rules engine</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px' }}>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Facility Code</label>
              <input type="text" className="form-input" disabled defaultValue="MH-PUN-01" />
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>CPCB Pollution Category</label>
              <input type="text" className="form-input" defaultValue="RED (Heavy Industrial / Chemical)" />
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Steam Boiler Capacity (TPH)</label>
              <input type="number" className="form-input" defaultValue={4.5} />
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Hazardous Waste Output (TPA)</label>
              <input type="number" className="form-input" defaultValue={18.5} />
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Direct Workforce Count</label>
              <input type="number" className="form-input" defaultValue={150} />
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Contract Labour Headcount</label>
              <input type="number" className="form-input" defaultValue={50} />
            </div>
          </div>

          <div style={{ marginTop: '10px' }}>
            <button className="btn-primary" onClick={() => alert('Profile updated. Deterministic applicability engine re-evaluated 48 statutory rules.')}>
              Save Changes & Re-evaluate Applicability
            </button>
          </div>
        </div>
      )}

      {/* Screen 14 & 15: Admin Rule Bench */}
      {(selectedScreen === 'screen-14' || selectedScreen === 'screen-15') && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Deterministic Rule Authoring & Test Bench</h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>AST boolean tree evaluator (zero arbitrary executable code)</p>
          </div>

          <div style={{ backgroundColor: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-default)', fontFamily: 'monospace', fontSize: '0.85rem' }}>
            <div style={{ color: '#059669', fontWeight: 600 }}>RULE-BOILER-001 (Section 7, Indian Boilers Act, 1923)</div>
            <pre style={{ marginTop: '8px', color: '#1e293b' }}>
{`{
  "and": [
    { "==": ["plant.jurisdiction", "Maharashtra"] },
    { ">": ["plant.steam_capacity_tph", 0] }
  ]
}`}
            </pre>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', backgroundColor: '#ecfdf5', borderRadius: '6px', border: '1px solid #a7f3d0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#065f46', fontSize: '0.85rem', fontWeight: 600 }}>
              <CheckCircle2 size={16} />
              <span>Simulation Result against Acme Manufacturing (Pune): PASS (Requirement APPLICABLE)</span>
            </div>
            <button className="btn-secondary" style={{ padding: '4px 10px', fontSize: '0.78rem' }}>Run Test Bench</button>
          </div>
        </div>
      )}

      {/* Screen 16: Users & Roles */}
      {selectedScreen === 'screen-16' && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Users & Access Control</h2>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Manage roles, facility permissions, and audit privileges</p>
            </div>
            <button className="btn-primary">+ Invite User</button>
          </div>

          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Plant Scope</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Rohit Sharma</strong></td>
                  <td>rohit.sharma@acme-mfg.in</td>
                  <td><span className="badge badge-info">Plant Manager</span></td>
                  <td>All Plants (Pune)</td>
                  <td><span className="badge badge-valid">Active</span></td>
                </tr>
                <tr>
                  <td><strong>Priya Deshmukh</strong></td>
                  <td>priya.deshmukh@acme-mfg.in</td>
                  <td><span className="badge badge-valid">EHS Manager</span></td>
                  <td>Pune Unit 1</td>
                  <td><span className="badge badge-valid">Active</span></td>
                </tr>
                <tr>
                  <td><strong>Amit Jadhav</strong></td>
                  <td>amit.jadhav@acme-mfg.in</td>
                  <td><span className="badge badge-warning">Admin</span></td>
                  <td>All Plants</td>
                  <td><span className="badge badge-valid">Active</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Screen 17: Compliance Intelligence Search */}
      {selectedScreen === 'screen-17' && (
        <div className="card" style={{ maxWidth: '640px', margin: '0 auto', padding: '24px' }}>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '6px' }}>Compliance Intelligence Search</h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
            Ask questions grounded strictly in authorized statutory gazettes and your verified evidence vault
          </p>

          <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
            <input type="text" className="form-input" defaultValue="What is our boiler inspection renewal grace period?" />
            <button className="btn-primary"><Search size={14} /> Search</button>
          </div>

          <div style={{ backgroundColor: '#f8fafc', border: '1px solid var(--border-default)', borderRadius: '8px', padding: '16px', fontSize: '0.85rem', lineHeight: 1.5 }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>Grounded Answer:</div>
            <p style={{ color: 'var(--text-secondary)' }}>
              Under Section 7 of the Indian Boilers Act, 1923 and Maharashtra Boiler Rules, the renewal inspection certificate must be obtained prior to the expiration date (<strong>14 June 2026</strong>). A 30-day provisional operating extension may be granted upon submission of Form B inspection fees.
            </p>
            <div style={{ marginTop: '10px', fontSize: '0.75rem', color: 'var(--brand-primary)', fontWeight: 600 }}>
              Source: Indian Boilers Act, 1923 &bull; Inspection Certificate MH/B/2025/1042
            </div>
          </div>
        </div>
      )}

      {/* Screen 18: Global Application States */}
      {selectedScreen === 'screen-18' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Sub-State Picker */}
          <div style={{ display: 'flex', gap: '10px' }}>
            {(['loading', 'empty', 'error', 'forbidden'] as const).map((st) => (
              <button
                key={st}
                className={globalState === st ? 'btn-primary' : 'btn-secondary'}
                onClick={() => setGlobalState(st)}
                style={{ textTransform: 'capitalize' }}
              >
                {st} State
              </button>
            ))}
          </div>

          {/* Skeleton Loading State Preview */}
          {globalState === 'loading' && (
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div className="skeleton" style={{ height: '24px', width: '40%' }} />
              <div className="skeleton" style={{ height: '14px', width: '60%' }} />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '14px', marginTop: '10px' }}>
                <div className="skeleton" style={{ height: '80px' }} />
                <div className="skeleton" style={{ height: '80px' }} />
                <div className="skeleton" style={{ height: '80px' }} />
              </div>
            </div>
          )}

          {/* Actionable Empty State */}
          {globalState === 'empty' && (
            <div className="card" style={{ padding: '48px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '48px', height: '48px', borderRadius: '50%', backgroundColor: '#f1f5f9', color: '#64748b', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Search size={24} />
              </div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)' }}>No matching records found</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: '400px' }}>
                No compliance requirements match your active filter criteria. Try adjusting your jurisdiction or status filters.
              </p>
              <button className="btn-secondary" style={{ marginTop: '6px' }} onClick={() => setGlobalState('normal')}>
                Clear Filters
              </button>
            </div>
          )}

          {/* Error Banner */}
          {globalState === 'error' && (
            <div className="card" style={{ borderLeft: '4px solid #dc2626', backgroundColor: '#fef2f2', display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <AlertCircle size={20} color="#dc2626" style={{ marginTop: '2px', flexShrink: 0 }} />
              <div>
                <h4 style={{ fontSize: '0.92rem', fontWeight: 600, color: '#991b1b' }}>Unable to synchronize with MPCB portal</h4>
                <p style={{ fontSize: '0.85rem', color: '#7f1d1d', marginTop: '2px' }}>
                  The government notice server is currently undergoing scheduled maintenance. Your local register remains cached and fully functional.
                </p>
                <button className="btn-secondary" style={{ marginTop: '10px', fontSize: '0.78rem' }}>
                  Retry Connection
                </button>
              </div>
            </div>
          )}

          {/* Permission Denied (HTTP 403) */}
          {globalState === 'forbidden' && (
            <div className="card" style={{ padding: '48px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '48px', height: '48px', borderRadius: '50%', backgroundColor: '#fef2f2', color: '#dc2626', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Lock size={24} />
              </div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)' }}>Access Restricted (Role: Viewer)</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: '420px' }}>
                You have read-only auditor access. Modifying plant operational profiles or approving compliance documents requires <strong>EHS Manager</strong> or <strong>Plant Manager</strong> authorization.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
