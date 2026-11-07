import React, { useState } from 'react';
import { PrioritisedOpportunity } from '../../types/api';
import { Target, Info } from 'lucide-react';
import { formatScorePercent, normalizeScoreTo100 } from '../../utils/formatters';

interface OpportunityDimensionsChartProps {
  opportunities: PrioritisedOpportunity[];
  onSelectOpportunity?: (oppId: string) => void;
}

type DimensionKey = 'priority' | 'readiness' | 'impact' | 'confidence';

export const OpportunityDimensionsChart: React.FC<OpportunityDimensionsChartProps> = ({
  opportunities,
  onSelectOpportunity,
}) => {
  const [hoveredDim, setHoveredDim] = useState<{ oppId: string; dim: DimensionKey } | null>(null);

  if (!opportunities || opportunities.length === 0) {
    return (
      <div className="chart-empty-state">
        <p>No opportunity ranking dimensions available.</p>
      </div>
    );
  }

  // Display top opportunities (up to 5)
  const topOpps = opportunities.slice(0, 5);

  return (
    <div className="chart-container" aria-label="Opportunity Multi-Factor Comparison Chart">
      <div className="chart-header">
        <div>
          <div className="chart-title">
            <Target size={16} className="text-cyan" />
            <span>Multi-Factor Opportunity Evaluation</span>
          </div>
          <div className="chart-subtitle">
            Comparing Operational Priority against Readiness, Impact, and Confidence dimensions
          </div>
        </div>

        <div className="dimension-legend">
          <span className="legend-chip">
            <span className="legend-dot dot-cyan" /> Operational Priority
          </span>
          <span className="legend-chip">
            <span className="legend-dot dot-emerald" /> Readiness Score
          </span>
          <span className="legend-chip">
            <span className="legend-dot dot-purple" /> Impact Score
          </span>
          <span className="legend-chip">
            <span className="legend-dot dot-amber" /> Confidence
          </span>
        </div>
      </div>

      <div className="opp-dimension-cards-list" role="list" aria-label="Top prioritised opportunities">
        {topOpps.map((opp) => {
          const priorityPct = Math.min(Math.max(normalizeScoreTo100(opp.operational_priority_score), 5), 100);
          const readinessVal = opp.factors.readiness_score !== null && opp.factors.readiness_score !== undefined
            ? opp.factors.readiness_score
            : null;
          const readinessPct = readinessVal !== null ? Math.min(Math.max(normalizeScoreTo100(readinessVal), 5), 100) : 0;
          
          const impactVal = opp.factors.impact_score !== null && opp.factors.impact_score !== undefined
            ? opp.factors.impact_score
            : null;
          const impactPct = impactVal !== null ? Math.min(Math.max(normalizeScoreTo100(impactVal), 5), 100) : 0;

          const confidencePct = Math.min(Math.max(normalizeScoreTo100(opp.factors.confidence_score), 5), 100);

          return (
            <div
              key={opp.opportunity_id}
              className="opp-dimension-row"
              onClick={() => onSelectOpportunity && onSelectOpportunity(opp.opportunity_id)}
              role="listitem"
              tabIndex={0}
              aria-label={`Opportunity #${opp.rank_order}: ${opp.opportunity_id}, Archetype: ${opp.archetype}, Priority: ${opp.operational_priority_score.toFixed(0)} of 100`}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectOpportunity && onSelectOpportunity(opp.opportunity_id);
                }
              }}
            >
              <div className="opp-dimension-meta">
                <div className="opp-rank-badge">#{opp.rank_order}</div>
                <div>
                  <div className="opp-id-title font-mono font-medium" title={opp.opportunity_id}>{opp.opportunity_id}</div>
                  <div className="opp-archetype-line">
                    <span className="badge badge-subtle text-xs">{opp.archetype}</span>
                    <span className="text-muted text-xs ml-2">{opp.portfolio_cohort}</span>
                  </div>
                </div>
              </div>

              {/* Dimensional Bars Grid */}
              <div className="opp-bars-grid">
                {/* 1. Operational Priority */}
                <div
                  className={`dim-bar-item ${hoveredDim?.oppId === opp.opportunity_id && hoveredDim.dim === 'priority' ? 'dim-bar-hovered' : ''}`}
                  onMouseEnter={(e) => { e.stopPropagation(); setHoveredDim({ oppId: opp.opportunity_id, dim: 'priority' }); }}
                  onMouseLeave={() => setHoveredDim(null)}
                >
                  <div className="dim-bar-label">
                    <span>Priority</span>
                    <strong className="text-cyan tabular-nums">{opp.operational_priority_score.toFixed(0)}/100</strong>
                  </div>
                  <div className="bar-track">
                    <div className="bar-fill bar-cyan" style={{ width: `${priorityPct}%` }} />
                  </div>
                  {hoveredDim?.oppId === opp.opportunity_id && hoveredDim.dim === 'priority' && (
                    <div className="dim-bar-tooltip" role="tooltip">
                      <span>Operational Priority: <strong>{opp.operational_priority_score.toFixed(1)}/100</strong></span>
                      <small>Composite weighted evaluation</small>
                    </div>
                  )}
                </div>

                {/* 2. Readiness */}
                <div
                  className={`dim-bar-item ${hoveredDim?.oppId === opp.opportunity_id && hoveredDim.dim === 'readiness' ? 'dim-bar-hovered' : ''}`}
                  onMouseEnter={(e) => { e.stopPropagation(); setHoveredDim({ oppId: opp.opportunity_id, dim: 'readiness' }); }}
                  onMouseLeave={() => setHoveredDim(null)}
                >
                  <div className="dim-bar-label">
                    <span>Readiness</span>
                    <strong className="text-emerald tabular-nums">
                      {readinessVal !== null ? `${readinessVal.toFixed(0)}/100` : 'Assessing'}
                    </strong>
                  </div>
                  <div className="bar-track">
                    <div className="bar-fill bar-emerald" style={{ width: `${readinessPct}%` }} />
                  </div>
                  {hoveredDim?.oppId === opp.opportunity_id && hoveredDim.dim === 'readiness' && (
                    <div className="dim-bar-tooltip" role="tooltip">
                      <span>Readiness: <strong>{readinessVal !== null ? `${readinessVal.toFixed(1)}/100` : 'Assessing'}</strong></span>
                      <small>Workflow & automation prerequisite status</small>
                    </div>
                  )}
                </div>

                {/* 3. Impact */}
                <div
                  className={`dim-bar-item ${hoveredDim?.oppId === opp.opportunity_id && hoveredDim.dim === 'impact' ? 'dim-bar-hovered' : ''}`}
                  onMouseEnter={(e) => { e.stopPropagation(); setHoveredDim({ oppId: opp.opportunity_id, dim: 'impact' }); }}
                  onMouseLeave={() => setHoveredDim(null)}
                >
                  <div className="dim-bar-label">
                    <span>Impact</span>
                    <strong className="text-purple tabular-nums">
                      {impactVal !== null ? `${impactVal.toFixed(0)}/100` : 'Pending'}
                    </strong>
                  </div>
                  <div className="bar-track">
                    <div className="bar-fill bar-purple" style={{ width: `${impactPct}%` }} />
                  </div>
                  {hoveredDim?.oppId === opp.opportunity_id && hoveredDim.dim === 'impact' && (
                    <div className="dim-bar-tooltip" role="tooltip">
                      <span>Impact: <strong>{impactVal !== null ? `${impactVal.toFixed(1)}/100` : 'Pending'}</strong></span>
                      <small>Cycle time and delay reduction capacity</small>
                    </div>
                  )}
                </div>

                {/* 4. Confidence */}
                <div
                  className={`dim-bar-item ${hoveredDim?.oppId === opp.opportunity_id && hoveredDim.dim === 'confidence' ? 'dim-bar-hovered' : ''}`}
                  onMouseEnter={(e) => { e.stopPropagation(); setHoveredDim({ oppId: opp.opportunity_id, dim: 'confidence' }); }}
                  onMouseLeave={() => setHoveredDim(null)}
                >
                  <div className="dim-bar-label">
                    <span>Confidence</span>
                    <strong className="text-amber tabular-nums">{formatScorePercent(opp.factors.confidence_score)}</strong>
                  </div>
                  <div className="bar-track">
                    <div className="bar-fill bar-amber" style={{ width: `${confidencePct}%` }} />
                  </div>
                  {hoveredDim?.oppId === opp.opportunity_id && hoveredDim.dim === 'confidence' && (
                    <div className="dim-bar-tooltip" role="tooltip">
                      <span>Confidence: <strong>{formatScorePercent(opp.factors.confidence_score)}</strong></span>
                      <small>Sample volume and evidence integrity</small>
                    </div>
                  )}
                </div>
              </div>

              <div className="opp-action-hint">
                <span className="text-xs text-cyan">Inspect &rarr;</span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="chart-footer-note">
        <Info size={13} />
        <span>
          <strong>Epistemic Discipline:</strong> Readiness (operational prerequisites), Impact (potential delay compression), and Confidence (evidence density) are kept strictly separate and are never conflated into a single ambiguous metric.
        </span>
      </div>
    </div>
  );
};
