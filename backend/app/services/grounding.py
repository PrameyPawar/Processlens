"""
Independent, deterministic grounding verification and anti-hallucination guardrails for ProcessLens Phase 10.
Verifies proposed opportunity explanations against underlying Phase 9 evidence dossiers.
Detects unsupported numerical claims with metric-to-context compatibility, fabricated entities,
unverified causal assertions, and violations of economic/epistemic boundaries.
"""

import re
import math
from typing import List, Set, Dict, Any, Tuple, Optional

from app.schemas.evidence import (
    EpistemicType,
    OpportunityEvidenceDossier,
    MetricDerivationAudit,
)
from app.schemas.explanation import (
    GroundingVerificationStatus,
    GroundingAudit,
    OpportunityExplanation,
)


# Banned causal assertions that exceed operational log correlation
UNSUPPORTED_CAUSAL_PATTERNS = [
    r"\bdefinitively\s+causes\b",
    r"\bconclusively\s+proves\b",
    r"\bguarantees\s+that\b",
    r"\bguarantees\s+an?\b",
    r"\bguaranteed\s+outcome\b",
    r"\bproves\s+causation\b",
    r"\bdirect\s+cause\s+of\b",
    r"\bcausally\s+leads\s+to\b",
    r"\bproves\s+that\b",
]

# Banned economic claims violating capacity reallocation rules
BANNED_SAVINGS_PATTERNS = [
    r"\bguaranteed\s+savings\b",
    r"\bguaranteed\s+cash\b",
    r"\bguaranteed\s+roi\b",
    r"\brealized\s+cash\s+savings\b",
    r"\bcash-flow\s+savings\b",
    r"\bbudget\s+reduction\b",
    r"\bpayroll\s+reduction\b",
]

# Preceding negation words indicating a compliant disclaimer
DISCLAIMER_NEGATION_WORDS = ["not", "never", "no", "does not", "cannot", "do not", "neither", "nor", "without"]


