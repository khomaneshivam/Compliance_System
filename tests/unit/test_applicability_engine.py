"""
Unit Tests for Deterministic Applicability Engine
Tests allowlisted operators, threshold boundaries, boolean nesting,
three-valued logic (TRUE, FALSE, UNKNOWN), and explainable rationales.
"""

import pytest
from app.modules.applicability.engine import (
    ApplicabilityEngine,
    EvalResult,
    three_valued_and,
    three_valued_or,
    three_valued_not,
)


@pytest.fixture
def engine():
    return ApplicabilityEngine()


# ------------------------------------------------------------------------------
# 1. Three-Valued Logic Tests
# ------------------------------------------------------------------------------

def test_three_valued_and():
    assert three_valued_and([EvalResult.TRUE, EvalResult.TRUE]) == EvalResult.TRUE
    assert three_valued_and([EvalResult.TRUE, EvalResult.FALSE]) == EvalResult.FALSE
    assert three_valued_and([EvalResult.FALSE, EvalResult.UNKNOWN]) == EvalResult.FALSE
    assert three_valued_and([EvalResult.TRUE, EvalResult.UNKNOWN]) == EvalResult.UNKNOWN
    assert three_valued_and([EvalResult.UNKNOWN, EvalResult.UNKNOWN]) == EvalResult.UNKNOWN


def test_three_valued_or():
    assert three_valued_or([EvalResult.FALSE, EvalResult.FALSE]) == EvalResult.FALSE
    assert three_valued_or([EvalResult.TRUE, EvalResult.FALSE]) == EvalResult.TRUE
    assert three_valued_or([EvalResult.TRUE, EvalResult.UNKNOWN]) == EvalResult.TRUE
    assert three_valued_or([EvalResult.FALSE, EvalResult.UNKNOWN]) == EvalResult.UNKNOWN
    assert three_valued_or([EvalResult.UNKNOWN, EvalResult.UNKNOWN]) == EvalResult.UNKNOWN


def test_three_valued_not():
    assert three_valued_not(EvalResult.TRUE) == EvalResult.FALSE
    assert three_valued_not(EvalResult.FALSE) == EvalResult.TRUE
    assert three_valued_not(EvalResult.UNKNOWN) == EvalResult.UNKNOWN


# ------------------------------------------------------------------------------
# 2. Numeric Thresholds & Boundary Conditions
# ------------------------------------------------------------------------------

def test_numeric_threshold_boundaries(engine: ApplicabilityEngine):
    ast_gte = {"field": "steam_capacity_tph", "operator": "gte", "value": 5.0}

    # Exactly at boundary (5.0 >= 5.0 -> True)
    res_equal = engine.evaluate_rule(ast_gte, {"steam_capacity_tph": 5.0})
    assert res_equal.status == "APPLICABLE"
    assert res_equal.raw_result == EvalResult.TRUE
    assert res_equal.matched_facts["steam_capacity_tph"] == 5.0

    # 1 below boundary (4.99 >= 5.0 -> False)
    res_below = engine.evaluate_rule(ast_gte, {"steam_capacity_tph": 4.99})
    assert res_below.status == "NOT_APPLICABLE"
    assert res_below.raw_result == EvalResult.FALSE

    # 1 above boundary (5.01 >= 5.0 -> True)
    res_above = engine.evaluate_rule(ast_gte, {"steam_capacity_tph": 5.01})
    assert res_above.status == "APPLICABLE"
    assert res_above.raw_result == EvalResult.TRUE


def test_strict_greater_than_boundary(engine: ApplicabilityEngine):
    ast_gt = {"field": "hazardous_waste_tpa", "operator": "gt", "value": 10.0}

    # Exactly at threshold (10.0 > 10.0 -> False)
    res_equal = engine.evaluate_rule(ast_gt, {"hazardous_waste_tpa": 10.0})
    assert res_equal.status == "NOT_APPLICABLE"

    # Just above (10.01 > 10.0 -> True)
    res_above = engine.evaluate_rule(ast_gt, {"hazardous_waste_tpa": 10.01})
    assert res_above.status == "APPLICABLE"


# ------------------------------------------------------------------------------
# 3. Missing Facts & Unknown Outcomes (Unknown != Not Applicable)
# ------------------------------------------------------------------------------

