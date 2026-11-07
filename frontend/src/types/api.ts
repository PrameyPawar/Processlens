/**
 * ProcessLens Canonical Frontend TypeScript Interfaces.
 * Strictly aligned with backend FastAPI / Pydantic schemas (Phases 1 - 10).
 */

// ==========================================
// Phase 1: Ingestion & Data Quality
// ==========================================

export interface DataQualityIssue {
  row_index: number;
  issue_type: 'MISSING_CASE_ID' | 'MISSING_ACTIVITY' | 'MISSING_TIMESTAMP' | 'INVALID_TIMESTAMP' | 'DUPLICATE_EVENT' | 'POTENTIAL_DUPLICATE_EVENT' | string;
  severity?: 'ERROR' | 'WARNING';
  column_name: string;
  raw_value: string | null;
  details: string;
}

export interface QualitySummary {
  missing_case_id_count: number;
  missing_activity_count: number;
  missing_timestamp_count: number;
  invalid_timestamp_count: number;
  duplicate_event_count: number;
  potential_duplicate_event_count?: number;
  malformed_row_count?: number;
}

export interface DataQualityReport {
  filename: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  summary: QualitySummary;
  issues: DataQualityIssue[];
  preview: Record<string, any>[];
}

// ==========================================
// Phase 2 & 3: Process Reconstruction & Analytics
// ==========================================

export interface DurationStats {
  mean_seconds: number;
  median_seconds: number;
  min_seconds: number;
  max_seconds: number;
  p90_seconds: number;
}

export interface ReconstructionSummary {
  total_source_rows: number;
  eligible_event_count: number;
  total_cases_found: number;
  complete_cases_count: number;
  incomplete_cases_count: number;
  variant_count: number;
}

export interface ActivityFrequency {
  activity: string;
  total_occurrences: number;
  case_count: number;
  case_coverage_percentage: number;
  repetition_ratio: number;
}

export interface ActivityRework {
  activity: string;
  rework_case_count: number;
  rework_case_percentage: number;
  rework_occurrences: number;
  duplicate_events_count: number;
  potential_duplicate_events_count?: number;
}

export interface ActivityTransition {
  source_activity: string;
  target_activity: string;
  transition_count: number;
  case_count: number;
  duration_stats: DurationStats;
}

export interface CycleTimeSummary {
  evaluated_cases_count: number;
  duration_stats: DurationStats;
}

export interface ProcessVariant {
  variant_id: string;
  activity_sequence: string[];
  case_count: number;
  case_ids: string[];
  percentage: number;
}

export interface ProcessAnalyticsResult {
  filename: string;
  reconstruction_summary: ReconstructionSummary;
  cycle_time: CycleTimeSummary;
  activity_frequency: ActivityFrequency[];
  rework: ActivityRework[];
  transitions: ActivityTransition[];
  variants?: ProcessVariant[];
}

// ==========================================
// Phase 4: Problem Detection & Operational Signals
// ==========================================

export type FindingCategory =
  | 'DURATION_CONCENTRATION'
  | 'REPETITION'
  | 'CYCLE_TIME_OUTLIER'
  | 'PATH_VARIATION'
  | 'DATA_QUALITY_LIMITATION'
  | 'BOTTLENECK';

export type SignalLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
export type EvidenceStrength = 'HIGH' | 'MODERATE' | 'LIMITED';

export interface ReconciliationStatus {
  reconciled: boolean;
  total_transition_duration_seconds: number;
  cumulative_cycle_time_seconds?: number;
  discrepancy_seconds?: number;
  discrepancy_percentage?: number;
  tolerance_percentage?: number;
  duration_share_suppressed?: boolean;
  limitation_note?: string;
  // Optional / backward compatibility fields
  total_case_cycle_time_seconds?: number;
  absolute_discrepancy_seconds?: number;
  relative_discrepancy_percentage?: number;
  evaluation_note?: string;
}

export interface DetectionSummary {
  evaluated_cases_count: number;
  total_findings_count: number;
  high_signal_count?: number;
  medium_signal_count?: number;
  low_signal_count?: number;
  info_signal_count?: number;
  high_severity_count?: number;
  medium_severity_count?: number;
  low_severity_count?: number;
  info_severity_count?: number;
  category_counts?: Record<string, number>;
  signal_level_counts?: Record<string, number>;
  reconciliation: ReconciliationStatus;
}

export interface ProblemFinding {
  id: string;
  category: FindingCategory;
  rule: string;
  rule_id?: string;
  title: string;
  signal_level: SignalLevel;
  severity?: SignalLevel;
  evidence_strength: EvidenceStrength;
  metrics: Record<string, any>;
  explanation: string;
  limitations: string[];
}

