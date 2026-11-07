import React, { useState } from 'react';
import { ActivityTransition } from '../../types/api';
import { formatDuration, formatHoursOnly } from '../../utils/formatters';
import { ArrowRight, GitCommit, Info } from 'lucide-react';

export type TransitionSortMetric = 'cumulative' | 'median' | 'p90';

interface TransitionDurationChartProps {
  transitions: ActivityTransition[];
  initialSortMetric?: TransitionSortMetric;
}

export const TransitionDurationChart: React.FC<TransitionDurationChartProps> = ({
  transitions,
  initialSortMetric = 'cumulative',
}) => {
  const [sortMetric, setSortMetric] = useState<TransitionSortMetric>(initialSortMetric);
  const [topCount, setTopCount] = useState<number>(6);
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);

  if (!transitions || transitions.length === 0) {
    return (
      <div className="chart-empty-state">
        <p>No transition telemetry records available.</p>
      </div>
    );
  }

  // Calculate total cumulative duration across all transitions
  const totalProcessTransitionSeconds = transitions.reduce(
    (sum, t) => sum + t.transition_count * t.duration_stats.mean_seconds,
    0
  );

  // Helper to calculate metric value for sorting and bar width
  const getMetricValue = (t: ActivityTransition, metric: TransitionSortMetric): number => {
    switch (metric) {
      case 'cumulative':
        return t.transition_count * t.duration_stats.mean_seconds;
      case 'median':
        return t.duration_stats.median_seconds;
      case 'p90':
        return t.duration_stats.p90_seconds;
      default:
        return t.duration_stats.median_seconds;
    }
  };

  // Sort transitions according to selected metric
  const sortedTransitions = [...transitions]
    .sort((a, b) => getMetricValue(b, sortMetric) - getMetricValue(a, sortMetric))
    .slice(0, topCount);

  const maxMetricValue = Math.max(
    ...sortedTransitions.map((t) => getMetricValue(t, sortMetric)),
    1
  );

  return (
    <div className="chart-container" aria-label="Transition Bottleneck Chart">
      <div className="chart-header">
        <div>
          <div className="chart-title">
            <GitCommit size={16} className="text-cyan" />
            <span>Process Step Handoffs &amp; Bottlenecks</span>
          </div>
          <div className="chart-subtitle">
            {sortMetric === 'cumulative' &&
              'Ranked by cumulative elapsed duration impact across complete cases (Phase 4 Signal Alignment)'}
            {sortMetric === 'median' &&
              'Ranked by typical (50th percentile) single-case elapsed handover time'}
            {sortMetric === 'p90' &&
              'Ranked by 90th percentile long-tail delay between consecutive operational steps'}
          </div>
        </div>

        <div className="chart-controls-wrapper">
          <div className="chart-controls">
            <span className="control-label">Ranking Basis:</span>
            <button
              type="button"
              className={`btn-pill ${sortMetric === 'cumulative' ? 'active' : ''}`}
              onClick={() => setSortMetric('cumulative')}
              title="Rank by total cumulative time consumed in the process"
            >
              Cumulative Impact
            </button>
            <button
              type="button"
              className={`btn-pill ${sortMetric === 'median' ? 'active' : ''}`}
              onClick={() => setSortMetric('median')}
              title="Rank by median single-case handover time"
            >
              Median Handover
            </button>
            <button
              type="button"
              className={`btn-pill ${sortMetric === 'p90' ? 'active' : ''}`}
              onClick={() => setSortMetric('p90')}
              title="Rank by 90th percentile long-tail delay"
            >
              Tail (P90)
            </button>
          </div>

          <div className="chart-controls">
            <span className="control-label">Show top:</span>
            {[4, 6, 10].map((num) => (
              <button
                key={num}
                type="button"
                className={`btn-pill ${topCount === num ? 'active' : ''}`}
                onClick={() => setTopCount(num)}
              >
                {num}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="transition-chart-list" role="list">
        {sortedTransitions.map((t, idx) => {
          const key = `${t.source_activity}->${t.target_activity}`;
          const isHovered = hoveredKey === key;
          const metricVal = getMetricValue(t, sortMetric);
          const barWidth = Math.min(
            Math.max((metricVal / maxMetricValue) * 100, 3),
            100
          );
          const isTopRanked = idx === 0;

          // Cumulative metrics
          const cumSeconds = t.transition_count * t.duration_stats.mean_seconds;
          const sharePct =
            totalProcessTransitionSeconds > 0
              ? (cumSeconds / totalProcessTransitionSeconds) * 100
              : 0;

          return (
            <div
              key={key}
              className={`transition-bar-card ${isHovered ? 'transition-card-hovered' : ''}`}
              role="listitem"
              tabIndex={0}
              onMouseEnter={() => setHoveredKey(key)}
              onMouseLeave={() => setHoveredKey(null)}
              onFocus={() => setHoveredKey(key)}
              onBlur={() => setHoveredKey(null)}
              title={`${t.source_activity} → ${t.target_activity}: Cumulative ${formatHoursOnly(cumSeconds)} (${sharePct.toFixed(1)}%), Median ${formatDuration(t.duration_stats.median_seconds)}, P90 ${formatDuration(t.duration_stats.p90_seconds)}`}
            >
              <div className="transition-meta-header">
                <div className="transition-flow-title">
                  <span className="font-semibold text-primary">{t.source_activity}</span>
                  <ArrowRight size={14} className="text-cyan mx-1" />
                  <span className="font-semibold text-primary">{t.target_activity}</span>
                  {isTopRanked && sortMetric === 'cumulative' && (
                    <span className="badge badge-rose text-xs ml-2">Primary Bottleneck</span>
                  )}
                  {isTopRanked && sortMetric === 'median' && (
                    <span className="badge badge-warning text-xs ml-2">Longest Median Handover</span>
                  )}
                  {isTopRanked && sortMetric === 'p90' && (
                    <span className="badge badge-purple text-xs ml-2">Highest Tail Latency</span>
                  )}
                </div>
                <div className="transition-quick-stats">
                  <span className="text-xs text-muted">
                    {t.transition_count} handoffs ({t.case_count} cases)
                  </span>
                  {sortMetric === 'cumulative' && (
                    <span className="font-mono text-rose font-semibold ml-3">
                      Impact: {formatHoursOnly(cumSeconds)} ({sharePct.toFixed(1)}% share)
                    </span>
                  )}
                  {sortMetric === 'median' && (
                    <span className="font-mono text-cyan font-semibold ml-3">
                      Median: {formatDuration(t.duration_stats.median_seconds)}
                    </span>
                  )}
                  {sortMetric === 'p90' && (
                    <span className="font-mono text-amber font-semibold ml-3">
                      P90: {formatHoursOnly(t.duration_stats.p90_seconds)}
                    </span>
                  )}
                </div>
              </div>

              {/* Comparative Duration Bar */}
              <div className="transition-bar-wrapper">
                <div className="bar-track">
                  <div
                    className={`bar-fill ${
                      isTopRanked
                        ? sortMetric === 'cumulative'
                          ? 'bar-rose'
                          : sortMetric === 'p90'
                          ? 'bar-purple'
                          : 'bar-amber'
                        : 'bar-cyan'
                    }`}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
                <div className="transition-stats-inline">
                  <span>Cumulative: {formatHoursOnly(cumSeconds)} ({sharePct.toFixed(1)}%)</span>
                  <span>Median: {formatDuration(t.duration_stats.median_seconds)}</span>
                  <span>P90: {formatHoursOnly(t.duration_stats.p90_seconds)}</span>
                  <span>Mean: {formatHoursOnly(t.duration_stats.mean_seconds)}</span>
                  <span>Max: {formatHoursOnly(t.duration_stats.max_seconds)}</span>
                </div>
              </div>

              {/* Interactive Tooltip Callout on Hover */}
              {isHovered && (
                <div className="bar-interactive-tooltip" role="tooltip">
                  <span>Total Elapsed Impact: <strong>{formatHoursOnly(cumSeconds)} ({sharePct.toFixed(1)}% of total)</strong></span>
                  <span>•</span>
                  <span>Median: <strong>{formatDuration(t.duration_stats.median_seconds)}</strong></span>
                  <span>•</span>
                  <span>P90: <strong>{formatDuration(t.duration_stats.p90_seconds)}</strong></span>
                  <span>•</span>
                  <span>Tail Dispersion (P90/P50): <strong>{(t.duration_stats.p90_seconds / Math.max(t.duration_stats.median_seconds, 1)).toFixed(1)}x</strong></span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="chart-footer-note">
        <Info size={13} />
        <span>
          <strong>Analytical Distinction:</strong> Cumulative Impact aggregates total process elapsed time (handoff count &times; mean duration) where heavy-tailed delays dominate overall system lead time even if the typical median case moves quickly. Median handover reflects the typical duration experienced by a single case.
        </span>
      </div>
    </div>
  );
};