def test_missing_facts_produce_needs_review(engine: ApplicabilityEngine):
    """
    CRITICAL REQUIREMENT:
    Unknown/insufficient information must evaluate to NEEDS_REVIEW, never silently NOT_APPLICABLE.
    """
    ast = {"field": "hazardous_waste_tpa", "operator": "gt", "value": 5.0}

    # Missing hazardous_waste_tpa fact
    outcome = engine.evaluate_rule(ast, {"employee_count": 100})
    assert outcome.status == "NEEDS_REVIEW"
    assert outcome.raw_result == EvalResult.UNKNOWN
    assert "hazardous_waste_tpa" in outcome.missing_facts
    assert "missing company facts" in outcome.explanation


def test_and_group_with_unknown_and_false(engine: ApplicabilityEngine):
    """
    In AND group: If one condition is demonstrably FALSE, overall group is FALSE
    even if another is UNKNOWN (since False AND Unknown = False).
    """
    ast = {
        "operator": "AND",
        "rules": [
            {"field": "jurisdiction", "operator": "eq", "value": "Maharashtra"},
            {"field": "unknown_chemical_kg", "operator": "gt", "value": 100},
        ]
    }
    # Jurisdiction is Gujarat (FALSE), unknown_chemical is missing (UNKNOWN)
    outcome = engine.evaluate_rule(ast, {"jurisdiction": "Gujarat"})
    assert outcome.status == "NOT_APPLICABLE"
    assert outcome.raw_result == EvalResult.FALSE


def test_and_group_with_true_and_unknown(engine: ApplicabilityEngine):
    """
    In AND group: If one condition is TRUE and another is UNKNOWN, overall is UNKNOWN.
    """
    ast = {
        "operator": "AND",
        "rules": [
            {"field": "jurisdiction", "operator": "eq", "value": "Maharashtra"},
            {"field": "unknown_chemical_kg", "operator": "gt", "value": 100},
        ]
    }
    # Jurisdiction is Maharashtra (TRUE), unknown_chemical is missing (UNKNOWN)
    outcome = engine.evaluate_rule(ast, {"jurisdiction": "Maharashtra"})
    assert outcome.status == "NEEDS_REVIEW"
    assert outcome.raw_result == EvalResult.UNKNOWN
    assert "unknown_chemical_kg" in outcome.missing_facts


# ------------------------------------------------------------------------------
# 4. Membership, Activity & Presence Operators
# ------------------------------------------------------------------------------

def test_membership_and_activity_operators(engine: ApplicabilityEngine):
    # 'in' operator
    ast_in = {"field": "industry_category", "operator": "in", "value": ["RED", "ORANGE"]}
    assert engine.evaluate_rule(ast_in, {"industry_category": "RED"}).status == "APPLICABLE"
    assert engine.evaluate_rule(ast_in, {"industry_category": "GREEN"}).status == "NOT_APPLICABLE"

    # 'has_activity' operator
    ast_act = {"field": "activities", "operator": "has_activity", "value": "Electroplating"}
    assert engine.evaluate_rule(ast_act, {"activities": ["Foundry", "Electroplating"]}).status == "APPLICABLE"
    assert engine.evaluate_rule(ast_act, {"activities": ["Foundry", "Assembly"]}).status == "NOT_APPLICABLE"

    # 'is_null' vs 'is_not_null'
    ast_null = {"field": "effluent_treatment_plant", "operator": "is_null"}
    assert engine.evaluate_rule(ast_null, {"effluent_treatment_plant": None}).status == "APPLICABLE"
    assert engine.evaluate_rule(ast_null, {"effluent_treatment_plant": "ETP-01"}).status == "NOT_APPLICABLE"


# ------------------------------------------------------------------------------
# 5. Nested Boolean Rule Trees & Templates
# ------------------------------------------------------------------------------

def test_nested_boolean_tree_with_template(engine: ApplicabilityEngine):
    ast = {
        "operator": "OR",
        "rules": [
            {
                "operator": "AND",
                "rules": [
                    {"field": "industry_category", "operator": "eq", "value": "RED"},
                    {"field": "effluent_discharge_kld", "operator": "gt", "value": 0},
                ]
            },
            {"field": "hazardous_waste_tpa", "operator": "gte", "value": 10.0}
        ]
    }
    pass_tmpl = "Facility is categorized under {industry_category} category with {effluent_discharge_kld} KLD effluent discharge."
    
    facts = {
        "industry_category": "RED",
        "effluent_discharge_kld": 45.0,
        "hazardous_waste_tpa": 2.0,
    }
    outcome = engine.evaluate_rule(ast, facts, pass_template=pass_tmpl)
    assert outcome.status == "APPLICABLE"
    assert "45.0 KLD effluent discharge" in outcome.explanation
    assert outcome.matched_facts["industry_category"] == "RED"
    assert outcome.matched_facts["effluent_discharge_kld"] == 45.0
