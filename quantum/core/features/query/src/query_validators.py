"""
Quantum Query Validators — re-export of the canonical implementation.

This module used to hold a full 290-line COPY of QueryValidator. Nothing
imported it, so it quietly drifted out of step with the module the runtime
actually uses (quantum/runtime/query_validators.py) — and by the time the
audit looked, the two copies of a SECURITY validator disagreed with each
other. A stale duplicate of a validator is worse than no duplicate: whoever
reads this one believes they are reading what runs.

It re-exports instead of copying, so the two cannot diverge again. Import
from quantum.runtime.query_validators directly in new code.
"""

from quantum.runtime.query_validators import (  # noqa: F401
    QueryValidationError,
    QueryValidator,
)

__all__ = ["QueryValidationError", "QueryValidator"]
