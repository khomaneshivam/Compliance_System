"""
Deterministic Regulatory Applicability Rules Engine
Evaluates declarative AST rule conditions against structured company and plant facts.
Enforces Three-Valued Logic (TRUE, FALSE, UNKNOWN) without running eval/exec or LLMs.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Set
from pydantic import BaseModel, Field


class EvalResult(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


def three_valued_and(results: List[EvalResult]) -> EvalResult:
    """
    Kleene three-valued AND logic:
    - If ANY operand is FALSE -> FALSE (False AND anything is False)
    - If ALL operands are TRUE -> TRUE
    - Otherwise -> UNKNOWN
    """
    if not results:
        return EvalResult.TRUE
    if any(r == EvalResult.FALSE for r in results):
        return EvalResult.FALSE
    if all(r == EvalResult.TRUE for r in results):
        return EvalResult.TRUE
    return EvalResult.UNKNOWN


def three_valued_or(results: List[EvalResult]) -> EvalResult:
    """
    Kleene three-valued OR logic:
    - If ANY operand is TRUE -> TRUE (True OR anything is True)
    - If ALL operands are FALSE -> FALSE
    - Otherwise -> UNKNOWN
    """
    if not results:
        return EvalResult.FALSE
    if any(r == EvalResult.TRUE for r in results):
        return EvalResult.TRUE
    if all(r == EvalResult.FALSE for r in results):
        return EvalResult.FALSE
    return EvalResult.UNKNOWN


def three_valued_not(result: EvalResult) -> EvalResult:
    """
    Kleene three-valued NOT logic:
    - NOT TRUE -> FALSE
    - NOT FALSE -> TRUE
    - NOT UNKNOWN -> UNKNOWN
    """
    if result == EvalResult.TRUE:
        return EvalResult.FALSE
    if result == EvalResult.FALSE:
        return EvalResult.TRUE
    return EvalResult.UNKNOWN


class RuleEvaluationOutcome(BaseModel):
    status: str = Field(..., description="APPLICABLE, NOT_APPLICABLE, or NEEDS_REVIEW")
    raw_result: EvalResult = Field(..., description="TRUE, FALSE, or UNKNOWN")
    explanation: str = Field(..., description="Human-readable traceable justification")
    matched_facts: Dict[str, Any] = Field(default_factory=dict, description="Facts that satisfied rule conditions")
    missing_facts: List[str] = Field(default_factory=list, description="Missing facts preventing definitive evaluation")
    condition_trace: Dict[str, Any] = Field(default_factory=dict, description="Detailed AST evaluation breakdown")


class ApplicabilityEngine:
    """
    Pure deterministic rule evaluator.
    Thread-safe and stateless.
    """

    ALLOWED_OPERATORS = {
        "eq", "==", "ne", "!=",
        "gt", ">", "gte", ">=",
        "lt", "<", "lte", "<=",
        "in", "not_in",
        "exists", "is_null", "is_not_null",
        "contains", "starts_with", "ends_with",
        "jurisdiction_eq", "jurisdiction_in",
        "has_activity", "activity_in",
    }

    def evaluate_rule(
        self,
        expression_ast: Dict[str, Any],
        facts: Dict[str, Any],
        pass_template: Optional[str] = None,
        fail_template: Optional[str] = None,
    ) -> RuleEvaluationOutcome:
        """
        Evaluates an applicability rule AST against a dictionary of plant/company facts.
        """
        matched_facts: Dict[str, Any] = {}
        missing_facts: Set[str] = set()

        result, trace = self._evaluate_node(expression_ast, facts, matched_facts, missing_facts)

        # Generate traceable explanation
        if result == EvalResult.TRUE:
            status = "APPLICABLE"
            missing_facts_list = []
            if pass_template:
                try:
                    explanation = pass_template.format(**facts)
                except Exception:
                    matched_desc = ", ".join(f"{k}={v}" for k, v in matched_facts.items())
                    explanation = f"Statutory requirement is applicable based on plant parameters: {matched_desc}."
            else:
                matched_desc = ", ".join(f"{k}={v}" for k, v in matched_facts.items())
                explanation = f"Statutory requirement is applicable based on verified parameters: {matched_desc}."
        elif result == EvalResult.FALSE:
            status = "NOT_APPLICABLE"
            missing_facts_list = []
            matched_facts = {}
            if fail_template:
                try:
                    explanation = fail_template.format(**facts)
                except Exception:
                    explanation = "Plant operational parameters do not meet the statutory threshold criteria for this obligation."
            else:
                explanation = "Plant operational parameters do not meet the statutory threshold criteria for this obligation."
        else:
            status = "NEEDS_REVIEW"
            missing_facts_list = sorted(list(missing_facts))
            missing_desc = f" ({', '.join(missing_facts_list)})" if missing_facts_list else ""
            explanation = (
                f"Potentially applicable: evaluation requires missing company facts"
                f"{missing_desc}. Human review and profile verification required."
            )

        return RuleEvaluationOutcome(
            status=status,
            raw_result=result,
            explanation=explanation,
            matched_facts=matched_facts,
            missing_facts=missing_facts_list,
            condition_trace=trace,
        )

    def _evaluate_node(
        self,
        node: Dict[str, Any],
        facts: Dict[str, Any],
        matched_facts: Dict[str, Any],
        missing_facts: Set[str],
    ) -> Tuple[EvalResult, Dict[str, Any]]:
        """Recursively evaluates an AST node."""
        if not isinstance(node, dict) or not node:
            return EvalResult.UNKNOWN, {"error": "Invalid or empty node format"}

        # Check for group operators: "operator": "AND" | "OR" | "NOT"
        if "operator" in node and str(node["operator"]).upper() in ("AND", "OR", "NOT"):
            op = str(node["operator"]).upper()
            rules = node.get("rules") or node.get("conditions") or []
            return self._evaluate_group(op, rules, facts, matched_facts, missing_facts)

        if "and" in node or "AND" in node:
            rules = node.get("and") or node.get("AND") or []
            return self._evaluate_group("AND", rules, facts, matched_facts, missing_facts)

        if "or" in node or "OR" in node:
            rules = node.get("or") or node.get("OR") or []
            return self._evaluate_group("OR", rules, facts, matched_facts, missing_facts)

        if "not" in node or "NOT" in node:
            child = node.get("not") or node.get("NOT")
            child_rules = [child] if isinstance(child, dict) else (child or [])
            return self._evaluate_group("NOT", child_rules, facts, matched_facts, missing_facts)

        # Prefix style operator support: e.g. { "==": ["field", "value"] } or { ">": ["boiler_count", 0] }
        for k, v in node.items():
            if k in self.ALLOWED_OPERATORS and isinstance(v, list) and len(v) == 2:
                field_name = v[0]
                expected_val = v[1]
                return self._evaluate_leaf(field_name, k, expected_val, facts, matched_facts, missing_facts)

        # Standard leaf format: { "field": "...", "operator": "...", "value": ... }
        field_name = node.get("field")
        op = node.get("operator")
        expected_val = node.get("value")

        if field_name and op:
            return self._evaluate_leaf(str(field_name), str(op), expected_val, facts, matched_facts, missing_facts)

        return EvalResult.UNKNOWN, {"error": f"Unrecognized AST node: {node}"}

    def _evaluate_group(
        self,
        op: str,
        rules: List[Dict[str, Any]],
        facts: Dict[str, Any],
        matched_facts: Dict[str, Any],
        missing_facts: Set[str],
    ) -> Tuple[EvalResult, Dict[str, Any]]:
        """Evaluates an AND, OR, or NOT group using three-valued logic."""
        if not rules:
            return EvalResult.UNKNOWN, {
                "group_operator": op,
                "result": EvalResult.UNKNOWN.value,
                "error": f"Empty condition group for operator '{op}'",
                "children": [],
            }

        child_results = []
        child_traces = []

        for rule in rules:
            res, trace = self._evaluate_node(rule, facts, matched_facts, missing_facts)
            child_results.append(res)
            child_traces.append(trace)

        if op == "AND":
            final_res = three_valued_and(child_results)
        elif op == "OR":
            final_res = three_valued_or(child_results)
        elif op == "NOT":
            if len(child_results) == 1:
                final_res = three_valued_not(child_results[0])
            else:
                final_res = EvalResult.UNKNOWN
        else:
            final_res = EvalResult.UNKNOWN

        return final_res, {
            "group_operator": op,
            "result": final_res.value,
            "children": child_traces,
        }

    def _evaluate_leaf(
        self,
        field_name: str,
        operator: str,
        expected_val: Any,
        facts: Dict[str, Any],
        matched_facts: Dict[str, Any],
        missing_facts: Set[str],
    ) -> Tuple[EvalResult, Dict[str, Any]]:
        """Evaluates a single leaf comparison against fact values."""
        clean_op = operator.lower().strip()
        if clean_op not in self.ALLOWED_OPERATORS:
            return EvalResult.UNKNOWN, {
                "field": field_name,
                "operator": operator,
                "error": f"Operator '{operator}' is not allowlisted.",
            }

        # Resolve field value (support nested 'plant.jurisdiction' or 'jurisdiction')
        actual_val = self._resolve_field_value(field_name, facts)

        # Handle existence / nullness checks where missing is a valid evaluation
        if clean_op == "is_null":
            is_null = actual_val is None
            res = EvalResult.TRUE if is_null else EvalResult.FALSE
            if res == EvalResult.TRUE:
                matched_facts[field_name] = None
            return res, {"field": field_name, "op": "is_null", "result": res.value}

        if clean_op in ("is_not_null", "exists"):
            exists = actual_val is not None
            res = EvalResult.TRUE if exists else EvalResult.FALSE
            if res == EvalResult.TRUE:
                matched_facts[field_name] = actual_val
            return res, {"field": field_name, "op": clean_op, "result": res.value}

        # If the fact is missing or None, evaluation is UNKNOWN
        if actual_val is None:
            missing_facts.add(field_name)
            return EvalResult.UNKNOWN, {
                "field": field_name,
                "operator": operator,
                "expected": expected_val,
                "actual": None,
                "result": EvalResult.UNKNOWN.value,
                "reason": "Missing fact in company profile",
            }

        # Perform typed comparison
        is_match = self._compare(actual_val, clean_op, expected_val)
        if is_match is None:
            # Comparison could not be computed due to type incompatibility or conversion failure
            missing_facts.add(field_name)
            return EvalResult.UNKNOWN, {
                "field": field_name,
                "operator": operator,
                "expected": expected_val,
                "actual": actual_val,
                "result": EvalResult.UNKNOWN.value,
                "error": f"Type mismatch or invalid value for comparison: cannot compare value of type {type(actual_val).__name__} with operator '{operator}'",
            }

        res = EvalResult.TRUE if is_match else EvalResult.FALSE

        if res == EvalResult.TRUE:
            matched_facts[field_name] = actual_val

        return res, {
            "field": field_name,
            "operator": operator,
            "expected": expected_val,
            "actual": actual_val,
            "result": res.value,
        }

    def _resolve_field_value(self, field_name: str, facts: Dict[str, Any]) -> Any:
        """Resolves field name supporting prefixes (e.g. 'plant.boiler_count' or 'profile.boiler_count')."""
        if field_name in facts:
            return facts[field_name]

        parts = field_name.split(".")
        if len(parts) == 2 and parts[1] in facts:
            return facts[parts[1]]

        # Search in raw_attributes or equipment if present
        raw_attrs = facts.get("raw_attributes", {})
        if isinstance(raw_attrs, dict) and field_name in raw_attrs:
            return raw_attrs[field_name]

        return None

    def _compare(self, actual: Any, op: str, expected: Any) -> Optional[bool]:
        """Safely executes allowlisted comparison without eval/exec. Returns None on type or conversion error."""
        try:
            # Reject booleans for numeric comparisons (since bool is an int subclass in Python)
            if (isinstance(actual, bool) or isinstance(expected, bool)) and op in (
                "gt", ">", "gte", ">=", "lt", "<", "lte", "<="
            ):
                return None

            # String / Equality
            if op in ("eq", "=="):
                if isinstance(actual, str) and isinstance(expected, str):
                    return actual.strip().lower() == expected.strip().lower()
                return actual == expected

            if op in ("ne", "!="):
                if isinstance(actual, str) and isinstance(expected, str):
                    return actual.strip().lower() != expected.strip().lower()
                return actual != expected

            # Numeric comparisons
            if op in ("gt", ">"):
                return float(actual) > float(expected)
            if op in ("gte", ">="):
                return float(actual) >= float(expected)
            if op in ("lt", "<"):
                return float(actual) < float(expected)
            if op in ("lte", "<="):
                return float(actual) <= float(expected)

            # Membership
            if op in ("in", "jurisdiction_in", "activity_in"):
                if isinstance(expected, (list, tuple, set)):
                    if isinstance(actual, str):
                        expected_normalized = [str(x).strip().lower() for x in expected]
                        return actual.strip().lower() in expected_normalized
                    return actual in expected
                if isinstance(expected, str) and isinstance(actual, str):
                    return actual.strip().lower() == expected.strip().lower()
                return False

            if op == "not_in":
                if isinstance(expected, (list, tuple, set)):
                    if isinstance(actual, str):
                        expected_normalized = [str(x).strip().lower() for x in expected]
                        return actual.strip().lower() not in expected_normalized
                    return actual not in expected
                return True

            # Text searching
            if op == "contains":
                if isinstance(actual, (list, tuple, set)):
                    return expected in actual
                return str(expected).lower() in str(actual).lower()

            if op == "starts_with":
                return str(actual).lower().startswith(str(expected).lower())

            if op == "ends_with":
                return str(actual).lower().endswith(str(expected).lower())

            # Activity matching
            if op == "has_activity":
                activities = actual if isinstance(actual, (list, tuple, set)) else [str(actual)]
                expected_str = str(expected).strip().lower()
                return any(str(act).strip().lower() == expected_str for act in activities)

            if op == "jurisdiction_eq":
                return str(actual).strip().lower() == str(expected).strip().lower()

        except (ValueError, TypeError):
            return None

        return None


engine = ApplicabilityEngine()
