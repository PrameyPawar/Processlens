import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App } from '../App';
import * as api from '../services/api';

import {
  DataQualityReport,
  ProcessAnalyticsResult,
  ProblemDetectionResult,
  PrioritisationResponse,
  ExplanationResponse,
  EvidenceAuditResponse,
} from '../types/api';

// ==========================================
// Fixtures based on actual backend schemas
// ==========================================

const mockQualityReportClean: DataQualityReport = {
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
  preview: [
    { case_id: 'MO-001', activity: 'Order Received', timestamp: '2026-01-01T08:00:00Z' },
  ],
};

const mockQualityReportEmptyValid: DataQualityReport = {
  filename: 'invalid_orders.csv',
  total_rows: 10,
  valid_rows: 0,
  invalid_rows: 10,
  summary: {
    missing_case_id_count: 0,
    missing_activity_count: 0,
    missing_timestamp_count: 0,
    invalid_timestamp_count: 10,
    duplicate_event_count: 0,
  },
  issues: [
    {
      row_index: 1,
      issue_type: 'INVALID_TIMESTAMP',
      column_name: 'timestamp',
      raw_value: 'bad_time',
      details: "Timestamp string 'bad_time' could not be parsed into valid datetime format",
    },
  ],
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
      mean_seconds: 139601.03,
      median_seconds: 132983.2,
      min_seconds: 76523.62,
      max_seconds: 293023.11,
      p90_seconds: 191706.21,
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
      activity: 'Production',
      total_occurrences: 750,
      case_count: 750,
      case_coverage_percentage: 100.0,
      repetition_ratio: 1.0,
    },
  ],
  rework: [
    {
      activity: 'Quality Inspection',
      rework_case_count: 0,
      rework_case_percentage: 0.0,
      rework_occurrences: 0,
      duplicate_events_count: 0,
    },
  ],
  transitions: [
    {
      source_activity: 'Production',
      target_activity: 'Quality Inspection',
      transition_count: 750,
      case_count: 750,
      duration_stats: {
        mean_seconds: 82000.0,
        median_seconds: 79000.0,
        min_seconds: 40000.0,
        max_seconds: 180000.0,
        p90_seconds: 120000.0,
      },
    },
  ],
};

const mockProblems: ProblemDetectionResult = {
  filename: 'manufacturing_orders_clean.csv',
  summary: {
    evaluated_cases_count: 750,
    total_findings_count: 2,
    high_signal_count: 1,
    medium_signal_count: 1,
    low_signal_count: 0,
    info_signal_count: 0,
    category_counts: { DURATION_CONCENTRATION: 2 },
    signal_level_counts: { HIGH: 1, MEDIUM: 1 },
    reconciliation: {
      reconciled: true,
      total_transition_duration_seconds: 104700772.5,
      cumulative_cycle_time_seconds: 104700772.5,
      discrepancy_seconds: 0.0,
      discrepancy_percentage: 0.0,
      total_case_cycle_time_seconds: 104700772.5,
      absolute_discrepancy_seconds: 0.0,
      relative_discrepancy_percentage: 0.0,
      limitation_note: 'Accounting reconciled within tolerance',
      evaluation_note: 'Accounting reconciled within tolerance',
    },
  },
  findings: [
    {
      id: 'finding_transition_production_quality_inspection',
      category: 'DURATION_CONCENTRATION',
      rule: 'RULE_DURATION_CONCENTRATION',
      rule_id: 'RULE_DURATION_CONCENTRATION',
      title: 'High Duration Concentration on Production to Quality Inspection',
      signal_level: 'HIGH',
      evidence_strength: 'HIGH',
      metrics: {
        transition_duration_share_percentage: 58.74,
        mean_transition_seconds: 82000.0,
      },
      explanation: 'Transition Production -> Quality Inspection accounts for 58.74% of cumulative operational duration.',
      limitations: [
        'Elapsed duration is derived from event intervals; queue waiting is not asserted.',
      ],
    },
  ],
};

