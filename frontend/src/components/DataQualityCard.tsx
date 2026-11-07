import React, { useState } from 'react';
import { DataQualityReport } from '../types/api';
import { CheckCircle2, AlertTriangle, Database } from 'lucide-react';

interface DataQualityCardProps {
  report: DataQualityReport;
}

export const DataQualityCard: React.FC<DataQualityCardProps> = ({ report }) => {
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
      case 'MALFORMED_ROW':
        return 'badge-info';
      case 'POTENTIAL_DUPLICATE_EVENT':
        return 'badge-warning';
      default:
        return 'badge-danger';
    }
  };

  const potentialDuplicates = report.summary.potential_duplicate_event_count ?? 0;

  return (
    <section className="glass-panel animate-fade-in" aria-label="Data Quality Report">
      <div className="section-header">
        <div>
          <h2 className="section-title">Phase 1: Ingestion & Data Quality Report</h2>
          <p className="section-subtitle">
            Source file: <code className="code-highlight">{report.filename}</code>
          </p>
        </div>
        <div>
          {report.invalid_rows > 0 ? (
            <span className="badge badge-warning">
              <AlertTriangle size={14} /> {report.invalid_rows} Invalid Records Detected
            </span>
          ) : potentialDuplicates > 0 ? (
            <span className="badge badge-warning">
              <AlertTriangle size={14} /> {potentialDuplicates} Possible Duplicate Matches to Review
            </span>
          ) : (
            <span className="badge badge-success">
              <CheckCircle2 size={14} /> 100% Schema Valid
            </span>
          )}
        </div>
      </div>

      {/* Primary KPI Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Source Rows</div>
          <div className="stat-value">{report.total_rows.toLocaleString()}</div>
          <div className="stat-caption">Events parsed from CSV</div>
        </div>
        <div className="stat-card border-emerald">
          <div className="stat-label text-emerald">Valid Events</div>
          <div className="stat-value text-emerald">{report.valid_rows.toLocaleString()}</div>
          <div className="stat-caption">
            {report.total_rows > 0 ? ((report.valid_rows / report.total_rows) * 100).toFixed(1) : 0}% of input
          </div>
        </div>
        <div className={`stat-card ${report.invalid_rows > 0 ? 'border-rose' : ''}`}>
          <div className={`stat-label ${report.invalid_rows > 0 ? 'text-rose' : ''}`}>Invalid Rows</div>
          <div className={`stat-value ${report.invalid_rows > 0 ? 'text-rose' : ''}`}>
            {report.invalid_rows.toLocaleString()}
          </div>
          <div className="stat-caption">Confirmed data errors</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Confirmed Duplicate IDs</div>
          <div className="stat-value text-amber">{report.summary.duplicate_event_count.toLocaleString()}</div>
          <div className="stat-caption">Repeated source event ID within a case</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Possible Duplicate Matches</div>
          <div className="stat-value text-amber">{potentialDuplicates.toLocaleString()}</div>
          <div className="stat-caption">No source event ID to confirm identity</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="tab-bar">
        <button
          type="button"
          className={`tab-btn ${activeTab === 'summary' ? 'active' : ''}`}
          onClick={() => setActiveTab('summary')}
        >
          Quality Breakdown
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === 'issues' ? 'active' : ''}`}
          onClick={() => setActiveTab('issues')}
        >
          Flagged Issues ({report.issues.length})
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === 'preview' ? 'active' : ''}`}
          onClick={() => setActiveTab('preview')}
        >
          Data Preview ({report.preview.length})
        </button>
      </div>

      {/* Tab 1: Summary */}
      {activeTab === 'summary' && (
        <div className="tab-pane animate-fade-in">
          <table className="data-table">
            <thead>
              <tr>
                <th>Data Quality Check</th>
                <th>Validation Rule</th>
                <th>Defect Count</th>
                <th>Impact on Downstream Analysis</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Missing Case ID</td>
                <td>Mandatory canonical column <code>case_id</code></td>
                <td>
                  <span className={report.summary.missing_case_id_count > 0 ? 'text-rose font-bold' : 'text-muted'}>
                    {report.summary.missing_case_id_count}
                  </span>
                </td>
                <td>Row cannot be attached to any process trace; excluded from case sequence.</td>
              </tr>
              <tr>
                <td>Missing Activity</td>
                <td>Mandatory canonical column <code>activity</code></td>
                <td>
                  <span className={report.summary.missing_activity_count > 0 ? 'text-rose font-bold' : 'text-muted'}>
                    {report.summary.missing_activity_count}
                  </span>
                </td>
                <td>Activity step unknown; case flagged incomplete and excluded from variants.</td>
              </tr>
              <tr>
                <td>Missing Timestamp</td>
                <td>Mandatory canonical column <code>timestamp</code></td>
                <td>
                  <span className={report.summary.missing_timestamp_count > 0 ? 'text-rose font-bold' : 'text-muted'}>
                    {report.summary.missing_timestamp_count}
                  </span>
                </td>
                <td>Chronological ordering impossible; case flagged incomplete.</td>
              </tr>
              <tr>
                <td>Invalid Timestamp Format</td>
                <td>ISO-8601 or standard datetime parseable string</td>
                <td>
                  <span className={report.summary.invalid_timestamp_count > 0 ? 'text-rose font-bold' : 'text-muted'}>
                    {report.summary.invalid_timestamp_count}
                  </span>
                </td>
                <td>Unparseable datetime; excluded from cycle-time derivations.</td>
              </tr>
              <tr>
                <td>Confirmed Duplicate Event IDs</td>
                <td>Same case and source event ID</td>
                <td>
                  <span className={report.summary.duplicate_event_count > 0 ? 'text-amber font-bold' : 'text-muted'}>
                    {report.summary.duplicate_event_count}
                  </span>
                </td>
                <td>Repeated source identity; retained and flagged in trace evidence.</td>
              </tr>
              <tr>
                <td>Possible Duplicate Matches</td>
                <td>Same case, activity, and timestamp with no source event ID</td>
                <td>
                  <span className={potentialDuplicates > 0 ? 'text-amber font-bold' : 'text-muted'}>
                    {potentialDuplicates}
                  </span>
                </td>
                <td>Warning only: rows stay valid and are not excluded from analytics because identity is unknown.</td>
              </tr>
              <tr>
                <td>Malformed Rows</td>
                <td>CSV row must not contain values beyond its header columns</td>
                <td>
                  <span className={(report.summary.malformed_row_count ?? 0) > 0 ? 'text-rose font-bold' : 'text-muted'}>
                    {report.summary.malformed_row_count ?? 0}
                  </span>
                </td>
                <td>Extra cells are reported and excluded from process traces.</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 2: Flagged Issues */}
      {activeTab === 'issues' && (
        <div className="tab-pane animate-fade-in">
          {report.issues.length === 0 ? (
            <div className="empty-state">
              <CheckCircle2 size={32} className="text-emerald" />
              <p>No schema defects, row errors, or duplicate identity warnings detected in this dataset.</p>
            </div>
          ) : (
            <div className="table-responsive" style={{ maxHeight: '350px' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Row #</th>
                    <th>Issue Type</th>
                    <th>Column</th>
                    <th>Raw Value</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {report.issues.map((issue, idx) => (
                    <tr key={`${issue.row_index}-${idx}`}>
                      <td><code>#{issue.row_index}</code></td>
                      <td>
                        <span className={`badge ${issueBadgeClass(issue.issue_type)}`}>
                          {issue.issue_type}
                        </span>
                      </td>
                      <td><code>{issue.column_name}</code></td>
                      <td>
                        <span className="code-subtle">{issue.raw_value === null ? 'null' : issue.raw_value}</span>
                      </td>
                      <td>{issue.details}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Preview */}
      {activeTab === 'preview' && (
        <div className="tab-pane animate-fade-in">
          {report.preview.length === 0 ? (
            <div className="empty-state">
              <Database size={32} className="text-muted" />
              <p>No preview rows available.</p>
            </div>
          ) : (
            <div className="table-responsive" style={{ maxHeight: '350px' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    {Object.keys(report.preview[0] || {}).map((col) => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {report.preview.map((row, idx) => (
                    <tr key={idx}>
                      {Object.keys(report.preview[0] || {}).map((col) => (
                        <td key={col}>
                          {row[col] !== null && row[col] !== undefined ? String(row[col]) : <span className="text-muted">null</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
};
