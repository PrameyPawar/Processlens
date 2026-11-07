import React from 'react';
import { ExplanationResponse, GroundingVerificationStatus } from '../types/api';
import { BookOpen, ShieldCheck, AlertTriangle, Info, Lock } from 'lucide-react';

interface ExplanationsViewProps {
  explanations: ExplanationResponse;
  onSelectDossier: (opportunityId: string) => void;
}

export const ExplanationsView: React.FC<ExplanationsViewProps> = ({
  explanations,
  onSelectDossier,
}) => {
  const { portfolio_summary, explanations: items, explanation_source, manifest } = explanations;

  const groundingBadge = (status?: GroundingVerificationStatus) => {
    switch (status) {
      case 'VERIFIED_GROUNDED':
        return (
          <span className="badge badge-success">
            <ShieldCheck size={14} /> Grounding Verified
          </span>
        );
      case 'FALLBACK_APPLIED':
        return (
          <span className="badge badge-warning">
            <AlertTriangle size={14} /> Fallback Applied (Protected)
          </span>
        );
      case 'NOT_EVALUATED':
      default:
        return (
          <span className="badge badge-neutral">
            <Lock size={14} /> Deterministic Baseline (Offline)
          </span>
        );
    }
  };

  return (
    <section className="glass-panel animate-fade-in" aria-label="Evidence-Backed Explanations & Executive Briefing">
      <div className="section-header">
        <div>
          <h2 className="section-title">Phase 10: Evidence-Backed Executive Explanations</h2>
          <p className="section-subtitle">
            Executive-ready narratives grounded directly in Phase 9 evidence dossiers. Zero hallucinated metrics or guaranteed ROI claims.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span className="badge badge-info">
            Source: {explanation_source}
          </span>
          <span className="badge badge-neutral">
            SHA-256: <code>{manifest.source_file_sha256.substring(0, 8)}...</code>
          </span>
        </div>
      </div>

      {/* Portfolio Executive Briefing Banner */}
      <div className="portfolio-briefing-card">
        <h3 className="briefing-title">Portfolio Executive Briefing</h3>
        <p className="briefing-narrative">{portfolio_summary.overall_narrative}</p>

        {portfolio_summary.top_recommended_actions.length > 0 && (
          <div className="briefing-section">
            <h4 className="briefing-subtitle text-cyan">Top Recommended Strategic Actions</h4>
            <ul className="bullet-list">
              {portfolio_summary.top_recommended_actions.map((act, i) => (
                <li key={i}>{act}</li>
              ))}
            </ul>
          </div>
        )}

        {portfolio_summary.foundational_prerequisites.length > 0 && (
          <div className="briefing-section">
            <h4 className="briefing-subtitle text-amber">Foundational Governance & Data Prerequisites</h4>
            <ul className="bullet-list">
              {portfolio_summary.foundational_prerequisites.map((req, i) => (
                <li key={i}>{req}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="briefing-caveat">
          <Info size={14} className="text-muted" />
          <span>{portfolio_summary.portfolio_economics_caveat}</span>
        </div>
      </div>

      {/* Per-Opportunity Grounded Explanations */}
      <div className="explanations-list">
        {items.length === 0 ? (
          <div className="empty-state">
            <ShieldCheck size={32} className="text-muted" />
            <p>No opportunity explanations generated for the current portfolio.</p>
          </div>
        ) : (
          items.map((expl) => {
            const audit = expl.grounding_audit;

            return (
              <div key={expl.opportunity_id} className="explanation-card">
              <div className="explanation-header">
                <div>
                  <div className="explanation-meta-row">
                    <span className="rank-badge">#{expl.rank_order}</span>
                    <span className="badge badge-neutral">{expl.archetype}</span>
                    <span className="badge badge-info">{expl.portfolio_cohort}</span>
                    {groundingBadge(audit?.status)}
                    <code className="text-muted text-xs">{expl.opportunity_id}</code>
                  </div>
                  <h3 className="explanation-title">
                    Target: <code>{expl.target_entity}</code>
                  </h3>
                </div>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => onSelectDossier(expl.opportunity_id)}
                >
                  <BookOpen size={14} /> View Audit Dossier
                </button>
              </div>

              {/* Discrepancies if Fallback was applied */}
              {audit?.status === 'FALLBACK_APPLIED' && audit.discrepancies.length > 0 && (
                <div className="discrepancy-notice">
                  <AlertTriangle size={15} className="text-amber" />
                  <div>
                    <strong>Grounding / Fallback Reason:</strong>
                    <ul className="text-xs">
                      {audit.discrepancies.map((disc, idx) => (
                        <li key={idx}>{disc}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Executive Summary */}
              <div className="narrative-block">
                <h4 className="narrative-label text-cyan">Executive Summary</h4>
                <p className="narrative-text">{expl.executive_summary}</p>
              </div>

              {/* Operational Problem Narrative */}
              <div className="narrative-block">
                <h4 className="narrative-label">Operational Problem Narrative</h4>
                <p className="narrative-text">{expl.operational_problem_narrative}</p>
              </div>

              {/* Economic Interpretation */}
              <div className="narrative-block">
                <h4 className="narrative-label">Economic Interpretation</h4>
                <p className="narrative-text">{expl.economic_interpretation}</p>
              </div>

              {/* Strategic Rationale */}
              <div className="narrative-block">
                <h4 className="narrative-label">Strategic Roadmap Rationale</h4>
                <p className="narrative-text">{expl.strategic_rationale}</p>
              </div>

              {/* Key Assumptions & Risks */}
              {expl.key_assumptions_and_risks.length > 0 && (
                <div className="narrative-block">
                  <h4 className="narrative-label text-amber">Key Assumptions, Hypotheses & Boundaries</h4>
                  <ul className="bullet-list">
                    {expl.key_assumptions_and_risks.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Next Steps */}
              {expl.investigation_next_steps.length > 0 && (
                <div className="narrative-block">
                  <h4 className="narrative-label text-emerald">Recommended Operational Next Steps</h4>
                  <ul className="bullet-list">
                    {expl.investigation_next_steps.map((step, idx) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })
      )}
      </div>
    </section>
  );
};