const mockPrioritisation: PrioritisationResponse = {
  filename: 'manufacturing_orders_clean.csv',
  summary: {
    total_opportunities_prioritised: 1,
    cohort_distribution: { FEASIBILITY_INVESTIGATION: 1 },
    top_opportunity_id: 'opp_delay_production_quality_inspection',
    top_three_opportunity_ids: ['opp_delay_production_quality_inspection'],
    top_three_cumulative_capacity_scenario: null, // Unknown / Not provided
    capacity_scenario_caveats: [
      'Non-additive scenario estimate. Requires wage inputs.',
    ],
  },
  ranked_opportunities: [
    {
      rank_order: 1,
      opportunity_id: 'opp_delay_production_quality_inspection',
      archetype: 'DELAY_COMPRESSION',
      portfolio_cohort: 'FEASIBILITY_INVESTIGATION',
      scoring_status: 'SCORED',
      composite_priority_score: 61.8323,
      factors: {
        impact_score: 50.0,
        coverage_score: 50.0,
        concentration_score: 29.37,
        evidence_score: 20.0,
        readiness_score: null,
        payback_score: null,
        effort_score: null,
        risk_score: null,
        confidence_score: 0.95,
        effective_weights: {},
        factor_caveats: [],
      },
      economics: {
        opportunity_id: 'opp_delay_production_quality_inspection',
        archetype: 'DELAY_COMPRESSION',
        observation_window: {},
        labor_effort: {
          sample_addressable_hours: null, // UNKNOWN
          annual_addressable_hours: null, // UNKNOWN
          provenance: 'DEFAULT_UNKNOWN',
        },
        capacity_valuation: {
          gross_annual_capacity_value: null, // UNKNOWN
          net_annual_capacity_benefit: null, // UNKNOWN
          assumptions: [],
        },
        cash_flow: {},
        synthesis: {
          strategic_decision: 'INVESTIGATE_FEASIBILITY',
          economic_tier: 'INSUFFICIENT_ECONOMIC_INPUTS',
          recommendation_summary: 'Investigate queueing mechanisms before automating.',
          decision_caveats: [],
        },
      },
      operational_priority_score: 83.97,
      primary_strength: 'High volume coverage across 100% of complete cases',
      primary_constraint: 'Unmonetized; missing labor rate parameters',
    },
  ],
};

const mockExplanations: ExplanationResponse = {
  manifest: {
    source_file_sha256: 'bdb33bb5b3b0...',
    source_filename: 'manufacturing_orders_clean.csv',
    source_file_size_bytes: 693995,
    total_source_rows: 6000,
    complete_cases_count: 750,
    reconciliation_status: 'RECONCILED',
    effective_prioritisation_weights: {},
    formula_version: 'v1.0',
    is_persisted_snapshot: false,
    notes: 'Audit manifest verified',
  },
  portfolio_summary: {
    overall_narrative: 'Portfolio roadmap highlights Production -> Quality Inspection as the primary operational delay.',
    top_recommended_actions: ['Conduct time-study between Production and Quality Inspection.'],
    foundational_prerequisites: ['Log QA queue intake timestamps to distinguish active inspection from idle queue.'],
    portfolio_economics_caveat: 'Capacity estimates are non-additive and require wage rate inputs.',
  },
  explanations: [
    {
      opportunity_id: 'opp_delay_production_quality_inspection',
      archetype: 'DELAY_COMPRESSION',
      portfolio_cohort: 'FEASIBILITY_INVESTIGATION',
      rank_order: 1,
      composite_priority_score: 61.8323,
      target_entity: 'Production -> Quality Inspection',
      executive_summary: "Opportunity addresses Delay Compression on target 'Production -> Quality Inspection'. Ranked #1.",
      operational_problem_narrative: 'Elapsed time averages 22.8 hours per complete order.',
      economic_interpretation: 'Financial impact remains unmonetized pending hourly wage inputs.',
      strategic_rationale: 'Assigned to Feasibility Investigation due to lack of queue queue distinction.',
      key_assumptions_and_risks: ['Waiting time cannot be asserted without queue events.'],
      investigation_next_steps: ['Interview QA lead regarding batch release policies.'],
      grounding_audit: {
        status: 'NOT_EVALUATED',
        verified_numbers: [],
        verified_entities: [],
        discrepancies: [],
      },
    },
  ],
  explanation_source: 'DETERMINISTIC_TEMPLATE',
  model_identifier: null,
  execution_duration_seconds: 0.042,
};

