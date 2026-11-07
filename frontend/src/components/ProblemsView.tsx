import React from 'react';
import { ProblemDetectionResult, FindingCategory, SignalLevel, EvidenceStrength } from '../types/api';
import { AlertTriangle, CheckCircle, Info } from 'lucide-react';

interface ProblemsViewProps {
  problems: ProblemDetectionResult;
}

export const ProblemsView: React.FC<ProblemsViewProps> = ({ problems }) => {
  const { summary, findings } = problems;

  const categoryBadgeClass = (category: FindingCategory) => {
    switch (category) {
      case 'DURATION_CONCENTRATION':
        return 'badge-warning';
      case 'REPETITION':
        return 'badge-danger';
      case 'CYCLE_TIME_OUTLIER':
        return 'badge-purple';
      case 'PATH_VARIATION':
        return 'badge-info';
      default:
        return 'badge-neutral';
    }
  };

  const signalBadgeClass = (signal: SignalLevel) => {
    switch (signal) {
      case 'HIGH':
        return 'badge-danger';
      case 'MEDIUM':
        return 'badge-warning';
      case 'LOW':
        return 'badge-neutral';
      case 'INFO':
        return 'badge-info';
    }
  };

  const evidenceStrengthBadgeClass = (strength: EvidenceStrength) => {
    switch (strength) {
      case 'HIGH':
        return 'badge-success';
      case 'MODERATE':
        return 'badge-warning';
      case 'LIMITED':
        return 'badge-danger';
    }
  };

  return (
    <section className="glass-panel animate-fade-in" aria-label="Detected Problems and Operational Signals">
      <div className="section-header">
        <div>
          <h2 className="section-title">Phase 4: Problem Detection & Operational Signals</h2>
          <p className="section-subtitle">
            Deterministic signal detection across {summary.evaluated_cases_count} evaluated cases. Identifies pattern magnitude without ungrounded causal claims.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {summary.reconciliation.reconciled ? (
            <span className="badge badge-success" title="Sum of transitions reconciles with total case cycle time">
              <CheckCircle size={14} /> Accounting Reconciled
            </span>
          ) : (
            <span className="badge badge-danger">
              <AlertTriangle size={14} /> Accounting Discrepancy Flagged
            </span>
          )}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Detected Signals</div>
          <div className="stat-value text-amber">{findings.length}</div>
          <div className="stat-caption">Evaluated across 5 deterministic rules</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">High / Prominent Signals</div>
          <div className="stat-value text-rose">
            {summary.high_signal_count ?? summary.signal_level_counts?.['HIGH'] ?? 0}
          </div>
          <div className="stat-caption">Concentration magnitude &gt; 25% or prominent loops</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">High Evidence Strength</div>
          <div className="stat-value text-emerald">
            {findings.filter((f) => f.evidence_strength === 'HIGH').length}
          </div>
          <div className="stat-caption">Statistical basis &ge; 30 distinct cases</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Accounting Discrepancy</div>
          <div className="stat-value">
            {summary.reconciliation.discrepancy_percentage !== undefined
              ? `${summary.reconciliation.discrepancy_percentage.toFixed(2)}%`
              : summary.reconciliation.relative_discrepancy_percentage !== undefined
              ? `${summary.reconciliation.relative_discrepancy_percentage.toFixed(2)}%`
              : '0.00%'}
          </div>
          <div className="stat-caption">
            {summary.reconciliation.limitation_note || summary.reconciliation.evaluation_note || 'Reconciled within tolerance'}
          </div>
        </div>
      </div>

      {/* Findings List */}
      <div className="findings-container">
        {findings.length === 0 ? (
          <div className="empty-state">
            <CheckCircle size={32} className="text-emerald" />
            <p>No operational bottlenecks, extreme duration concentrations, or repetition signals exceeded detection thresholds.</p>
          </div>
        ) : (
          findings.map((finding) => (
            <div key={finding.id} className="finding-card">
              <div className="finding-header">
                <div>
                  <div className="finding-tags">
                    <span className={`badge ${categoryBadgeClass(finding.category)}`}>
                      {finding.category.replace(/_/g, ' ')}
                    </span>
                    <span className={`badge ${signalBadgeClass(finding.signal_level)}`}>
                      Signal: {finding.signal_level}
                    </span>
                    <span className={`badge ${evidenceStrengthBadgeClass(finding.evidence_strength)}`}>
                      Evidence: {finding.evidence_strength}
                    </span>
                    <code className="text-muted text-xs">Rule: {finding.rule || finding.rule_id}</code>
                  </div>
                  <h3 className="finding-title">{finding.title}</h3>
                </div>
              </div>

              <div className="finding-explanation-block">
                <div className="finding-section-label text-xs font-semibold text-muted mb-1">Observed Operational Pattern:</div>
                <p className="finding-explanation">{finding.explanation}</p>
              </div>

              {/* Supporting Quantitative Evidence */}
              {Object.keys(finding.metrics || {}).length > 0 && (
                <div className="finding-evidence-block mb-3">
                  <div className="finding-section-label text-xs font-semibold text-muted mb-2">Empirical Quantitative Evidence:</div>
                  <div className="finding-metrics-grid">
                    {Object.entries(finding.metrics).map(([key, val]) => {
                      const displayVal =
                        typeof val === 'number'
                          ? val % 1 === 0
                            ? val.toLocaleString()
                            : val.toFixed(2)
                          : Array.isArray(val)
                          ? `${val.length} cases (${val.slice(0, 3).join(', ')}${val.length > 3 ? '...' : ''})`
                          : String(val);
                      return (
                        <div key={key} className="metric-chip" title={`${key.replace(/_/g, ' ')}: ${Array.isArray(val) ? val.join(', ') : val}`}>
                          <span className="metric-key">{key.replace(/_/g, ' ')}:</span>
                          <strong className="metric-val">{displayVal}</strong>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Explicit Boundaries & Limitations */}
              {finding.limitations && finding.limitations.length > 0 && (
                <div className="finding-limitations">
                  <div className="limitations-header">
                    <Info size={13} className="text-muted" />
                    <span>Explicit Boundaries & Non-Assertions</span>
                  </div>
                  <ul className="limitations-list">
                    {finding.limitations.map((lim, i) => (
                      <li key={i}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </section>
  );
};
