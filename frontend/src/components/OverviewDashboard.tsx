import React from 'react';
import {
  DataQualityReport,
  ProcessAnalyticsResult,
  ProblemDetectionResult,
  PrioritisationResponse,
  ExplanationResponse,
} from '../types/api';
import { formatDuration, formatScorePercent } from '../utils/formatters';
import { MetricCard } from './ui/MetricCard';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { CycleTimePercentileChart } from './charts/CycleTimePercentileChart';
import { OpportunityDimensionsChart } from './charts/OpportunityDimensionsChart';
import { ActivityFrequencyChart } from './charts/ActivityFrequencyChart';
import { TransitionDurationChart } from './charts/TransitionDurationChart';
import {
  FileCheck2,
  Clock,
  AlertTriangle,
  Target,
  Sparkles,
  ShieldCheck,
  Compass,
  ArrowRight,
  HelpCircle,
  FileText,
} from 'lucide-react';

interface OverviewDashboardProps {
  qualityReport: DataQualityReport;
  analytics: ProcessAnalyticsResult;
  problems: ProblemDetectionResult;
  prioritisation: PrioritisationResponse;
  explanations: ExplanationResponse | null;
  onNavigateToStep: (stepId: any) => void;
  onSelectDossier: (oppId: string) => void;
}

