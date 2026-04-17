"""
AOS Policy Engine — the runtime queried by every agent before execution.

Design principles:
  - Queryable in real time (sub-10ms for in-memory ruleset).
  - Editable by business users (YAML files + admin API).
  - Versioned (every RuleSet carries a version; changes produce a new version).
  - Auditable (every decision is returned with the list of matched rules).

Usage:
    engine = PolicyEngine.load_from_dir("app/engine/policies")
    decision = engine.evaluate(
        domain="procurement",
        action="create_purchase_order",
        context={"amount": 1_500_000, "vendor_id": "...", "user_role": "procurement_manager"},
    )
    if decision.requires_approval:
        # route to approval workflow
        ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.engine.policy.evaluator import rule_matches
from app.engine.policy.rules import Rule, RuleSet, load_rules


@dataclass
class PolicyDecision:
    """Result of evaluating an action against the policy engine."""

    allowed: bool = True
    requires_approval: bool = False
    approver_roles: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)       # human-readable block reasons
    warnings: list[str] = field(default_factory=list)
    effects: dict[str, Any] = field(default_factory=dict)  # merged `then` side-effects
    matched_rules: list[str] = field(default_factory=list)  # rule IDs that fired
    ruleset_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "requires_approval": self.requires_approval,
            "approver_roles": self.approver_roles,
            "blocks": self.blocks,
            "warnings": self.warnings,
            "effects": self.effects,
            "matched_rules": self.matched_rules,
            "ruleset_version": self.ruleset_version,
        }


class PolicyEngine:
    """In-memory policy engine. Reload from disk on demand."""

    def __init__(self, ruleset: Optional[RuleSet] = None) -> None:
        self.ruleset = ruleset or RuleSet()

    @classmethod
    def load_from_dir(cls, path: str | Path) -> "PolicyEngine":
        return cls(load_rules(path))

    def reload(self, path: str | Path) -> None:
        self.ruleset = load_rules(path)

    def add_rule(self, rule: Rule) -> None:
        self.ruleset.add(rule)

    def evaluate(
        self,
        domain: str,
        action: str,
        context: dict[str, Any],
    ) -> PolicyDecision:
        """Evaluate every rule for (domain, action) against context."""
        decision = PolicyDecision(ruleset_version=self.ruleset.version)

        for rule in self.ruleset.for_action(domain, action):
            if not rule_matches(rule, context):
                continue

            decision.matched_rules.append(rule.id)
            self._apply_effects(rule, decision)

        # If any rule blocked, allowed=False wins
        if decision.blocks:
            decision.allowed = False

        return decision

    @staticmethod
    def _apply_effects(rule: Rule, decision: PolicyDecision) -> None:
        """Merge a matched rule's `then` clause into the running decision."""
        then = rule.then or {}

        if then.get("block"):
            reason = then.get("reason", f"Blocked by {rule.id}")
            decision.blocks.append(f"[{rule.id}] {reason}")

        if then.get("warn"):
            decision.warnings.append(f"[{rule.id}] {then['warn']}")

        require = then.get("require_approval")
        if require:
            decision.requires_approval = True
            if isinstance(require, str):
                if require not in decision.approver_roles:
                    decision.approver_roles.append(require)
            elif isinstance(require, list):
                for r in require:
                    if r not in decision.approver_roles:
                        decision.approver_roles.append(r)

        # Side-effect fields the caller can use (limits, rate caps, required checks, etc.)
        for key, value in then.items():
            if key in ("block", "warn", "require_approval", "reason"):
                continue
            decision.effects[key] = value
