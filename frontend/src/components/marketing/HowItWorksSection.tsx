import React from 'react';
import { Upload, GitMerge, AlertCircle, Award } from 'lucide-react';

export const HowItWorksSection: React.FC = () => {
  return (
    <section id="how-it-works" className="mkt-section-padded">
      <div className="mkt-container">
        <div className="mkt-section-header">
          <div className="mkt-badge-eyebrow">
            <span>DETERMINISTIC PIPELINE</span>
          </div>
          <h2 className="mkt-section-title">
            From raw event data to confident decisions.
          </h2>
          <p className="mkt-section-lead">
            ProcessLens follows a transparent, deterministic four-step pipeline that preserves
            analytical provenance at every stage.
          </p>
        </div>

        <div className="mkt-steps-container">
          {/* Step 1 */}
          <div className="mkt-step-card">
            <span className="mkt-step-number">STEP 01</span>
            <div style={{ color: '#0369A1', marginBottom: '12px' }}>
              <Upload size={22} />
            </div>
            <h3 className="mkt-step-title">Bring your data</h3>
            <p className="mkt-step-desc">
              Upload standard CSV event records containing <code>case_id</code>, <code>activity</code>,
              and <code>timestamp</code>. Automated schema auditing validates timestamp formatting and reports row defects.
            </p>
          </div>

          {/* Step 2 */}
          <div className="mkt-step-card">
            <span className="mkt-step-number">STEP 02</span>
            <div style={{ color: '#0369A1', marginBottom: '12px' }}>
              <GitMerge size={22} />
            </div>
            <h3 className="mkt-step-title">Reconstruct the process</h3>
            <p className="mkt-step-desc">
              Group and sort events chronologically per case. Discover process execution variants,
              transition frequency, and exact cycle-time distribution percentiles.
            </p>
          </div>

          {/* Step 3 */}
          <div className="mkt-step-card">
            <span className="mkt-step-number">STEP 03</span>
            <div style={{ color: '#0369A1', marginBottom: '12px' }}>
              <AlertCircle size={22} />
            </div>
            <h3 className="mkt-step-title">Surface findings</h3>
            <p className="mkt-step-desc">
              Scan deterministically for duration anomalies, queue delays, and rework loops.
              Every finding identifies affected cases and mathematical severity without LLM hallucinations.
            </p>
          </div>

          {/* Step 4 */}
          <div className="mkt-step-card">
            <span className="mkt-step-number">STEP 04</span>
            <div style={{ color: '#0369A1', marginBottom: '12px' }}>
              <Award size={22} />
            </div>
            <h3 className="mkt-step-title">Prioritise with evidence</h3>
            <p className="mkt-step-desc">
              Rank improvement and automation opportunities by impact and readiness. Inspect
              auditable evidence dossiers that clearly separate facts from assumptions.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
