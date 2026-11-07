import React, { useState } from 'react';
import {
  PrioritisationResponse,
  OpportunityArchetype,
  PortfolioCohort,
} from '../types/api';
import { OpportunityDimensionsChart } from './charts/OpportunityDimensionsChart';
import { formatScorePercent, normalizeScoreTo100 } from '../utils/formatters';
import { CheckCircle, BookOpen, AlertCircle, Filter, Search, ArrowUpDown, BarChart2 } from 'lucide-react';

interface OpportunitiesViewProps {
  prioritisation: PrioritisationResponse;
  onSelectDossier: (opportunityId: string) => void;
}

export const OpportunitiesView: React.FC<OpportunitiesViewProps> = ({
  prioritisation,
  onSelectDossier,
}) => {
  const { summary, ranked_opportunities } = prioritisation;
  const [selectedCohort, setSelectedCohort] = useState<string>('ALL');
  const [selectedArchetype, setSelectedArchetype] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<'rank' | 'priority' | 'readiness' | 'impact' | 'confidence'>('rank');
  const [showChart, setShowChart] = useState<boolean>(true);

  const archetypeBadgeClass = (archetype: OpportunityArchetype) => {
    switch (archetype) {
      case 'DELAY_COMPRESSION':
        return 'badge-warning';
      case 'RECURRENCE_REDUCTION':
        return 'badge-danger';
      case 'TAIL_VARIANCE_MITIGATION':
        return 'badge-purple';
      case 'PATH_STANDARDIZATION':
        return 'badge-info';
      case 'DATA_INSTRUMENTATION':
        return 'badge-neutral';
      default:
        return 'badge-neutral';
    }
  };

  const cohortBadgeClass = (cohort: PortfolioCohort) => {
    switch (cohort) {
      case 'IMMEDIATE_AUTOMATION_SPECIFICATION':
        return 'badge-success';
      case 'FEASIBILITY_INVESTIGATION':
        return 'badge-info';
      case 'BUSINESS_CASE_VALIDATION':
        return 'badge-warning';
      case 'PROCESS_RESTRUCTURING':
        return 'badge-purple';
      case 'REVISE_OR_DEFERRED':
      case 'BLOCKED_BY_BARRIERS':
        return 'badge-danger';
      case 'FOUNDATIONAL_DATA_QUALITY':
        return 'badge-amber';
      default:
        return 'badge-neutral';
    }
  };

  // Distinct cohorts present in dataset
  const availableCohorts = Array.from(
    new Set(ranked_opportunities.map((o) => o.portfolio_cohort))
  );

  // Distinct archetypes present in dataset
  const availableArchetypes = Array.from(
    new Set(ranked_opportunities.map((o) => o.archetype))
  );

  // Filter & sort opportunities
  const filteredOpportunities = ranked_opportunities
    .filter((opp) => {
      if (selectedCohort !== 'ALL' && opp.portfolio_cohort !== selectedCohort) return false;
      if (selectedArchetype !== 'ALL' && opp.archetype !== selectedArchetype) return false;
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesId = opp.opportunity_id.toLowerCase().includes(query);
        const matchesArch = opp.archetype.toLowerCase().includes(query);
        const matchesCohort = opp.portfolio_cohort.toLowerCase().includes(query);
        if (!matchesId && !matchesArch && !matchesCohort) return false;
      }
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'priority') {
        return b.operational_priority_score - a.operational_priority_score;
      }
      if (sortBy === 'readiness') {
        return (b.factors.readiness_score ?? 0) - (a.factors.readiness_score ?? 0);
      }
      if (sortBy === 'impact') {
        return (b.factors.impact_score ?? 0) - (a.factors.impact_score ?? 0);
      }
      if (sortBy === 'confidence') {
        return normalizeScoreTo100(b.factors.confidence_score) - normalizeScoreTo100(a.factors.confidence_score);
      }
      return a.rank_order - b.rank_order;
    });


  return (
    <section className="glass-panel animate-fade-in" aria-label="Prioritised Improvement & Automation Opportunities">
      <div className="section-header">
        <div>
          <h2 className="section-title">Phase 5 – 8: Opportunities, Readiness & Prioritisation Roadmap</h2>
          <p className="section-subtitle">
            Defensible portfolio roadmap ranking {summary.total_opportunities_prioritised} opportunity candidate(s). Distinguishes empirical facts, assumptions, and unmonetized estimates.
          </p>
        </div>
        <div>
          <span className="badge badge-success">
            <CheckCircle size={14} /> Multi-Factor Scored & Ranked
          </span>
        </div>
      </div>

      {/* Roadmap Summary Cards */}
      <div className="stats-grid mb-6">
        <div className="stat-card">
          <div className="stat-label">Total Prioritised Opportunities</div>
          <div className="stat-value text-emerald">{summary.total_opportunities_prioritised}</div>
          <div className="stat-caption">Ranked by composite multi-factor precedence</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Top Ranked Candidate</div>
          <div className="stat-value text-cyan" style={{ fontSize: '1.25rem', wordBreak: 'break-all' }}>
            {summary.top_opportunity_id || 'None'}
          </div>
          <div className="stat-caption">Rank #1 in portfolio action roadmap</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Cohort Allocation</div>
          <div className="stat-value text-amber">
            {Object.keys(summary.cohort_distribution).length} Cohort(s)
          </div>
          <div className="stat-caption">
            {Object.entries(summary.cohort_distribution)
              .map(([cohort, count]) => `${cohort.replace(/_/g, ' ')}: ${count}`)
              .join(', ')}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Cumulative Capacity Valuation</div>
          <div className="stat-value">
            {summary.top_three_cumulative_capacity_scenario !== null && summary.top_three_cumulative_capacity_scenario !== undefined ? (
              `$${summary.top_three_cumulative_capacity_scenario.toLocaleString()}`
            ) : (
              <span className="text-muted" style={{ fontSize: '1rem' }}>Unknown (Inputs required)</span>
            )}
          </div>
          <div className="stat-caption">Non-additive scenario; requires wage inputs</div>
        </div>
      </div>

      {/* Non-additive caveat notice */}
      {summary.capacity_scenario_caveats.length > 0 && (
        <div className="caveat-banner mb-6">
          <AlertCircle size={16} className="text-amber" />
          <span>{summary.capacity_scenario_caveats[0]}</span>
        </div>
      )}

      {/* Interactive Visual Comparison Chart */}
      {showChart && ranked_opportunities.length > 0 && (
        <div className="glass-panel mb-6">
          <OpportunityDimensionsChart
            opportunities={ranked_opportunities}
            onSelectOpportunity={(id) => onSelectDossier(id)}
          />
        </div>
      )}

      {/* Filter and Search Controls */}
      <div className="workspace-filter-bar glass-panel mb-6">
        <div className="filter-group">
          <Search size={15} className="text-muted" />
          <input
            type="text"
            className="search-input"
            placeholder="Search opportunities..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <Filter size={15} className="text-muted" />
          <span className="filter-label">Cohort:</span>
          <select
            className="filter-select"
            value={selectedCohort}
            onChange={(e) => setSelectedCohort(e.target.value)}
          >
            <option value="ALL">All Cohorts ({ranked_opportunities.length})</option>
            {availableCohorts.map((c) => (
              <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <span className="filter-label">Archetype:</span>
          <select
            className="filter-select"
            value={selectedArchetype}
            onChange={(e) => setSelectedArchetype(e.target.value)}
          >
            <option value="ALL">All Archetypes</option>
            {availableArchetypes.map((a) => (
              <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <ArrowUpDown size={15} className="text-muted" />
          <span className="filter-label">Sort:</span>
          <select
            className="filter-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
          >
            <option value="rank">Rank Order (Default)</option>
            <option value="priority">Operational Priority</option>
            <option value="readiness">Readiness Score</option>
            <option value="impact">Impact Score</option>
            <option value="confidence">Confidence Score</option>
          </select>

        </div>

        <button
          type="button"
          className="btn-pill"
          onClick={() => setShowChart(!showChart)}
        >
          <BarChart2 size={14} /> {showChart ? 'Hide Comparison Chart' : 'Show Comparison Chart'}
        </button>
      </div>

      {/* Ranked Opportunities Cards */}
      <div className="opportunities-container">
        {filteredOpportunities.length === 0 ? (
          <div className="empty-state">
            <CheckCircle size={32} className="text-emerald" />
            <p>No improvement or automation opportunities match the current filter criteria.</p>
            {(selectedCohort !== 'ALL' || selectedArchetype !== 'ALL' || searchQuery) && (
              <button
                type="button"
                className="btn-link mt-2"
                onClick={() => {
                  setSelectedCohort('ALL');
                  setSelectedArchetype('ALL');
                  setSearchQuery('');
                }}
              >
                Clear Filters
              </button>
            )}
          </div>
        ) : (
          filteredOpportunities.map((opp) => {
            const { factors, economics } = opp;
            const laborHours = economics?.labor_effort?.annual_addressable_labor_hours ?? economics?.labor_effort?.annual_addressable_hours;
            const capacityVal = economics?.capacity_valuation?.gross_annual_capacity_value;

            // Extract target transition/activity from opportunity_id
            let targetLabel = opp.opportunity_id.replace(/^opp_/, '');
            if (targetLabel.startsWith('transition_')) {
              targetLabel = targetLabel.replace(/^transition_/, '').replace(/_to_/g, ' → ').replace(/_/g, ' ');
            } else if (targetLabel.startsWith('activity_')) {
              targetLabel = targetLabel.replace(/^activity_/, '').replace(/_/g, ' ');
            } else {
              targetLabel = targetLabel.replace(/_/g, ' ');
            }

            const priorityPct = Math.min(Math.max(normalizeScoreTo100(opp.operational_priority_score), 5), 100);
            const readinessVal = factors.readiness_score !== null && factors.readiness_score !== undefined
              ? factors.readiness_score
              : null;
            const readinessPct = readinessVal !== null ? Math.min(Math.max(normalizeScoreTo100(readinessVal), 5), 100) : 0;

            const impactVal = factors.impact_score !== null && factors.impact_score !== undefined
              ? factors.impact_score
              : factors.coverage_score !== undefined
              ? factors.coverage_score
              : null;
            const impactPct = impactVal !== null ? Math.min(Math.max(normalizeScoreTo100(impactVal), 5), 100) : 0;

            const confidencePct = Math.min(Math.max(normalizeScoreTo100(factors.confidence_score), 5), 100);

            const opportunityHeadline =
              opp.archetype === 'DELAY_COMPRESSION'
                ? `Compress Elapsed Delay on ${targetLabel}`
                : opp.archetype === 'RECURRENCE_REDUCTION'
                ? `Eliminate Repetitions & Loopbacks on ${targetLabel}`
                : opp.archetype === 'PATH_STANDARDIZATION'
                ? `Standardize Rare Routing Path on ${targetLabel}`
                : opp.archetype === 'DATA_INSTRUMENTATION'
                ? `Instrument Logging Telemetry for ${targetLabel}`
                : `Mitigate Outlier Variance on ${targetLabel}`;

            return (
              <div key={opp.opportunity_id} className="pl-opportunity-card">
                {/* 1. TOP ROW: Rank | Opportunity Name & Target | Inspect Action */}
                <div className="pl-opp-top-bar">
                  <div className="pl-opp-top-identity">
                    <div className="pl-opp-rank-badge">#{opp.rank_order}</div>
                    <div className="pl-opp-identity-content">
                      <div className="pl-opp-meta-row">
                        <span className={`badge ${archetypeBadgeClass(opp.archetype)}`}>
                          {opp.archetype.replace(/_/g, ' ')}
                        </span>
                        <span className={`badge ${cohortBadgeClass(opp.portfolio_cohort)}`}>
                          {opp.portfolio_cohort.replace(/_/g, ' ')}
                        </span>
                        <span className="pl-opp-target-badge font-mono">
                          Target: {targetLabel}
                        </span>
                      </div>
                      <h3 className="pl-opp-title">{opportunityHeadline}</h3>
                    </div>
                  </div>

                  <div className="pl-opp-top-actions">
                    <button
                      type="button"
                      className="pl-btn-inspect"
                      onClick={() => onSelectDossier(opp.opportunity_id)}
                      aria-label={`Inspect evidence dossier for opportunity #${opp.rank_order}`}
                    >
                      <BookOpen size={14} />
                      <span>Inspect Evidence Dossier & Row Anchors</span>
                    </button>
                  </div>
                </div>

                {/* 2. MAIN CONTENT: 4 Core Pillars Grid (Label above, Value, Progress bar below) */}
                <div className="pl-opp-metrics-grid" role="group" aria-label="Opportunity Evaluation Scores">
                  {/* Operational Priority */}
                  <div className="pl-opp-metric-card">
                    <span className="pl-opp-metric-label">Operational Priority</span>
                    <div className="pl-opp-metric-value-wrap">
                      <strong className="pl-opp-metric-val text-cyan tabular-nums">
                        {opp.operational_priority_score.toFixed(0)}
                      </strong>
                      <span className="pl-opp-metric-max">/100</span>
                    </div>
                    <div className="pl-opp-bar-track" aria-hidden="true">
                      <div className="pl-opp-bar-fill bar-cyan" style={{ width: `${priorityPct}%` }} />
                    </div>
                  </div>

                  {/* Automation Readiness */}
                  <div className="pl-opp-metric-card">
                    <span className="pl-opp-metric-label">Automation Readiness</span>
                    <div className="pl-opp-metric-value-wrap">
                      <strong className="pl-opp-metric-val text-emerald tabular-nums">
                        {readinessVal !== null ? `${readinessVal.toFixed(0)}` : 'Assessing'}
                      </strong>
                      {readinessVal !== null && <span className="pl-opp-metric-max">/100</span>}
                    </div>
                    <div className="pl-opp-bar-track" aria-hidden="true">
                      <div className="pl-opp-bar-fill bar-emerald" style={{ width: `${readinessPct}%` }} />
                    </div>
                  </div>

                  {/* Impact Score */}
                  <div className="pl-opp-metric-card">
                    <span className="pl-opp-metric-label">Delay Impact Potential</span>
                    <div className="pl-opp-metric-value-wrap">
                      <strong className="pl-opp-metric-val text-purple tabular-nums">
                        {impactVal !== null ? `${impactVal.toFixed(0)}` : 'Pending'}
                      </strong>
                      {impactVal !== null && <span className="pl-opp-metric-max">/100</span>}
                    </div>
                    <div className="pl-opp-bar-track" aria-hidden="true">
                      <div className="pl-opp-bar-fill bar-purple" style={{ width: `${impactPct}%` }} />
                    </div>
                  </div>

                  {/* Evidence Confidence */}
                  <div className="pl-opp-metric-card">
                    <span className="pl-opp-metric-label">Evidence Confidence</span>
                    <div className="pl-opp-metric-value-wrap">
                      <strong className="pl-opp-metric-val text-amber tabular-nums">
                        {formatScorePercent(factors.confidence_score)}
                      </strong>
                    </div>
                    <div className="pl-opp-bar-track" aria-hidden="true">
                      <div className="pl-opp-bar-fill bar-amber" style={{ width: `${confidencePct}%` }} />
                    </div>
                  </div>
                </div>

                {/* 3. SUPPORTING CONTENT: Strengths, Constraints & Economics Synthesis */}
                <div className="pl-opp-supporting-section">
                  <div className="pl-opp-evidence-flow">
                    <div className="pl-opp-evidence-item">
                      <span className="pl-opp-evidence-label text-emerald">Empirical Strength:</span>
                      <span className="pl-opp-evidence-text">{opp.primary_strength}</span>
                    </div>
                    {opp.primary_constraint && (
                      <div className="pl-opp-evidence-item">
                        <span className="pl-opp-evidence-label text-amber">Operational Constraint:</span>
                        <span className="pl-opp-evidence-text">{opp.primary_constraint}</span>
                      </div>
                    )}
                  </div>

                  <div className="pl-opp-economics-row">
                    <div className="pl-opp-econ-item">
                      <span className="pl-opp-econ-label">Addressable Labor</span>
                      <span className="pl-opp-econ-val font-mono">
                        {laborHours !== null && laborHours !== undefined
                          ? `${laborHours.toFixed(1)} hrs/yr`
                          : <span className="text-muted">Unknown (Missing Hourly Wage Input)</span>}
                      </span>
                    </div>
                    <div className="pl-opp-econ-item">
                      <span className="pl-opp-econ-label">Annual Valuation</span>
                      <span className="pl-opp-econ-val font-mono">
                        {capacityVal !== null && capacityVal !== undefined
                          ? `$${capacityVal.toLocaleString()}`
                          : <span className="text-muted">Unmonetized (Requires Financial Parameters)</span>}
                      </span>
                    </div>
                    <div className="pl-opp-econ-item">
                      <span className="pl-opp-econ-label">Strategic Decision</span>
                      <span className="pl-opp-econ-val text-cyan font-semibold">
                        {economics?.synthesis?.strategic_decision || 'FEASIBILITY_INVESTIGATION'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
};
