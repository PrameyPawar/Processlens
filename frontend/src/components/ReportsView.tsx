import React from 'react';
import {
  DataQualityReport,
  ProcessAnalyticsResult,
  ProblemDetectionResult,
  PrioritisationResponse,
  ExplanationResponse,
} from '../types/api';
import { formatDuration, formatScorePercent } from '../utils/formatters';
import { Printer, Download, FileSpreadsheet, ShieldCheck, FileText, Compass, Target } from 'lucide-react';

export function encodeCsvCell(value: string | number | null | undefined): string {
  const raw = value === null || value === undefined ? '' : String(value);
  const formulaLike = typeof value === 'string' && /^[\u0000-\u0020\uFEFF]*[=+\-@]/.test(raw);
  const safe = formulaLike ? `'${raw}` : raw;
  return `"${safe.replace(/"/g, '""')}"`;
}

function safeExportStem(filename: string): string {
  const basename = filename.split(/[\\/]/).pop() || 'processlens_report';
  return basename.replace(/\.csv$/i, '').replace(/[<>:"/\\|?*\u0000-\u001F]/g, '_').slice(0, 100) || 'processlens_report';
}

interface ReportsViewProps {
  qualityReport: DataQualityReport;
  analytics: ProcessAnalyticsResult;
  problems: ProblemDetectionResult;
  prioritisation: PrioritisationResponse;
  explanations: ExplanationResponse | null;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  qualityReport,
  analytics,
  problems,
  prioritisation,
  explanations,
}) => {
  const { cycle_time, reconstruction_summary, transitions } = analytics;
  const stats = cycle_time.duration_stats;
  const manifest = explanations?.manifest;

  // Handle Export Opportunities CSV
  const handleExportOpportunitiesCsv = () => {
    const headers = [
      'Rank',
      'Opportunity_ID',
      'Archetype',
      'Portfolio_Cohort',
      'Operational_Priority_Score',
      'Confidence_Score',
      'Impact_Score',
      'Readiness_Score',
      'Sample_Addressable_Hours',
      'Annual_Addressable_Hours',
      'Strategic_Decision',
      'Primary_Strength',
    ];

    const rows = prioritisation.ranked_opportunities.map((opp) => [
      opp.rank_order,
      opp.opportunity_id,
      opp.archetype,
      opp.portfolio_cohort,
      opp.operational_priority_score.toFixed(1),
      formatScorePercent(opp.factors.confidence_score),
      opp.factors.impact_score !== null && opp.factors.impact_score !== undefined
        ? opp.factors.impact_score.toFixed(1)
        : 'N/A',
      opp.factors.readiness_score !== null && opp.factors.readiness_score !== undefined
        ? opp.factors.readiness_score.toFixed(1)
        : 'N/A',
      opp.economics.labor_effort.sample_addressable_labor_hours ?? 'N/A',
      opp.economics.labor_effort.annual_addressable_labor_hours ?? 'N/A',
      opp.economics.synthesis.strategic_decision,
      opp.primary_strength,
    ]);

    const csvContent = [headers, ...rows].map((row) => row.map(encodeCsvCell).join(',')).join('\r\n');
    downloadFile(csvContent, `${safeExportStem(qualityReport.filename)}_prioritised_opportunities.csv`, 'text/csv;charset=utf-8');
  };

  // Handle Export Process Transitions CSV
  const handleExportTransitionsCsv = () => {
    const headers = [
      'Source_Activity',
      'Target_Activity',
      'Handoff_Count',
      'Case_Count',
      'Median_Seconds',
      'Mean_Seconds',
      'P90_Seconds',
      'Max_Seconds',
      'Median_Formatted',
    ];

    const rows = transitions.map((t) => [
      t.source_activity,
      t.target_activity,
      t.transition_count,
      t.case_count,
      t.duration_stats.median_seconds.toFixed(1),
      t.duration_stats.mean_seconds.toFixed(1),
      t.duration_stats.p90_seconds.toFixed(1),
      t.duration_stats.max_seconds.toFixed(1),
      formatDuration(t.duration_stats.median_seconds),
    ]);

    const csvContent = [headers, ...rows].map((row) => row.map(encodeCsvCell).join(',')).join('\r\n');
    downloadFile(csvContent, `${safeExportStem(qualityReport.filename)}_process_transitions.csv`, 'text/csv;charset=utf-8');
  };

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="reports-workspace animate-fade-in" aria-label="Reports & Export Workspace">
      {/* Action Toolbar */}
      <div className="reports-toolbar glass-panel no-print mb-6">
        <div>
          <h2 className="section-title">Reports & Data Export</h2>
          <p className="section-subtitle">
            Prepare a decision briefing and export observed metrics and ranked opportunities
          </p>
        </div>

        <div className="reports-actions-group">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => window.print()}
          >
            <Printer size={16} /> Print / Save as PDF
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleExportOpportunitiesCsv}
          >
            <Download size={16} /> Export Opportunities (CSV)
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleExportTransitionsCsv}
          >
            <FileSpreadsheet size={16} /> Export Transitions (CSV)
          </button>
        </div>
      </div>

      {/* Printable Executive Briefing Document */}
      <article className="printable-report glass-panel" aria-label="Executive Briefing Document">
        {/* Document Header */}
        <header className="report-doc-header">
          <div className="report-brand">
            <span className="brand-title">ProcessLens</span>
            <span className="report-type-badge">OPERATIONS INTELLIGENCE BRIEFING</span>
          </div>

          <div className="report-meta-grid">
            <div>
              <span className="report-meta-label">Dataset:</span>
              <strong className="font-mono">{qualityReport.filename}</strong>
            </div>
            <div>
              <span className="report-meta-label">Source Events:</span>
              <span>{qualityReport.total_rows.toLocaleString()}</span>
            </div>
            <div>
              <span className="report-meta-label">Evaluated Cases:</span>
              <span>{reconstruction_summary.complete_cases_count}</span>
            </div>
            <div>
            <span className="report-meta-label">Source SHA-256:</span>
              <span className="font-mono text-xs">
              {manifest?.source_file_sha256 ? manifest.source_file_sha256 : 'Not included in this report'}
              </span>
            </div>
          </div>
        </header>

        {/* Executive Summary Narrative */}
        <section className="report-section">
          <h3 className="report-section-title">
            <FileText size={16} className="text-cyan inline mr-1" />
            1. Executive Synthesis & Strategic Guidance
          </h3>
          <p className="report-prose">
            {explanations?.portfolio_summary?.overall_narrative ||
              `ProcessLens completed deterministic reconstruction across ${reconstruction_summary.complete_cases_count} completed cases. The operational sequence exhibits a median cycle time of ${formatDuration(stats.median_seconds)} with ${problems.findings.length} detected operational problem signals.`}
          </p>

          {explanations?.portfolio_summary?.top_recommended_actions && explanations.portfolio_summary.top_recommended_actions.length > 0 && (
            <div className="report-recommendations-box">
              <h4 className="font-semibold text-sm mb-2 text-cyan">Top Recommended Strategic Actions:</h4>
              <ul className="report-bullets">
                {explanations.portfolio_summary.top_recommended_actions.map((act, idx) => (
                  <li key={idx}>{act}</li>
                ))}
              </ul>
            </div>
          )}
        </section>

        {/* Key Process Metrics & Bottlenecks */}
        <section className="report-section">
          <h3 className="report-section-title">
            <Compass size={16} className="text-cyan inline mr-1" />
            2. Observed Process Metrics
          </h3>
          <div className="report-metrics-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Metric Name</th>
                  <th>Observed Value</th>
                  <th>Statistical Role / Interpretation</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Median Cycle Time</td>
                  <td className="font-mono font-bold text-emerald">{formatDuration(stats.median_seconds)}</td>
                  <td>Typical case throughput duration (50th percentile)</td>
                </tr>
                <tr>
                  <td>Mean Cycle Time</td>
                  <td className="font-mono">{formatDuration(stats.mean_seconds)}</td>
                  <td>Arithmetic average elapsed case duration</td>
                </tr>
                <tr>
                  <td>P90 Cycle Time</td>
                  <td className="font-mono text-amber">{formatDuration(stats.p90_seconds)}</td>
                  <td>90% of completed cases conclude within this threshold</td>
                </tr>
                <tr>
                  <td>Process Variants</td>
                  <td className="font-mono">{reconstruction_summary.variant_count}</td>
                  <td>Distinct sequential activity paths observed in this dataset</td>
                </tr>
                <tr>
                  <td>Telemetry Completeness</td>
                  <td className="font-mono text-emerald">
                    {qualityReport.total_rows > 0
                      ? `${((qualityReport.valid_rows / qualityReport.total_rows) * 100).toFixed(1)}%`
                      : '0%'}
                  </td>
                  <td>{qualityReport.invalid_rows} rows flagged; malformed and incomplete rows are excluded, while duplicate events are retained and separately handled.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Prioritised Improvement Roadmap */}
        <section className="report-section">
          <h3 className="report-section-title">
            <Target size={16} className="text-cyan inline mr-1" />
            3. Prioritised Improvement Levers
          </h3>
          <div className="report-opps-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Opportunity ID</th>
                  <th>Archetype</th>
                  <th>Portfolio Cohort</th>
                  <th>Composite Score</th>
                  <th>Operational Priority</th>
                  <th>Confidence</th>
                  <th>Strategic Action</th>
                </tr>
              </thead>
              <tbody>
                {prioritisation.ranked_opportunities.map((opp) => (
                  <tr key={opp.opportunity_id}>
                    <td className="font-bold">#{opp.rank_order}</td>
                    <td className="font-mono text-sm">{opp.opportunity_id}</td>
                    <td>{opp.archetype}</td>
                    <td>
                      <span className="badge badge-subtle text-xs">{opp.portfolio_cohort}</span>
                    </td>
                    <td className="font-mono font-bold text-cyan">
                      {opp.composite_priority_score !== null && opp.composite_priority_score !== undefined
                        ? `${opp.composite_priority_score.toFixed(1)}/100`
                        : 'Unscored'}
                    </td>
                    <td className="font-mono text-muted">
                      {opp.operational_priority_score.toFixed(0)}/100
                    </td>
                    <td className="font-mono">{formatScorePercent(opp.factors.confidence_score)}</td>
                    <td className="text-xs">{opp.economics.synthesis.strategic_decision}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Epistemic Assurance & Caveats */}
        <footer className="report-footer">
          <div className="report-footer-note">
            <ShieldCheck size={14} className="text-emerald inline mr-1" />
            <span>
              <strong>Calculation scope:</strong> Process metrics are deterministic calculations over observed timestamps. Financial results require supplied inputs and assumptions; they are not guaranteed savings.
            </span>
          </div>
        </footer>
      </article>
    </div>
  );
};
