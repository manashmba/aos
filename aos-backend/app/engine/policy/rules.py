"""
AOS Policy Rules — YAML-based rule definitions.

Policies are first-class editable artifacts. Business users can modify
thresholds, approval matrices, and conditional logic without code changes.
Every policy is versioned and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class Rule:
    """A single policy rule.

    Example:
        id: PROC-001
        name: PO requires CFO approval above 10L
        domain: procurement
        action: create_purchase_order
        when:
          - field: amount
            op: gte
            value: 1000000
        then:
          require_approval: cfo
          max_wait_hours: 24
    """

    id: str
    name: str
    domain: str
    action: str
    when: list[dict[str, Any]] = field(default_factory=list)
    then: dict[str, Any] = field(default_factory=dict)
    version: int = 1
    active: bool = True
    description: Optional[str] = None
    severity: str = "standard"  # standard / critical / advisory

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Rule":
        return cls(
            id=data["id"],
            name=data["name"],
            domain=data["domain"],
            action=data["action"],
            when=data.get("when", []),
            then=data.get("then", {}),
            version=data.get("version", 1),
            active=data.get("active", True),
            description=data.get("description"),
            severity=data.get("severity", "standard"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "action": self.action,
            "when": self.when,
            "then": self.then,
            "version": self.version,
            "active": self.active,
            "description": self.description,
            "severity": self.severity,
        }


@dataclass
class RuleSet:
    """A collection of rules, keyed by id."""

    rules: dict[str, Rule] = field(default_factory=dict)
    version: str = "1.0.0"

    def add(self, rule: Rule) -> None:
        self.rules[rule.id] = rule

    def get(self, rule_id: str) -> Optional[Rule]:
        return self.rules.get(rule_id)

    def for_action(self, domain: str, action: str) -> list[Rule]:
        """Return all active rules matching a domain+action."""
        return [
            r for r in self.rules.values()
            if r.active and r.domain == domain and r.action == action
        ]

    def __len__(self) -> int:
        return len(self.rules)

    def __iter__(self):
        return iter(self.rules.values())


def load_rules(path: str | Path) -> RuleSet:
    """Load a ruleset from a YAML file or directory of YAML files."""
    path = Path(path)
    ruleset = RuleSet()

    if path.is_file():
        _load_yaml_into(path, ruleset)
    elif path.is_dir():
        for yaml_file in sorted(path.glob("*.yaml")) + sorted(path.glob("*.yml")):
            _load_yaml_into(yaml_file, ruleset)
    else:
        raise FileNotFoundError(f"Policy path not found: {path}")

    return ruleset


def _load_yaml_into(file_path: Path, ruleset: RuleSet) -> None:
    """Parse a single YAML file and merge its rules into the ruleset."""
    with open(file_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    if "version" in data:
        ruleset.version = str(data["version"])

    for raw in data.get("rules", []):
        ruleset.add(Rule.from_dict(raw))


def to_decimal(value: Any) -> Decimal:
    """Coerce a value (int/float/str) to Decimal for money comparisons."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
