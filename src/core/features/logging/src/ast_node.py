"""
AST Node for q:log - Structured Logging
"""

from typing import Optional
from core.ast_nodes import QuantumNode


class LogNode(QuantumNode):
    """
    Represents a <q:log> - Structured logging statement

    Example:
        <q:log level="info" message="User {userName} logged in" context="{user}" />
        <q:log level="error" message="API failed" when="{!api_result.success}" />
    """

    VALID_LEVELS = ['trace', 'debug', 'info', 'warning', 'error', 'critical']

    def __init__(
        self,
        level: str,
        message: str,
        context: Optional[str] = None,
        when: Optional[str] = None,
        provider: Optional[str] = None,
        async_mode: bool = True,
        correlation_id: Optional[str] = None
    ):
        """
        Initialize a LogNode

        Args:
            level: Log severity level (trace, debug, info, warning, error, critical)
            message: Log message with databinding support
            context: Optional structured data (JSON expression)
            when: Optional conditional expression
            provider: Optional output destination (Phase 2)
            async_mode: Async logging mode (Phase 2)
            correlation_id: Optional request tracking ID (Phase 2)
        """
        # Validate level
        if not level:
            raise ValueError("Log requires 'level' attribute")

        if level not in self.VALID_LEVELS:
            raise ValueError(
                f"Invalid log level '{level}'. Must be one of: {', '.join(self.VALID_LEVELS)}"
            )

        # Validate message
        if message is None:
            raise ValueError("Log requires 'message' attribute")

        self.level = level
        self.message = message
        self.context = context
        self.when = when
        self.provider = provider
        self.async_mode = async_mode
        self.correlation_id = correlation_id

    def __repr__(self):
        attrs = [f"level={self.level!r}", f"message={self.message!r}"]
        if self.context:
            attrs.append(f"context={self.context!r}")
        if self.when:
            attrs.append(f"when={self.when!r}")
        return f"LogNode({', '.join(attrs)})"

    def to_dict(self):
        """Convert node to dictionary for debugging/serialization"""
        return {
            "type": "log",
            "level": self.level,
            "message": self.message[:50] + "..." if self.message and len(self.message) > 50 else self.message,
            "context": self.context,
            "when": self.when,
            "provider": self.provider,
            "async": self.async_mode,
            "correlation_id": self.correlation_id
        }

    def validate(self):
        """Validate the node and return list of errors"""
        errors = []

        if not self.level:
            errors.append("Log requires 'level' attribute")
        elif self.level not in self.VALID_LEVELS:
            errors.append(f"Invalid log level '{self.level}'. Must be one of: {', '.join(self.VALID_LEVELS)}")

        if not self.message:
            errors.append("Log requires 'message' attribute")

        return errors
