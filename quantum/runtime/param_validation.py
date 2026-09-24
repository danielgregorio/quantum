"""ONE implementation of `q:param`, used by both places that validate.

There were two, and they disagreed.

`ComponentRuntime._coerce_param` (quantum/runtime/component.py) accepted
`integer|int|long` and `number|numeric|decimal|float|double`, left
string/file/array/object as they were and applied min/max to any value that
became a number. `ActionHandler._validate_type`
(quantum/runtime/action_handler.py) knew only `integer`, `decimal` and
`float`, and everything else fell into a final `return str(value)`. The same

    <q:param name="age" type="number" min="18" />

was a float with its minimum checked inside a component and the STRING "7"
with no check at all inside a `q:action` — 32 .q files in the repository use
`type="number"`, all of them in that situation when they are in an action.

The worst case was `type="file"`, which 5 shipped files use:

    <q:param name="avatar" type="file" required="true" />
    <q:file action="upload" file="{avatar}" destination="..." />

The final `str(value)` turned the upload object into its repr —
`"<FileStorage: 'photo.png' ('image/png')>"` — and `q:file` received that
string instead of the file. Uploading through a form did not work, and the
symptom pointed nowhere.

This module is the union of the two: the component's coercion plus the
`email`/`url` validations only the action had, plus a file type that is never
turned into text.
"""

import logging
import re
from typing import Any, List, Optional, Tuple

from quantum.core.expressions import coerce_number

logger = logging.getLogger('quantum.param')

INT_TYPES = ('integer', 'int', 'long')
FLOAT_TYPES = ('number', 'numeric', 'decimal', 'float', 'double')
FILE_TYPES = ('file', 'binary', 'upload')
# Types that pass through untouched: converting would change data the
# destination expects to receive as it came.
PASSTHROUGH_TYPES = ('string', 'text', 'array', 'object', 'any', 'json')

# FN-4: what q:function returnType= accepts ('void': returns nothing).
RETURN_TYPES = frozenset(INT_TYPES + FLOAT_TYPES + PASSTHROUGH_TYPES + ('boolean', 'email', 'url', 'void'))

# PARSE-5: what q:param type= accepts — the types coerce() converts or checks,
# the passthrough ones, and date (a form draws <input type="date">, UI-9).
PARAM_TYPES = INT_TYPES + FLOAT_TYPES + FILE_TYPES + PASSTHROUGH_TYPES + ('boolean', 'email', 'url', 'date')
# PARSE-5: what q:param type= accepts inside q:query (QueryValidator.validate_param).
QUERY_PARAM_TYPES = ('string', 'integer', 'decimal', 'boolean', 'datetime', 'date', 'time', 'array', 'json')


def check_param_type(where: str, ptype, allowed=PARAM_TYPES, exact: bool = False, element=None) -> None:
    """PARSE-5: an unknown q:param type is a parse error (the caller's line).

    It used to be accepted and then ignored (a form field of type "numbr" was
    text) — or, in a q:query, to fail only when the query ran. Types in a
    q:query are compared exactly, as QueryValidator does."""
    if ptype is not None and (ptype if exact else ptype.lower()) not in allowed:
        from quantum.core.parser import QuantumParseError
        error = QuantumParseError(f'{where} type="{ptype}" does not exist; type is one of: '
                                  f'{", ".join(allowed)}')
        error.line = getattr(element, 'sourceline', None)      # DEV-2: the q:param's own line
        raise error

_EMAIL = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_URL = re.compile(r'^https?://', re.IGNORECASE)


def is_uploaded_file(value: Any) -> bool:
    """An upload (a werkzeug FileStorage or equivalent).

    Checked by shape, not by import: werkzeug is optional, and an isinstance
    check would force importing it just to decide whether a value can become
    text.
    """
    return hasattr(value, 'filename') and hasattr(value, 'read')


def coerce(param_def, value: Any) -> Tuple[Any, Optional[str]]:
    """Returns (converted_value, error). The error is None when all is well."""
    ptype = (getattr(param_def, 'type', None) or 'string').lower()
    name = getattr(param_def, 'name', '?')

    if ptype in FILE_TYPES:
        if value is None or is_uploaded_file(value):
            return value, None
        return value, (
            f"Parameter '{name}' must be an uploaded file, got "
            f"{type(value).__name__}")

    # A file never becomes text or a number. Before, `str(value)` produced
    # the FileStorage's repr and the rest of the flow worked with that.
    if is_uploaded_file(value):
        return value, (
            f"Parameter '{name}' received an uploaded file but is declared "
            f"type=\"{ptype}\" — use type=\"file\"")

    if ptype in INT_TYPES:
        if isinstance(value, bool):
            return value, f"Parameter '{name}' must be an integer"
        if isinstance(value, int):
            return value, None
        try:
            return int(str(value).strip()), None
        except (TypeError, ValueError):
            return value, f"Parameter '{name}' must be an integer, got {value!r}"

    if ptype in FLOAT_TYPES:
        if isinstance(value, bool):
            return value, f"Parameter '{name}' must be a number"
        # Same rule as q:set type="number" (ERR-1): "30" is 30, "2.5" is 2.5.
        # float() made every form number a float, so "30" displayed as 30.0.
        number = coerce_number(value) if isinstance(value, str) else value
        if isinstance(number, (int, float)) and not isinstance(number, bool):
            return (float(number) if ptype in ('decimal', 'float', 'double') else number), None
        return value, f"Parameter '{name}' must be a number, got {value!r}"

    if ptype == 'boolean':
        if isinstance(value, bool):
            return value, None
        text = str(value).strip().lower()
        if text in ('true', 'yes', '1', 'on'):
            return True, None
        if text in ('false', 'no', '0', 'off', ''):
            return False, None
        return value, f"Parameter '{name}' must be a boolean, got {value!r}"

    if ptype == 'email':
        text = str(value)
        if not _EMAIL.match(text):
            return value, f"Parameter '{name}' must be a valid email"
        return text, None

    if ptype == 'url':
        text = str(value)
        if not _URL.match(text):
            return value, f"Parameter '{name}' must be a valid URL"
        return text, None

    return value, None


