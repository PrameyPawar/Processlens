import React from 'react';
import { Clock, GitBranch, ArrowUpRight } from 'lucide-react';

export const ProblemSection: React.FC = () => {
  return (
    <section className="mkt-section-padded" style={{ background: '#FFFFFF', borderTop: '1px solid #E2E8F0', borderBottom: '1px solid #E2E8F0' }}>
      <div className="mkt-container">
        <div className="mkt-section-header">
          <div className="mkt-badge-eyebrow">
            <span>OPERATIONAL REALITY</span>
          </div>
          <h2 className="mkt-section-title">
            Work rarely breaks in just one place.
          </h2>
          <p className="mkt-section-lead">
            Delays, rework loops, inconsistent handoffs, and unmeasured queue times make it difficult
            to know where operational improvement efforts should actually begin.
          </p>
        </div>

        <div className="mkt-cards-grid">
          {/* Card 1 */}
          <div className="mkt-feature-card">
            <div className="mkt-card-icon-box">
              <Clock size={24} />
            </div>
            <h3 className="mkt-card-title">See the bottlenecks</h3>
            <p className="mkt-card-desc">
              Understand where work slows down and which transitions consume disproportionate
              cycle time across your end-to-end case workflows.
            </p>
          </div>

          {/* Card 2 */}
          <div className="mkt-feature-card">
            <div className="mkt-card-icon-box">
              <GitBranch size={24} />
            </div>
            <h3 className="mkt-card-title">Find the underlying signals</h3>
            <p className="mkt-card-desc">
              Connect findings directly to operational event logs and case exemplars rather
              than relying on intuition or anecdotal observations.
            </p>
          </div>

          {/* Card 3 */}
          <div className="mkt-feature-card">
            <div className="mkt-card-icon-box">
              <ArrowUpRight size={24} />
            </div>
            <h3 className="mkt-card-title">Prioritise the next move</h3>
            <p className="mkt-card-desc">
              Compare improvement initiatives using transparent criteria—readiness, impact,
              effort, and confidence—so teams address the highest-leverage friction first.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
