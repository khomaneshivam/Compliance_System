import React, { useState, useEffect, useCallback } from 'react';
import {
  GitBranch,
  Play,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  ShieldAlert,
  Code,
} from 'lucide-react';
import { api } from '../services/api';
import type { RuleResponseItem, RuleSimulationResult } from '../types';

export const AdminRulesPage: React.FC = () => {
  const [rules, setRules] = useState<RuleResponseItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [selectedRule, setSelectedRule] = useState<RuleResponseItem | null>(null);

  // Simulator State
  const [simulating, setSimulating] = useState<boolean>(false);
  const [simulationResult, setSimulationResult] = useState<RuleSimulationResult | null>(null);

  const fetchRules = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getAdminRules({
        status: statusFilter || undefined,
      });
      setRules(data);
      if (data.length > 0 && !selectedRule) {
        setSelectedRule(data[0]);
      }
    } catch (err: unknown) {
      console.error('Failed to load rules', err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, selectedRule]);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const handleSimulate = async () => {
    if (!selectedRule) return;
    setSimulating(true);
    setSimulationResult(null);
    try {
      const res = await api.simulateAdminRule(selectedRule.id, 'plant-pune-01');
      setSimulationResult(res);
    } catch (err: unknown) {
      alert((err as Error).message || 'Failed to simulate rule evaluation');
    } finally {
      setSimulating(false);
    }
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
              <GitBranch size={18} />
            </div>
            <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
              Deterministic Rule Bench & AST Simulator
            </h1>
          </div>
          <p style={{ color: '#64748b', fontSize: '13px', margin: 0 }}>
            Author, test, and version typed boolean condition trees. Simulates statutory applicability against factory operational facts without arbitrary code execution.
          </p>
        </div>

        <button
          onClick={() => fetchRules()}
          className="btn btn-secondary"
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={14} className={loading ? 'spin-slow' : ''} />
          <span>Refresh Bench</span>
        </button>
      </div>

      {/* Cardinal Rule Tenet Banner */}
      <div
        style={{
          backgroundColor: '#f8fafc',
          border: '1px solid #cbd5e1',
          borderLeft: '4px solid #059669',
          borderRadius: '8px',
          padding: '12px 18px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          fontSize: '12.5px',
          color: '#334155',
        }}
      >
        <ShieldAlert size={20} color="#059669" style={{ flexShrink: 0 }} />
        <div>
          <strong>Safety & AST Invariant: </strong>
          All applicability rules are strictly declarative boolean trees evaluated against typed plant profile facts. The engine strictly prohibits running <code>eval()</code>, <code>exec()</code>, or arbitrary SQL from rule expressions.
        </div>
      </div>

      {/* Main Grid: Left side Rules List, Right side Simulator Bench */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: '24px' }}>
        {/* Rules Table */}
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
              padding: '14px 18px',
              borderBottom: '1px solid #f1f5f9',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: '#fafbfc',
            }}
          >
            <div style={{ fontSize: '13.5px', fontWeight: 600, color: '#0f172a' }}>
              Statutory Rules Version Archive ({rules.length})
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                padding: '4px 8px',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                fontSize: '12px',
              }}
            >
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active (Effective)</option>
              <option value="PROPOSED">Proposed</option>
              <option value="SUPERSEDED">Superseded</option>
            </select>
          </div>

          <div style={{ maxHeight: '640px', overflowY: 'auto' }}>
            {rules.length === 0 ? (
              <div style={{ padding: '36px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
                No applicability rules found.
              </div>
            ) : (
              rules.map((rule) => {
                const isSelected = selectedRule?.id === rule.id;
                return (
                  <div
                    key={rule.id}
                    onClick={() => {
                      setSelectedRule(rule);
                      setSimulationResult(null);
                    }}
                    style={{
                      padding: '14px 18px',
                      borderBottom: '1px solid #f1f5f9',
                      backgroundColor: isSelected ? '#ecfdf5' : '#ffffff',
                      borderLeft: isSelected ? '4px solid #059669' : '4px solid transparent',
                      cursor: 'pointer',
                      transition: 'background-color 0.15s ease',
                    }}
                    className="table-row-hover"
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 700, fontSize: '13px', color: '#0f172a' }}>
                        {rule.statutory_requirement_code || 'REQUIREMENT'}
                      </span>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <span
                          style={{
                            fontSize: '10.5px',
                            fontWeight: 700,
                            padding: '1px 6px',
                            borderRadius: '4px',
                            backgroundColor: rule.status === 'ACTIVE' ? '#ecfdf5' : '#fef3c7',
                            color: rule.status === 'ACTIVE' ? '#059669' : '#d97706',
                          }}
                        >
                          {rule.status}
                        </span>
                        <span style={{ fontSize: '11px', color: '#64748b' }}>
                          v{rule.rule_version}
                        </span>
                      </div>
                    </div>

                    <p style={{ margin: '0 0 6px 0', fontSize: '12px', color: '#475569', lineHeight: 1.45 }}>
                      {rule.pass_explanation_template || 'Pass condition explanation template'}
                    </p>

                    <div style={{ fontSize: '11px', color: '#94a3b8', display: 'flex', gap: '10px' }}>
                      <span>Effective: {new Date(rule.effective_from).toLocaleDateString('en-IN')}</span>
                      <span>•</span>
                      <span>Immutable: {rule.is_immutable ? 'Yes (Audited)' : 'Draft'}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Simulator Bench & AST Inspector */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {selectedRule ? (
            <div
              style={{
                backgroundColor: '#ffffff',
                borderRadius: '12px',
                border: '1px solid #e2e8f0',
                padding: '20px 24px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                <div>
                  <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#059669', fontWeight: 700 }}>
                    Selected Evaluation Rule
                  </div>
                  <h2 style={{ fontSize: '16px', fontWeight: 700, color: '#0f172a', margin: '2px 0 0 0' }}>
                    {selectedRule.statutory_requirement_code} (v{selectedRule.rule_version})
                  </h2>
                </div>
                <button
                  onClick={handleSimulate}
                  disabled={simulating}
                  className="btn btn-primary"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    backgroundColor: '#059669',
                    borderColor: '#059669',
                  }}
                >
                  <Play size={13} className={simulating ? 'spin-slow' : ''} />
                  <span>{simulating ? 'Simulating...' : 'Simulate Against Pune Plant'}</span>
                </button>
              </div>

              {/* AST Tree Visualizer */}
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Code size={13} color="#059669" />
                  <span>Declarative Expression AST</span>
                </div>
                <div
                  style={{
                    backgroundColor: '#0f172a',
                    color: '#a7f3d0',
                    fontFamily: 'monospace',
                    fontSize: '11.5px',
                    padding: '12px 14px',
                    borderRadius: '8px',
                    overflowX: 'auto',
                    lineHeight: 1.5,
                  }}
                >
                  {JSON.stringify(selectedRule.expression_ast, null, 2)}
                </div>
              </div>

              {/* Interpolated Explanation Templates */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                <div style={{ backgroundColor: '#f8fafc', padding: '10px 12px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <strong style={{ color: '#059669' }}>Pass Template: </strong>
                  <span style={{ color: '#334155' }}>{selectedRule.pass_explanation_template}</span>
                </div>
                <div style={{ backgroundColor: '#f8fafc', padding: '10px 12px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <strong style={{ color: '#dc2626' }}>Fail Template: </strong>
                  <span style={{ color: '#334155' }}>{selectedRule.fail_explanation_template}</span>
                </div>
              </div>

              {/* Live Simulation Output Card */}
              {simulationResult && (
                <div
                  style={{
                    marginTop: '20px',
                    padding: '16px',
                    borderRadius: '8px',
                    backgroundColor: simulationResult.outcome === 'PASS' ? '#ecfdf5' : '#fef2f2',
                    border: `1px solid ${simulationResult.outcome === 'PASS' ? '#a7f3d0' : '#fecaca'}`,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    {simulationResult.outcome === 'PASS' ? (
                      <CheckCircle2 size={18} color="#059669" />
                    ) : (
                      <AlertTriangle size={18} color="#dc2626" />
                    )}
                    <span style={{ fontWeight: 700, fontSize: '13.5px', color: simulationResult.outcome === 'PASS' ? '#065f46' : '#991b1b' }}>
                      Simulation Outcome: {simulationResult.outcome}
                    </span>
                  </div>
                  <p style={{ margin: '0 0 10px 0', fontSize: '12.5px', color: '#334155', lineHeight: 1.5 }}>
                    {simulationResult.explanation}
                  </p>

                  <div style={{ fontSize: '11px', color: '#64748b' }}>
                    <strong>Evaluated Facts: </strong>
                    {Object.entries(simulationResult.evaluated_facts)
                      .map(([k, v]) => `${k}=${String(v)}`)
                      .join('; ')}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div
              style={{
                backgroundColor: '#ffffff',
                borderRadius: '12px',
                border: '1px solid #e2e8f0',
                padding: '40px',
                textAlign: 'center',
                color: '#64748b',
              }}
            >
              Select a statutory rule version from the left panel to inspect its condition tree.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
