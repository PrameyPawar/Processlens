import React, { useState } from 'react';
import { HealthStatus } from './components/HealthStatus';
import { FileUpload } from './components/FileUpload';
import { QualityReport } from './components/QualityReport';

export const App: React.FC = () => {
  const [report, setReport] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUploadSuccess = (data: any) => {
    setReport(data);
    setError(null);
  };

  const handleUploadError = (errorMsg: string) => {
    setError(errorMsg);
  };

  const handleReset = () => {
    setReport(null);
    setError(null);
  };

  return (
    <div className="container">
      {/* Header Bar */}
      <header className="header-bar">
        <div>
          <div className="brand-title">
            🔍 ProcessLens
          </div>
          <p className="brand-subtitle">
            Operational Event Data → Evidence → Economics → Prioritized Action
          </p>
        </div>
        <HealthStatus />
      </header>

      {/* Main Content Area */}
      <main>
        {error && (
          <div
            className="animate-fade-in"
            style={{
              background: 'rgba(248, 113, 113, 0.15)',
              border: '1px solid rgba(248, 113, 113, 0.4)',
              color: 'var(--accent-rose)',
              padding: '1rem',
              borderRadius: 'var(--radius-md)',
              marginBottom: '1.5rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <div>
              <strong>Ingestion Error:</strong> {error}
            </div>
            <button
              onClick={() => setError(null)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent-rose)',
                cursor: 'pointer',
                fontWeight: 700,
                fontSize: '1rem'
              }}
            >
              ✕
            </button>
          </div>
        )}

        {!report ? (
          <div className="glass-panel animate-fade-in">
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem' }}>
              Phase 1: CSV Event Log Ingestion & Quality Validation
            </h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
              Upload an operational event log in CSV format. ProcessLens will inspect mandatory schema fields (<code>case_id</code>, <code>activity</code>, <code>timestamp</code>), validate data formatting, and generate an auditable Data Quality Report without dropping bad records silently.
            </p>
            <FileUpload
              onUploadSuccess={handleUploadSuccess}
              onUploadError={handleUploadError}
            />
          </div>
        ) : (
          <QualityReport report={report} onReset={handleReset} />
        )}
      </main>
    </div>
  );
};

export default App;