def check_rules(param_def, value: Any) -> List[str]:
    """min/max/minlength/maxlength/pattern/enum/range."""
    errors: List[str] = []
    name = getattr(param_def, 'name', '?')

    # No length, range or pattern makes sense on a file. What applies to an
    # upload is accept= (ACT-11).
    if is_uploaded_file(value):
        accept = getattr(param_def, 'accept', None)
        if accept and not accepts_file(value, accept):
            errors.append(f"Parameter '{name}' accepts {accept}; got "
                          f"'{getattr(value, 'filename', '')}'")
        max_size = getattr(param_def, 'maxsize', None)
        if max_size:
            # FILE-1: maxsize= was parsed and never checked.
            from quantum.runtime.file_upload_service import FileUploadService
            size = upload_size(value)
            if size > FileUploadService.parse_size(str(max_size)):
                measured = f"{size / 1048576:.1f}MB" if size >= 1048576 else f"{-(-size // 1024)}KB"
                errors.append(f"Parameter '{name}' must be at most {max_size}; "
                              f"'{getattr(value, 'filename', '')}' has {measured}")
        return errors

    minimum = getattr(param_def, 'min', None)
    maximum = getattr(param_def, 'max', None)
    if minimum is not None or maximum is not None:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = None
        if numeric is not None:
            for bound, comparison, word in (
                (minimum, lambda a, b: a < b, "at least"),
                (maximum, lambda a, b: a > b, "at most"),
            ):
                if bound is None:
                    continue
                try:
                    limit = float(bound)
                except (TypeError, ValueError):
                    continue
                if comparison(numeric, limit):
                    errors.append(
                        f"Parameter '{name}' must be {word} {bound} "
                        f"(got {value})")

    if isinstance(value, str):
        minlength = getattr(param_def, 'minlength', None)
        maxlength = getattr(param_def, 'maxlength', None)
        if minlength is not None and len(value) < minlength:
            errors.append(
                f"Parameter '{name}' must be at least {minlength} characters")
        if maxlength is not None and len(value) > maxlength:
            errors.append(
                f"Parameter '{name}' must be at most {maxlength} characters")
        pattern = getattr(param_def, 'pattern', None)
        if pattern:
            try:
                if not re.search(pattern, value):
                    errors.append(
                        f"Parameter '{name}' does not match {pattern!r}")
            except re.error as exc:
                logger.warning(
                    "q:param %s has an invalid pattern %r: %s",
                    name, pattern, exc)

    enum = getattr(param_def, 'enum', None)
    if enum:
        allowed = [v.strip() for v in str(enum).split(',') if v.strip()]
        if allowed and str(value) not in allowed:
            errors.append(
                f"Parameter '{name}' must be one of: {', '.join(allowed)}")

    # FN-1 / ACT-2: range= applied to q:function params only; an action's
    # accepted it and let any value through.
    value_range = getattr(param_def, 'range', None)
    if value_range:
        from quantum.runtime.validators import QuantumValidators
        valid, error = QuantumValidators.validate_range(value, str(value_range))
        if not valid:
            errors.append(f"Parameter '{name}': {error}")

    return errors


def upload_size(upload) -> int:
    """The size of an upload in bytes, without consuming it."""
    stream = getattr(upload, 'stream', upload)
    position = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(position)
    return size


def accepts_file(upload, accept: str) -> bool:
    """ACT-11: does an upload match an HTML-style accept list (".pdf", "image/*")?

    The Content-Type an upload declares comes from the browser, so a MIME
    pattern is matched against the type the FILE NAME implies as well: an
    .exe sent as image/png does not pass image/*. An extension pattern is
    matched against the file name.
    """
    import mimetypes
    filename = (getattr(upload, 'filename', '') or '').lower()
    by_name = (mimetypes.guess_type(filename)[0] or '').lower()
    declared = (getattr(upload, 'content_type', '') or '').split(';')[0].strip().lower()
    for item in (a.strip().lower() for a in accept.split(',') if a.strip()):
        if item.startswith('.'):
            if filename.endswith(item):
                return True
        elif item.endswith('/*'):
            base = item[:-1]
            if by_name.startswith(base) and (not declared or declared.startswith(base)):
                return True
        elif by_name == item and (not declared or declared == item):
            return True
    return False
