import React from 'react';

export const EvidenceSection: React.FC = () => {
  return (
    <section id="trust-evidence" className="mkt-section-padded" style={{ background: '#FFFFFF', borderTop: '1px solid #E2E8F0', borderBottom: '1px solid #E2E8F0' }}>
      <div className="mkt-container">
        <div className="mkt-section-header">
          <div className="mkt-badge-eyebrow">
            <span>EPISTEMIC GROUNDING</span>
          </div>
          <h2 className="mkt-section-title">
            Recommendations should have receipts.
          </h2>
          <p className="mkt-section-lead">
            ProcessLens is designed to connect every opportunity directly to available operational
            records, distinguish verified facts from assumptions, and expose uncertainty transparently.
          </p>
        </div>

        <div className="mkt-evidence-grid">
          {/* Opportunity Panel */}
          <div className="mkt-evidence-panel">
            <div className="mkt-evidence-panel-header">
              <div>
                <span style={{ fontSize: '12px', fontWeight: '700', color: '#0369A1', textTransform: 'uppercase' }}>
                  Rank #1 Opportunity
                </span>
                <h3 className="mkt-evidence-h3">Purchase Order Release Automation</h3>
              </div>
              <span className="mkt-pill mkt-pill-teal">Priority Score: 88.4</span>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '13px', color: '#475569', marginBottom: '8px' }}>
                <strong>Target Transition:</strong> <code>Quote Received → PO Released</code>
              </div>
              <p style={{ fontSize: '13.5px', color: '#334155', lineHeight: '1.5' }}>
                Significant administrative latency identified between quotation receipt and purchase
                order sign-off. High frequency and low variant complexity make this an ideal automation candidate.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
              <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '6px', padding: '10px' }}>
                <div style={{ fontSize: '11px', color: '#64748B', fontWeight: '600' }}>READINESS SCORE</div>
                <div style={{ fontSize: '18px', fontWeight: '700', color: '#0F766E' }}>82 / 100</div>
                <div style={{ fontSize: '11px', color: '#475569' }}>Standard variant path</div>
              </div>

              <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '6px', padding: '10px' }}>
                <div style={{ fontSize: '11px', color: '#64748B', fontWeight: '600' }}>EVIDENCE CONFIDENCE</div>
                <div style={{ fontSize: '18px', fontWeight: '700', color: '#0369A1' }}>91% High</div>
                <div style={{ fontSize: '11px', color: '#475569' }}>750 cases observed</div>
              </div>
            </div>

            <div style={{ background: '#FEF3C7', border: '1px solid #FDE68A', borderRadius: '6px', padding: '10px 14px', fontSize: '12px', color: '#92400E' }}>
              <strong>Economic Note:</strong> Return on investment is labelled <em>Unmonetised</em>.
              ProcessLens will not fabricate dollar savings until you supply your operational hourly cost parameters.
            </div>
          </div>

          {/* Evidence & Grounding Panel */}
          <div className="mkt-evidence-panel">
            <div className="mkt-evidence-panel-header">
              <div>
                <span style={{ fontSize: '12px', fontWeight: '700', color: '#0F766E', textTransform: 'uppercase' }}>
                  Auditable Evidence Dossier
                </span>
                <h3 className="mkt-evidence-h3">Epistemic Grounding Standard</h3>
              </div>
              <span className="mkt-pill mkt-pill-blue">Verified Manifest</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
              <div className="mkt-ledger-item">
                <span className="mkt-ledger-tag mkt-tag-fact">FACT</span>
                <div style={{ fontSize: '13px' }}>
                  <strong>750 of 750 cases</strong> executed the Quote Received to PO Released sequence.
                </div>
              </div>

              <div className="mkt-ledger-item">
                <span className="mkt-ledger-tag mkt-tag-fact">FACT</span>
                <div style={{ fontSize: '13px' }}>
                  <strong>Cumulative duration:</strong> 61,500,000s across entire observed history.
                </div>
              </div>

              <div className="mkt-ledger-item">
                <span className="mkt-ledger-tag mkt-tag-assumption">ASSUMPTION</span>
                <div style={{ fontSize: '13px' }}>
                  <strong>Transition Duration Proxy:</strong> Single-timestamp logs reflect total elapsed
                  interval, not purely active human touch time.
                </div>
              </div>

              <div className="mkt-ledger-item">
                <span className="mkt-ledger-tag mkt-tag-unknown">UNKNOWN</span>
                <div style={{ fontSize: '13px' }}>
                  <strong>Organizational Capacity Impact:</strong> Non-additive across shared resource pools.
                </div>
              </div>
            </div>

            <div className="mkt-derivation-formula">
              // Deterministic Derivation Expression
              transition_share = cumulative_transition_duration / cumulative_cycle_time * 100
            </div>

            <p style={{ fontSize: '12px', color: '#64748B', lineHeight: '1.45', margin: 0 }}>
              * Rule-based epistemic grounding ensures claims remain bounded by empirical event log records.
              ProcessLens enforces intellectual honesty over exaggerated promises.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
