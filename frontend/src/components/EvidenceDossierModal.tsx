import React, { useState } from 'react';
import { OpportunityEvidenceDossier, EvidenceAuditManifest, EpistemicType } from '../types/api';
import { X, ShieldCheck } from 'lucide-react';

interface EvidenceDossierModalProps {
  dossier: OpportunityEvidenceDossier;
  manifest?: EvidenceAuditManifest;
  onClose: () => void;
}

export const EvidenceDossierModal: React.FC<EvidenceDossierModalProps> = ({
  dossier,
  manifest,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'anchors' | 'exemplars' | 'epistemic' | 'derivations'>('anchors');

  const epistemicBadgeClass = (type: EpistemicType) => {
    switch (type) {
      case 'FACT':
        return 'badge-success';
      case 'ASSUMPTION':
        return 'badge-warning';
      case 'HYPOTHESIS':
        return 'badge-purple';
      case 'ESTIMATE':
        return 'badge-info';
      case 'DECISION':
        return 'badge-neutral';
      default:
        return 'badge-neutral';
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose} aria-label="Evidence Dossier Dialog">
      <div className="modal-content glass-panel animate-fade-in" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div>
            <div className="modal-meta-row">
              <span className="badge badge-info">{dossier.portfolio_cohort}</span>
              <span className="badge badge-warning">{dossier.archetype}</span>
              <code className="text-muted text-xs">Opportunity: {dossier.opportunity_id}</code>
            </div>
            <h2 className="modal-title">Phase 9 Evidence Audit Dossier</h2>
            <p className="modal-subtitle">
              Target Entity: <code>{dossier.target_entity}</code> | Exemplar Policy: {dossier.exemplar_selection_policy}
            </p>
          </div>
          <button type="button" className="btn-icon" onClick={onClose} aria-label="Close Modal">
            <X size={20} />
          </button>
        </div>

        {/* Cryptographic Manifest Bar */}
        {manifest && (
          <div className="manifest-bar">
            <div>
              <strong>SHA-256:</strong> <code>{manifest.source_file_sha256}</code>
            </div>
            <div className="manifest-details">
              <span>{manifest.source_filename} ({manifest.source_file_size_bytes} bytes)</span>
              <span>Reconciliation: <strong className="text-emerald">{manifest.reconciliation_status}</strong></span>
              <span>Complete Cases: <strong>{manifest.complete_cases_count}</strong></span>
            </div>
          </div>
        )}

        {/* Modal Tabs */}
        <div className="tab-bar">
          <button
            type="button"
            className={`tab-btn ${activeTab === 'anchors' ? 'active' : ''}`}
            onClick={() => setActiveTab('anchors')}
          >
            Row Anchors ({dossier.primary_source_rows.length})
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'exemplars' ? 'active' : ''}`}
            onClick={() => setActiveTab('exemplars')}
          >
            Case Exemplars ({dossier.case_exemplars.length})
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'epistemic' ? 'active' : ''}`}
            onClick={() => setActiveTab('epistemic')}
          >
            Epistemic Ledger ({dossier.epistemic_ledger.length})
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'derivations' ? 'active' : ''}`}
            onClick={() => setActiveTab('derivations')}
          >
            Formula Derivations ({dossier.derivations.length})
          </button>
        </div>

        {/* Tab 1: Row Anchors */}
        {activeTab === 'anchors' && (
          <div className="tab-pane animate-fade-in">
            <div className="table-responsive" style={{ maxHeight: '380px' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Data Row</th>
                    <th>CSV Line</th>
                    <th>Case ID</th>
                    <th>Activity</th>
                    <th>Raw Timestamp</th>
                    <th>Resource</th>
                    <th>Role in Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {dossier.primary_source_rows.map((row, idx) => (
                    <tr key={idx}>
                      <td><code>Row #{row.row_index}</code></td>
                      <td><code>Line #{row.csv_line_number}</code></td>
                      <td><code>{row.case_id || 'N/A'}</code></td>
                      <td><span className="badge badge-neutral">{row.activity || 'N/A'}</span></td>
                      <td className="code-subtle">{row.timestamp_raw || 'N/A'}</td>
                      <td>{row.resource || '—'}</td>
                      <td><span className="badge badge-info">{row.role_in_evidence}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="caption-notice">
              * Exact 1-based row anchors map directly to physical source CSV line numbers, establishing complete audit traceability.
            </p>
          </div>
        )}

        {/* Tab 2: Case Trace Exemplars */}
        {activeTab === 'exemplars' && (
          <div className="tab-pane animate-fade-in">
            {dossier.case_exemplars.map((ex, idx) => (
              <div key={idx} className="exemplar-card">
                <div className="exemplar-header">
                  <div>
                    <strong>Case: <code>{ex.case_id}</code></strong>
                    {ex.variant_id && <span className="badge badge-neutral" style={{ marginLeft: '0.5rem' }}>{ex.variant_id}</span>}
                  </div>
                  <span className="badge badge-info">
                    Cycle Time: {(ex.cycle_time_seconds / 3600).toFixed(1)} hrs ({ex.cycle_time_seconds.toFixed(0)}s)
                  </span>
                </div>
                <p className="exemplar-reason">{ex.relevance_reason}</p>
                <div className="table-responsive" style={{ maxHeight: '200px' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Line #</th>
                        <th>Activity</th>
                        <th>Timestamp</th>
                        <th>Role</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ex.events.map((ev, eIdx) => (
                        <tr key={eIdx}>
                          <td><code>Line #{ev.csv_line_number}</code></td>
                          <td><strong>{ev.activity}</strong></td>
                          <td className="code-subtle">{ev.timestamp_raw}</td>
                          <td><span className="badge badge-neutral">{ev.role_in_evidence}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Tab 3: Epistemic Ledger */}
        {activeTab === 'epistemic' && (
          <div className="tab-pane animate-fade-in">
            <div className="table-responsive" style={{ maxHeight: '380px' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Epistemic Status</th>
                    <th>Assertion / Metric Statement</th>
                    <th>Source or Basis</th>
                    <th>Provenance Details</th>
                  </tr>
                </thead>
                <tbody>
                  {dossier.epistemic_ledger.map((item) => (
                    <tr key={item.item_id}>
                      <td>
                        <span className={`badge ${epistemicBadgeClass(item.epistemic_type)}`}>
                          {item.epistemic_type}
                        </span>
                      </td>
                      <td>{item.statement}</td>
                      <td><code>{item.source_or_basis}</code></td>
                      <td className="text-muted text-xs">{item.provenance_details || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="caption-notice">
              * Epistemic discipline: Strictly separates measured operational FACTS from ASSUMPTIONS, HYPOTHESES, ESTIMATES, and human DECISIONS.
            </p>
          </div>
        )}

        {/* Tab 4: Formula Derivations */}
        {activeTab === 'derivations' && (
          <div className="tab-pane animate-fade-in">
            <div className="table-responsive" style={{ maxHeight: '380px' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Metric Name</th>
                    <th>Formula Expression</th>
                    <th>Calculated Value</th>
                    <th>Reproducible?</th>
                    <th>Input Parameters</th>
                  </tr>
                </thead>
                <tbody>
                  {dossier.derivations.map((d, idx) => (
                    <tr key={idx}>
                      <td><strong>{d.metric_name}</strong></td>
                      <td><code>{d.formula_expression}</code></td>
                      <td>
                        <strong>{typeof d.calculated_value === 'number' ? d.calculated_value.toFixed(2) : d.calculated_value}</strong> {d.unit}
                      </td>
                      <td>
                        {d.is_reproducible ? (
                          <span className="badge badge-success"><ShieldCheck size={12} /> Verified</span>
                        ) : (
                          <span className="badge badge-warning">Non-deterministic</span>
                        )}
                      </td>
                      <td className="text-xs">
                        <code>{JSON.stringify(d.input_parameters)}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Boundaries & Limitations footer */}
        {dossier.boundary_limitations.length > 0 && (
          <div className="modal-limitations">
            <strong>Evidence Boundary Scope:</strong>
            <ul>
              {dossier.boundary_limitations.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Modal Footer */}
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Close Dossier
          </button>
        </div>
      </div>
    </div>
  );
};
