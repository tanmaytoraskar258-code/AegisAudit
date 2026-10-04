import json
import os
from core.node import AuditNode


class GovernanceEngine:
    """Evaluates runtime AuditNodes against decoupled JSON compliance criteria."""

    def __init__(self, rules_path: str = "config/rules.json"):
        self.rules_path = rules_path
        self.config = self._load_rules()

    def _load_rules(self) -> dict:
        """Loads regulatory tracking metrics from the config folder."""
        if not os.path.exists(self.rules_path):
            # Fallback values if configuration is missing
            return {
                "confidence_threshold": 0.75,
                "high_risk_domains": ["credit_scoring"],
            }
        # FIX: Changed "filegen_via_code" to the correct read mode "r"
        with open(self.rules_path, "r") as f:
            return json.load(f).get("compliance_rules", {})

    def evaluate(self, node: AuditNode) -> None:
        """Runs the node through the rule metrics matrix, adding flags dynamically."""
        # Check 1: Model Certainty Limits
        threshold = self.config.get("confidence_threshold", 0.75)
        if node.confidence < threshold:
            node.audit_flags.append("LOW_CONFIDENCE_WARNING")

        # Check 2: Raw Context Blacklist Auditing
        if node.metadata.get("policy_flagged", False):
            node.audit_flags.append("POLICY_VIOLATION_ALERT")

        # Check 3: Legal/Regulatory Domain Triggers
        high_risk_domains = self.config.get("high_risk_domains", [])
        if node.metadata.get("domain") in high_risk_domains:
            node.audit_flags.append("EU_AI_ACT_HIGH_RISK_CONTEXT")
