"""Tests for the AOS policy engine."""

from pathlib import Path

from app.engine.policy import PolicyEngine
from app.engine.policy.rules import Rule, RuleSet


POLICY_DIR = Path(__file__).resolve().parents[2] / "app" / "engine" / "policies"


def test_loads_all_policy_files():
    engine = PolicyEngine.load_from_dir(POLICY_DIR)
    assert len(engine.ruleset) > 0
    # Spot-check expected rule ids
    assert engine.ruleset.get("PROC-001") is not None
    assert engine.ruleset.get("FIN-005") is not None


def test_po_above_10l_requires_cfo():
    engine = PolicyEngine.load_from_dir(POLICY_DIR)
    decision = engine.evaluate(
        domain="procurement",
        action="create_purchase_order",
        context={"amount": 1_500_000},
    )
    assert decision.allowed is True
    assert decision.requires_approval is True
    assert "cfo" in decision.approver_roles
    assert "PROC-001" in decision.matched_rules


def test_po_under_50k_auto_approves():
    engine = PolicyEngine.load_from_dir(POLICY_DIR)
    decision = engine.evaluate(
        domain="procurement",
        action="create_purchase_order",
        context={"amount": 30_000},
    )
    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.effects.get("auto_approve") is True


def test_unbalanced_journal_blocked():
    engine = PolicyEngine.load_from_dir(POLICY_DIR)
    decision = engine.evaluate(
        domain="finance",
        action="post_journal_entry",
        context={"is_balanced": False, "period_closed": False},
    )
    assert decision.allowed is False
    assert any("FIN-005" in b for b in decision.blocks)


def test_no_gstin_blocks_taxable_po():
    engine = PolicyEngine.load_from_dir(POLICY_DIR)
    decision = engine.evaluate(
        domain="procurement",
        action="create_purchase_order",
        context={
            "amount": 200_000,
            "is_taxable": True,
            "vendor": {"gstin": None},
        },
    )
    # Should be blocked by PROC-004 despite PROC-002 also matching
    assert decision.allowed is False
    assert "PROC-004" in decision.matched_rules


def test_custom_rule_with_multi_role_approval():
    engine = PolicyEngine()
    engine.add_rule(Rule(
        id="TEST-001",
        name="Multi-role approval",
        domain="hr",
        action="revise_salary",
        then={"require_approval": ["cfo", "hr_head"]},
    ))
    decision = engine.evaluate("hr", "revise_salary", {})
    assert decision.requires_approval
    assert set(decision.approver_roles) == {"cfo", "hr_head"}
