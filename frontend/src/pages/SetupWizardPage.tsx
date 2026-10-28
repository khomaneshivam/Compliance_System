import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Building2,
  MapPin,
  Flame,
  Users,
  Factory,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  Save,
  RotateCcw,
  Sparkles,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../services/api';

const wizardSchema = z.object({
  // Step 1: Legal Entity & Jurisdiction
  legalEntityName: z.string().min(3, 'Legal entity name must be at least 3 characters'),
  cinOrRegistration: z.string().min(5, 'Registration/CIN number is required'),
  jurisdictionState: z.string().min(2, 'Please select state jurisdiction'),

  // Step 2: Site / Plant Info
  plantName: z.string().min(3, 'Plant / Facility name is required'),
  plantCode: z.string().min(2, 'Unique plant code is required'),
  district: z.string().min(2, 'District is required'),
  pincode: z.string().regex(/^\d{6}$/, 'Enter a valid 6-digit Indian PIN code'),
  industrialZone: z.string().optional(),

  // Step 3: Industrial Categorization
  industryCategory: z.enum(['RED', 'ORANGE', 'GREEN', 'WHITE']),
  sector: z.string().min(2, 'Industrial sector is required'),

  // Step 4: Operational Facts & Capacities
  employeeCount: z.number().min(1, 'Headcount must be at least 1'),
  contractLabourCount: z.number().min(0, 'Cannot be negative'),
  boilerCount: z.number().min(0, 'Cannot be negative'),
  steamCapacityTph: z.number().min(0, 'Cannot be negative'),
  hazardousWasteTpa: z.number().min(0, 'Cannot be negative'),
  effluentDischargeKld: z.number().min(0, 'Cannot be negative'),
  dgSetCapacityKva: z.number().min(0, 'Cannot be negative'),
});

type WizardFormData = z.infer<typeof wizardSchema>;

const DRAFT_STORAGE_KEY = 'plantproof_onboarding_draft';

