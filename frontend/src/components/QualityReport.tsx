import React, { useState } from 'react';

interface QualityIssue {
  row_index: number;
  issue_type: string;
  column_name: string;
  raw_value: string | null;
  details: string;
}

interface QualitySummary {
  missing_case_id_count: number;
  missing_activity_count: number;
  missing_timestamp_count: number;
  invalid_timestamp_count: number;
  duplicate_event_count: number;
}

interface QualityReportProps {
  report: {
    filename: string;
    total_rows: number;
    valid_rows: number;
    invalid_rows: number;
    summary: QualitySummary;
    issues: QualityIssue[];
    preview: Record<string, any>[];
  };
  onReset: () => void;
}

export const QualityReport: React.FC<QualityReportProps> = ({ report, onReset }) => {
  const [activeTab, setActiveTab] = useState<'summary' | 'issues' | 'preview'>('summary');

  const issueBadgeClass = (type: string) => {
    switch (type) {
      case 'MISSING_CASE_ID':
      case 'MISSING_ACTIVITY':
        return 'badge-danger';
      case 'INVALID_TIMESTAMP':
      case 'MISSING_TIMESTAMP':
        return 'badge-warning';
      case 'DUPLICATE_EVENT':
        return 'badge-warning';
      default:
        return 'badge-danger';
    }
  };

  return (
    <div className="glass-panel animate-fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Data Quality Report</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            File: <code style={{ color: 'var(--accent-cyan)' }}>{report.filename}</code>
          </p>
        </div>
        <button
          onClick={onReset}
          style={{
            background: 'var(--bg-card)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
            padding: '0.5rem 1rem',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '0.85rem'
          }}
        >
          Upload Another File
        </button>
      </div>

      {/* Summary KPI Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Events</div>
          <div className="stat-value">{report.total_rows.toLocaleString()}</div>
        </div>
        <div className="stat-card" style={{ borderColor: 'rgba(52, 211, 153, 0.4)' }}>
          <div className="stat-label" style={{ color: 'var(--accent-emerald)' }}>Valid Events</div>
          <div className="stat-value" style={{ color: 'var(--accent-emerald)' }}>
            {report.valid_rows.toLocaleString()}
          </div>
        </div>
        <div className="stat-card" style={{ borderColor: report.invalid_rows > 0 ? 'rgba(248, 113, 113, 0.4)' : 'var(--border-color)' }}>
          <div className="stat-label" style={{ color: report.invalid_rows > 0 ? 'var(--accent-rose)' : 'var(--text-secondary)' }}>
            Invalid / Flagged Rows
          </div>
          <div className="stat-value" style={{ color: report.invalid_rows > 0 ? 'var(--accent-rose)' : 'var(--text-primary)' }}>
            {report.invalid_rows.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '1rem', borderBottom: '1px solid var(--border-color)', marginBottom: '1rem' }}>
        <button
          onClick={() => setActiveTab('summary')}
          style={{
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'summary' ? '2px solid var(--accent-cyan)' : '2px solid transparent',
            color: activeTab === 'summary' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
            padding: '0.5rem 1rem',
            cursor: 'pointer',
            fontWeight: 600
          }}
        >
          Issue Breakdown ({report.issues.length})
        </button>
        <button
          onClick={() => setActiveTab('preview')}
          style={{
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'preview' ? '2px solid var(--accent-cyan)' : '2px solid transparent',
            color: activeTab === 'preview' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
            padding: '0.5rem 1rem',
            cursor: 'pointer',
            fontWeight: 600
          }}
        >
          Dataset Preview (First 10 Rows)
        </button>
      </div>

      {/* Tab Content: Summary */}
      {activeTab === 'summary' && (
        <div>
          {report.issues.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', background: 'rgba(52, 211, 153, 0.05)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(52, 211, 153, 0.2)' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>✅</div>
              <h3 style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>100% Data Quality Verification Passed</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                No missing required fields, unparseable timestamps, or duplicate events detected.
              </p>
            </div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Row #</th>
                    <th>Issue Type</th>
                    <th>Column</th>
                    <th>Details</th>
                    <th>Raw Value</th>
                  </tr>
                </thead>
                <tbody>
                  {report.issues.slice(0, 50).map((issue, i) => (
                    <tr key={i}>
                      <td><code>Line {issue.row_index}</code></td>
                      <td>
                        <span className={`badge ${issueBadgeClass(issue.issue_type)}`}>
                          {issue.issue_type}
                        </span>
                      </td>
                      <td><code>{issue.column_name}</code></td>
                      <td>{issue.details}</td>
                      <td><code>{issue.raw_value || 'NULL'}</code></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {report.issues.length > 50 && (
                <div style={{ padding: '0.75rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  Showing first 50 flagged rows out of {report.issues.length} total issues.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab Content: Preview */}
      {activeTab === 'preview' && (
        <div className="table-container">
          {report.preview.length > 0 ? (
            <table>
              <thead>
                <tr>
                  {Object.keys(report.preview[0]).map((key) => (
                    <th key={key}>{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {report.preview.map((row, idx) => (
                  <tr key={idx}>
                    {Object.values(row).map((val, valIdx) => (
                      <td key={valIdx}>{String(val)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p style={{ padding: '1rem', color: 'var(--text-secondary)' }}>No preview available.</p>
          )}
        </div>
      )}
    </div>
  );
};