export const OverviewDashboard: React.FC<OverviewDashboardProps> = ({
  qualityReport,
  analytics,
  problems,
  prioritisation,
  explanations,
  onNavigateToStep,
  onSelectDossier,
}) => {
  const { reconstruction_summary, cycle_time } = analytics;
  const topOpportunity = prioritisation.ranked_opportunities.length > 0
    ? prioritisation.ranked_opportunities[0]
    : null;

  const topProblems = problems.findings.slice(0, 3);
  const topOpportunitiesList = prioritisation.ranked_opportunities.slice(0, 3);

  const highSeverityCount = problems.findings.filter(
    (f) => f.signal_level === 'HIGH' || f.severity === 'HIGH'
  ).length;

  const validPercentage = qualityReport.total_rows > 0
    ? ((qualityReport.valid_rows / qualityReport.total_rows) * 100).toFixed(1)
    : '0';

  return (
    <div className="pl-overview-view" aria-label="Executive Overview Dashboard">
      {/* ============================================================== */}
      {/* A. PAGE CONTEXT & WORKSPACE HEADER */}
      {/* ============================================================== */}
      <section className="pl-page-context-card" aria-label="Page Context">
        <div className="pl-context-main">
          <div className="pl-context-tag">
            <ShieldCheck size={14} className="text-teal" />
            <span>DETERMINISTIC ANALYSIS VERIFIED</span>
          </div>
          <h1 className="pl-context-title">Operations Intelligence Overview</h1>
          <p className="pl-context-description">
            Analysis of <strong className="font-mono text-cyan">{qualityReport.filename}</strong>:
            reconstruction of {reconstruction_summary.complete_cases_count} complete process traces,
            cycle-time percentiles, bottleneck identification, and evidence-backed opportunity prioritisation.
          </p>
        </div>

        <div className="pl-context-actions">
          <Button
            variant="primary"
            size="md"
            iconRight={<ArrowRight size={14} />}
            onClick={() => onNavigateToStep('opportunities')}
          >
            Explore Opportunities Roadmap
          </Button>
        </div>
      </section>

      {/* ============================================================== */}
      {/* B. KEY METRICS GRID (6 CORE DECISION KPIS) */}
      {/* ============================================================== */}
      <section className="pl-metrics-section" aria-label="Key Operational Metrics">
        <div className="pl-metrics-grid">
          {/* KPI 1: Cases Analysed */}
          <MetricCard
            label="Cases Analysed"
            value={reconstruction_summary.complete_cases_count}
            caption={`${reconstruction_summary.variant_count} unique sequence variant(s)`}
            icon={<Compass size={14} className="text-cyan" />}
            variant="cyan"
            tooltip="Total complete end-to-end process instances reconstructed from ordered events."
          />

          {/* KPI 2: Valid-Event Percentage */}
          <MetricCard
            label="Valid Event Rate"
            value={validPercentage}
            unit="%"
            caption={`${qualityReport.valid_rows.toLocaleString()} of ${qualityReport.total_rows.toLocaleString()} rows valid`}
            icon={<FileCheck2 size={14} className="text-teal" />}
            variant="teal"
            tooltip="Percentage of raw log rows satisfying the canonical event schema. Note: Schema validity confirms structural integrity, not complete shop-floor telemetry coverage."
          />

          {/* KPI 3: Median Cycle Time */}
          <MetricCard
            label="Median Cycle Time"
            value={formatDuration(cycle_time.duration_stats.median_seconds)}
            caption="50% of cases complete faster"
            icon={<Clock size={14} className="text-amber" />}
            variant="amber"
            tooltip="50th percentile elapsed time from first activity to case completion."
          />

          {/* KPI 4: P90 Cycle Time */}
          <MetricCard
            label="P90 Cycle Time"
            value={formatDuration(cycle_time.duration_stats.p90_seconds)}
            caption="Highlights severe tail delay"
            icon={<Clock size={14} className="text-coral" />}
            variant="coral"
            tooltip="90th percentile elapsed duration; reveals delays experienced by long-tail delayed orders."
          />

          {/* KPI 5: Operational Findings */}
          <MetricCard
            label="Operational Findings"
            value={problems.findings.length}
            caption={`${highSeverityCount} high-severity bottleneck(s)`}
            icon={<AlertTriangle size={14} className="text-coral" />}
            variant="coral"
            tooltip="Statistically significant bottlenecks, loopbacks, and variance signals detected."
            onClick={() => onNavigateToStep('problems')}
          />

          {/* KPI 6: Prioritised Opportunities */}
          <MetricCard
            label="Prioritised Opportunities"
            value={prioritisation.ranked_opportunities.length}
            caption={`Top candidate: ${topOpportunity?.archetype || 'None'}`}
            icon={<Target size={14} className="text-purple" />}
            variant="purple"
            tooltip="Improvement and automation levers ranked deterministically by composite priority."
            onClick={() => onNavigateToStep('opportunities')}
          />
        </div>
      </section>

      {/* ============================================================== */}
      {/* C. RECOMMENDED NEXT INVESTIGATION (SPOTLIGHT DECISION) */}
      {/* ============================================================== */}
      {topOpportunity && (
        <section className="pl-spotlight-decision" aria-label="Recommended Next Investigation">
          <div className="pl-spotlight-header">
            <div className="pl-spotlight-badge">
              <Sparkles size={15} />
              <span>WHAT SHOULD THIS BUSINESS FIX OR AUTOMATE FIRST?</span>
            </div>
            <span className="pl-spotlight-id font-mono">{topOpportunity.opportunity_id}</span>
          </div>

          <div className="pl-spotlight-body">
            <div className="pl-spotlight-lead">
              <h2 className="pl-spotlight-title">
                Rank #1: {topOpportunity.archetype.replace(/_/g, ' ')} on{' '}
                <span className="text-cyan font-mono">{topOpportunity.opportunity_id.replace(/^opp_/, '')}</span>
              </h2>

              <p className="pl-spotlight-narrative">
                {explanations?.explanations?.[0]?.executive_summary ||
                  topOpportunity.primary_strength ||
                  `Prioritised as the leading operational improvement candidate with composite priority score ${topOpportunity.operational_priority_score.toFixed(0)}/100.`}
              </p>
            </div>

            {/* Structured Factor Chips */}
            <div className="pl-spotlight-factors">
              <div className="pl-factor-item">
                <span className="pl-factor-label">Portfolio Cohort</span>
                <span className="pl-factor-value cohort-badge font-bold">{topOpportunity.portfolio_cohort}</span>
              </div>
              <div className="pl-factor-item">
                <span className="pl-factor-label">Operational Priority</span>
                <span className="pl-factor-value font-mono text-cyan font-bold">
                  {(topOpportunity.operational_priority_score ?? (topOpportunity as any).composite_priority_score) != null
                    ? `${(topOpportunity.operational_priority_score ?? (topOpportunity as any).composite_priority_score).toFixed(0)}/100`
                    : '—'}
                </span>
              </div>
              <div className="pl-factor-item">
                <span className="pl-factor-label">Automation Readiness</span>
                <span className="pl-factor-value font-mono text-teal font-bold">
                  {((topOpportunity.factors as any).automation_readiness_score ?? (topOpportunity.factors as any).readiness_score) != null
                    ? `${((topOpportunity.factors as any).automation_readiness_score ?? (topOpportunity.factors as any).readiness_score).toFixed(0)}/100`
                    : 'Unknown'}
                </span>
              </div>
              <div className="pl-factor-item">
                <span className="pl-factor-label">Statistical Confidence</span>
                <span className="pl-factor-value font-mono text-teal">
                  {formatScorePercent(topOpportunity.factors.confidence_score)}
                </span>
              </div>
            </div>

            {/* Financial Inputs & Unknowns Notice */}
            <div className="pl-spotlight-economics-notice">
              <div className="pl-economics-item">
                <Badge variant="teal">EMPIRICAL EVIDENCE</Badge>
                <span className="pl-economics-text">
                  Direct cycle-time delay confirmed across {reconstruction_summary.complete_cases_count} cases.
                </span>
              </div>
              <div className="pl-economics-item">
                <Badge variant="amber">UNMONETISED</Badge>
                <span className="pl-economics-text text-muted">
                  {topOpportunity.economics.capacity_valuation?.gross_annual_capacity_value !== null &&
                  topOpportunity.economics.capacity_valuation?.gross_annual_capacity_value !== undefined
                    ? 'Annual capacity return calculated using user-specified hourly parameters.'
                    : 'Monetary ROI remains unknown until hourly labor wage and implementation cost parameters are provided; never assumed as $0.'}
                </span>
              </div>
            </div>

            <div className="pl-spotlight-footer">
              <Button
                variant="primary"
                size="md"
                iconLeft={<FileText size={14} />}
                onClick={() => onSelectDossier(topOpportunity.opportunity_id)}
              >
                Inspect Evidence Dossier
              </Button>
              <Button
                variant="secondary"
                size="md"
                onClick={() => onNavigateToStep('opportunities')}
              >
                Inspect Opportunity Details
              </Button>
            </div>
          </div>
        </section>
      )}

      {/* ============================================================== */}
      {/* D. VISUAL ANALYSIS (DATA-GROUNDED CHARTS) */}
      {/* ============================================================== */}
      <section className="pl-visual-analysis-section" aria-label="Visual Analysis">
        <div className="pl-section-heading">
          <h2 className="pl-section-title">Visual Process & Opportunity Analysis</h2>
          <p className="pl-section-subtitle">
            Deterministic duration percentiles, activity frequencies, and multi-dimensional opportunity trade-offs.
          </p>
        </div>

        <div className="pl-charts-grid">
          {/* Chart 1: Cycle-Time Percentiles */}
          <div className="pl-chart-panel">
            <CycleTimePercentileChart
              stats={cycle_time.duration_stats}
              totalCases={reconstruction_summary.complete_cases_count}
            />
          </div>

          {/* Chart 2: Opportunity Dimensions Radar/Comparison */}
          <div className="pl-chart-panel">
            <OpportunityDimensionsChart
              opportunities={prioritisation.ranked_opportunities}
            />
          </div>

          {/* Chart 3: Activity Frequency & Volume */}
          <div className="pl-chart-panel">
            <ActivityFrequencyChart
              activities={analytics.activity_frequency}
              totalCases={reconstruction_summary.complete_cases_count}
            />
          </div>

          {/* Chart 4: Transition Duration & Bottlenecks */}
          <div className="pl-chart-panel">
            <TransitionDurationChart
              transitions={analytics.transitions}
            />
          </div>
        </div>
      </section>

      {/* ============================================================== */}
      {/* E. SUPPORTING FINDINGS & ACTIONABLE WORKSPACE LINKS */}
      {/* ============================================================== */}
      <section className="pl-supporting-grid-section" aria-label="Supporting Findings & Workspaces">
        <div className="pl-supporting-card">
          <div className="pl-supporting-header">
            <div className="pl-supporting-title-group">
              <AlertTriangle size={16} className="text-coral" />
              <h3>Critical Operational Findings ({problems.findings.length})</h3>
            </div>
            <button
              type="button"
              className="pl-text-link"
              onClick={() => onNavigateToStep('problems')}
            >
              View all &rarr;
            </button>
          </div>
          <div className="pl-supporting-list">
            {topProblems.map((f, idx) => {
              const sev = (f.severity || f.signal_level || 'INFO').toUpperCase();
              const label = (f as any).name || f.title || f.rule || 'Operational Finding';
              const impactedCases = (f as any).impacted_cases_count ?? 0;
              const totalCases = reconstruction_summary.complete_cases_count || 1;
              const pct = ((impactedCases / totalCases) * 100).toFixed(0);

              return (
                <div key={idx} className="pl-supporting-item">
                  <span className={`pl-severity-pill severity-${sev.toLowerCase()}`}>
                    {sev}
                  </span>
                  <div className="pl-supporting-info">
                    <span className="pl-supporting-name">{label}</span>
                    <span className="pl-supporting-meta">
                      Impacts {impactedCases} cases ({pct}%)
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="pl-supporting-card">
          <div className="pl-supporting-header">
            <div className="pl-supporting-title-group">
              <Target size={16} className="text-purple" />
              <h3>Top Improvement Levers ({prioritisation.ranked_opportunities.length})</h3>
            </div>
            <button
              type="button"
              className="pl-text-link"
              onClick={() => onNavigateToStep('opportunities')}
            >
              View portfolio &rarr;
            </button>
          </div>
          <div className="pl-supporting-list">
            {topOpportunitiesList.map((opp) => (
              <div
                key={opp.opportunity_id}
                className="pl-supporting-item cursor-pointer hover-surface"
                onClick={() => onSelectDossier(opp.opportunity_id)}
              >
                <span className="pl-rank-pill font-mono font-bold text-cyan">
                  #{opp.rank_order ?? (opp as any).rank ?? 1}
                </span>
                <div className="pl-supporting-info">
                  <span className="pl-supporting-name">
                    {opp.archetype.replace(/_/g, ' ')}
                  </span>
                  <span className="pl-supporting-meta font-mono">
                    Priority: {(opp.operational_priority_score ?? (opp as any).composite_priority_score)?.toFixed(0) ?? '—'}/100 · Readiness: {((opp.factors as any).automation_readiness_score ?? (opp.factors as any).readiness_score)?.toFixed(0) ?? '—'}/100
                  </span>
                </div>
                <Button variant="subtle" size="sm">
                  Dossier
                </Button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============================================================== */}
      {/* F. EVIDENCE TRANSPARENCY & EPISTEMIC STATUS LEGEND */}
      {/* ============================================================== */}
      <footer className="pl-epistemic-legend-bar" aria-label="Epistemic Classification Standard">
        <div className="pl-legend-title">
          <HelpCircle size={14} className="text-muted" />
          <span>Epistemic Grounding Standard:</span>
        </div>
        <div className="pl-legend-badges">
          <span className="pl-legend-item">
            <Badge variant="fact">FACT</Badge>
            <span className="pl-legend-text">Directly calculated from event logs</span>
          </span>
          <span className="pl-legend-item">
            <Badge variant="estimate">ESTIMATE</Badge>
            <span className="pl-legend-text">Modelled using stated assumptions</span>
          </span>
          <span className="pl-legend-item">
            <Badge variant="assumption">ASSUMPTION</Badge>
            <span className="pl-legend-text">Configurable parameter input</span>
          </span>
          <span className="pl-legend-item">
            <Badge variant="unknown">UNKNOWN</Badge>
            <span className="pl-legend-text">Requires user input; never assumed as $0</span>
          </span>
        </div>
      </footer>
    </div>
  );
};