const mockEvidenceAudit: EvidenceAuditResponse = {
  manifest: mockExplanations.manifest,
  summary: {
    total_opportunities_evaluated: 1,
    dossiers_emitted: 1,
    cohort_distribution: { FEASIBILITY_INVESTIGATION: 1 },
  },
  dossiers: [
    {
      opportunity_id: 'opp_delay_production_quality_inspection',
      archetype: 'DELAY_COMPRESSION',
      target_entity: 'Production -> Quality Inspection',
      portfolio_cohort: 'FEASIBILITY_INVESTIGATION',
      rank_order: 1,
      composite_priority_score: 61.8323,
      supporting_finding_ids: ['finding_transition_production_quality_inspection'],
      primary_source_rows: [
        {
          row_index: 5,
          csv_line_number: 6,
          case_id: 'MO-001',
          activity: 'Production',
          timestamp_raw: '2026-01-01T14:00:00Z',
          resource: 'Operator A',
          role_in_evidence: 'TRANSITION_SOURCE',
        },
      ],
      case_exemplars: [
        {
          case_id: 'MO-001',
          variant_id: 'VAR-001',
          cycle_time_seconds: 132000.0,
          relevance_reason: 'Exemplar demonstrating typical transition delay',
          events: [],
        },
      ],
      exemplar_selection_policy: 'MEDIAN_CYCLE_TIME',
      derivations: [
        {
          metric_name: 'transition_duration_share_percentage',
          formula_expression: 'cumulative_transition_duration / cumulative_cycle_time * 100',
          input_parameters: { duration: 61500000, total: 104700772 },
          calculated_value: 58.74,
          unit: '%',
          is_reproducible: true,
        },
      ],
      epistemic_ledger: [
        {
          item_id: 'ep_1',
          epistemic_type: 'FACT',
          statement: 'Transition Production -> Quality Inspection observed in 750 cases',
          source_or_basis: 'Observed event logs',
        },
        {
          item_id: 'ep_2',
          epistemic_type: 'ASSUMPTION',
          statement: 'Labor cost assumed unmonetized without user input',
          source_or_basis: 'Default policy',
        },
      ],
      boundary_limitations: ['Queue time is not asserted as fact.'],
    },
  ],
};

// ==========================================
// Tests
// ==========================================

