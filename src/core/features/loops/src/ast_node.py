"""
AST Node for Loops (q:loop)
"""

from typing import Dict, Any, List

# Import base class
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.ast_nodes import QuantumNode


class LoopNode(QuantumNode):
    """Represents a <q:loop> with various types"""

    def __init__(self, loop_type: str, var_name: str):
        self.loop_type = loop_type    # range, array, list, object, query, while
        self.var_name = var_name      # variable name for current item
        self.index_name = None        # optional index variable
        self.items = None             # data source expression
        self.condition = None         # for while loops
        self.from_value = None        # for range loops
        self.to_value = None          # for range loops
        self.step_value = 1           # for range loops
        self.delimiter = ","          # for list loops
        self.body: List[QuantumNode] = []  # statements inside loop

    def add_statement(self, statement: QuantumNode):
        self.body.append(statement)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "loop",
            "loop_type": self.loop_type,
            "var_name": self.var_name,
            "index_name": self.index_name,
            "from_value": self.from_value,
            "to_value": self.to_value,
            "step_value": self.step_value,
            "body_statements": len(self.body)
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.var_name:
            errors.append("Loop variable name is required")

        if self.loop_type == 'range':
            if not self.from_value:
                errors.append("Range loop requires 'from' attribute")
            if not self.to_value:
                errors.append("Range loop requires 'to' attribute")
        elif self.loop_type in ['array', 'list', 'object']:
            if not self.items:
                errors.append(f"{self.loop_type.title()} loop requires 'items' attribute")

        for statement in self.body:
            errors.extend(statement.validate())

        return errors
