import React, { useState } from 'react';
import { DurationStats } from '../../types/api';
import { formatDuration, formatHoursOnly } from '../../utils/formatters';
import { Clock, Info } from 'lucide-react';

interface CycleTimePercentileChartProps {
  stats: DurationStats;
  totalCases: number;
}

type MetricKey = 'min' | 'median' | 'mean' | 'p90' | 'max';

export const CycleTimePercentileChart: React.FC<CycleTimePercentileChartProps> = ({
  stats,
  totalCases,
}) => {
  const [activeMetric, setActiveMetric] = useState<MetricKey | null>(null);
  const { min_seconds, median_seconds, mean_seconds, p90_seconds, max_seconds } = stats;
  const maxVal = Math.max(max_seconds, 1);

  // Percent position along timeline (0 to 100%)
  const minPos = Math.min(Math.max((min_seconds / maxVal) * 100, 0), 100);
  const medianPos = Math.min(Math.max((median_seconds / maxVal) * 100, 2), 98);
  const meanPos = Math.min(Math.max((mean_seconds / maxVal) * 100, 2), 98);
  const p90Pos = Math.min(Math.max((p90_seconds / maxVal) * 100, 2), 98);

  return (
    <div className="chart-container" aria-label="Cycle Time Distribution Chart">
      <div className="chart-header">
        <div className="chart-title">
          <Clock size={16} className="text-cyan" />
          <span>Case Cycle-Time Distribution & Percentiles</span>
        </div>
        <div className="chart-subtitle">
          Computed across <strong>{totalCases}</strong> complete process traces (elapsed end-to-end duration)
        </div>
      </div>

      {/* Visual Timeline Range Bar */}
      <div className="percentile-timeline-wrapper">
        <div className="percentile-track" role="region" aria-label="Cycle time percentile timeline">
          {/* Active range bar from Min to Max */}
          <div
            className="percentile-range-fill"
            style={{ left: `${minPos}%`, width: `${Math.max(100 - minPos, 1)}%` }}
          />

          {/* Median Marker */}
          <div
            className={`percentile-marker marker-median ${activeMetric === 'median' ? 'is-active' : ''}`}
            style={{ left: `${medianPos}%` }}
            tabIndex={0}
            role="button"
            aria-label={`Median cycle time: ${formatDuration(median_seconds)}`}
            onMouseEnter={() => setActiveMetric('median')}
            onMouseLeave={() => setActiveMetric(null)}
            onFocus={() => setActiveMetric('median')}
            onBlur={() => setActiveMetric(null)}
          >
            <div className="marker-pin" />
            <div className="marker-badge">
              <span className="marker-badge-text">P50</span>
              <span style={{ position: 'absolute', width: 1, height: 1, padding: 0, margin: -1, overflow: 'hidden', clip: 'rect(0, 0, 0, 0)', whiteSpace: 'nowrap', border: 0 }}>
                MEDIAN (50th)
              </span>
            </div>
            {activeMetric === 'median' && (
              <div className="percentile-hover-tooltip" role="tooltip">
                <span className="tooltip-title">50th Percentile (Median)</span>
                <span className="tooltip-val">{formatDuration(median_seconds)} ({formatHoursOnly(median_seconds)})</span>
                <span className="tooltip-sub">Typical case flow; 50% completed faster</span>
              </div>
            )}
          </div>

          {/* Mean Marker */}
          <div
            className={`percentile-marker marker-mean ${activeMetric === 'mean' ? 'is-active' : ''}`}
            style={{ left: `${meanPos}%` }}
            tabIndex={0}
            role="button"
            aria-label={`Arithmetic mean cycle time: ${formatDuration(mean_seconds)}`}
            onMouseEnter={() => setActiveMetric('mean')}
            onMouseLeave={() => setActiveMetric(null)}
            onFocus={() => setActiveMetric('mean')}
            onBlur={() => setActiveMetric(null)}
          >
            <div className="marker-pin pin-dashed" />
            <div className="marker-badge marker-badge-bottom">
              <span className="marker-badge-text">AVG</span>
            </div>
            {activeMetric === 'mean' && (
              <div className="percentile-hover-tooltip tooltip-bottom" role="tooltip">
                <span className="tooltip-title">Arithmetic Mean</span>
                <span className="tooltip-val">{formatDuration(mean_seconds)} ({formatHoursOnly(mean_seconds)})</span>
                <span className="tooltip-sub">Overall average elapsed case duration</span>
              </div>
            )}
          </div>

          {/* 90th Percentile Marker */}
          <div
            className={`percentile-marker marker-p90 ${activeMetric === 'p90' ? 'is-active' : ''}`}
            style={{ left: `${p90Pos}%` }}
            tabIndex={0}
            role="button"
            aria-label={`90th percentile cycle time: ${formatDuration(p90_seconds)}`}
            onMouseEnter={() => setActiveMetric('p90')}
            onMouseLeave={() => setActiveMetric(null)}
            onFocus={() => setActiveMetric('p90')}
            onBlur={() => setActiveMetric(null)}
          >
            <div className="marker-pin" />
            <div className="marker-badge">
              <span className="marker-badge-text">P90</span>
            </div>
            {activeMetric === 'p90' && (
              <div className="percentile-hover-tooltip" role="tooltip">
                <span className="tooltip-title">90th Percentile (P90)</span>
                <span className="tooltip-val">{formatDuration(p90_seconds)} ({formatHoursOnly(p90_seconds)})</span>
                <span className="tooltip-sub">Long-tail delay threshold; worst 10% exceed this</span>
              </div>
            )}
          </div>
        </div>

        {/* Axis Bounds */}
        <div className="percentile-axis-bounds">
          <span>Min: {formatDuration(min_seconds)}</span>
          <span>Max: {formatDuration(max_seconds)}</span>
        </div>
      </div>

      {/* Numerical Benchmark Table */}
      <div className="percentile-metrics-grid" role="list" aria-label="Cycle time benchmark metrics">
        <div
          className={`percentile-metric-box ${activeMetric === 'min' ? 'is-active' : ''}`}
          role="listitem"
          tabIndex={0}
          onMouseEnter={() => setActiveMetric('min')}
          onMouseLeave={() => setActiveMetric(null)}
          onFocus={() => setActiveMetric('min')}
          onBlur={() => setActiveMetric(null)}
        >
          <span className="metric-box-title">Minimum</span>
          <span className="metric-box-val">{formatHoursOnly(min_seconds)}</span>
          <span className="metric-box-sub">Fastest observed ({Math.round(min_seconds)}s)</span>
        </div>
        <div
          className={`percentile-metric-box highlight-emerald ${activeMetric === 'median' ? 'is-active' : ''}`}
          role="listitem"
          tabIndex={0}
          onMouseEnter={() => setActiveMetric('median')}
          onMouseLeave={() => setActiveMetric(null)}
          onFocus={() => setActiveMetric('median')}
          onBlur={() => setActiveMetric(null)}
        >
          <span className="metric-box-title">Median (P50)</span>
          <span className="metric-box-val text-emerald">{formatHoursOnly(median_seconds)}</span>
          <span className="metric-box-sub">Typical flow ({Math.round(median_seconds)}s)</span>
        </div>
        <div
          className={`percentile-metric-box ${activeMetric === 'mean' ? 'is-active' : ''}`}
          role="listitem"
          tabIndex={0}
          onMouseEnter={() => setActiveMetric('mean')}
          onMouseLeave={() => setActiveMetric(null)}
          onFocus={() => setActiveMetric('mean')}
          onBlur={() => setActiveMetric(null)}
        >
          <span className="metric-box-title">Arithmetic Mean</span>
          <span className="metric-box-val">{formatHoursOnly(mean_seconds)}</span>
          <span className="metric-box-sub">Average across all cases</span>
        </div>
        <div
          className={`percentile-metric-box highlight-amber ${activeMetric === 'p90' ? 'is-active' : ''}`}
          role="listitem"
          tabIndex={0}
          onMouseEnter={() => setActiveMetric('p90')}
          onMouseLeave={() => setActiveMetric(null)}
          onFocus={() => setActiveMetric('p90')}
          onBlur={() => setActiveMetric(null)}
        >
          <span className="metric-box-title">90th Percentile (P90)</span>
          <span className="metric-box-val text-amber">{formatHoursOnly(p90_seconds)}</span>
          <span className="metric-box-sub">90% of cases within</span>
        </div>
        <div
          className={`percentile-metric-box highlight-rose ${activeMetric === 'max' ? 'is-active' : ''}`}
          role="listitem"
          tabIndex={0}
          onMouseEnter={() => setActiveMetric('max')}
          onMouseLeave={() => setActiveMetric(null)}
          onFocus={() => setActiveMetric('max')}
          onBlur={() => setActiveMetric(null)}
        >
          <span className="metric-box-title">Maximum</span>
          <span className="metric-box-val text-rose">{formatHoursOnly(max_seconds)}</span>
          <span className="metric-box-sub">Worst-case outlier</span>
        </div>
      </div>

      <div className="chart-footer-note">
        <Info size={13} />
        <span>
          <strong>Epistemic Note:</strong> Measured from timestamps of chronological event pairs. Duration reflects total elapsed time; it does not assume continuous manual labor without dedicated task-duration recording.
        </span>
      </div>
    </div>
  );
};