class DossierMetricPool:
    """
    Categorized collection of all valid numerical values from a dossier,
    partitioned by semantic metric type to prevent false-positive cross-validation.
    """
    def __init__(self, dossier: OpportunityEvidenceDossier):
        self.currencies: Set[float] = set()
        self.percentages: Set[float] = set()
        self.durations_seconds: Set[float] = set()
        self.months: Set[float] = set()
        self.labor_hours: Set[float] = set()
        self.repetition_counts: Set[float] = set()
        self.ranks: Set[float] = {float(dossier.rank_order)}
        self.scores: Set[float] = set()
        self.rows_and_lines: Set[float] = set()
        self.case_counts: Set[float] = {float(len(dossier.exemplars))}

        if dossier.composite_priority_score is not None:
            self._add_with_roundings(self.scores, float(dossier.composite_priority_score))

        # Exemplars
        for ex in dossier.exemplars:
            self._add_with_roundings(self.durations_seconds, float(ex.exemplar_metric_value))
            if ex.total_case_duration_seconds is not None:
                self._add_with_roundings(self.durations_seconds, float(ex.total_case_duration_seconds))
            self._add_with_roundings(self.repetition_counts, float(ex.exemplar_metric_value))
            for anchor in ex.event_anchors:
                self.rows_and_lines.add(float(anchor.row_index))
                self.rows_and_lines.add(float(anchor.csv_line_number))

        # Derivations
        for drv in dossier.derivations:
            mid = drv.metric_id
            out = drv.output_value
            inp = drv.input_variables
            inter = drv.intermediate_values

            if mid == "OPS_SCORE_V1":
                if isinstance(out, (int, float)):
                    self._add_with_roundings(self.scores, float(out))
                for k in ["coverage_score", "concentration_score", "raw_score_sum"]:
                    val = inp.get(k, inter.get(k))
                    if isinstance(val, (int, float)):
                        self._add_with_roundings(self.scores, float(val))

            elif mid == "ANNUALIZATION_V1":
                for k in ["observation_duration_days", "sample_completed_cases", "evaluated_case_volume"]:
                    val = inp.get(k)
                    if isinstance(val, (int, float)):
                        self.case_counts.add(float(val))
                if isinstance(out, (int, float)):
                    self._add_with_roundings(self.percentages, float(out))

            elif mid == "LABOR_EFFORT_V1":
                if isinstance(out, (int, float)):
                    self._add_with_roundings(self.labor_hours, float(out))
                for k in ["sample_active_labor_hours", "annual_active_labor_hours"]:
                    val = inp.get(k, inter.get(k))
                    if isinstance(val, (int, float)):
                        self._add_with_roundings(self.labor_hours, float(val))
                if "cumulative_transition_duration_seconds" in inp and isinstance(inp["cumulative_transition_duration_seconds"], (int, float)):
                    self._add_with_roundings(self.durations_seconds, float(inp["cumulative_transition_duration_seconds"]))
                if "active_labor_share_percentage" in inp and isinstance(inp["active_labor_share_percentage"], (int, float)):
                    self._add_with_roundings(self.percentages, float(inp["active_labor_share_percentage"]))

            elif mid == "CAPACITY_VAL_V1":
                for k in ["gross_annual_capacity_value", "annual_recurring_cost", "hourly_labor_rate"]:
                    val = inp.get(k)
                    if isinstance(val, (int, float)):
                        self._add_with_roundings(self.currencies, float(val))
                for k in ["gross_capacity_valuation", "net_annual_capacity_benefit"]:
                    val = inter.get(k, out if k == "net_annual_capacity_benefit" else None)
                    if isinstance(val, (int, float)):
                        self._add_with_roundings(self.currencies, float(val))

            elif mid == "PAYBACK_PERIOD_V1":
                if isinstance(out, (int, float)):
                    self._add_with_roundings(self.months, float(out))
                if "implementation_cost" in inp and isinstance(inp["implementation_cost"], (int, float)):
                    self._add_with_roundings(self.currencies, float(inp["implementation_cost"]))

            elif mid == "COMPOSITE_SCORE_V1":
                if isinstance(out, (int, float)):
                    self._add_with_roundings(self.scores, float(out))
                for v in inp.values():
                    if isinstance(v, (int, float)):
                        self._add_with_roundings(self.scores, float(v))

        # Epistemic ledger numbers
        for item in dossier.epistemic_ledger:
            for val, raw in _extract_raw_currency(item.statement):
                self._add_with_roundings(self.currencies, val)
            for val, raw in _extract_raw_score(item.statement):
                self._add_with_roundings(self.scores, val)

        # Standard system percentages
        self.percentages.add(2.0)   # Rare variant (<2%)
        self.percentages.add(100.0) # Base weight scale

    def _add_with_roundings(self, target_set: Set[float], val: float):
        target_set.add(val)
        target_set.add(round(val))
        target_set.add(round(val, 1))
        target_set.add(round(val, 2))
        target_set.add(round(val, 4))


def _extract_raw_currency(text: str) -> List[Tuple[float, str]]:
    found = []
    for m in re.finditer(r"\$([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)", text):
        raw = m.group(0)
        num_str = m.group(1).replace(",", "")
        try:
            found.append((float(num_str), raw))
        except ValueError:
            pass
    return found


def _extract_raw_score(text: str) -> List[Tuple[float, str]]:
    found = []
    for m in re.finditer(r"\bscore\s+(?:of\s+)?([0-9]+(?:\.[0-9]+)?)\b", text, re.IGNORECASE):
        raw = m.group(0)
        try:
            found.append((float(m.group(1)), raw))
        except ValueError:
            pass
    return found


