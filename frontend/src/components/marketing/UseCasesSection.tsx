import React from 'react';
import { Factory, FileSpreadsheet, Workflow, Cpu } from 'lucide-react';

export const UseCasesSection: React.FC = () => {
  return (
    <section id="use-cases" className="mkt-section-padded">
      <div className="mkt-container">
        <div className="mkt-section-header">
          <div className="mkt-badge-eyebrow">
            <span>OPERATIONAL APPLICATIONS</span>
          </div>
          <h2 className="mkt-section-title">
            Built for operational and engineering teams.
          </h2>
          <p className="mkt-section-lead">
            Whether improving manufacturing cycle times or evaluating business process automation,
            ProcessLens delivers concrete analytical grounding.
          </p>
        </div>

        <div className="mkt-usecases-grid">
          {/* Use Case 1 */}
          <div className="mkt-usecase-item">
            <div className="mkt-usecase-icon">
              <Factory size={22} />
            </div>
            <div className="mkt-usecase-content">
              <h4>Manufacturing & Production Workflows</h4>
              <p>
                Track work orders from receipt to dispatch. Surface scheduling bottlenecks, assembly
                handoff latency, and shift-to-shift cycle time variance with empirical case logs.
              </p>
            </div>
          </div>

          {/* Use Case 2 */}
          <div className="mkt-usecase-item">
            <div className="mkt-usecase-icon">
              <FileSpreadsheet size={22} />
            </div>
            <div className="mkt-usecase-content">
              <h4>Procurement & Order-to-Cash</h4>
              <p>
                Identify administrative approval loops between quote generation, purchase orders,
                and invoice dispatch. Pinpoint transitions where orders dwell awaiting authorization.
              </p>
            </div>
          </div>

          {/* Use Case 3 */}
          <div className="mkt-usecase-item">
            <div className="mkt-usecase-icon">
              <Workflow size={22} />
            </div>
            <div className="mkt-usecase-content">
              <h4>Service Delivery & Ticket Resolution</h4>
              <p>
                Analyze case flow variants across service operations. Detect rework cycles where
                tickets bounce repeatedly between support tiers or external vendor queues.
              </p>
            </div>
          </div>

          {/* Use Case 4 */}
          <div className="mkt-usecase-item">
            <div className="mkt-usecase-icon">
              <Cpu size={22} />
            </div>
            <div className="mkt-usecase-content">
              <h4>Automation Opportunity Discovery</h4>
              <p>
                Evaluate automation readiness deterministically before investing in RPA or APIs.
                Filter out complex, high-variant transitions that are unsuited for straight-through automation.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