export interface ProblemDetectionResult {
  filename: string;
  summary: DetectionSummary;
  findings: ProblemFinding[];
}

// ==========================================
// Phase 5 - 8: Opportunities, Economics, Prioritisation
// ==========================================

export type OpportunityArchetype =
  | 'DELAY_COMPRESSION'
  | 'RECURRENCE_REDUCTION'
  | 'TAIL_VARIANCE_MITIGATION'
  | 'PATH_STANDARDIZATION'
  | 'DATA_INSTRUMENTATION';

export type PortfolioCohort =
  | 'FOUNDATIONAL_DATA_QUALITY'
  | 'IMMEDIATE_AUTOMATION_SPECIFICATION'
  | 'GUARDRAILED_AUTOMATION'
  | 'PROCESS_RESTRUCTURING'
  | 'BUSINESS_CASE_VALIDATION'
  | 'FEASIBILITY_INVESTIGATION'
  | 'REVISE_OR_DEFERRED'
  | 'BLOCKED_BY_BARRIERS';

export type ScoringStatus = 'SCORED' | 'UNSCORED';

export interface FactorBreakdown {
  impact_score?: number | null;
  impact_basis?: string;
  impact_provenance?: string;
  readiness_score?: number | null;
  payback_score?: number | null;
  effort_score?: number | null;
  risk_score?: number | null;
  confidence_score: number;
  effective_weights?: Record<string, number>;
  factor_caveats?: string[];
  // Optional aliases for safety
  coverage_score?: number;
  concentration_score?: number;
  evidence_score?: number;
}

export interface LaborEffortMetrics {
  sample_affected_cases?: number;
  sample_occurrences?: number | null;
  sample_addressable_labor_hours?: number | null;
  annual_affected_cases?: number | null;
  annual_occurrences?: number | null;
  annual_addressable_labor_hours?: number | null;
  annual_active_labor_hours?: number | null;
  affected_cases_provenance?: string;
  labor_metrics_provenance?: string;
  caveats?: string[];
  // backward compatibility aliases
  annual_addressable_hours?: number | null;
  sample_addressable_hours?: number | null;
  provenance?: string;
}

export interface CapacityValuationMetrics {
  hourly_labor_rate?: number | null;
  gross_annual_capacity_value?: number | null;
  net_annual_capacity_benefit?: number | null;
  implementation_cost?: number | null;
  annual_recurring_cost?: number | null;
  payback_period_months?: number | null;
  three_year_capacity_roi_percentage?: number | null;
  economic_tier?: string;
  caveats?: string[];
  assumptions?: string[];
}

export interface StrategicSynthesis {
  operational_priority?: string;
  overall_readiness?: string;
  economic_tier?: string;
  strategic_decision: string;
  decision_rationale?: string;
  recommendation_summary?: string;
  decision_caveats?: string[];
}

export interface OpportunityEconomicsResult {
  opportunity_id: string;
  archetype: OpportunityArchetype;
  observation_window: Record<string, any>;
  labor_effort: LaborEffortMetrics;
  capacity_valuation: CapacityValuationMetrics;
  cash_flow: Record<string, any>;
  synthesis: StrategicSynthesis;
}

export interface PrioritisedOpportunity {
  rank_order: number;
  opportunity_id: string;
  archetype: OpportunityArchetype;
  portfolio_cohort: PortfolioCohort;
  scoring_status: ScoringStatus;
  composite_priority_score_raw?: number | null;
  composite_priority_score?: number | null;
  score_bucket?: number | null;
  factors: FactorBreakdown;
  economics: OpportunityEconomicsResult;
  operational_priority_score: number;
  primary_strength: string;
  primary_constraint?: string | null;
  constraint_status?: string | null;
}

export interface PrioritisationSummary {
  total_opportunities_prioritised: number;
  cohort_distribution: Record<string, number>;
  top_opportunity_id?: string | null;
  top_three_opportunity_ids: string[];
  top_three_cumulative_capacity_scenario?: number | null;
  capacity_scenario_caveats: string[];
}

export interface PrioritisationResponse {
  filename: string;
  summary: PrioritisationSummary;
  ranked_opportunities: PrioritisedOpportunity[];
}

// ==========================================
// Phase 9: Evidence Architecture & Audit Dossiers
// ==========================================

export type EpistemicType = 'FACT' | 'ASSUMPTION' | 'HYPOTHESIS' | 'ESTIMATE' | 'DECISION';

export interface EpistemicItem {
  item_id: string;
  epistemic_type: EpistemicType;
  statement: string;
  source_or_basis: string;
  provenance_details?: string | null;
}

