"""
AST Nodes for Event System (q:on, q:dispatch)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.ast_nodes import QuantumNode


@dataclass
class OnEventNode(QuantumNode):
    """
    Represents a <q:on> - Event handler

    Example:
      <q:on event="userLogin" function="handleLogin" />
      <q:on event="dataChange" once="true">
        <q:set name="updated" value="true" />
      </q:on>
    """
    event_name: str
    function_name: Optional[str] = None  # Call this function
    once: bool = False  # Remove handler after first trigger
    capture: bool = False  # Capture phase (vs bubble)
    debounce: Optional[int] = None  # Milliseconds
    throttle: Optional[int] = None  # Milliseconds
    prevent_default: bool = False
    stop_propagation: bool = False

    # Inline handler (statements)
    body: List[QuantumNode] = field(default_factory=list)

    def add_statement(self, statement: QuantumNode):
        """Add statement to inline handler body"""
        self.body.append(statement)

    def validate(self) -> List[str]:
        errors = []
        if not self.event_name:
            errors.append("Event handler requires 'event' attribute")
        if not self.function_name and not self.body:
            errors.append("Event handler must have either 'function' attribute or inline body")
        for stmt in self.body:
            errors.extend(stmt.validate())
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "on_event",
            "event": self.event_name,
            "function": self.function_name,
            "once": self.once,
            "capture": self.capture,
            "debounce": self.debounce,
            "throttle": self.throttle,
            "prevent_default": self.prevent_default,
            "stop_propagation": self.stop_propagation,
            "body_statements": len(self.body)
        }


@dataclass
class DispatchEventNode(QuantumNode):
    """
    Represents a <q:dispatch> - Emit an event

    Example:
      <q:dispatch event="userLogin" data="{user}" />
      <q:dispatch event="dataChange" bubbles="true" cancelable="true">
        <data key="field" value="{newValue}" />
      </q:dispatch>
    """
    event_name: str
    data: Optional[str] = None  # Event data (expression)
    bubbles: bool = True  # Bubble up through component tree
    cancelable: bool = True  # Can be canceled with preventDefault()
    composed: bool = False  # Cross shadow DOM boundary

    # Custom event data (key-value pairs)
    event_data: Dict[str, str] = field(default_factory=dict)

    def validate(self) -> List[str]:
        errors = []
        if not self.event_name:
            errors.append("Event dispatch requires 'event' attribute")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "dispatch_event",
            "event": self.event_name,
            "data": self.data,
            "bubbles": self.bubbles,
            "cancelable": self.cancelable,
            "composed": self.composed,
            "event_data": self.event_data
        }
