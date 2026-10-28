import React from 'react';
import {
  FileText,
  Clock,
  AlertTriangle,
  Scale,
  ChevronDown,
  Building,
} from 'lucide-react';
import type { DashboardSummary } from '../types';
import { api } from '../services/api';

interface DashboardPageProps {
  summary?: DashboardSummary;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ summary: summaryProp }) => {
  const summary = summaryProp || api.getDashboardSummary();
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Page Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <h1
            style={{
              fontSize: '1.65rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
              letterSpacing: '-0.02em',
            }}
          >
            Dashboard
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '2px' }}>
            Your compliance overview and key actions
          </p>
        </div>

        {/* Plant Selector Dropdown */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-card)',
            padding: '8px 14px',
            borderRadius: '8px',
            fontSize: '0.88rem',
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          <Building size={16} color="var(--brand-primary)" />
          <span>All Plants</span>
          <ChevronDown size={16} color="var(--text-muted)" />
        </div>
      </div>

      {/* Row of 4 Hero Stat Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '20px',
        }}
      >
        {/* Card 1: Requirements */}
        <div className="card" style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: '10px',
              backgroundColor: 'rgba(16, 185, 129, 0.12)',
              color: 'var(--brand-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <FileText size={24} />
          </div>
          <div>
            <div style={{ fontSize: '1.85rem', fontWeight: 700, lineHeight: 1.1, color: 'var(--text-primary)' }}>
              {summary.totalRequirements}
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
              Requirements
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {summary.applicableCount} applicable &bull; {summary.notApplicableCount} not applicable
            </div>
          </div>
        </div>

        {/* Card 2: Due Soon */}
        <div className="card" style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: '10px',
              backgroundColor: 'rgba(245, 158, 11, 0.12)',
              color: '#fbbf24',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <Clock size={24} />
          </div>
          <div>
            <div style={{ fontSize: '1.85rem', fontWeight: 700, lineHeight: 1.1, color: 'var(--text-primary)' }}>
              {summary.dueSoonCount}
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
              Due Soon
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Next 30 days{' '}
              <span style={{ color: '#f87171', fontWeight: 600, marginLeft: '4px' }}>
                &uarr; 3 from last month
              </span>
            </div>
          </div>
        </div>

        {/* Card 3: Evidence Gaps */}
        <div className="card" style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: '10px',
              backgroundColor: 'rgba(239, 68, 68, 0.12)',
              color: '#f87171',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <AlertTriangle size={24} />
          </div>
          <div>
            <div style={{ fontSize: '1.85rem', fontWeight: 700, lineHeight: 1.1, color: 'var(--text-primary)' }}>
              {summary.evidenceGapsCount}
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
              Evidence Gaps
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Missing or expired{' '}
              <span style={{ color: '#f87171', fontWeight: 600, marginLeft: '4px' }}>
                &uarr; 2 from last month
              </span>
            </div>
          </div>
        </div>

        {/* Card 4: Regulatory Changes */}
        <div className="card" style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: '10px',
              backgroundColor: 'rgba(59, 130, 246, 0.12)',
              color: '#60a5fa',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <Scale size={24} />
          </div>
          <div>
            <div style={{ fontSize: '1.85rem', fontWeight: 700, lineHeight: 1.1, color: 'var(--text-primary)' }}>
              {summary.regulatoryChangesCount}
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
              Regulatory Changes
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              May affect your business{' '}
              <span style={{ color: '#60a5fa', fontWeight: 600, marginLeft: '4px' }}>
                {summary.regulatoryChangesRequireReview} require review
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Middle Section: Compliance Status Donut + Upcoming Deadlines Histogram */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
          gap: '24px',
        }}
      >
        {/* Compliance Status Donut Card */}
        <div className="card">
          <h2 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '20px' }}>
            Compliance Status
          </h2>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-around',
              gap: '24px',
              flexWrap: 'wrap',
            }}
          >
            {/* SVG Donut Chart */}
            <div style={{ position: 'relative', width: '160px', height: '160px' }}>
              <svg viewBox="0 0 36 36" style={{ width: '100%', height: '100%', transform: 'rotate(-90deg)' }}>
                {/* Background Ring */}
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#e2e8f0"
                  strokeWidth="3.2"
                />
                {/* Compliant Arc (75%) */}
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="3.2"
                  strokeDasharray="75, 100"
                  strokeLinecap="round"
                />
                {/* Due Soon Arc (15%) */}
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#f59e0b"
                  strokeWidth="3.2"
                  strokeDasharray="15, 100"
                  strokeDashoffset="-75"
                />
                {/* Overdue Arc (10%) */}
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="3.2"
                  strokeDasharray="10, 100"
                  strokeDashoffset="-90"
                />
              </svg>
              {/* Donut Center Label */}
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  pointerEvents: 'none',
                }}
              >
                <span style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)' }}>75%</span>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Compliant</span>
              </div>
            </div>

            {/* Donut Legend */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#10b981' }} />
                <span style={{ color: 'var(--text-secondary)' }}>Compliant</span>
                <strong style={{ marginLeft: 'auto', color: 'var(--text-primary)' }}>{summary.statusBreakdown.compliant}</strong>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#f59e0b' }} />
                <span style={{ color: 'var(--text-secondary)' }}>Due Soon</span>
                <strong style={{ marginLeft: 'auto', color: 'var(--text-primary)' }}>{summary.statusBreakdown.dueSoon}</strong>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#ef4444' }} />
                <span style={{ color: 'var(--text-secondary)' }}>Overdue</span>
                <strong style={{ marginLeft: 'auto', color: 'var(--text-primary)' }}>{summary.statusBreakdown.overdue}</strong>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#6366f1' }} />
                <span style={{ color: 'var(--text-secondary)' }}>Not Applicable</span>
                <strong style={{ marginLeft: 'auto', color: 'var(--text-primary)' }}>{summary.statusBreakdown.notApplicable}</strong>
              </div>
            </div>
          </div>
        </div>

        {/* Upcoming Deadlines Bar Chart Card */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)' }}>Upcoming Deadlines</h2>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.78rem',
                color: 'var(--text-secondary)',
                backgroundColor: 'rgba(0, 0, 0, 0.04)',
                padding: '4px 10px',
                borderRadius: '6px',
                border: '1px solid var(--border-default)',
                cursor: 'pointer',
              }}
            >
              <span>Next 6 months</span>
              <ChevronDown size={14} />
            </div>
          </div>

          {/* Bar Chart Visualization */}
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-end',
              justifyContent: 'space-between',
              height: '140px',
              paddingTop: '10px',
              gap: '12px',
            }}
          >
            {summary.upcomingDeadlines.map((item, idx) => {
              const maxVal = 14;
              const heightPercent = Math.round((item.count / maxVal) * 100);
              const isUrgent = item.count >= 8;
              const barColor = isUrgent ? (idx === 0 ? '#ef4444' : '#f59e0b') : '#10b981';

              return (
                <div
                  key={item.month}
                  style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '8px',
                    height: '100%',
                    justifyContent: 'flex-end',
                  }}
                >
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>{item.count}</span>
                  <div
                    style={{
                      width: '100%',
                      maxWidth: '32px',
                      height: `${heightPercent}%`,
                      backgroundColor: barColor,
                      borderRadius: '4px 4px 0 0',
                      transition: 'height 0.3s ease',
                    }}
                  />
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{item.month}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Section: Needs Attention Queue */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <h2 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)' }}>Needs Attention</h2>
          <span style={{ fontSize: '0.82rem', color: 'var(--brand-primary)', fontWeight: 600, cursor: 'pointer' }}>
            View all
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {summary.needsAttention.map((item) => {
            const isOverdue = item.status === 'OVERDUE';
            return (
              <div
                key={item.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '14px 16px',
                  backgroundColor: '#f8fafc',
                  borderRadius: '8px',
                  border: '1px solid var(--border-default)',
                  flexWrap: 'wrap',
                  gap: '12px',
                }}
              >
                {/* Left: Icon and Name */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px', minWidth: '220px', flex: 1 }}>
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '50%',
                      backgroundColor: isOverdue ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                      color: isOverdue ? '#f87171' : '#fbbf24',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    {isOverdue ? <AlertTriangle size={18} /> : <Clock size={18} />}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--text-primary)' }}>{item.title}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{item.authority}</div>
                  </div>
                </div>

                {/* Center: Type */}
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {item.type}
                </div>

                {/* Right Center: Due Date with Status Badge */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '0.85rem', color: isOverdue ? '#f87171' : '#fbbf24', fontWeight: 500 }}>
                    {item.dueDate}
                  </span>
                  <span className={`badge ${isOverdue ? 'badge-danger' : 'badge-warning'}`}>
                    {isOverdue ? 'Overdue' : 'Due Soon'}
                  </span>
                </div>

                {/* Right: Owner Avatar & Info */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div
                    style={{
                      width: '30px',
                      height: '30px',
                      borderRadius: '50%',
                      backgroundColor: '#1e3a5f',
                      color: '#93c5fd',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    {item.ownerInitials}
                  </div>
                  <div>
                    <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>{item.ownerName}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{item.ownerRole}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