export const SetupWizardPage: React.FC = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState<number>(1);
  const [draftRestored, setDraftRestored] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [engineEvaluating, setEngineEvaluating] = useState<boolean>(false);

  const defaultValues: WizardFormData = {
    legalEntityName: 'Acme Manufacturing Private Limited',
    cinOrRegistration: 'U24100MH2020PTC345678',
    jurisdictionState: 'Maharashtra',
    plantName: 'Acme Pune Manufacturing Unit',
    plantCode: 'PUNE-PLANT-01',
    district: 'Pune',
    pincode: '410501',
    industrialZone: 'Chakan MIDC Phase II',
    industryCategory: 'RED',
    sector: 'Chemicals & Synthetic Formulations',
    employeeCount: 250,
    contractLabourCount: 75,
    boilerCount: 2,
    steamCapacityTph: 12.5,
    hazardousWasteTpa: 45.0,
    effluentDischargeKld: 60.0,
    dgSetCapacityKva: 750.0,
  };

  const {
    register,
    handleSubmit,
    watch,
    reset,
    trigger,
    formState: { errors },
  } = useForm<WizardFormData>({
    resolver: zodResolver(wizardSchema),
    defaultValues,
    mode: 'onChange',
  });

  const formValues = watch();

  // Restore draft from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(DRAFT_STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        reset(parsed);
        setDraftRestored(true);
      } catch {
        // Ignore corrupted draft
      }
    }
  }, [reset]);

  // Save draft on change
  const handleSaveDraft = () => {
    localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(formValues));
    alert('Onboarding draft saved to local storage. You can safely resume this setup anytime.');
  };

  const handleClearDraft = () => {
    localStorage.removeItem(DRAFT_STORAGE_KEY);
    reset(defaultValues);
    setDraftRestored(false);
  };

  const validateStep = async (currentStep: number): Promise<boolean> => {
    if (currentStep === 1) {
      return await trigger(['legalEntityName', 'cinOrRegistration', 'jurisdictionState']);
    }
    if (currentStep === 2) {
      return await trigger(['plantName', 'plantCode', 'district', 'pincode']);
    }
    if (currentStep === 3) {
      return await trigger(['industryCategory', 'sector']);
    }
    if (currentStep === 4) {
      return await trigger([
        'employeeCount',
        'contractLabourCount',
        'boilerCount',
        'steamCapacityTph',
        'hazardousWasteTpa',
        'effluentDischargeKld',
        'dgSetCapacityKva',
      ]);
    }
    return true;
  };

  const handleNext = async () => {
    const ok = await validateStep(step);
    if (ok) {
      localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(formValues));
      setStep((s) => Math.min(5, s + 1));
    }
  };

  const handleBack = () => {
    setStep((s) => Math.max(1, s - 1));
  };

  const onFinalSubmit = async (data: WizardFormData) => {
    setSubmitting(true);
    setEngineEvaluating(true);
    try {
      // 1. Submit plant profile to backend
      await api.applyProfileReassessment('plant-pune-01', {
        profile_updates: {
          industry_category: data.industryCategory,
          employee_count: data.employeeCount,
          boiler_count: data.boilerCount,
          steam_capacity_tph: data.steamCapacityTph,
          hazardous_waste_tpa: data.hazardousWasteTpa,
          activities: [
            'chemical_manufacturing',
            'boiler_operation',
            'hazardous_waste_storage',
            'etp_discharge',
          ],
        },
        auto_approve_changes: true,
        rationale: 'Initial enterprise plant onboarding calibration',
      });

      // Clear draft
      localStorage.removeItem(DRAFT_STORAGE_KEY);

      // Brief animation for statutory engine evaluation
      setTimeout(() => {
        setEngineEvaluating(false);
        navigate('/dashboard');
      }, 1200);
    } catch (err: unknown) {
      alert((err as Error).message || 'Failed to submit onboarding profile. Please try again.');
      setSubmitting(false);
      setEngineEvaluating(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#f8fafc',
        padding: '32px 16px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}
    >
      <div style={{ width: '100%', maxWidth: '820px' }}>
        {/* Header Title */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              color: '#059669',
              marginBottom: '6px',
            }}
          >
            <Building2 size={28} />
            <span style={{ fontSize: '22px', fontWeight: 700, color: '#0f172a' }}>
              First-Run Facility Onboarding Wizard
            </span>
          </div>
          <p style={{ color: '#64748b', fontSize: '13.5px', margin: 0 }}>
            Configure your enterprise manufacturing profile to calibrate the deterministic statutory applicability engine.
          </p>
        </div>

        {/* Draft Notice Banner */}
        {draftRestored && (
          <div
            style={{
              backgroundColor: '#ecfdf5',
              border: '1px solid #a7f3d0',
              borderRadius: '8px',
              padding: '10px 16px',
              marginBottom: '20px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '12.5px',
              color: '#065f46',
            }}
          >
            <span>✓ Restored your in-progress onboarding draft from local cache.</span>
            <button
              type="button"
              onClick={handleClearDraft}
              style={{
                background: 'none',
                border: 'none',
                color: '#047857',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: '12px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <RotateCcw size={12} />
              <span>Reset Defaults</span>
            </button>
          </div>
        )}

        {/* Stepper Progress Bar */}
        <div
          style={{
            backgroundColor: '#ffffff',
            borderRadius: '12px',
            border: '1px solid #e2e8f0',
            padding: '18px 24px',
            marginBottom: '24px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', position: 'relative' }}>
            {[
              { num: 1, title: 'Legal Entity' },
              { num: 2, title: 'Site & Facility' },
              { num: 3, title: 'CPCB Category' },
              { num: 4, title: 'Operational Facts' },
              { num: 5, title: 'Review & Engine' },
            ].map((s) => {
              const isPassed = step > s.num;
              const isCurrent = step === s.num;
              return (
                <div
                  key={s.num}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    flex: 1,
                    position: 'relative',
                    zIndex: 2,
                  }}
                >
                  <div
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '50%',
                      backgroundColor: isPassed
                        ? '#059669'
                        : isCurrent
                        ? '#06281e'
                        : '#f1f5f9',
                      color: isPassed || isCurrent ? '#ffffff' : '#64748b',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 700,
                      fontSize: '13px',
                      border: isCurrent ? '2px solid #059669' : '1px solid transparent',
                      marginBottom: '6px',
                    }}
                  >
                    {isPassed ? '✓' : s.num}
                  </div>
                  <span
                    style={{
                      fontSize: '11.5px',
                      fontWeight: isCurrent ? 700 : 500,
                      color: isCurrent ? '#0f172a' : '#64748b',
                      textAlign: 'center',
                    }}
                  >
                    {s.title}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Wizard Form Card */}
        <div
          style={{
            backgroundColor: '#ffffff',
            borderRadius: '12px',
            border: '1px solid #e2e8f0',
            boxShadow: '0 2px 4px rgba(0,0,0,0.04)',
            overflow: 'hidden',
          }}
        >
          <form onSubmit={handleSubmit(onFinalSubmit)}>
            <div style={{ padding: '28px 32px' }}>
              {/* STEP 1 */}
              {step === 1 && (
                <div>
                  <h2 style={{ fontSize: '17px', fontWeight: 700, color: '#0f172a', marginBottom: '6px' }}>
                    Step 1: Corporate Legal Entity & Statutory Jurisdiction
                  </h2>
                  <p style={{ color: '#64748b', fontSize: '13px', marginBottom: '20px' }}>
                    Define your manufacturing company's registered entity and governing state pollution control board jurisdiction.
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                        Registered Corporate Entity Name *
                      </label>
                      <input
                        type="text"
                        {...register('legalEntityName')}
                        placeholder="e.g. Acme Manufacturing Private Limited"
                        style={{
                          width: '100%',
                          padding: '9px 12px',
                          borderRadius: '6px',
                          border: errors.legalEntityName ? '1px solid #dc2626' : '1px solid #cbd5e1',
                          fontSize: '13px',
                          boxSizing: 'border-box',
                        }}
                      />
                      {errors.legalEntityName && (
                        <span style={{ fontSize: '11.5px', color: '#dc2626', marginTop: '4px', display: 'block' }}>
                          {errors.legalEntityName.message}
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                      <div>
                        <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                          Corporate Identification Number (CIN / ROC) *
                        </label>
                        <input
                          type="text"
                          {...register('cinOrRegistration')}
                          placeholder="e.g. U24100MH2020PTC345678"
                          style={{
                            width: '100%',
                            padding: '9px 12px',
                            borderRadius: '6px',
                            border: errors.cinOrRegistration ? '1px solid #dc2626' : '1px solid #cbd5e1',
                            fontSize: '13px',
                            boxSizing: 'border-box',
                          }}
                        />
                        {errors.cinOrRegistration && (
                          <span style={{ fontSize: '11.5px', color: '#dc2626', marginTop: '4px', display: 'block' }}>
                            {errors.cinOrRegistration.message}
                          </span>
                        )}
                      </div>

                      <div>
                        <label htmlFor="jurisdictionState" style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                          Primary State Jurisdiction *
                        </label>
                        <select
                          id="jurisdictionState"
                          aria-label="Primary State Jurisdiction"
                          {...register('jurisdictionState')}
                          style={{
                            width: '100%',
                            padding: '9px 12px',
                            borderRadius: '6px',
                            border: '1px solid #cbd5e1',
                            fontSize: '13px',
                            backgroundColor: '#ffffff',
                          }}
                        >
                          <option value="Maharashtra">Maharashtra (MPCB & DISH Maharashtra)</option>
                          <option value="Gujarat">Gujarat (GPCB & DISH Gujarat)</option>
                          <option value="Karnataka">Karnataka (KSPCB)</option>
                          <option value="Central">Central / National (MoEFCC & CPCB)</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 2 */}
              {step === 2 && (
                <div>
                  <h2 style={{ fontSize: '17px', fontWeight: 700, color: '#0f172a', marginBottom: '6px' }}>
                    Step 2: Manufacturing Site & Facility Identification
                  </h2>
                  <p style={{ color: '#64748b', fontSize: '13px', marginBottom: '20px' }}>
                    Enter operational plant location details used for district-level factory inspectorate and environmental consents.
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '16px' }}>
                      <div>
                        <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                          Plant / Facility Name *
                        </label>
                        <input
                          type="text"
                          {...register('plantName')}
                          placeholder="e.g. Acme Pune Manufacturing Unit"
                          style={{
                            width: '100%',
                            padding: '9px 12px',
                            borderRadius: '6px',
                            border: errors.plantName ? '1px solid #dc2626' : '1px solid #cbd5e1',
                            fontSize: '13px',
                            boxSizing: 'border-box',
                          }}
                        />
                        {errors.plantName && (
                          <span style={{ fontSize: '11.5px', color: '#dc2626', marginTop: '4px', display: 'block' }}>
                            {errors.plantName.message}
                          </span>
                        )}
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                          Internal Plant Code *
                        </label>
                        <input
                          type="text"
                          {...register('plantCode')}
                          placeholder="e.g. PUNE-PLANT-01"
                          style={{
                            width: '100%',
                            padding: '9px 12px',
                            borderRadius: '6px',
                            border: errors.plantCode ? '1px solid #dc2626' : '1px solid #cbd5e1',
                            fontSize: '13px',
                            boxSizing: 'border-box',
                          }}
                        />
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                      <div>
                        <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                          District *
                        </label>
                        <input
                          type="text"
                          {...register('district')}
                          placeholder="e.g. Pune"
                          style={{
                            width: '100%',
                            padding: '9px 12px',
                            borderRadius: '6px',
                            border: '1px solid #cbd5e1',
                            fontSize: '13px',
                            boxSizing: 'border-box',
                          }}
                        />
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                          PIN Code (6 digits) *
                        </label>
                        <input
                          type="text"
                          {...register('pincode')}
                          placeholder="e.g. 410501"
                          style={{
                            width: '100%',
                            padding: '9px 12px',
                            borderRadius: '6px',
                            border: errors.pincode ? '1px solid #dc2626' : '1px solid #cbd5e1',
                            fontSize: '13px',
                            boxSizing: 'border-box',
                          }}
                        />
                        {errors.pincode && (
                          <span style={{ fontSize: '11.5px', color: '#dc2626', marginTop: '4px', display: 'block' }}>
                            {errors.pincode.message}
                          </span>
                        )}
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                          Industrial Zone / MIDC Area
                        </label>
                        <input
                          type="text"
                          {...register('industrialZone')}
                          placeholder="e.g. Chakan MIDC Phase II"
                          style={{
                            width: '100%',
                            padding: '9px 12px',
                            borderRadius: '6px',
                            border: '1px solid #cbd5e1',
                            fontSize: '13px',
                            boxSizing: 'border-box',
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 3 */}
              {step === 3 && (
                <div>
                  <h2 style={{ fontSize: '17px', fontWeight: 700, color: '#0f172a', marginBottom: '6px' }}>
                    Step 3: CPCB Industrial Categorization & Sector
                  </h2>
                  <p style={{ color: '#64748b', fontSize: '13px', marginBottom: '20px' }}>
                    The Central Pollution Control Board (CPCB) classifies manufacturing facilities by Pollution Index score (60+, 41-59, 21-40, &lt;20).
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '8px' }}>
                        Pollution Control Category *
                      </label>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                        {[
                          {
                            key: 'RED',
                            title: 'RED Category',
                            desc: 'Pollution Index >= 60. Heavy chemical, synthetic organic, pharmaceutical API, electroplating.',
                            border: '#dc2626',
                            bg: '#fef2f2',
                          },
                          {
                            key: 'ORANGE',
                            title: 'ORANGE Category',
                            desc: 'Pollution Index 41-59. Medium engineering, food processing, paint formulation.',
                            border: '#d97706',
                            bg: '#fffbeb',
                          },
                          {
                            key: 'GREEN',
                            title: 'GREEN Category',
                            desc: 'Pollution Index 21-40. Light fabrication, dry assembly, packaging.',
                            border: '#059669',
                            bg: '#ecfdf5',
                          },
                          {
                            key: 'WHITE',
                            title: 'WHITE Category',
                            desc: 'Pollution Index <= 20. Practically non-polluting industrial activities.',
                            border: '#64748b',
                            bg: '#f8fafc',
                          },
                        ].map((cat) => {
                          const isSelected = formValues.industryCategory === cat.key;
                          return (
                            <label
                              key={cat.key}
                              style={{
                                display: 'block',
                                padding: '14px',
                                borderRadius: '8px',
                                border: isSelected ? `2px solid ${cat.border}` : '1px solid #e2e8f0',
                                backgroundColor: isSelected ? cat.bg : '#ffffff',
                                cursor: 'pointer',
                                transition: 'all 0.15s ease',
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                <input
                                  type="radio"
                                  value={cat.key}
                                  {...register('industryCategory')}
                                  style={{ accentColor: cat.border }}
                                />
                                <span style={{ fontWeight: 700, fontSize: '13px', color: '#0f172a' }}>
                                  {cat.title}
                                </span>
                              </div>
                              <p style={{ margin: 0, fontSize: '11.5px', color: '#64748b', lineHeight: 1.45, paddingLeft: '20px' }}>
                                {cat.desc}
                              </p>
                            </label>
                          );
                        })}
                      </div>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                        Manufacturing Sector / Primary Activity *
                      </label>
                      <input
                        type="text"
                        {...register('sector')}
                        placeholder="e.g. Chemicals & Synthetic Formulations"
                        style={{
                          width: '100%',
                          padding: '9px 12px',
                          borderRadius: '6px',
                          border: errors.sector ? '1px solid #dc2626' : '1px solid #cbd5e1',
                          fontSize: '13px',
                          boxSizing: 'border-box',
                        }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 4 */}
              {step === 4 && (
                <div>
                  <h2 style={{ fontSize: '17px', fontWeight: 700, color: '#0f172a', marginBottom: '6px' }}>
                    Step 4: Operational Capacities & Statutory Threshold Facts
                  </h2>
                  <p style={{ color: '#64748b', fontSize: '13px', marginBottom: '20px' }}>
                    These numbers deterministically trigger threshold-based rules (Factories Act 1948, Boilers Act 1923, Hazardous Waste Rules 2016).
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {/* Workforce */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                      <div>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                          <Users size={14} color="#059669" />
                          <span>Permanent Workforce (Workers) *</span>
                        </label>
                        <input
                          type="number"
                          {...register('employeeCount', { valueAsNumber: true })}
                          style={{
                            width: '100%',
                            padding: '8px 12px',
                            borderRadius: '6px',
                            border: '1px solid #cbd5e1',
                            fontSize: '13px',
                            boxSizing: 'border-box',
                          }}
                        />
                        <span style={{ fontSize: '11px', color: '#64748b', marginTop: '3px', display: 'block' }}>
                          Triggers Safety Committee at 250+ workers.
                        </span>
                      </div>

                      <div>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                          <Users size={14} color="#0284c7" />
                          <span>Contract Labour Headcount</span>
                        </label>
                        <input
                          type="number"
                          {...register('contractLabourCount', { valueAsNumber: true })}
                          style={{
                            width: '100%',
                            padding: '8px 12px',
                            borderRadius: '6px',
                            border: '1px solid #cbd5e1',
                            fontSize: '13px',
                            boxSizing: 'border-box',
                          }}
                        />
                        <span style={{ fontSize: '11px', color: '#64748b', marginTop: '3px', display: 'block' }}>
                          Triggers Contract Labour (R&A) Act at 20+ workers.
                        </span>
                      </div>
                    </div>

                    {/* Boilers & Steam */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                      <div>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                          <Flame size={14} color="#d97706" />
                          <span>Steam Boiler Units</span>
                        </label>
                        <input
                          type="number"
                          {...register('boilerCount', { valueAsNumber: true })}
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
                          <Factory size={14} color="#d97706" />
                          <span>Total Steam Capacity (TPH)</span>
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          {...register('steamCapacityTph', { valueAsNumber: true })}
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

                    {/* Hazardous Waste & Effluent */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                      <div>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
                          <AlertTriangle size={14} color="#dc2626" />
                          <span>Hazardous Waste Generated (TPA)</span>
                        </label>
                        <input
                          type="number"
                          step="0.5"
                          {...register('hazardousWasteTpa', { valueAsNumber: true })}
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
                          <MapPin size={14} color="#0284c7" />
                          <span>Industrial Effluent (KLD)</span>
                        </label>
                        <input
                          type="number"
                          step="0.5"
                          {...register('effluentDischargeKld', { valueAsNumber: true })}
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
                  </div>
                </div>
              )}

              {/* STEP 5 */}
              {step === 5 && (
                <div>
                  <h2 style={{ fontSize: '17px', fontWeight: 700, color: '#0f172a', marginBottom: '6px' }}>
                    Step 5: Review Profile & Run Deterministic Applicability Engine
                  </h2>
                  <p style={{ color: '#64748b', fontSize: '13px', marginBottom: '20px' }}>
                    Verify your facility parameters before triggering the compliance evaluation engine.
                  </p>

                  <div style={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '18px', marginBottom: '20px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', fontSize: '12.5px' }}>
                      <div>
                        <span style={{ color: '#64748b' }}>Legal Entity:</span>{' '}
                        <strong>{formValues.legalEntityName}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>Jurisdiction:</span>{' '}
                        <strong>{formValues.jurisdictionState}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>Facility:</span>{' '}
                        <strong>{formValues.plantName} ({formValues.plantCode})</strong>
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>District / Zone:</span>{' '}
                        <strong>{formValues.district}, {formValues.industrialZone || 'N/A'}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>CPCB Category:</span>{' '}
                        <strong style={{ color: formValues.industryCategory === 'RED' ? '#dc2626' : '#059669' }}>
                          {formValues.industryCategory}
                        </strong>
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>Sector:</span>{' '}
                        <strong>{formValues.sector}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>Workforce:</span>{' '}
                        <strong>{formValues.employeeCount} permanent, {formValues.contractLabourCount} contract</strong>
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>Equipment:</span>{' '}
                        <strong>{formValues.boilerCount} boilers ({formValues.steamCapacityTph} TPH)</strong>
                      </div>
                    </div>
                  </div>

                  <div
                    style={{
                      backgroundColor: '#ecfdf5',
                      border: '1px solid #a7f3d0',
                      borderRadius: '8px',
                      padding: '14px',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '12px',
                    }}
                  >
                    <ShieldCheck size={20} color="#059669" style={{ flexShrink: 0, marginTop: '2px' }} />
                    <div style={{ fontSize: '12px', color: '#065f46', lineHeight: 1.5 }}>
                      <strong>Deterministic Rule Evaluation: </strong>
                      PlantProof will evaluate 48+ central and state statutory requirements against these facts. No arbitrary code or AI hallucinatory logic is executed; rules use typed boolean AST evaluation.
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Bottom Actions Bar */}
            <div
              style={{
                padding: '18px 32px',
                backgroundColor: '#f8fafc',
                borderTop: '1px solid #e2e8f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                {step > 1 ? (
                  <button
                    type="button"
                    onClick={handleBack}
                    className="btn btn-secondary"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                  >
                    <ArrowLeft size={14} />
                    <span>Back</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => navigate('/dashboard')}
                    className="btn btn-secondary"
                  >
                    Exit Setup
                  </button>
                )}
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  type="button"
                  onClick={handleSaveDraft}
                  className="btn btn-secondary"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                >
                  <Save size={14} />
                  <span>Save Draft</span>
                </button>

                {step < 5 ? (
                  <button
                    type="button"
                    onClick={handleNext}
                    className="btn btn-primary"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      backgroundColor: '#059669',
                      borderColor: '#059669',
                    }}
                  >
                    <span>Save & Continue</span>
                    <ArrowRight size={14} />
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={submitting}
                    className="btn btn-primary"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      backgroundColor: '#059669',
                      borderColor: '#059669',
                    }}
                  >
                    <Sparkles size={15} />
                    <span>
                      {engineEvaluating
                        ? 'Calibrating Statutory Engine...'
                        : 'Finalize & Generate Register'}
                    </span>
                  </button>
                )}
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