export interface EventRowAnchor {
  row_index: number;
  csv_line_number: number;
  case_id?: string | null;
  activity?: string | null;
  timestamp_raw?: string | null;
  resource?: string | null;
  role_in_evidence: string;
}

export interface CaseTraceExemplar {
  case_id: string;
  variant_id?: string | null;
  cycle_time_seconds: number;
  relevance_reason: string;
  events: EventRowAnchor[];
}

export interface MetricDerivationAudit {
  metric_name: string;
  formula_expression: string;
  input_parameters: Record<string, any>;
  calculated_value: number;
  unit: string;
  is_reproducible: boolean;
  notes?: string | null;
}

export interface OpportunityEvidenceDossier {
  opportunity_id: string;
  archetype: OpportunityArchetype;
  target_entity: string;
  portfolio_cohort: PortfolioCohort;
  rank_order: number;
  composite_priority_score?: number | null;
  supporting_finding_ids: string[];
  primary_source_rows: EventRowAnchor[];
  case_exemplars: CaseTraceExemplar[];
  exemplar_selection_policy: string;
  derivations: MetricDerivationAudit[];
  epistemic_ledger: EpistemicItem[];
  boundary_limitations: string[];
}

export interface EvidenceAuditManifest {
  source_file_sha256: string;
  source_filename: string;
  source_file_size_bytes: number;
  total_source_rows: number;
  complete_cases_count: number;
  reconciliation_status: string;
  effective_prioritisation_weights: Record<string, number>;
  formula_version: string;
  is_persisted_snapshot: boolean;
  notes: string;
}

export interface EvidenceAuditSummary {
  total_opportunities_evaluated: number;
  dossiers_emitted: number;
  filter_applied?: string | null;
  cohort_distribution: Record<string, number>;
}

export interface EvidenceAuditResponse {
  manifest: EvidenceAuditManifest;
  summary: EvidenceAuditSummary;
  dossiers: OpportunityEvidenceDossier[];
}

// ==========================================
// Phase 10: Explanation Layer
// ==========================================

export type ExplanationSource = 'DETERMINISTIC_TEMPLATE' | 'LLM_AUGMENTED';
export type GroundingVerificationStatus = 'NOT_EVALUATED' | 'VERIFIED_GROUNDED' | 'FALLBACK_APPLIED';

export interface GroundingAudit {
  status: GroundingVerificationStatus;
  verified_numbers: string[];
  verified_entities: string[];
  discrepancies: string[];
}

export interface OpportunityExplanation {
  opportunity_id: string;
  archetype: OpportunityArchetype;
  portfolio_cohort: PortfolioCohort;
  rank_order: number;
  composite_priority_score?: number | null;
  target_entity: string;
  executive_summary: string;
  operational_problem_narrative: string;
  economic_interpretation: string;
  strategic_rationale: string;
  key_assumptions_and_risks: string[];
  investigation_next_steps: string[];
  grounding_audit?: GroundingAudit | null;
}

export interface PortfolioExecutiveSummary {
  overall_narrative: string;
  top_recommended_actions: string[];
  foundational_prerequisites: string[];
  portfolio_economics_caveat: string;
}

export interface ExplanationResponse {
  manifest: EvidenceAuditManifest;
  portfolio_summary: PortfolioExecutiveSummary;
  explanations: OpportunityExplanation[];
  explanation_source: ExplanationSource;
  model_identifier?: string | null;
  execution_duration_seconds: number;
}

// ==========================================
// Dashboard Composite State
// ==========================================

export interface DashboardState {
  file: File | null;
  filename: string | null;
  isProcessing: boolean;
  currentStep: 'upload' | 'quality' | 'analytics' | 'problems' | 'prioritisation' | 'explanations';
  error: string | null;
  qualityReport: DataQualityReport | null;
  analytics: ProcessAnalyticsResult | null;
  problems: ProblemDetectionResult | null;
  prioritisation: PrioritisationResponse | null;
  explanations: ExplanationResponse | null;
  activeDossier: OpportunityEvidenceDossier | null;
  loadingDossier: boolean;
}

// ==========================================
// Authentication & Role Types
// ==========================================

export type UserRole = 'customer' | 'developer';

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
  user: UserResponse;
}

export interface DevStatusResponse {
  status: string;
  version: string;
  environment: string;
  python_version: string;
  uptime_seconds: number;
  cors_origins_configured: number;
  llm_provider_configured: boolean;
  max_file_size_mb: number;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  event_type: string;
  email_masked: string;
  client_ip: string;
  details?: string | null;
}

export interface DevAuditEventsResponse {
  events: AuditEvent[];
}
