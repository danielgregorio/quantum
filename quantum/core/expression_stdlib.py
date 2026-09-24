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

import math
import random as _random_module
import re
from decimal import Decimal, ROUND_HALF_UP
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


def _slugify(v: Any) -> str:
    """'Olá, Mundo!' -> 'ola-mundo': for URLs made from a title (EXPR-9)."""
    import unicodedata
    text = unicodedata.normalize('NFKD', str(v)).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


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
    # EXPR-9: half away from zero, as in ColdFusion and spreadsheets. Python's
    # round() is banker's rounding over binary floats: round(2.5) was 2 and
    # round(0.125, 2) was 0.12. Decimal over the number's text avoids both.
    places = int(digits)
    step = Decimal(1).scaleb(-places)
    result = Decimal(str(v)).quantize(step, rounding=ROUND_HALF_UP)
    return int(result) if places <= 0 else float(result)


def _ceil(v: Any) -> int:
    return math.ceil(float(v))


def _floor(v: Any) -> int:
    return math.floor(float(v))


# -- passwords ---------------------------------------------------------------
#
# Authentication is Core (decision D4), and a login is "look the user up, then
# check the password". Without these, a .q could not check a password against
# a stored hash without q:python — so every login example just set
# session.authenticated=true for whoever submitted the form (gap AUTH-1).

def hash_password(password: Any) -> str:
    """bcrypt hash of a password, for storing. Never store the password itself."""
    import bcrypt
    if password is None or password == '':
        raise ValueError("hashPassword: the password is empty")
    return bcrypt.hashpw(str(password).encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: Any, hashed: Any) -> bool:
    """True when `password` matches a hash made by hashPassword.

    Fail-closed: an empty password, a missing hash or a malformed hash is
    False, never an error — so `q:if condition="verifyPassword(password, h)"`
    cannot be tricked into the true branch by bad data.
    """
    import bcrypt
    if not password or not hashed or not isinstance(hashed, str):
        return False
    try:
        return bcrypt.checkpw(str(password).encode('utf-8'), hashed.encode('utf-8'))
    except (ValueError, TypeError):
        return False


def _urlencode(v) -> str:
    """EXPR-12: a value made safe to put in a URL — `q:redirect url="/?q={urlencode(q)}"`."""
    from urllib.parse import quote_plus
    return quote_plus('' if v is None else str(v))


# -- chance (EXPR-15) -------------------------------------------------------

_rng = _random_module.SystemRandom()


def _random(low: Any = None, high: Any = None) -> Any:
    """random() is a number in [0, 1); random(a, b) an integer from a to b."""
    if low is None and high is None:
        return _rng.random()
    if low is None or high is None:
        raise ValueError("random() takes no arguments, or two: random(a, b)")
    a, b = int(low), int(high)
    if a > b:
        raise ValueError(f"random({a}, {b}): the first bound is larger than the second")
    return _rng.randint(a, b)


def _chance(p: Any) -> bool:
    """True with probability p (0 to 1)."""
    p = float(p)
    if not 0 <= p <= 1:
        raise ValueError(f"chance({p}): the probability is between 0 and 1")
    return _rng.random() < p


def _get(container: Any, key: Any, default: Any = None) -> Any:
    """EXPR-16: an optional key or index — `default` when it is not there.

    `d['k']` and `d.k` are an error when the key is missing (a typo must not
    render as nothing); this is how a key that may be absent is read.
    """
    if isinstance(container, dict):
        return container.get(key, default)
    if isinstance(container, (list, tuple, str)) and isinstance(key, int) and not isinstance(key, bool):
        return container[key] if -len(container) <= key < len(container) else default
    if container is None:
        return default
    raise ValueError(f"get() reads a key of an object or an index of a list, not of {type(container).__name__}")


def _pick(items: Any) -> Any:
    """One element of a list, at random."""
    items = list(items)
    if not items:
        raise ValueError("pick() of an empty list")
    return _rng.choice(items)


STDLIB = {
    # passwords
    'hashPassword': hash_password,
    'verifyPassword': verify_password,
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
    'slugify': _slugify,
    'urlencode': _urlencode,
    # collections
    'get': _get,
    'len': _len,
    'first': _first,
    'last': _last,
    'join': _join,
    'sort': _sort,
    # numbers
    'round': _round,
    'ceil': _ceil,
    'floor': _floor,
    'abs': abs,
    'min': min,
    'max': max,
    'int': int,
    'float': float,
    'str': str,
    # chance (EXPR-15)
    'random': _random,
    'chance': _chance,
    'pick': _pick,
}