def _collect_dossier_entities(dossier: OpportunityEvidenceDossier) -> Set[str]:
    """
    Extracts all valid process activities, transitions, case IDs, and cohorts from the dossier.
    """
    entities: Set[str] = set()

    # Target entity and its components
    entities.add(dossier.target_entity.strip())
    if " -> " in dossier.target_entity:
        parts = dossier.target_entity.split(" -> ")
        for p in parts:
            entities.add(p.strip())

    # Archetype and Cohort names
    entities.add(dossier.archetype.value)
    entities.add(dossier.portfolio_cohort.value)

    # Exemplars
    for ex in dossier.exemplars:
        entities.add(ex.case_id.strip())
        for anchor in ex.event_anchors:
            if anchor.activity:
                entities.add(anchor.activity.strip())
            if anchor.case_id:
                entities.add(anchor.case_id.strip())

    # Epistemic ledger statements
    for item in dossier.epistemic_ledger:
        for act in re.findall(r"activity '([^']+)'", item.statement):
            entities.add(act.strip())
        for tr in re.findall(r"transition '([^']+)'", item.statement):
            entities.add(tr.strip())

    return entities


def _is_number_in_pool(num: float, valid_pool: Set[float]) -> bool:
    """Checks whether a number exists in the specific metric pool within tight rounding tolerance."""
    for sup in valid_pool:
        if math.isclose(num, sup, rel_tol=1e-3, abs_tol=0.01):
            return True
        if abs(num - sup) < 1.0 and abs(round(num) - round(sup)) == 0:
            return True
    return False


