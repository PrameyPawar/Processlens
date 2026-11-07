import React, { useState } from 'react';
import { ActivityFrequency } from '../../types/api';
import { BarChart3, ArrowUpDown, Info } from 'lucide-react';

interface ActivityFrequencyChartProps {
  activities: ActivityFrequency[];
  totalCases: number;
}

export const ActivityFrequencyChart: React.FC<ActivityFrequencyChartProps> = ({
  activities,
  totalCases,
}) => {
  const [sortBy, setSortBy] = useState<'occurrences' | 'coverage' | 'repetition'>('occurrences');
  const [hoveredActivity, setHoveredActivity] = useState<string | null>(null);

  if (!activities || activities.length === 0) {
    return (
      <div className="chart-empty-state">
        <p>No activity frequency records available.</p>
      </div>
    );
  }

  const sortedActivities = [...activities].sort((a, b) => {
    if (sortBy === 'occurrences') return b.total_occurrences - a.total_occurrences;
    if (sortBy === 'coverage') return b.case_coverage_percentage - a.case_coverage_percentage;
    return b.repetition_ratio - a.repetition_ratio;
  });

  const maxOccurrences = Math.max(...activities.map((a) => a.total_occurrences), 1);

  return (
    <div className="chart-container" aria-label="Activity Frequency Chart">
      <div className="chart-header">
        <div>
          <div className="chart-title">
            <BarChart3 size={16} className="text-cyan" />
            <span>Activity Volume &amp; Process Coverage</span>
          </div>
          <div className="chart-subtitle">
            Relative occurrence frequency and case coverage across {totalCases} cases
          </div>
        </div>

        {/* Sort Controls */}
        <div className="chart-controls">
          <span className="control-label">
            <ArrowUpDown size={13} /> Sort:
          </span>
          <button
            type="button"
            className={`btn-pill ${sortBy === 'occurrences' ? 'active' : ''}`}
            onClick={() => setSortBy('occurrences')}
          >
            Volume
          </button>
          <button
            type="button"
            className={`btn-pill ${sortBy === 'coverage' ? 'active' : ''}`}
            onClick={() => setSortBy('coverage')}
          >
            Case Coverage
          </button>
          <button
            type="button"
            className={`btn-pill ${sortBy === 'repetition' ? 'active' : ''}`}
            onClick={() => setSortBy('repetition')}
          >
            Repetition
          </button>
        </div>
      </div>

      {/* Horizontal Bar Chart List */}
      <div className="bar-chart-list" role="list">
        {sortedActivities.map((item) => {
          const widthPct = Math.min(Math.max((item.total_occurrences / maxOccurrences) * 100, 2), 100);
          const hasRework = item.repetition_ratio > 1.05;
          const isHovered = hoveredActivity === item.activity;

          return (
            <div
              key={item.activity}
              className={`bar-row ${isHovered ? 'bar-row-hovered' : ''}`}
              role="listitem"
              tabIndex={0}
              onMouseEnter={() => setHoveredActivity(item.activity)}
              onMouseLeave={() => setHoveredActivity(null)}
              onFocus={() => setHoveredActivity(item.activity)}
              onBlur={() => setHoveredActivity(null)}
              title={`${item.activity}: ${item.total_occurrences} events, ${item.case_coverage_percentage.toFixed(1)}% coverage, ${item.repetition_ratio.toFixed(2)}x repetition`}
            >
              <div className="bar-row-header">
                <span className="bar-row-label font-medium">{item.activity}</span>
                <div className="bar-row-stats">
                  <span className="badge badge-subtle">{item.total_occurrences} events</span>
                  <span className="text-muted text-xs">
                    {item.case_coverage_percentage.toFixed(0)}% cases
                  </span>
                  {hasRework && (
                    <span className="badge badge-amber text-xs">
                      {item.repetition_ratio.toFixed(2)}x loopback
                    </span>
                  )}
                </div>
              </div>

              {/* Progress Bar Container */}
              <div className="bar-track">
                <div
                  className={`bar-fill ${hasRework ? 'bar-amber' : 'bar-cyan'}`}
                  style={{ width: `${widthPct}%` }}
                />
              </div>

              {/* Interactive Tooltip Callout on Hover */}
              {isHovered && (
                <div className="bar-interactive-tooltip" role="tooltip">
                  <span>Occurrences: <strong>{item.total_occurrences}</strong></span>
                  <span>•</span>
                  <span>Cases: <strong>{item.case_count}</strong> ({item.case_coverage_percentage.toFixed(1)}%)</span>
                  <span>•</span>
                  <span>Repetition: <strong>{item.repetition_ratio.toFixed(2)}x</strong></span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="chart-footer-note">
        <Info size={13} />
        <span>
          <strong>Coverage vs. Repetition:</strong> Coverage indicates what fraction of distinct cases execute this step. Repetition ratio &gt; 1.0 indicates multiple executions per case (potential rework, re-inspection, or retry loops).
        </span>
      </div>
    </div>
  );
};
