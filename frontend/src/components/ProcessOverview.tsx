import React, { useState } from 'react';
import { ProcessAnalyticsResult } from '../types/api';
import { formatDuration } from '../utils/formatters';
import { CycleTimePercentileChart } from './charts/CycleTimePercentileChart';
import { TransitionDurationChart } from './charts/TransitionDurationChart';
import { ActivityFrequencyChart } from './charts/ActivityFrequencyChart';
import { ArrowRight, Compass, CheckCircle2, Search } from 'lucide-react';

export { formatDuration };

interface ProcessOverviewProps {
  analytics: ProcessAnalyticsResult;
}

export const ProcessOverview: React.FC<ProcessOverviewProps> = ({ analytics }) => {
  const [activeSubTab, setActiveSubTab] = useState<'variants' | 'transitions' | 'activities' | 'rework' | 'visuals'>('visuals');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const { cycle_time, reconstruction_summary, transitions, rework, activity_frequency } = analytics;
  const stats = cycle_time.duration_stats;

  const reworkActivities = rework.filter((r) => r.rework_case_count > 0 || r.rework_occurrences > 0);

  // Filtered lists based on search
  const filteredTransitions = transitions.filter(
    (t) =>
      t.source_activity.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.target_activity.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredActivities = activity_frequency.filter((a) =>
    a.activity.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <section className="glass-panel animate-fade-in" aria-label="Process Overview">
      <div className="section-header">
        <div>
          <h2 className="section-title">Phase 2 & 3: Process Reconstruction & Analytics</h2>
          <p className="section-subtitle">
            Evaluated on <strong className="text-emerald">{cycle_time.evaluated_cases_count} complete cases</strong> across {reconstruction_summary.total_source_rows.toLocaleString()} source events
          </p>
        </div>
        <div className="badge badge-info">
          <Compass size={14} /> Deterministic Metrics (Zero LLM Derivations)
        </div>
      </div>

      {/* KPI Cards */}
      <div className="stats-grid mb-6">
        <div className="stat-card">
          <div className="stat-label">Complete Cases Evaluated</div>
          <div className="stat-value text-emerald">{cycle_time.evaluated_cases_count}</div>
          <div className="stat-caption">
            {reconstruction_summary.total_cases_found > 0
              ? `${((reconstruction_summary.complete_cases_count / reconstruction_summary.total_cases_found) * 100).toFixed(1)}% of cases complete`
              : 'No cases available for completeness calculation'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Mean Case Cycle Time</div>
          <div className="stat-value">{formatDuration(stats.mean_seconds)}</div>
          <div className="stat-caption">Median: {formatDuration(stats.median_seconds)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">90th Percentile (p90)</div>
          <div className="stat-value text-amber">{formatDuration(stats.p90_seconds)}</div>
          <div className="stat-caption">Min: {formatDuration(stats.min_seconds)} | Max: {formatDuration(stats.max_seconds)}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Process Variants</div>
          <div className="stat-value">{reconstruction_summary.variant_count}</div>
          <div className="stat-caption">{transitions.length} direct step transitions</div>
        </div>
      </div>

      {/* Sub Tabs */}
      <div className="tab-bar mb-4">
        <button
          type="button"
          className={`tab-btn ${activeSubTab === 'visuals' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('visuals')}
        >
          Visual Analytics
        </button>
        <button
          type="button"
          className={`tab-btn ${activeSubTab === 'transitions' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('transitions')}
        >
          Step Transitions ({transitions.length})
        </button>
        <button
          type="button"
          className={`tab-btn ${activeSubTab === 'activities' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('activities')}
        >
          Activity Frequencies ({activity_frequency.length})
        </button>
        <button
          type="button"
          className={`tab-btn ${activeSubTab === 'variants' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('variants')}
        >
          Process Variants ({reconstruction_summary.variant_count})
        </button>
        <button
          type="button"
          className={`tab-btn ${activeSubTab === 'rework' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('rework')}
        >
          Rework & Repetition ({reworkActivities.length})
        </button>
      </div>

      {/* Search Bar for Table Subtabs */}
      {(activeSubTab === 'transitions' || activeSubTab === 'activities') && (
        <div className="table-search-bar mb-4">
          <Search size={15} className="text-muted" />
          <input
            type="text"
            className="search-input"
            placeholder={`Filter ${activeSubTab}...`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          {searchTerm && (
            <button type="button" className="btn-link text-xs" onClick={() => setSearchTerm('')}>
              Clear
            </button>
          )}
        </div>
      )}

      {/* SubTab 0: Visual Analytics */}
      {activeSubTab === 'visuals' && (
        <div className="tab-pane animate-fade-in space-y-6">
          <CycleTimePercentileChart
            stats={stats}
            totalCases={cycle_time.evaluated_cases_count}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <TransitionDurationChart transitions={transitions} />
            <ActivityFrequencyChart
              activities={activity_frequency}
              totalCases={cycle_time.evaluated_cases_count}
            />
          </div>
        </div>
      )}

      {/* SubTab 1: Transitions */}
      {activeSubTab === 'transitions' && (
        <div className="tab-pane animate-fade-in">
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Transition Path</th>
                  <th>Observed Count</th>
                  <th>Case Coverage</th>
                  <th>Mean Elapsed Time</th>
                  <th>Median Elapsed Time</th>
                  <th>90th Percentile (p90)</th>
                </tr>
              </thead>
              <tbody>
                {filteredTransitions.map((t, idx) => (
                  <tr key={`${t.source_activity}-${t.target_activity}-${idx}`}>
                    <td>
                      <div className="transition-path">
                        <span className="badge badge-neutral">{t.source_activity}</span>
                        <ArrowRight size={14} className="text-muted" />
                        <span className="badge badge-neutral">{t.target_activity}</span>
                      </div>
                    </td>
                    <td><code>{t.transition_count.toLocaleString()}</code></td>
                    <td>
                      {t.case_count} cases ({((t.case_count / Math.max(1, cycle_time.evaluated_cases_count)) * 100).toFixed(1)}%)
                    </td>
                    <td><strong>{formatDuration(t.duration_stats.mean_seconds)}</strong></td>
                    <td>{formatDuration(t.duration_stats.median_seconds)}</td>
                    <td className="text-amber">{formatDuration(t.duration_stats.p90_seconds)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="caption-notice">
            * Elapsed duration measures transition milestone interval between distinct events. Waiting time is not asserted without specific queue start/end evidence.
          </p>
        </div>
      )}

      {/* SubTab 2: Variants */}
      {activeSubTab === 'variants' && (
        <div className="tab-pane animate-fade-in">
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Variant</th>
                  <th>Execution Sequence</th>
                  <th>Complete Cases</th>
                  <th>Volume Share</th>
                </tr>
              </thead>
              <tbody>
                {analytics.variants && analytics.variants.length > 0 ? (
                  analytics.variants.map((v) => {
                    const hasRework = v.activity_sequence.some(
                      (act, idx) => v.activity_sequence.indexOf(act) !== idx
                    );
                    return (
                      <tr key={v.variant_id}>
                        <td>
                          <code>{v.variant_id}</code>
                          {v.percentage > 50 && (
                            <span className="badge badge-success text-xs ml-2">Dominant Flow</span>
                          )}
                          {hasRework && (
                            <span className="badge badge-danger text-xs ml-2">Rework Loop</span>
                          )}
                        </td>
                        <td>
                          <div className="sequence-flow">
                            {v.activity_sequence.map((act, i) => (
                              <React.Fragment key={`${act}-${i}`}>
                                <span
                                  className={`badge ${
                                    i > 0 && v.activity_sequence[i - 1] === act
                                      ? 'badge-danger font-bold'
                                      : 'badge-neutral'
                                  }`}
                                >
                                  {act}
                                </span>
                                {i < v.activity_sequence.length - 1 && (
                                  <ArrowRight size={12} className="text-muted" />
                                )}
                              </React.Fragment>
                            ))}
                          </div>
                        </td>
                        <td>
                          <strong>{v.case_count.toLocaleString()}</strong>
                          <div className="text-xs text-muted font-mono mt-1" title={v.case_ids.join(', ')}>
                            {v.case_ids.length <= 4
                              ? v.case_ids.join(', ')
                              : `${v.case_ids.slice(0, 3).join(', ')}... (+${v.case_ids.length - 3})`}
                          </div>
                        </td>
                        <td>
                          <span className={`badge ${v.percentage > 50 ? 'badge-success' : 'badge-neutral'}`}>
                            {v.percentage.toFixed(1)}%
                          </span>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td><code>VAR-001 (Dominant)</code></td>
                    <td>
                      <div className="sequence-flow">
                        {activity_frequency.map((act, i) => (
                          <React.Fragment key={act.activity}>
                            <span className="badge badge-neutral">{act.activity}</span>
                            {i < activity_frequency.length - 1 && <ArrowRight size={12} className="text-muted" />}
                          </React.Fragment>
                        ))}
                      </div>
                    </td>
                    <td><strong>{cycle_time.evaluated_cases_count}</strong></td>
                    <td>
                      <span className="badge badge-success">
                        {reconstruction_summary.variant_count === 1 ? '100.0%' : 'Standard Flow'}
                      </span>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="caption-notice">
            * Process variants are derived strictly from complete cases with error-free sequential traces. Cases exhibiting repeated activities form distinct variants rather than being collapsed.
          </p>
        </div>
      )}

      {/* SubTab 3: Activities */}
      {activeSubTab === 'activities' && (
        <div className="tab-pane animate-fade-in">
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Activity Name</th>
                  <th>Total Executions</th>
                  <th>Cases Containing Step</th>
                  <th>Case Coverage %</th>
                  <th>Repetition Ratio</th>
                </tr>
              </thead>
              <tbody>
                {filteredActivities.map((act) => (
                  <tr key={act.activity}>
                    <td><strong>{act.activity}</strong></td>
                    <td>{act.total_occurrences.toLocaleString()}</td>
                    <td>{act.case_count.toLocaleString()}</td>
                    <td>
                      <div className="progress-cell">
                        <div className="progress-bar-bg">
                          <div className="progress-bar-fill" style={{ width: `${Math.min(100, act.case_coverage_percentage)}%` }} />
                        </div>
                        <span>{act.case_coverage_percentage.toFixed(1)}%</span>
                      </div>
                    </td>
                    <td>
                      <code className={act.repetition_ratio > 1.05 ? 'text-amber font-bold' : ''}>
                        {act.repetition_ratio.toFixed(2)}x
                      </code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SubTab 4: Rework */}
      {activeSubTab === 'rework' && (
        <div className="tab-pane animate-fade-in">
          {reworkActivities.length === 0 ? (
            <div className="empty-state">
              <CheckCircle2 size={32} className="text-emerald" />
              <p>No repeated-activity loops or rework iterations observed across complete cases.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Activity with Recurrence</th>
                    <th>Cases Exhibiting Rework</th>
                    <th>Rework Case %</th>
                    <th>Total Repeated Executions</th>
                    <th>Confirmed Repeated IDs</th>
                    <th>Possible Identity Collisions</th>
                  </tr>
                </thead>
                <tbody>
                  {reworkActivities.map((r) => (
                    <tr key={r.activity}>
                      <td><span className="badge badge-warning">{r.activity}</span></td>
                      <td><strong>{r.rework_case_count}</strong> cases</td>
                      <td>
                        <span className="text-rose font-bold">
                          {r.rework_case_percentage.toFixed(1)}%
                        </span>
                      </td>
                      <td><code>+{r.rework_occurrences} loopbacks</code></td>
                      <td>{r.duplicate_events_count}</td>
                      <td>{r.potential_duplicate_events_count ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="caption-notice">
            * Rework is identified by temporal repetitions at distinct timestamps within the same case trace. Repetition measures recurrence; avoidability requires domain validation.
          </p>
        </div>
      )}
    </section>
  );
};
