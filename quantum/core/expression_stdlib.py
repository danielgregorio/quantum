"""
Standard functions available inside Quantum `{...}` expressions.

Deliberately small. Every entry here is a function that was either already
needed by real .q files or whose absence caused a concrete bug:

- `now()` / `dateAdd()` / `dateFormat()` — their absence is why
  `session.sessionExpiry` had to be hardcoded to make login work at all
  (AUDIT_FIX_PLAN.md Fase 1). A framework that cannot express "24 hours from
  now" in its own language forces every app to hardcode a date.
- `len` / `first` / `last` — `.length` already worked on arrays via attribute
  access; these make the same thing available as a call.

Functions are looked up by name from expressions, so anything added here
becomes language surface. That is the reason to keep it short.
"""

from datetime import datetime, timedelta
from typing import Any, Iterable, Optional

_UNITS = {
    's': 'seconds', 'sec': 'seconds', 'second': 'seconds', 'seconds': 'seconds',
    'n': 'minutes', 'min': 'minutes', 'minute': 'minutes', 'minutes': 'minutes',
    'h': 'hours', 'hour': 'hours', 'hours': 'hours',
    'd': 'days', 'day': 'days', 'days': 'days',
    'w': 'weeks', 'week': 'weeks', 'weeks': 'weeks',
}


# -- dates -----------------------------------------------------------------

def now() -> datetime:
    """Current local datetime."""
    return datetime.now()


def date_add(unit: str, amount: int, start: Optional[Any] = None) -> datetime:
    """Add an interval to a datetime (defaults to now).

    dateAdd('h', 24)  ->  24 hours from now
    """
    key = _UNITS.get(str(unit).lower())
    if key is None:
        raise ValueError(
            f"unknown date unit {unit!r}; use s/n/h/d/w "
            f"(seconds/minutes/hours/days/weeks)"
        )
    base = _as_datetime(start) if start is not None else datetime.now()
    return base + timedelta(**{key: int(amount)})


def date_format(value: Any, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format a datetime (or ISO string) with a strftime pattern."""
    return _as_datetime(value).strftime(fmt)


def date_diff(unit: str, start: Any, end: Any) -> int:
    """Whole units between two datetimes."""
    key = _UNITS.get(str(unit).lower())
    if key is None:
        raise ValueError(f"unknown date unit {unit!r}")
    delta = _as_datetime(end) - _as_datetime(start)
    seconds = delta.total_seconds()
    per = {'seconds': 1, 'minutes': 60, 'hours': 3600,
           'days': 86400, 'weeks': 604800}[key]
    return int(seconds // per)


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError(f"cannot read {value!r} as a datetime")


# -- strings ---------------------------------------------------------------

def _upper(v: Any) -> str: return str(v).upper()
def _lower(v: Any) -> str: return str(v).lower()
def _trim(v: Any) -> str: return str(v).strip()
def _replace(v: Any, old: str, new: str) -> str: return str(v).replace(old, new)
def _split(v: Any, sep: str = ",") -> list: return str(v).split(sep)
def _contains(v: Any, needle: Any) -> bool: return str(needle) in str(v)


# -- collections -----------------------------------------------------------

def _len(v: Any) -> int:
    try:
        return len(v)
    except TypeError:
        return 0


def _first(v: Iterable) -> Any:
    items = list(v)
    return items[0] if items else None


def _last(v: Iterable) -> Any:
    items = list(v)
    return items[-1] if items else None


def _join(v: Iterable, sep: str = ", ") -> str:
    return sep.join(str(i) for i in v)


def _sort(v: Iterable, reverse: bool = False) -> list:
    return sorted(v, reverse=reverse)


# -- numbers ---------------------------------------------------------------

def _round(v: Any, digits: int = 0) -> Any:
    result = round(float(v), int(digits))
    return int(result) if digits == 0 else result


STDLIB = {
    # dates
    'now': now,
    'dateAdd': date_add,
    'dateFormat': date_format,
    'dateDiff': date_diff,
    # strings
    'upper': _upper,
    'lower': _lower,
    'trim': _trim,
    'replace': _replace,
    'split': _split,
    'contains': _contains,
    # collections
    'len': _len,
    'first': _first,
    'last': _last,
    'join': _join,
    'sort': _sort,
    # numbers
    'round': _round,
    'abs': abs,
    'min': min,
    'max': max,
    'int': int,
    'float': float,
    'str': str,
}