def verify_opportunity_explanation(
    explanation: OpportunityExplanation,
    dossier: OpportunityEvidenceDossier,
) -> GroundingAudit:
    """
    Deterministically evaluates an OpportunityExplanation against its source OpportunityEvidenceDossier.
    Performs context-aware metric verification, entity checking, and economic/causal guardrail tests.
    Returns a GroundingAudit record with status VERIFIED_GROUNDED or FALLBACK_APPLIED.
    """
    discrepancies: List[str] = []
    verified_numbers: List[str] = []
    verified_entities: List[str] = []

    # -------------------------------------------------------------------------
    # 1. Structural Identity Checks
    # -------------------------------------------------------------------------
    if explanation.opportunity_id != dossier.opportunity_id:
        discrepancies.append(
            f"Opportunity ID mismatch: explanation has '{explanation.opportunity_id}' but dossier has '{dossier.opportunity_id}'."
        )

    if explanation.archetype != dossier.archetype:
        discrepancies.append(
            f"Archetype mismatch: explanation has '{explanation.archetype.value}' but dossier has '{dossier.archetype.value}'."
        )

    if explanation.portfolio_cohort != dossier.portfolio_cohort:
        discrepancies.append(
            f"Portfolio cohort mismatch: explanation has '{explanation.portfolio_cohort.value}' but dossier has '{dossier.portfolio_cohort.value}'."
        )

    if explanation.rank_order != dossier.rank_order:
        discrepancies.append(
            f"Rank order mismatch: explanation has #{explanation.rank_order} but dossier has #{dossier.rank_order}."
        )

    if explanation.target_entity.strip() != dossier.target_entity.strip():
        discrepancies.append(
            f"Target entity mismatch: explanation has '{explanation.target_entity}' but dossier has '{dossier.target_entity}'."
        )

    if dossier.composite_priority_score is None:
        if explanation.composite_priority_score is not None:
            discrepancies.append(
                f"Composite priority score discrepancy: dossier is unscored (None), but explanation claims score {explanation.composite_priority_score}."
            )
    else:
        if explanation.composite_priority_score is None:
            discrepancies.append(
                f"Composite priority score discrepancy: dossier has score {dossier.composite_priority_score}, but explanation has None."
            )
        elif not math.isclose(explanation.composite_priority_score, dossier.composite_priority_score, abs_tol=1e-4):
            discrepancies.append(
                f"Composite priority score mismatch: explanation has {explanation.composite_priority_score} but dossier has {dossier.composite_priority_score}."
            )

    # -------------------------------------------------------------------------
    # 2. Entity Verification Checks
    # -------------------------------------------------------------------------
    valid_entities = _collect_dossier_entities(dossier)
    full_text = " ".join([
        explanation.executive_summary,
        explanation.operational_problem_narrative,
        explanation.economic_interpretation,
        explanation.strategic_rationale,
    ])

    # Case mentions: e.g. Case 'CASE_123'
    for c_id in re.findall(r"\bCase\s+'([^']+)'", full_text, re.IGNORECASE):
        if c_id not in valid_entities:
            discrepancies.append(
                f"Unsupported case reference: '{c_id}' does not exist in dossier exemplars or evidence records."
            )
        else:
            verified_entities.append(c_id)

    # Process entity mentions: e.g. target 'XYZ', transition 'XYZ', activity 'XYZ'
    for ent in re.findall(r"(?:target|transition|activity)\s+'([^']+)'", full_text, re.IGNORECASE):
        if ent not in valid_entities:
            discrepancies.append(
                f"Unsupported process entity: '{ent}' is not the candidate target entity or an observed activity."
            )
        else:
            verified_entities.append(ent)

    # Confirm candidate target entity itself
    if explanation.target_entity in valid_entities:
        verified_entities.append(explanation.target_entity)

    # -------------------------------------------------------------------------
    # 3. Context-Aware Metric Verification Checks
    # -------------------------------------------------------------------------
    pool = DossierMetricPool(dossier)

    # 3.1 Currency claims: $X
    for val, raw in _extract_raw_currency(full_text):
        if _is_number_in_pool(val, pool.currencies):
            verified_numbers.append(raw)
        else:
            discrepancies.append(
                f"Unsupported currency claim: '{raw}' (${val:,.2f}) is not supported by dossier financial derivations."
            )

    # 3.2 Percentage claims: X%
    for m in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*%", full_text):
        raw = m.group(0)
        try:
            val = float(m.group(1))
            if _is_number_in_pool(val, pool.percentages):
                verified_numbers.append(raw)
            else:
                discrepancies.append(
                    f"Unsupported percentage claim: '{raw}' is not grounded in dossier metrics."
                )
        except ValueError:
            pass

    # 3.3 Duration claims in seconds: Xs
    for m in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*s\b", full_text):
        raw = m.group(0)
        try:
            val = float(m.group(1))
            if _is_number_in_pool(val, pool.durations_seconds):
                verified_numbers.append(raw)
            else:
                discrepancies.append(
                    f"Unsupported duration claim: '{raw}' is not supported by observed transition or cycle times."
                )
        except ValueError:
            pass

    # 3.4 Payback in months: X months
    for m in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*months?\b", full_text):
        raw = m.group(0)
        try:
            val = float(m.group(1))
            if _is_number_in_pool(val, pool.months):
                verified_numbers.append(raw)
            else:
                discrepancies.append(
                    f"Unsupported payback period claim: '{raw}' does not match dossier payback derivation."
                )
        except ValueError:
            pass

    # 3.5 Labor hours: X hours
    for m in re.finditer(r"([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(?:annual\s+active\s+labor\s+)?hours?\b", full_text):
        raw = m.group(0)
        num_str = m.group(1).replace(",", "")
        try:
            val = float(num_str)
            if _is_number_in_pool(val, pool.labor_hours):
                verified_numbers.append(raw)
            else:
                discrepancies.append(
                    f"Unsupported labor hours claim: '{raw}' ({val:,.0f}h) is not supported by labor effort derivations."
                )
        except ValueError:
            pass

    # 3.6 Repetition count: X times
    for m in re.finditer(r"([0-9]+)\s*times?\b", full_text):
        raw = m.group(0)
        try:
            val = float(m.group(1))
            if _is_number_in_pool(val, pool.repetition_counts):
                verified_numbers.append(raw)
            else:
                discrepancies.append(
                    f"Unsupported repetition claim: '{raw}' does not match observed activity recurrence counts."
                )
        except ValueError:
            pass

    # 3.7 Row and Line anchors: Row X / line X
    for m in re.finditer(r"\b(?:Row|line)\s*([0-9]+)\b", full_text, re.IGNORECASE):
        raw = m.group(0)
        try:
            val = float(m.group(1))
            if val in pool.rows_and_lines:
                verified_numbers.append(raw)
            else:
                discrepancies.append(
                    f"Unsupported source row anchor: '{raw}' is not an anchored source record in this dossier."
                )
        except ValueError:
            pass

    # 3.8 Rank order: #X
    for m in re.finditer(r"#([0-9]+)\b", full_text):
        raw = m.group(0)
        try:
            val = float(m.group(1))
            if val in pool.ranks:
                verified_numbers.append(raw)
            else:
                discrepancies.append(
                    f"Unsupported rank claim: '{raw}' does not match assigned portfolio rank #{dossier.rank_order}."
                )
        except ValueError:
            pass

    # 3.9 Score claims: score of X
    for val, raw in _extract_raw_score(full_text):
        if _is_number_in_pool(val, pool.scores):
            verified_numbers.append(raw)
        else:
            discrepancies.append(
                f"Unsupported priority score claim: '{raw}' does not match dossier priority or composite scores."
            )

    # -------------------------------------------------------------------------
    # 4. Economic, Epistemic, and Causal Guardrails
    # -------------------------------------------------------------------------
    # 4.1 Banned savings assertions (guaranteed cash savings, budget reductions)
    for pat in BANNED_SAVINGS_PATTERNS:
        for match in re.finditer(pat, full_text, re.IGNORECASE):
            start_pos = max(0, match.start() - 40)
            prefix_text = full_text[start_pos:match.start()].lower()
            is_negated = any(neg in prefix_text for neg in DISCLAIMER_NEGATION_WORDS)
            if not is_negated:
                discrepancies.append(
                    f"Economic guardrail violation: '{match.group(0)}' asserts guaranteed cash savings or budget reduction without mandatory disclaimer."
                )

    # 4.2 Unsupported causal assertions (definitively causes, conclusively proves)
    for pat in UNSUPPORTED_CAUSAL_PATTERNS:
        match = re.search(pat, full_text, re.IGNORECASE)
        if match:
            discrepancies.append(
                f"Causal assertion guardrail violation: '{match.group(0)}' asserts proven causality, which operational log correlations cannot establish."
            )

    # 4.3 Unmonetized economics substitution check
    cap_drv = next((drv for drv in dossier.derivations if drv.metric_id == "CAPACITY_VAL_V1"), None)
    is_unmonetized = (cap_drv is None or cap_drv.output_value is None)

    if is_unmonetized:
        zero_sub = re.search(r"\$(?:0|0\.00)\s*(?:in\s+)?net\s+annual", explanation.economic_interpretation, re.IGNORECASE)
        if zero_sub:
            discrepancies.append(
                "Economic guardrail violation: Missing economic inputs must remain unmonetized/unknown, not substituted with $0 or zero net benefit."
            )
        econ_currencies = re.findall(r"\$([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)", explanation.economic_interpretation)
        if econ_currencies:
            discrepancies.append(
                f"Economic guardrail violation: Opportunity is unmonetized, but claims monetary figure(s): {', '.join(['$' + c for c in econ_currencies])}."
            )

    # 4.4 Epistemic integrity check (prohibits classifying estimates/decisions as directly observed facts)
    epistemic_inversion = re.search(
        r"(?:observed|measured)\s+fact\s+that\s+(?:net\s+annual|capacity\s+benefit|composite\s+score|priority\s+tier|payback)",
        full_text,
        re.IGNORECASE,
    )
    if epistemic_inversion:
        discrepancies.append(
            f"Epistemic integrity violation: '{epistemic_inversion.group(0)}' represents projected estimates or decisions as directly observed facts."
        )

    # -------------------------------------------------------------------------
    # 5. Final Status Assignment
    # -------------------------------------------------------------------------
    verified_numbers_sorted = sorted(list(set(verified_numbers)))
    verified_entities_sorted = sorted(list(set(verified_entities)))

    if len(discrepancies) == 0:
        status = GroundingVerificationStatus.VERIFIED_GROUNDED
    else:
        status = GroundingVerificationStatus.FALLBACK_APPLIED

    return GroundingAudit(
        status=status,
        verified_numbers=verified_numbers_sorted,
        verified_entities=verified_entities_sorted,
        discrepancies=discrepancies,
    )
