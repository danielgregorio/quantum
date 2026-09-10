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

# Authentication is Core too (decision D4, 2026-09-10), but it is not a tag:
# it is the require_auth / require_role attributes of q:component plus the
# session scope. Listed here so the surface is complete in one place.
CORE_ATTRIBUTES = frozenset({"require_auth", "require_role"})

# Application types, by tier. A q:application's type decides which engine
# runs it, so the tier of the type is the tier of the whole app.
#
# LABORATORIO (decision D1/D2): the 2D game engine (qg:, including the Godot
# codegen) stays in the repository on purpose — games press on the language
# and surface features and bugs the core needs — but it carries no stability
# promise and is not part of the pitch. Its tests run in the main suite, so a
# core change that breaks a game shows up in CI.
LAB_APP_TYPES = frozenset({"game"})
EXPERIMENTAL_APP_TYPES = frozenset({"terminal", "ui", "testing"})

# Removed in 0.11 (APP-1), because they never worked: `quantum run` on a
# type="html" application failed at once (gap G17), and the type="api" server —
# also behind "microservices" — never executed a route's body, serving the
# literal text of the first q:return (gap G18). A web app is pages in
# components/ served by `quantum start`. "html" was also the default when
# type= was left out.
REMOVED_APP_TYPES = frozenset({"html", "api", "microservices"})


def removed_app_type_message(app_type: str, declared: bool) -> str:
    what = f'type="{app_type}"' if declared else 'with no type= (it meant type="html")'
    return (
        f"<q:application> {what} was removed in Quantum 0.11: it never ran its "
        f"routes. Build a web app as pages in components/ (components/index.q is "
        f"/) and run `quantum start`. See "
        f"https://danielgregorio.github.io/quantum/guide/getting-started")


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


def app_tier_of(app_type: str) -> str:
    """'laboratorio' | 'experimental' | 'supported' for a q:application type."""
    if app_type in LAB_APP_TYPES:
        return "laboratorio"
    if app_type in EXPERIMENTAL_APP_TYPES:
        return "experimental"
    return "supported"


def warn_app_type(app_type: str) -> None:
    """One-time warning when an application of a non-supported type runs."""
    tier = app_tier_of(app_type)
    key = f"application:{app_type}"
    if tier == "supported" or key in _warned:
        return
    _warned.add(key)
    if tier == "laboratorio":
        logger.warning(
            "q:application type=%r is LABORATÓRIO — it exists to press on the "
            "language, with no stability promise (SUPPORT_TIERS.md). It may "
            "change or break without notice.", app_type
        )
    else:
        logger.warning(
            "q:application type=%r is EXPERIMENTAL — not covered by the "
            "supported surface (SUPPORT_TIERS.md). It may change or break "
            "without notice; do not rely on it in production.", app_type
        )


def reset_warnings() -> None:
    """For tests, and for a reloading server."""
    _warned.clear()
