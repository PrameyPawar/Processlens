import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CycleTimePercentileChart } from '../components/charts/CycleTimePercentileChart';
import { ActivityFrequencyChart } from '../components/charts/ActivityFrequencyChart';
import { TransitionDurationChart } from '../components/charts/TransitionDurationChart';
import { DataQualityChart } from '../components/charts/DataQualityChart';
import { OpportunityDimensionsChart } from '../components/charts/OpportunityDimensionsChart';
import { OverviewDashboard } from '../components/OverviewDashboard';
import { ReportsView, encodeCsvCell } from '../components/ReportsView';
import { OpportunitiesView } from '../components/OpportunitiesView';
import {
  DataQualityReport,
  ProcessAnalyticsResult,
  ProblemDetectionResult,
  PrioritisationResponse,
} from '../types/api';

const mockQualityReport: DataQualityReport = {
  filename: 'manufacturing_orders_clean.csv',
  total_rows: 6000,
  valid_rows: 6000,
  invalid_rows: 0,
  summary: {
    missing_case_id_count: 0,
    missing_activity_count: 0,
    missing_timestamp_count: 0,
    invalid_timestamp_count: 0,
    duplicate_event_count: 0,
  },
  issues: [],
  preview: [],
};

const mockAnalytics: ProcessAnalyticsResult = {
  filename: 'manufacturing_orders_clean.csv',
  reconstruction_summary: {
    total_source_rows: 6000,
    eligible_event_count: 6000,
    total_cases_found: 750,
    complete_cases_count: 750,
    incomplete_cases_count: 0,
    variant_count: 1,
  },
  cycle_time: {
    evaluated_cases_count: 750,
    duration_stats: {
      mean_seconds: 139601.0,
      median_seconds: 132983.0,
      min_seconds: 76523.0,
      max_seconds: 293023.0,
      p90_seconds: 191706.0,
    },
  },
  activity_frequency: [
    {
      activity: 'Order Received',
      total_occurrences: 750,
      case_count: 750,
      case_coverage_percentage: 100.0,
      repetition_ratio: 1.0,
    },
    {
      activity: 'Production Assembly',
      total_occurrences: 850,
      case_count: 750,
      case_coverage_percentage: 100.0,
      repetition_ratio: 1.13,
    },
  ],
  rework: [
    {
      activity: 'Production Assembly',
      rework_case_count: 80,
      rework_case_percentage: 10.7,
      rework_occurrences: 100,
      duplicate_events_count: 0,
    },
  ],
  transitions: [
    {
      source_activity: 'Material Allocation',
      target_activity: 'Production Assembly',
      transition_count: 750,
      case_count: 750,
      duration_stats: {
        mean_seconds: 72000.0,
        median_seconds: 68400.0,
        min_seconds: 36000.0,
        max_seconds: 150000.0,
        p90_seconds: 110000.0,
      },
    },
  ],
};

const mockProblems: ProblemDetectionResult = {
  filename: 'manufacturing_orders_clean.csv',
  summary: {
    evaluated_cases_count: 750,
    total_findings_count: 1,
    high_signal_count: 1,
    medium_signal_count: 0,
    low_signal_count: 0,
    info_signal_count: 0,
    reconciliation: {
      reconciled: true,
      total_transition_duration_seconds: 139601.0,
      cumulative_cycle_time_seconds: 139601.0,
      discrepancy_seconds: 0.0,
      discrepancy_percentage: 0.0,
    },
  },
  findings: [
    {
      id: 'FIND-001',
      category: 'DURATION_CONCENTRATION',
      rule: 'transition_bottleneck',
      title: 'High Duration Concentration on Material Allocation to Production Assembly',
      signal_level: 'HIGH',
      severity: 'HIGH',
      evidence_strength: 'HIGH',
      metrics: { share: 0.49 },
      explanation: '49% of total cycle time concentrated in this handoff',
      limitations: ['Handoff includes queue wait time'],
    },
  ],
};

