"""
Custom AST Nodes for Example Plugin

Demonstrates how to create custom AST nodes that can be
used with the Quantum parser and runtime.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import base class - works when plugin is loaded
try:
    from core.ast_nodes import QuantumNode
except ImportError:
    # Fallback for standalone testing
    class QuantumNode:
        def to_dict(self) -> Dict[str, Any]:
            pass

        def validate(self) -> List[str]:
            pass


@dataclass
class HelloNode(QuantumNode):
    """
    Custom AST node for <ex:hello> tag.

    Represents a simple greeting element that displays
    a personalized hello message.

    Example:
        <ex:hello name="World" />
        <ex:hello name="{userName}" greeting="Welcome" />
    """

    name: str = "World"
    greeting: str = "Hello"
    style: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "hello",
            "name": self.name,
            "greeting": self.greeting,
            "style": self.style
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("HelloNode requires 'name' attribute")
        return errors

    def __repr__(self):
        return f"<HelloNode {self.greeting}, {self.name}!>"


@dataclass
class CounterNode(QuantumNode):
    """
    Custom AST node for <ex:counter> tag.

    Represents a counter component with increment/decrement.

    Example:
        <ex:counter name="clicks" initial="0" />
        <ex:counter name="score" initial="100" step="10" />
    """

    name: str = ""
    initial: int = 0
    step: int = 1
    min_value: Optional[int] = None
    max_value: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "counter",
            "name": self.name,
            "initial": self.initial,
            "step": self.step,
            "min": self.min_value,
            "max": self.max_value
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("CounterNode requires 'name' attribute")
        if self.min_value is not None and self.max_value is not None:
            if self.min_value > self.max_value:
                errors.append("min cannot be greater than max")
        return errors

    def __repr__(self):
        return f"<CounterNode {self.name}={self.initial}>"


@dataclass
class TimestampNode(QuantumNode):
    """
    Custom AST node for <ex:timestamp> tag.

    Displays a formatted timestamp.

    Example:
        <ex:timestamp />
        <ex:timestamp format="%Y-%m-%d" />
        <ex:timestamp format="%H:%M:%S" timezone="UTC" />
    """

    format: str = "%Y-%m-%d %H:%M:%S"
    timezone: Optional[str] = None
    variable: Optional[str] = None  # Optional variable name to store result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "timestamp",
            "format": self.format,
            "timezone": self.timezone,
            "variable": self.variable
        }

    def validate(self) -> List[str]:
        errors = []
        # Validate format string
        try:
            datetime.now().strftime(self.format)
        except ValueError as e:
            errors.append(f"Invalid timestamp format: {e}")
        return errors

    def __repr__(self):
        return f"<TimestampNode format='{self.format}'>"
