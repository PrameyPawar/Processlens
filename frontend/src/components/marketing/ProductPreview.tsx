import React, { useState } from 'react';
import {
  FileCheck,
  Info,
  ExternalLink,
} from 'lucide-react';

interface ProductPreviewProps {
  onNavigate: (path: string) => void;
  isAuthenticated?: boolean;
}

export const ProductPreview: React.FC<ProductPreviewProps> = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState<'spotlight' | 'bottlenecks' | 'evidence'>('spotlight');

  return (
    <section id="product-preview" className="mkt-preview-section">
      <div className="mkt-container-wide">
        <div className="mkt-section-header" style={{ marginBottom: '32px' }}>
          <div className="mkt-badge-eyebrow" style={{ marginBottom: '12px' }}>
            <span>SAMPLE DATASET DEMONSTRATION</span>
          </div>
          <h2 className="mkt-section-title">
            The analytics interface behind the decision.
          </h2>
          <p className="mkt-section-lead">
            Explore how ProcessLens analyzes operational event logs, detects bottlenecks,
            and produces verifiable evidence dossiers.
          </p>
        </div>

        {/* Product Preview Browser Container */}
        <div className="mkt-preview-card">
          {/* Browser Chrome Header */}
          <div className="mkt-browser-chrome">
            <div className="mkt-browser-dots" aria-hidden="true">
              <span className="mkt-dot mkt-dot-red" />
              <span className="mkt-dot mkt-dot-yellow" />
              <span className="mkt-dot mkt-dot-green" />
            </div>

            <div className="mkt-browser-pill">
              <span style={{ color: '#0F766E' }}>●</span>
              <span>processlens.internal/workspace/manufacturing_quickstart.csv</span>
            </div>

            <div className="mkt-preview-badge-status">
              <FileCheck size={13} />
              100% Schema Valid (6,000 Events)
            </div>
          </div>

          {/* Product Body */}
          <div className="mkt-preview-body">
            {/* KPI Summary Ribbon */}
            <div className="mkt-preview-ribbon">
              <div className="mkt-preview-kpi">
                <div className="mkt-preview-kpi-label">Cases Analysed</div>
                <div className="mkt-preview-kpi-value">750</div>
                <div className="mkt-preview-kpi-note">100% complete paths</div>
              </div>

              <div className="mkt-preview-kpi">
                <div className="mkt-preview-kpi-label">Schema Validity</div>
                <div className="mkt-preview-kpi-value" style={{ color: '#0F766E' }}>100.0%</div>
                <div className="mkt-preview-kpi-note">0 rejected rows</div>
              </div>

              <div className="mkt-preview-kpi">
                <div className="mkt-preview-kpi-label">Median Cycle Time</div>
                <div className="mkt-preview-kpi-value">36.9h</div>
                <div className="mkt-preview-kpi-note">132,983s elapsed</div>
              </div>

              <div className="mkt-preview-kpi">
                <div className="mkt-preview-kpi-label">P90 Cycle Time</div>
                <div className="mkt-preview-kpi-value" style={{ color: '#0369A1' }}>53.3h</div>
                <div className="mkt-preview-kpi-note">Longest case 81.4h</div>
              </div>

              <div className="mkt-preview-kpi">
                <div className="mkt-preview-kpi-label">Prioritised Levers</div>
                <div className="mkt-preview-kpi-value" style={{ color: '#7C3AED' }}>2</div>
                <div className="mkt-preview-kpi-note">3 operational signals</div>
              </div>
            </div>

            {/* Interactive Preview Tabs */}
            <div className="mkt-preview-tabs" role="tablist" aria-label="Product Demonstration Views">
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'spotlight'}
                className={`mkt-preview-tab-btn ${activeTab === 'spotlight' ? 'active' : ''}`}
                onClick={() => setActiveTab('spotlight')}
              >
                Recommended Investigation
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'bottlenecks'}
                className={`mkt-preview-tab-btn ${activeTab === 'bottlenecks' ? 'active' : ''}`}
                onClick={() => setActiveTab('bottlenecks')}
              >
                Detected Bottlenecks & Signals
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'evidence'}
                className={`mkt-preview-tab-btn ${activeTab === 'evidence' ? 'active' : ''}`}
                onClick={() => setActiveTab('evidence')}
              >
                Epistemic Evidence Dossier
              </button>
            </div>

            {/* TAB 1: Spotlight Decision View */}
            {activeTab === 'spotlight' && (
              <div className="mkt-preview-grid">
                {/* Left Panel: Primary Spotlight Opportunity */}
                <div className="mkt-preview-panel">
                  <div className="mkt-preview-panel-title">
                    <span>Rank #1 Priority Opportunity</span>
                    <span className="mkt-pill mkt-pill-teal">Score: 88.4 / 100</span>
                  </div>

                  <div className="mkt-spotlight-box">
                    <div className="mkt-spotlight-tag">Target Transition</div>
                    <div className="mkt-spotlight-name">Quote Received → PO Released</div>
                    <p className="mkt-spotlight-desc">
                      Transition consumes 58.7% of total process cycle time across all 750 observed cases.
                      Identified as an operational delay archetype with high standardization potential.
                    </p>

                    <div className="mkt-factor-pills">
                      <span className="mkt-pill mkt-pill-blue">Automation Readiness: 82%</span>
                      <span className="mkt-pill mkt-pill-teal">Confidence: 91% (High)</span>
                      <span className="mkt-pill mkt-pill-amber">Economic Return: Unmonetised</span>
                    </div>
                  </div>

                  <div style={{ background: '#FEF3C7', border: '1px solid #FDE68A', borderRadius: '6px', padding: '10px 14px', fontSize: '12px', color: '#92400E', display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <Info size={16} style={{ flexShrink: 0 }} />
                    <span>
                      <strong>Transparent Economics:</strong> Return on investment remains explicitly
                      unknown until company-specific hourly labor and volume cost inputs are supplied.
                    </span>
                  </div>
                </div>

                {/* Right Panel: Top Impact Signals */}
                <div className="mkt-preview-panel">
                  <div className="mkt-preview-panel-title">
                    <span>Operational Signal Breakdown</span>
                    <span style={{ fontSize: '12px', color: '#64748B' }}>Deterministic Engine</span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div style={{ border: '1px solid #E2E8F0', borderRadius: '6px', padding: '12px', background: '#FFFFFF' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '13px', fontWeight: '600', color: '#0F172A' }}>Quote to PO Latency</span>
                        <span style={{ fontSize: '12px', fontWeight: '700', color: '#B91C1C' }}>21.6h Median</span>
                      </div>
                      <div style={{ height: '6px', background: '#F1F5F9', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ width: '58.7%', height: '100%', background: '#0284C7' }} />
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748B', marginTop: '6px' }}>58.7% of total order duration</div>
                    </div>

                    <div style={{ border: '1px solid #E2E8F0', borderRadius: '6px', padding: '12px', background: '#FFFFFF' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '13px', fontWeight: '600', color: '#0F172A' }}>Assembly Queue Wait</span>
                        <span style={{ fontSize: '12px', fontWeight: '700', color: '#B45309' }}>8.2h Median</span>
                      </div>
                      <div style={{ height: '6px', background: '#F1F5F9', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ width: '22.3%', height: '100%', background: '#F59E0B' }} />
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748B', marginTop: '6px' }}>22.3% of total order duration</div>
                    </div>

                    <div style={{ border: '1px solid #E2E8F0', borderRadius: '6px', padding: '12px', background: '#FFFFFF' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '13px', fontWeight: '600', color: '#0F172A' }}>Shipping & Invoice Delivery</span>
                        <span style={{ fontSize: '12px', fontWeight: '700', color: '#0F766E' }}>7.1h Median</span>
                      </div>
                      <div style={{ height: '6px', background: '#F1F5F9', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ width: '19.0%', height: '100%', background: '#10B981' }} />
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748B', marginTop: '6px' }}>19.0% of total order duration</div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: Detected Bottlenecks View */}
            {activeTab === 'bottlenecks' && (
              <div className="mkt-preview-grid">
                <div className="mkt-preview-panel">
                  <div className="mkt-preview-panel-title">
                    <span>Identified Process Bottlenecks</span>
                    <span className="mkt-pill mkt-pill-amber">3 Detected</span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <div style={{ padding: '12px', border: '1px solid #E2E8F0', borderRadius: '6px', background: '#FFFFFF' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <span className="mkt-pill mkt-pill-amber">HIGH DELAY</span>
                        <strong style={{ fontSize: '13px' }}>Transition: Quote Received → PO Released</strong>
                      </div>
                      <p style={{ fontSize: '12.5px', color: '#475569', margin: '4px 0' }}>
                        Observed duration is 2.8x higher than peer operational benchmarks. 750/750 cases affected.
                      </p>
                      <span style={{ fontSize: '11px', color: '#0369A1', fontWeight: '500' }}>Exemplar Case: MO-001 (132,000s duration)</span>
                    </div>

                    <div style={{ padding: '12px', border: '1px solid #E2E8F0', borderRadius: '6px', background: '#FFFFFF' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <span className="mkt-pill mkt-pill-blue">QUEUE LATENCY</span>
                        <strong style={{ fontSize: '13px' }}>PO Released → Assembly Started</strong>
                      </div>
                      <p style={{ fontSize: '12.5px', color: '#475569', margin: '4px 0' }}>
                        Production scheduling delay observed during shift handoffs. Median wait 8.2 hours.
                      </p>
                      <span style={{ fontSize: '11px', color: '#0369A1', fontWeight: '500' }}>Exemplar Case: MO-042 (31,200s duration)</span>
                    </div>
                  </div>
                </div>

                <div className="mkt-preview-panel">
                  <div className="mkt-preview-panel-title">
                    <span>Process Variant Distribution</span>
                    <span style={{ fontSize: '12px', color: '#64748B' }}>1 Dominant Variant</span>
                  </div>

                  <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '6px', padding: '16px' }}>
                    <div style={{ fontSize: '13px', fontWeight: '700', color: '#0F172A', marginBottom: '6px' }}>
                      Standard Production Path (100% Coverage)
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', fontSize: '12px', color: '#334155' }}>
                      <span style={{ background: '#FFFFFF', padding: '4px 8px', borderRadius: '4px', border: '1px solid #CBD5E1' }}>Order Received</span>
                      <span>→</span>
                      <span style={{ background: '#FFFFFF', padding: '4px 8px', borderRadius: '4px', border: '1px solid #CBD5E1' }}>Quote Received</span>
                      <span>→</span>
                      <span style={{ background: '#FEF2F2', padding: '4px 8px', borderRadius: '4px', border: '1px solid #FCA5A5', color: '#991B1B', fontWeight: '600' }}>PO Released (Bottleneck)</span>
                      <span>→</span>
                      <span style={{ background: '#FFFFFF', padding: '4px 8px', borderRadius: '4px', border: '1px solid #CBD5E1' }}>Assembly Completed</span>
                      <span>→</span>
                      <span style={{ background: '#FFFFFF', padding: '4px 8px', borderRadius: '4px', border: '1px solid #CBD5E1' }}>Shipped</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 3: Evidence Dossier View */}
            {activeTab === 'evidence' && (
              <div className="mkt-preview-grid">
                <div className="mkt-preview-panel">
                  <div className="mkt-preview-panel-title">
                    <span>Epistemic Ledger (Grounding Audit)</span>
                    <span className="mkt-pill mkt-pill-teal">4 Claims Classified</span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <div className="mkt-ledger-item">
                      <span className="mkt-ledger-tag mkt-tag-fact">FACT</span>
                      <div>
                        <strong>Observed 750 / 750 cases</strong> traversing Quote Received to PO Released.
                        <div style={{ fontSize: '11px', color: '#64748B' }}>Source: Canonical CSV Event Log Record</div>
                      </div>
                    </div>

                    <div className="mkt-ledger-item">
                      <span className="mkt-ledger-tag mkt-tag-fact">FACT</span>
                      <div>
                        <strong>Cumulative transition duration</strong> equals 61,500,000 seconds.
                        <div style={{ fontSize: '11px', color: '#64748B' }}>Source: Deterministic Timestamp Differencing</div>
                      </div>
                    </div>

                    <div className="mkt-ledger-item">
                      <span className="mkt-ledger-tag mkt-tag-assumption">ASSUMPTION</span>
                      <div>
                        <strong>Transition latency proxy</strong> is calculated from single-timestamp events; queue vs touch time is unmeasured.
                        <div style={{ fontSize: '11px', color: '#64748B' }}>Source: Epistemic Safeguard Rule ES-02</div>
                      </div>
                    </div>

                    <div className="mkt-ledger-item">
                      <span className="mkt-ledger-tag mkt-tag-unknown">UNKNOWN</span>
                      <div>
                        <strong>Direct monetary savings</strong> cannot be asserted without user labor rate parameters.
                        <div style={{ fontSize: '11px', color: '#64748B' }}>Source: Financial Integrity Policy</div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mkt-preview-panel">
                  <div className="mkt-preview-panel-title">
                    <span>Verifiable Derivation</span>
                    <span style={{ fontSize: '12px', color: '#64748B' }}>Audit Manifest</span>
                  </div>

                  <div className="mkt-derivation-formula">
                    duration_share = (61,500,000s / 104,700,772s) * 100 = 58.74%
                  </div>

                  <p style={{ fontSize: '13px', color: '#475569', lineHeight: '1.5' }}>
                    ProcessLens provides mathematical reproducibility for every generated metric.
                    Users can audit the exact formulas, inputs, and boundaries behind each recommendation.
                  </p>

                  <div style={{ marginTop: '16px' }}>
                    <button
                      type="button"
                      className="mkt-btn-secondary"
                      style={{ fontSize: '13px', padding: '8px 16px' }}
                      onClick={() => onNavigate('/login')}
                    >
                      Audit with Your Own Data <ExternalLink size={14} />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Disclaimer */}
            <p className="mkt-preview-disclaimer">
              * Illustrative demonstration rendered from standard manufacturing event logs. Real deployments execute deterministic ingestion and analysis on your own operational data.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
