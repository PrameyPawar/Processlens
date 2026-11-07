import React from 'react';
import { DataQualityReport } from '../../types/api';
import { ShieldCheck, AlertCircle, CheckCircle2 } from 'lucide-react';

interface DataQualityChartProps {
  report: DataQualityReport;
}

export const DataQualityChart: React.FC<DataQualityChartProps> = ({ report }) => {
  const { total_rows, valid_rows, invalid_rows, summary } = report;
  const validPct = total_rows > 0 ? (valid_rows / total_rows) * 100 : 0;
  const potentialDuplicates = summary.potential_duplicate_event_count ?? 0;
  const isAllValid = invalid_rows === 0;
  const isAllClear = isAllValid && potentialDuplicates === 0;

  const checks = [
    { label: 'Missing Case ID', count: summary.missing_case_id_count, key: 'case_id' },
    { label: 'Missing Activity', count: summary.missing_activity_count, key: 'activity' },
    { label: 'Missing Timestamp', count: summary.missing_timestamp_count, key: 'timestamp_missing' },
    { label: 'Invalid Timestamp', count: summary.invalid_timestamp_count, key: 'timestamp_invalid' },
    { label: 'Confirmed Duplicate IDs', count: summary.duplicate_event_count, key: 'duplicate' },
    { label: 'Possible Duplicate Matches', count: potentialDuplicates, key: 'possible_duplicate', warning: true },
    { label: 'Malformed Rows', count: summary.malformed_row_count ?? 0, key: 'malformed' },
  ];

  return (
    <div className="chart-container" aria-label="Data Quality Chart">
      <div className="chart-header">
        <div>
          <div className="chart-title">
            <ShieldCheck size={16} className={isAllClear ? 'text-emerald' : 'text-amber'} />
            <span>Telemetry Health & Ingestion Completeness</span>
          </div>
          <div className="chart-subtitle">
            {valid_rows.toLocaleString()} of {total_rows.toLocaleString()} events ({validPct.toFixed(1)}%) meet canonical standards
          </div>
        </div>

        <div className={`badge ${isAllClear ? 'badge-success' : 'badge-warning'}`}>
          {isAllClear ? (
            <>
              <CheckCircle2 size={13} /> 100% Ingestion Integrity
            </>
          ) : invalid_rows > 0 ? (
            <>
              <AlertCircle size={13} /> {invalid_rows.toLocaleString()} Flawed Rows Isolated
            </>
          ) : (
            <>
              <AlertCircle size={13} /> {potentialDuplicates.toLocaleString()} Possible Matches Need Review
            </>
          )}
        </div>
      </div>

      {/* Stacked Integrity Bar */}
      <div className="quality-stacked-bar-container">
        <div className="bar-track quality-track">
          <div
            className="bar-fill bar-emerald"
            style={{ width: `${validPct}%` }}
            title={`Valid: ${valid_rows} (${validPct.toFixed(1)}%)`}
          />
          {invalid_rows > 0 && (
            <div
              className="bar-fill bar-rose"
              style={{ width: `${100 - validPct}%` }}
              title={`Flagged / Excluded: ${invalid_rows}`}
            />
          )}
        </div>
        <div className="quality-bar-legend">
          <div className="legend-item">
            <span className="legend-dot dot-emerald" />
            <span>Valid Events: <strong>{valid_rows.toLocaleString()}</strong> ({validPct.toFixed(1)}%)</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot dot-rose" />
            <span>Isolated / Excluded: <strong>{invalid_rows.toLocaleString()}</strong></span>
          </div>
        </div>
      </div>

      {/* Individual Rule Checks Breakdown */}
      <div className="quality-rules-grid">
        {checks.map((c) => {
          const hasIssues = c.count > 0;
          return (
            <div key={c.key} className={`quality-rule-item ${hasIssues ? (c.warning ? 'rule-has-warning' : 'rule-has-defects') : 'rule-passed'}`}>
              <div className="rule-item-top">
                <span className="rule-name">{c.label}</span>
                <span className={`rule-count-badge ${hasIssues ? (c.warning ? 'badge-warning' : 'badge-rose') : 'badge-emerald'}`}>
                  {c.count > 0 ? `${c.count} ${c.warning ? 'to review' : 'flagged'}` : 'Pass (0)'}
                </span>
              </div>
              <div className="rule-status-text">
                {hasIssues
                  ? c.warning
                    ? 'Warning only; matching rows lack enough source IDs to confirm identity'
                    : 'Rows isolated from trace reconstruction'
                  : 'Canonical field verified'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
