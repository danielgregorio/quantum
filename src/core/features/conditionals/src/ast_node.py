"""
AST Node for Conditionals (q:if/q:else/q:elseif)
"""

from typing import Dict, Any, List

# Import base class
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.ast_nodes import QuantumNode


class IfNode(QuantumNode):
    """Represents a <q:if> with elseif and else"""

    def __init__(self, condition: str):
        self.condition = condition
        self.if_body: List[QuantumNode] = []

        # Support for elseif blocks
        self.elseif_blocks: List[Dict[str, Any]] = []  # [{"condition": str, "body": List[QuantumNode]}]

        # Support for else block
        self.else_body: List[QuantumNode] = []

    def add_if_statement(self, statement: QuantumNode):
        """Add statement to if body"""
        self.if_body.append(statement)

    def add_elseif_block(self, condition: str, body: List[QuantumNode] = None):
        """Add elseif block"""
        self.elseif_blocks.append({
            "condition": condition,
            "body": body or []
        })

    def add_else_statement(self, statement: QuantumNode):
        """Add statement to else body"""
        self.else_body.append(statement)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "if",
            "condition": self.condition,
            "if_body_count": len(self.if_body),
            "elseif_count": len(self.elseif_blocks),
            "has_else": len(self.else_body) > 0
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.condition:
            errors.append("If condition is required")

        # Validate all bodies
        for statement in self.if_body:
            errors.extend(statement.validate())

        for elseif_block in self.elseif_blocks:
            if not elseif_block["condition"]:
                errors.append("Elseif condition is required")
            for statement in elseif_block["body"]:
                errors.extend(statement.validate())

        for statement in self.else_body:
            errors.extend(statement.validate())

        return errors