const mockPrioritisation: PrioritisationResponse = {
  filename: 'manufacturing_orders_clean.csv',
  summary: {
    total_opportunities_prioritised: 1,
    cohort_distribution: { IMMEDIATE_AUTOMATION_SPECIFICATION: 1 },
    top_opportunity_id: 'opp_delay_material_allocation_production_assembly',
    top_three_opportunity_ids: ['opp_delay_material_allocation_production_assembly'],
    top_three_cumulative_capacity_scenario: null,
    capacity_scenario_caveats: ['Non-additive scenario; requires wage inputs'],
  },
  ranked_opportunities: [
    {
      rank_order: 1,
      opportunity_id: 'opp_delay_material_allocation_production_assembly',
      archetype: 'DELAY_COMPRESSION',
      portfolio_cohort: 'IMMEDIATE_AUTOMATION_SPECIFICATION',
      scoring_status: 'SCORED',
      composite_priority_score: 84.5,
      operational_priority_score: 84.5,
      factors: {
        impact_score: 85.0,
        readiness_score: 90.0,
        payback_score: null,
        effort_score: 3.0,
        risk_score: 2.0,
        confidence_score: 0.95,
      },
      economics: {
        opportunity_id: 'opp_delay_material_allocation_production_assembly',
        archetype: 'DELAY_COMPRESSION',
        observation_window: { sample_orders: 750 },
        labor_effort: {
          sample_addressable_labor_hours: 420.5,
          annual_addressable_labor_hours: 1682.0,
        },
        capacity_valuation: {
          hourly_labor_rate: null,
          gross_annual_capacity_value: null,
        },
        cash_flow: {},
        synthesis: {
          strategic_decision: 'SPECIFY_AUTOMATION_SOLUTION',
          decision_rationale: 'High operational priority and stable schema',
        },
      },
      primary_strength: 'Strong evidence of delay concentration',
      primary_constraint: null,
    },
  ],
};

