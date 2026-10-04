import datetime
import json
from typing import Any, Dict, List, Optional


class AuditNode:
    """Represents a single auditable decision token within an AI execution graph."""

    def __init__(
        self,
        decision_id: str,
        decision: str,
        confidence: float,
        metadata: Dict[str, Any],
        parent_id: Optional[str] = None,
    ):
        self.decision_id: str = decision_id
        self.parent_id: Optional[str] = parent_id
        self.decision: str = decision
        self.confidence: float = confidence
        self.metadata: Dict[str, Any] = metadata
        # Fixed: Using timezone-aware UTC format
        self.timestamp: str = datetime.datetime.now(datetime.UTC).isoformat()

        # Governance properties mutated by the Evaluation Engine
        self.audit_flags: List[str] = []
        self.counterfactual_forks: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        """Serializes node contents for data persistence or visualization pipes."""
        return {
            "decision_id": self.decision_id,
            "parent_id": self.parent_id,
            "decision": self.decision,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "metadata": json.dumps(self.metadata),
            "audit_flags": json.dumps(self.audit_flags),
            "counterfactual_forks": json.dumps(self.counterfactual_forks),
        }
