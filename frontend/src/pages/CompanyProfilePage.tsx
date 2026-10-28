import React, { useState, useEffect } from 'react';
import {
  Building2,
  GitCompare,
  AlertTriangle,
  ShieldCheck,
  ArrowRight,
  Flame,
  Users,
  Factory,
  Save,
} from 'lucide-react';
import { api } from '../services/api';
import type { ProfileReassessmentSimulation, PlantProfile } from '../types';

export const CompanyProfilePage: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [profile, setProfile] = useState<PlantProfile | null>(null);

  // Editable Profile Form State
  const [industryCategory, setIndustryCategory] = useState<string>('RED');
  const [employeeCount, setEmployeeCount] = useState<number>(250);
  const [boilerCount, setBoilerCount] = useState<number>(2);
  const [steamCapacity, setSteamCapacity] = useState<number>(15.0);
  const [hazardousWasteTpa, setHazardousWasteTpa] = useState<number>(45.0);
  const [activities, setActivities] = useState<string[]>([
    'chemical_manufacturing',
    'hazardous_waste_storage',
    'boiler_operation',
    'etp_discharge',
  ]);

  // Simulation State
  const [simulating, setSimulating] = useState<boolean>(false);
  const [simulationResult, setSimulationResult] = useState<ProfileReassessmentSimulation | null>(null);

  // Apply State
  const [applying, setApplying] = useState<boolean>(false);
  const [rationale, setRationale] = useState<string>('Capacity expansion and annual regulatory fact update.');
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    // Load initial profile
    const loadProfile = async () => {
      setLoading(true);
      try {
        const data = await api.getPlantProfile('plant-pune-01');
        setProfile(data);
        if (data) {
          setIndustryCategory(data.industryCategory || 'RED');
          setEmployeeCount(data.employeeCount ?? 250);
          setBoilerCount(data.boilerCount ?? 2);
          setSteamCapacity(data.steamCapacityTph ?? 15.0);
          setHazardousWasteTpa(data.hazardousWasteTpa ?? 45.0);
          if (data.activities && data.activities.length > 0) {
            setActivities(data.activities);
          }
        }
      } catch (err: unknown) {
        console.error('Failed to load profile', err);
      } finally {
        setLoading(false);
      }
    };
    loadProfile();
  }, []);

  const handleSimulate = async () => {
    setSimulating(true);
    setFeedback(null);
    try {
      const sim = await api.simulateProfileReassessment('plant-pune-01', {
        industry_category: industryCategory,
        employee_count: Number(employeeCount),
        boiler_count: Number(boilerCount),
        steam_capacity_tph: Number(steamCapacity),
        hazardous_waste_tpa: Number(hazardousWasteTpa),
        activities,
      });
      setSimulationResult(sim);
      if (sim.attribute_changes.length === 0) {
        setFeedback({
          type: 'success',
          message: 'No attribute modifications detected relative to current active baseline.',
        });
      }
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        message: (err as Error).message || 'Failed to simulate regulatory reassessment.',
      });
    } finally {
      setSimulating(false);
    }
  };

  const handleApply = async () => {
    if (!simulationResult) return;
    const confirmed = window.confirm(
      'Are you sure you want to apply these operational master-data changes and trigger a formal compliance reassessment for this facility?'
    );
    if (!confirmed) return;

    setApplying(true);
    setFeedback(null);
    try {
      const res = await api.applyProfileReassessment('plant-pune-01', {
        profile_updates: {
          industry_category: industryCategory,
          employee_count: Number(employeeCount),
          boiler_count: Number(boilerCount),
          steam_capacity_tph: Number(steamCapacity),
          hazardous_waste_tpa: Number(hazardousWasteTpa),
          activities,
        },
        auto_approve_changes: true,
        rationale,
      });

      setFeedback({
        type: 'success',
        message: `Profile updated and reassessment completed successfully! ${res.simulation_diff.newly_applicable_count} new requirement(s) added to register.`,
      });
      setSimulationResult(null);

      // Refresh baseline
      const updated = await api.getPlantProfile('plant-pune-01');
      setProfile(updated);
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        message: (err as Error).message || 'Failed to apply profile reassessment.',
      });
    } finally {
      setApplying(false);
    }
  };

  const toggleActivity = (act: string) => {
    setActivities((prev) =>
      prev.includes(act) ? prev.filter((a) => a !== act) : [...prev, act]
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
              <Building2 size={18} />
            </div>
            <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
              Company & Facility Profile
            </h1>
          </div>
          <p style={{ color: '#64748b', fontSize: '13px', margin: 0 }}>
            Operational master data governing statutory applicability. Test prospective changes and preview "What Changed" diffs before committing to your legal register.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleSimulate}
            className="btn btn-secondary"
            disabled={simulating || loading}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <GitCompare size={15} className={simulating ? 'spin-slow' : ''} />
            <span>{simulating ? 'Simulating...' : 'Simulate Reassessment'}</span>
          </button>
          <button
            onClick={handleApply}
            className="btn btn-primary"
            disabled={applying || !simulationResult || simulationResult.attribute_changes.length === 0}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#059669',
              borderColor: '#059669',
            }}
            title={
              !simulationResult
                ? 'Run simulation first to review changes'
                : 'Commit changes and update compliance register'
            }
          >
            <Save size={15} />
            <span>Apply & Update Register</span>
          </button>
        </div>
      </div>

      {/* Tenet Banner */}
      <div
        style={{
          backgroundColor: '#f8fafc',
          border: '1px solid #cbd5e1',
          borderLeft: '4px solid #059669',
          borderRadius: '8px',
          padding: '14px 18px',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
        }}
      >
        <ShieldCheck size={20} color="#059669" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '12.5px', color: '#334155', lineHeight: '1.55' }}>
          <strong style={{ color: '#0f172a' }}>Deterministic Engine Rule: </strong>
          Statutory applicability (MPCB consent limits, Factory Act inspections, boiler certifications) is derived deterministically from these profile attributes. Simulating a change calculates newly triggered or exempt obligations without altering your active compliance audit register.
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
            ✕
          </button>
        </div>
      )}

      {/* Main Grid: Form on Left, Simulation Diff on Right */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: simulationResult ? '1fr 1.2fr' : '1fr',
          gap: '24px',
        }}
      >
        {/* Profile Editor Card */}
        <div
          style={{
            backgroundColor: '#ffffff',
            borderRadius: '12px',
            border: '1px solid #e2e8f0',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            padding: '24px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#0f172a', margin: 0 }}>
              Operational Facility Parameters
            </h2>
            <span
              style={{
                fontSize: '11px',
                padding: '3px 8px',
                borderRadius: '4px',
                backgroundColor: '#f1f5f9',
                color: '#475569',
                fontWeight: 600,
              }}
            >
              Version {profile?.version ?? '1.0'} Baseline
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            {/* Industry Category */}
            <div>
              <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                CPCB / MPCB Industrial Pollution Category
              </label>
              <select
                value={industryCategory}
                onChange={(e) => setIndustryCategory(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  fontSize: '13px',
                }}
              >
                <option value="RED">RED Category (High Pollution Potential - Heavy Synthetic / Chemical)</option>
                <option value="ORANGE">ORANGE Category (Medium Pollution Potential)</option>
                <option value="GREEN">GREEN Category (Low Pollution Potential)</option>
                <option value="WHITE">WHITE Category (Non-polluting / Excluded)</option>
              </select>
              <span style={{ fontSize: '11.5px', color: '#64748b', marginTop: '4px', display: 'block' }}>
                Dictates Consent to Operate (CTO) renewal validity periods (5 vs. 10 years) and audit frequencies.
              </span>
            </div>

            {/* Workforce & Boilers in Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  <Users size={14} color="#059669" />
                  <span>Total Workforce (Workers)</span>
                </label>
                <input
                  type="number"
                  value={employeeCount}
                  onChange={(e) => setEmployeeCount(Number(e.target.value))}
                  min={1}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '13px',
                    boxSizing: 'border-box',
                  }}
                />
                <span style={{ fontSize: '11px', color: '#64748b', marginTop: '4px', display: 'block' }}>
                  Crosses Factories Act 1948 safety committee threshold at 250 workers.
                </span>
              </div>

              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  <Flame size={14} color="#d97706" />
                  <span>Boiler Units On-Site</span>
                </label>
                <input
                  type="number"
                  value={boilerCount}
                  onChange={(e) => setBoilerCount(Number(e.target.value))}
                  min={0}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '13px',
                    boxSizing: 'border-box',
                  }}
                />
                <span style={{ fontSize: '11px', color: '#64748b', marginTop: '4px', display: 'block' }}>
                  Triggers Indian Boilers Act annual hydraulic test certificate requirements.
                </span>
              </div>
            </div>

            {/* Steam Capacity & Hazardous Waste in Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  <Factory size={14} color="#0284c7" />
                  <span>Steam Capacity (TPH)</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={steamCapacity}
                  onChange={(e) => setSteamCapacity(Number(e.target.value))}
                  min={0}
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
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                  <AlertTriangle size={14} color="#dc2626" />
                  <span>Hazardous Waste (TPA)</span>
                </label>
                <input
                  type="number"
                  step="0.5"
                  value={hazardousWasteTpa}
                  onChange={(e) => setHazardousWasteTpa(Number(e.target.value))}
                  min={0}
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

            {/* Activities Checkbox Badges */}
            <div>
              <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '8px' }}>
                Operational Activities & Sub-Processes
              </label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {[
                  { key: 'chemical_manufacturing', label: 'Synthetic Chemical Manufacturing' },
                  { key: 'hazardous_waste_storage', label: 'Hazardous Waste Storage Area' },
                  { key: 'boiler_operation', label: 'Steam Boiler Operations' },
                  { key: 'etp_discharge', label: 'On-site ETP Discharge to CETP' },
                  { key: 'dg_set_operation', label: 'Diesel Generator Backup (>500 kVA)' },
                  { key: 'solvent_recovery', label: 'Solvent Recovery Distillation Unit' },
                ].map((act) => {
                  const active = activities.includes(act.key);
                  return (
                    <button
                      type="button"
                      key={act.key}
                      onClick={() => toggleActivity(act.key)}
                      style={{
                        padding: '6px 12px',
                        borderRadius: '6px',
                        fontSize: '12px',
                        cursor: 'pointer',
                        border: active ? '1px solid #059669' : '1px solid #cbd5e1',
                        backgroundColor: active ? '#ecfdf5' : '#ffffff',
                        color: active ? '#065f46' : '#475569',
                        fontWeight: active ? 600 : 400,
                        transition: 'all 0.15s ease',
                      }}
                    >
                      {active ? '✓ ' : '+ '}
                      {act.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Rationale input */}
            <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '16px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                Audit Change Rationale / Memo *
              </label>
              <input
                type="text"
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                placeholder="Document reason for update (e.g. installation of new boiler #3)"
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

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                onClick={handleSimulate}
                className="btn btn-primary"
                disabled={simulating}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: '#0f766e',
                  borderColor: '#0f766e',
                }}
              >
                <GitCompare size={15} className={simulating ? 'spin-slow' : ''} />
                <span>Simulate Impact</span>
              </button>
            </div>
          </div>
        </div>

        {/* Simulation "What Changed" Diff Panel */}
        {simulationResult && (
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '12px',
              border: '1px solid #cbd5e1',
              boxShadow: '0 4px 6px -1px rgba(0,0,0,0.08)',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Header */}
            <div
              style={{
                backgroundColor: '#06281e',
                padding: '18px 24px',
                color: '#ffffff',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <span
                  style={{
                    fontSize: '11px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    color: '#34d399',
                    fontWeight: 600,
                  }}
                >
                  Prospective Reassessment Simulation
                </span>
                <h2 style={{ fontSize: '17px', fontWeight: 600, margin: '2px 0 0 0', color: '#ffffff' }}>
                  "What Changed" Regulatory Delta
                </h2>
              </div>
              <button
                onClick={() => setSimulationResult(null)}
                style={{ background: 'none', border: 'none', color: '#cbd5e1', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ padding: '20px 24px', flex: 1, overflowY: 'auto' }}>
              {/* Attribute Modifications Bar */}
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '8px' }}>
                  Modified Factory Attributes ({simulationResult.attribute_changes.length})
                </div>
                {simulationResult.attribute_changes.length === 0 ? (
                  <div style={{ fontSize: '13px', color: '#64748b', fontStyle: 'italic' }}>
                    No attributes changed.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {simulationResult.attribute_changes.map((attr, idx) => (
                      <div
                        key={idx}
                        style={{
                          backgroundColor: '#f1f5f9',
                          border: '1px solid #cbd5e1',
                          padding: '6px 12px',
                          borderRadius: '6px',
                          fontSize: '12px',
                          color: '#334155',
                        }}
                      >
                        <strong>{attr.field_name}: </strong>
                        <span style={{ color: '#dc2626', textDecoration: 'line-through' }}>
                          {String(attr.previous_value ?? 'None')}
                        </span>
                        <ArrowRight size={12} style={{ display: 'inline', margin: '0 4px' }} />
                        <span style={{ color: '#059669', fontWeight: 600 }}>
                          {String(attr.proposed_value)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Impact Metric Cards */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '10px',
                  marginBottom: '20px',
                }}
              >
                <div style={{ backgroundColor: '#ecfdf5', padding: '12px', borderRadius: '8px', border: '1px solid #a7f3d0', textAlign: 'center' }}>
                  <div style={{ fontSize: '11px', color: '#065f46', fontWeight: 600 }}>NEWLY APPLICABLE</div>
                  <div style={{ fontSize: '20px', fontWeight: 700, color: '#059669', marginTop: '2px' }}>
                    +{simulationResult.newly_applicable_count}
                  </div>
                </div>

                <div style={{ backgroundColor: '#fef3c7', padding: '12px', borderRadius: '8px', border: '1px solid #fde68a', textAlign: 'center' }}>
                  <div style={{ fontSize: '11px', color: '#92400e', fontWeight: 600 }}>EXEMPT / REMOVED</div>
                  <div style={{ fontSize: '20px', fontWeight: 700, color: '#d97706', marginTop: '2px' }}>
                    -{simulationResult.no_longer_applicable_count}
                  </div>
                </div>

                <div style={{ backgroundColor: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                  <div style={{ fontSize: '11px', color: '#475569', fontWeight: 600 }}>UNCHANGED</div>
                  <div style={{ fontSize: '20px', fontWeight: 700, color: '#334155', marginTop: '2px' }}>
                    {simulationResult.unchanged_applicable_count}
                  </div>
                </div>
              </div>

              {/* Requirement Level Delta Table */}
              <div style={{ fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '8px' }}>
                Impacted Requirement Breakdown
              </div>
              <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                      <th style={{ padding: '8px 12px', textAlign: 'left' }}>Requirement</th>
                      <th style={{ padding: '8px 12px', textAlign: 'left' }}>Authority</th>
                      <th style={{ padding: '8px 12px', textAlign: 'left' }}>Evaluation Impact</th>
                      <th style={{ padding: '8px 12px', textAlign: 'left' }}>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {simulationResult.impacted_requirements.length === 0 ? (
                      <tr>
                        <td colSpan={4} style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                          No statutory requirement additions or exclusions caused by this attribute change.
                        </td>
                      </tr>
                    ) : (
                      simulationResult.impacted_requirements.map((req, idx) => (
                        <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '8px 12px' }}>
                            <div style={{ fontWeight: 600, color: '#0f172a' }}>{req.requirement_code}</div>
                            <div style={{ fontSize: '11px', color: '#64748b' }}>{req.requirement_title}</div>
                          </td>
                          <td style={{ padding: '8px 12px', color: '#475569' }}>
                            {req.authority_code || 'General'}
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            <span
                              style={{
                                display: 'inline-block',
                                padding: '2px 8px',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 600,
                                backgroundColor:
                                  req.impact_type === 'NEWLY_APPLICABLE'
                                    ? '#ecfdf5'
                                    : req.impact_type === 'NO_LONGER_APPLICABLE'
                                    ? '#fef3c7'
                                    : '#f1f5f9',
                                color:
                                  req.impact_type === 'NEWLY_APPLICABLE'
                                    ? '#059669'
                                    : req.impact_type === 'NO_LONGER_APPLICABLE'
                                    ? '#d97706'
                                    : '#475569',
                              }}
                            >
                              {req.impact_type.replace(/_/g, ' ')}
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px', color: '#64748b', fontSize: '11.5px' }}>
                            {req.reason}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Action Button to Commit live */}
              <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => setSimulationResult(null)}
                  className="btn btn-secondary"
                  disabled={applying}
                >
                  Discard Simulation
                </button>
                <button
                  type="button"
                  onClick={handleApply}
                  className="btn btn-primary"
                  disabled={applying}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    backgroundColor: '#059669',
                    borderColor: '#059669',
                  }}
                >
                  <Save size={14} />
                  <span>{applying ? 'Applying Reassessment...' : 'Confirm & Apply to Register'}</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