describe('ProcessLens Visual Analytics & Workspaces', () => {
  it('renders CycleTimePercentileChart with distribution and percentiles', () => {
    render(
      <CycleTimePercentileChart
        stats={mockAnalytics.cycle_time.duration_stats}
        totalCases={750}
      />
    );

    expect(screen.getByText(/Case Cycle-Time Distribution & Percentiles/i)).toBeInTheDocument();
    expect(screen.getByText(/MEDIAN \(50th\)/i)).toBeInTheDocument();
    expect(screen.getAllByText(/P90/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/Epistemic Note:/i)).toBeInTheDocument();
  });

  it('renders ActivityFrequencyChart with volume and repetition ratio', () => {
    render(
      <ActivityFrequencyChart
        activities={mockAnalytics.activity_frequency}
        totalCases={750}
      />
    );

    expect(screen.getByText(/Activity Volume & Process Coverage/i)).toBeInTheDocument();
    expect(screen.getByText('Order Received')).toBeInTheDocument();
    expect(screen.getByText('Production Assembly')).toBeInTheDocument();
    expect(screen.getByText(/1\.13x loopback/i)).toBeInTheDocument();
  });

  it('renders TransitionDurationChart with bottleneck highlights', () => {
    render(<TransitionDurationChart transitions={mockAnalytics.transitions} />);

    expect(screen.getByText(/Process Step Handoffs & Bottlenecks/i)).toBeInTheDocument();
    expect(screen.getByText('Material Allocation')).toBeInTheDocument();
    expect(screen.getByText('Primary Bottleneck')).toBeInTheDocument();
  });

  it('renders DataQualityChart with stacked integrity breakdown', () => {
    render(<DataQualityChart report={mockQualityReport} />);

    expect(screen.getByText(/Telemetry Health & Ingestion Completeness/i)).toBeInTheDocument();
    expect(screen.getByText(/100% Ingestion Integrity/i)).toBeInTheDocument();
  });

  it('renders OpportunityDimensionsChart and separates readiness, impact, and confidence', () => {
    render(
      <OpportunityDimensionsChart
        opportunities={mockPrioritisation.ranked_opportunities}
      />
    );

    expect(screen.getByText(/Multi-Factor Opportunity Evaluation/i)).toBeInTheDocument();
    expect(screen.getAllByText(/85\/100/i)[0]).toBeInTheDocument(); // Impact
    expect(screen.getByText(/90\/100/i)).toBeInTheDocument(); // Readiness
    expect(screen.getByText(/95%/i)).toBeInTheDocument(); // Confidence
    expect(screen.getByText(/Epistemic Discipline:/i)).toBeInTheDocument();
  });

  it('correctly formats real backend 0-100 confidence score as 75% instead of 7500%', () => {
    const oppWithBackendScore = [
      {
        ...mockPrioritisation.ranked_opportunities[0],
        factors: {
          ...mockPrioritisation.ranked_opportunities[0].factors,
          confidence_score: 75.0,
        },
      },
    ];
    render(<OpportunityDimensionsChart opportunities={oppWithBackendScore} />);
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.queryByText(/7500%/)).not.toBeInTheDocument();
  });


  it('renders OverviewDashboard with KPI ribbon, spotlight, and epistemic framework', () => {
    const onNavigate = vi.fn();
    const onSelectDossier = vi.fn();

    render(
      <OverviewDashboard
        qualityReport={mockQualityReport}
        analytics={mockAnalytics}
        problems={mockProblems}
        prioritisation={mockPrioritisation}
        explanations={null}
        onNavigateToStep={onNavigate}
        onSelectDossier={onSelectDossier}
      />
    );

    expect(screen.getByText(/Operations Intelligence Overview/i)).toBeInTheDocument();
    expect(screen.getByText(/WHAT SHOULD THIS BUSINESS FIX OR AUTOMATE FIRST\?/i)).toBeInTheDocument();
    expect(screen.getByText('FACT')).toBeInTheDocument();
    expect(screen.getByText('ESTIMATE')).toBeInTheDocument();
    expect(screen.getByText('UNKNOWN')).toBeInTheDocument();

    // Spotlight buttons trigger callbacks
    fireEvent.click(screen.getByRole('button', { name: /Inspect Opportunity Details/i }));
    expect(onNavigate).toHaveBeenCalledWith('opportunities');
  });

  it('renders ReportsView and supports printing and CSV downloads', () => {
    // Mock window.print
    const printSpy = vi.spyOn(window, 'print').mockImplementation(() => {});

    render(
      <ReportsView
        qualityReport={mockQualityReport}
        analytics={mockAnalytics}
        problems={mockProblems}
        prioritisation={mockPrioritisation}
        explanations={null}
      />
    );

    expect(screen.getByText(/Reports & Data Export/i)).toBeInTheDocument();
    expect(screen.getByText(/OPERATIONS INTELLIGENCE BRIEFING/i)).toBeInTheDocument();

    // Trigger Print
    fireEvent.click(screen.getByRole('button', { name: /Print \/ Save as PDF/i }));
    expect(printSpy).toHaveBeenCalled();

    // Trigger Opportunities CSV Export
    const exportOppBtn = screen.getByRole('button', { name: /Export Opportunities \(CSV\)/i });
    expect(exportOppBtn).toBeInTheDocument();
  });

  it('neutralizes spreadsheet formula cells and quotes CSV delimiters', () => {
    expect(encodeCsvCell('=HYPERLINK("https://bad.example")')).toBe('"\'=HYPERLINK(""https://bad.example"")"');
    expect(encodeCsvCell('activity, with "quotes"')).toBe('"activity, with ""quotes"""');
    expect(encodeCsvCell(-12.5)).toBe('"-12.5"');
  });

  it('allows filtering and sorting opportunities in OpportunitiesView', () => {
    const onSelectDossier = vi.fn();

    render(
      <OpportunitiesView
        prioritisation={mockPrioritisation}
        onSelectDossier={onSelectDossier}
      />
    );

    expect(screen.getByPlaceholderText(/Search opportunities\.\.\./i)).toBeInTheDocument();
    expect(screen.getByText(/Hide Comparison Chart/i)).toBeInTheDocument();

    // Toggle chart visibility
    fireEvent.click(screen.getByText(/Hide Comparison Chart/i));
    expect(screen.getByText(/Show Comparison Chart/i)).toBeInTheDocument();
  });
});
