"""
Support tiers for Quantum tags.

PRODUCTION_READINESS.md Fase 0. "Production-ready" is meaningful only relative
to a defined surface, so the surface is defined here, in code, and a tag
outside the supported set announces itself the first time it is used instead
of pretending to be first-class.

The lists mirror SUPPORT_TIERS.md. When they disagree, this file is the one the
engine actually enforces, so keep it in step.
"""

import logging

logger = logging.getLogger("quantum.tiers")

# Documented, tested end-to-end, stable. A break here is a critical bug.
CORE = frozenset({
    "component", "param", "return", "set", "if", "loop", "function",
    "query", "action", "redirect", "flash", "invoke", "data",
    "import", "slot",
})

# The reason the project exists. Same contract as Core is the goal; some of it
# is still being validated end-to-end (PRODUCTION_READINESS.md Fase 4).
DIFERENCIAL = frozenset({"llm", "knowledge", "agent", "team"})

# Kept and registered, but no stability promise and not in the README. Using
# one is fine for experiments; relying on one in production is not supported.
EXPERIMENTAL = frozenset({
    "job", "schedule", "thread",
    "message", "queue", "subscribe", "messageAck", "messageNack",
    "websocket", "websocket-send", "websocket-close",
    "mail", "file", "log", "dump", "persist",
    "python", "pyclass", "pyimport", "class", "decorator", "pydecorator",
    "dispatchEvent", "transaction",
})

SUPPORTED = CORE | DIFERENCIAL


def tier_of(tag_name: str) -> str:
    """'core' | 'diferencial' | 'experimental' | 'unknown'."""
    if tag_name in CORE:
        return "core"
    if tag_name in DIFERENCIAL:
        return "diferencial"
    if tag_name in EXPERIMENTAL:
        return "experimental"
    return "unknown"


# Warn once per tag per process — a q:loop over 1,000 rows must not emit 1,000
# lines, the same discipline as expression_diagnostics.
_warned: set = set()


def warn_if_unsupported(tag_name: str) -> None:
    """Emit a one-time warning when an experimental tag is used.

    Not an error: experimental tags still run. The point is that an operator
    reading the log sees, once, that their app leans on something the project
    does not promise to keep working — the audit found apps built entirely on
    tags that parse and then explode, with nothing warning anyone.
    """
    tier = tier_of(tag_name)
    if tier in ("core", "diferencial", "unknown"):
        # 'unknown' is handled by the parser's own error path, not here.
        return
    if tag_name in _warned:
        return
    _warned.add(tag_name)
    logger.warning(
        "q:%s is EXPERIMENTAL — not covered by the production support surface "
        "(SUPPORT_TIERS.md). It may change or break without notice; do not rely "
        "on it in production.", tag_name
    )


def reset_warnings() -> None:
    """For tests, and for a reloading server."""
    _warned.clear()