describe('ProcessLens Dashboard Critical Acceptance Criteria', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default health mock
    vi.spyOn(api, 'checkBackendHealth').mockResolvedValue({
      status: 'ok',
      service: 'processlens-backend',
      version: '0.1.0',
    });
  });

  it('1. Uploads CSV and successfully renders Data Quality report', async () => {
    vi.spyOn(api, 'uploadAndValidateCsv').mockResolvedValue(mockQualityReportClean);
    vi.spyOn(api, 'fetchProcessAnalytics').mockResolvedValue(mockAnalytics);
    vi.spyOn(api, 'fetchProblemDetection').mockResolvedValue(mockProblems);
    vi.spyOn(api, 'fetchPrioritisation').mockResolvedValue(mockPrioritisation);
    vi.spyOn(api, 'fetchExplanations').mockResolvedValue(mockExplanations);

    render(<App />);

    const file = new File(['case_id,activity,timestamp\n1,A,2026-01-01'], 'clean.csv', { type: 'text/csv' });
    const dropzone = screen.getByRole('button', { name: /upload csv event log/i });

    // Trigger drop
    fireEvent.drop(dropzone, {
      dataTransfer: { files: [file] },
    });

    await waitFor(() => {
      expect(screen.getByText(/Phase 1: Ingestion & Data Quality Report/i)).toBeInTheDocument();
      expect(screen.getAllByText('6,000')[0]).toBeInTheDocument();
      expect(screen.getByText(/100% Schema Valid/i)).toBeInTheDocument();
    });
  });

  it('2. Successfully renders Process Overview metrics and variants', async () => {
    vi.spyOn(api, 'uploadAndValidateCsv').mockResolvedValue(mockQualityReportClean);
    vi.spyOn(api, 'fetchProcessAnalytics').mockResolvedValue(mockAnalytics);
    vi.spyOn(api, 'fetchProblemDetection').mockResolvedValue(mockProblems);
    vi.spyOn(api, 'fetchPrioritisation').mockResolvedValue(mockPrioritisation);
    vi.spyOn(api, 'fetchExplanations').mockResolvedValue(mockExplanations);

    render(<App />);
    const file = new File(['mock'], 'clean.csv', { type: 'text/csv' });
    fireEvent.drop(screen.getByRole('button', { name: /upload csv event log/i }), {
      dataTransfer: { files: [file] },
    });

    // Wait for pipeline and click Process Overview step
    await waitFor(() => screen.getByRole('button', { name: /2\. Process Overview/i }));
    fireEvent.click(screen.getByRole('button', { name: /2\. Process Overview/i }));

    expect(screen.getByText(/Phase 2 & 3: Process Reconstruction & Analytics/i)).toBeInTheDocument();
    expect(screen.getByText(/750 complete cases/i)).toBeInTheDocument();
    expect(screen.getByText('38.8h (139601s)')).toBeInTheDocument(); // Formatted duration
  });

  it('3. Renders Problem findings using actual API fields without inventing diagnosis', async () => {
    vi.spyOn(api, 'uploadAndValidateCsv').mockResolvedValue(mockQualityReportClean);
    vi.spyOn(api, 'fetchProcessAnalytics').mockResolvedValue(mockAnalytics);
    vi.spyOn(api, 'fetchProblemDetection').mockResolvedValue(mockProblems);
    vi.spyOn(api, 'fetchPrioritisation').mockResolvedValue(mockPrioritisation);
    vi.spyOn(api, 'fetchExplanations').mockResolvedValue(mockExplanations);

    render(<App />);
    const file = new File(['mock'], 'clean.csv', { type: 'text/csv' });
    fireEvent.drop(screen.getByRole('button', { name: /upload csv event log/i }), {
      dataTransfer: { files: [file] },
    });

    await waitFor(() => screen.getByRole('button', { name: /3\. Problems & Signals/i }));
    fireEvent.click(screen.getByRole('button', { name: /3\. Problems & Signals/i }));

    expect(screen.getByText(/High Duration Concentration on Production to Quality Inspection/i)).toBeInTheDocument();
    expect(screen.getByText(/Signal: HIGH/i)).toBeInTheDocument();
    expect(screen.getByText(/Evidence: HIGH/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Accounting Reconciled/i)[0]).toBeInTheDocument();
  });

  it('4. Missing economic values are NOT rendered as zero', async () => {
    vi.spyOn(api, 'uploadAndValidateCsv').mockResolvedValue(mockQualityReportClean);
    vi.spyOn(api, 'fetchProcessAnalytics').mockResolvedValue(mockAnalytics);
    vi.spyOn(api, 'fetchProblemDetection').mockResolvedValue(mockProblems);
    vi.spyOn(api, 'fetchPrioritisation').mockResolvedValue(mockPrioritisation);
    vi.spyOn(api, 'fetchExplanations').mockResolvedValue(mockExplanations);

    render(<App />);
    const file = new File(['mock'], 'clean.csv', { type: 'text/csv' });
    fireEvent.drop(screen.getByRole('button', { name: /upload csv event log/i }), {
      dataTransfer: { files: [file] },
    });

    await waitFor(() => screen.getByRole('button', { name: /4\. Opportunities & Roadmap/i }));
    fireEvent.click(screen.getByRole('button', { name: /4\. Opportunities & Roadmap/i }));

    // Verify missing economic values show Unknown, NOT $0 or 0 hrs
    expect(screen.getByText(/Unknown \(Missing Hourly Wage Input\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Unmonetized \(Requires Financial Parameters\)/i)).toBeInTheDocument();
    expect(screen.queryByText('$0')).not.toBeInTheDocument();
  });

  it('5. Failed downstream request does not silently produce fabricated results', async () => {
    vi.spyOn(api, 'uploadAndValidateCsv').mockResolvedValue(mockQualityReportClean);
    // Downstream analytics throws error
    vi.spyOn(api, 'fetchProcessAnalytics').mockRejectedValue(new Error('Downstream analytics computation failure'));

    render(<App />);
    const file = new File(['mock'], 'clean.csv', { type: 'text/csv' });
    fireEvent.drop(screen.getByRole('button', { name: /upload csv event log/i }), {
      dataTransfer: { files: [file] },
    });

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/Downstream analytics computation failure/i)).toBeInTheDocument();
    });

    // Downstream tabs should not be completed
    const oppsBtn = screen.getByRole('button', { name: /4\. Opportunities & Roadmap/i });
    expect(oppsBtn).toBeDisabled();
  });

  it('does not restore a pending evidence dossier into a later session after logout', async () => {
    let resolveAudit!: (audit: EvidenceAuditResponse) => void;
    const pendingAudit = new Promise<EvidenceAuditResponse>((resolve) => {
      resolveAudit = resolve;
    });
    vi.spyOn(api, 'uploadAndValidateCsv').mockResolvedValue(mockQualityReportClean);
    vi.spyOn(api, 'fetchProcessAnalytics').mockResolvedValue(mockAnalytics);
    vi.spyOn(api, 'fetchProblemDetection').mockResolvedValue(mockProblems);
    vi.spyOn(api, 'fetchPrioritisation').mockResolvedValue(mockPrioritisation);
    vi.spyOn(api, 'fetchExplanations').mockResolvedValue(mockExplanations);
    vi.spyOn(api, 'fetchEvidenceAudit').mockReturnValue(pendingAudit);
    vi.spyOn(api, 'logoutApi').mockResolvedValue({ message: 'Logged out successfully.' });
    vi.spyOn(api, 'loginApi').mockResolvedValue({
      access_token: 'new-session-token',
      token_type: 'bearer',
      expires_in_seconds: 28800,
      user: {
        id: 'usr_new_customer',
        email: 'new.customer@example.com',
        name: 'New Customer',
        role: 'customer',
        created_at: '2026-10-01T00:00:00Z',
      },
    });

    render(<App />);
    const file = new File(['case_id,activity,timestamp\n1,A,2026-01-01'], 'stale-customer-data.csv', { type: 'text/csv' });
    fireEvent.drop(screen.getByRole('button', { name: /upload csv event log/i }), {
      dataTransfer: { files: [file] },
    });
    await waitFor(() => screen.getByRole('button', { name: /4\. Opportunities & Roadmap/i }));
    fireEvent.click(screen.getByRole('button', { name: /4\. Opportunities & Roadmap/i }));
    fireEvent.click(screen.getByText(/Inspect Evidence Dossier & Row Anchors/i));
    await waitFor(() => expect(api.fetchEvidenceAudit).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: /sign out/i }));
    await waitFor(() => expect(screen.getByRole('button', { name: /Customer Sign In/i })).toBeInTheDocument());
    resolveAudit(mockEvidenceAudit);

    fireEvent.change(screen.getByLabelText(/Work Email/i), { target: { value: 'new.customer@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'A-long-test-password' } });
    fireEvent.click(screen.getByRole('button', { name: /Sign In to Workspace/i }));

    await waitFor(() => expect(screen.getByRole('button', { name: /upload csv event log/i })).toBeInTheDocument());
    expect(screen.queryByText(/Phase 9 Evidence Audit Dossier/i)).not.toBeInTheDocument();
  });

  it('shows the access-denied screen instead of the developer dashboard to a customer', () => {
    window.history.replaceState({}, '', '/dev/dashboard');
    render(<App />);
    expect(screen.getByText(/Developer Privileges Required/i)).toBeInTheDocument();
    expect(screen.queryByText(/ProcessLens DevConsole/i)).not.toBeInTheDocument();
    window.history.replaceState({}, '', '/');
  });

  it('6. Replacing a file refreshes the dashboard correctly', async () => {
    vi.spyOn(api, 'uploadAndValidateCsv').mockResolvedValue(mockQualityReportClean);
    vi.spyOn(api, 'fetchProcessAnalytics').mockResolvedValue(mockAnalytics);
    vi.spyOn(api, 'fetchProblemDetection').mockResolvedValue(mockProblems);
    vi.spyOn(api, 'fetchPrioritisation').mockResolvedValue(mockPrioritisation);
    vi.spyOn(api, 'fetchExplanations').mockResolvedValue(mockExplanations);

    render(<App />);
    const file1 = new File(['mock1'], 'clean.csv', { type: 'text/csv' });
    fireEvent.drop(screen.getByRole('button', { name: /upload csv event log/i }), {
      dataTransfer: { files: [file1] },
    });

    await waitFor(() => screen.getByText(/Upload Another Dataset/i));

    // Click Reset
    fireEvent.click(screen.getByText(/Upload Another Dataset/i));

    // Dashboard should return to initial dropzone state
    expect(screen.getByText(/SME Process Intelligence & Automation Decision Support/i)).toBeInTheDocument();
    expect(screen.queryByText(/Phase 1: Ingestion & Data Quality Report/i)).not.toBeInTheDocument();
  });

  it('7. Empty or entirely invalid dataset stops pipeline safely without crashing UI', async () => {
    vi.spyOn(api, 'uploadAndValidateCsv').mockResolvedValue(mockQualityReportEmptyValid);

    render(<App />);
    const file = new File(['bad'], 'invalid_orders.csv', { type: 'text/csv' });
    fireEvent.drop(screen.getByRole('button', { name: /upload csv event log/i }), {
      dataTransfer: { files: [file] },
    });

    await waitFor(() => {
      expect(screen.getByText(/No valid rows found in CSV file/i)).toBeInTheDocument();
      expect(screen.getByText(/10 Invalid Records Detected/i)).toBeInTheDocument();
    });

    // Stepper should not allow moving to analytics
    const analyticsBtn = screen.getByRole('button', { name: /2\. Process Overview/i });
    expect(analyticsBtn).toBeDisabled();
  });

  it('8. Renders Explanation grounding fallback status truthfully', async () => {
    const fallbackExplanation: ExplanationResponse = {
      ...mockExplanations,
      explanations: [
        {
          ...mockExplanations.explanations[0],
          grounding_audit: {
            status: 'FALLBACK_APPLIED',
            verified_numbers: [],
            verified_entities: [],
            discrepancies: ['Provider unconfigured. Deterministic fallback applied.'],
          },
        },
      ],
    };

    vi.spyOn(api, 'uploadAndValidateCsv').mockResolvedValue(mockQualityReportClean);
    vi.spyOn(api, 'fetchProcessAnalytics').mockResolvedValue(mockAnalytics);
    vi.spyOn(api, 'fetchProblemDetection').mockResolvedValue(mockProblems);
    vi.spyOn(api, 'fetchPrioritisation').mockResolvedValue(mockPrioritisation);
    vi.spyOn(api, 'fetchExplanations').mockResolvedValue(fallbackExplanation);

    render(<App />);
    const file = new File(['mock'], 'clean.csv', { type: 'text/csv' });
    fireEvent.drop(screen.getByRole('button', { name: /upload csv event log/i }), {
      dataTransfer: { files: [file] },
    });

    await waitFor(() => screen.getByRole('button', { name: /5\. Grounded Explanations/i }));
    fireEvent.click(screen.getByRole('button', { name: /5\. Grounded Explanations/i }));

    expect(screen.getByText(/Fallback Applied \(Protected\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Provider unconfigured\. Deterministic fallback applied\./i)).toBeInTheDocument();
  });

  it('9. Opens Evidence Dossier Modal on demand and displays exact row anchors & epistemic ledger', async () => {
    vi.spyOn(api, 'uploadAndValidateCsv').mockResolvedValue(mockQualityReportClean);
    vi.spyOn(api, 'fetchProcessAnalytics').mockResolvedValue(mockAnalytics);
    vi.spyOn(api, 'fetchProblemDetection').mockResolvedValue(mockProblems);
    vi.spyOn(api, 'fetchPrioritisation').mockResolvedValue(mockPrioritisation);
    vi.spyOn(api, 'fetchExplanations').mockResolvedValue(mockExplanations);
    vi.spyOn(api, 'fetchEvidenceAudit').mockResolvedValue(mockEvidenceAudit);

    render(<App />);
    const file = new File(['mock'], 'clean.csv', { type: 'text/csv' });
    fireEvent.drop(screen.getByRole('button', { name: /upload csv event log/i }), {
      dataTransfer: { files: [file] },
    });

    await waitFor(() => screen.getByRole('button', { name: /4\. Opportunities & Roadmap/i }));
    fireEvent.click(screen.getByRole('button', { name: /4\. Opportunities & Roadmap/i }));

    const inspectBtn = screen.getByText(/Inspect Evidence Dossier & Row Anchors/i);
    fireEvent.click(inspectBtn);

    await waitFor(() => {
      expect(screen.getByText(/Phase 9 Evidence Audit Dossier/i)).toBeInTheDocument();
      expect(screen.getByText(/Line #6/i)).toBeInTheDocument();
      expect(screen.getByText(/TRANSITION_SOURCE/i)).toBeInTheDocument();
    });

    // Switch to Epistemic Ledger tab
    fireEvent.click(screen.getByRole('button', { name: /Epistemic Ledger/i }));
    expect(screen.getByText('FACT')).toBeInTheDocument();
    expect(screen.getByText('ASSUMPTION')).toBeInTheDocument();
  });
});
