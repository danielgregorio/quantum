"""UMA implementacao de `q:param`, usada pelos dois lugares que validam.

Havia duas, e elas discordavam.

`ComponentRuntime._coerce_param` (quantum/runtime/component.py) aceitava
`integer|int|long` e `number|numeric|decimal|float|double`, deixava
string/file/array/object como estavam e aplicava min/max a qualquer valor
que virasse numero. `ActionHandler._validate_type`
(quantum/runtime/action_handler.py) conhecia so `integer`, `decimal` e
`float`, e tudo o mais caia num `return str(value)` final. O mesmo

    <q:param name="idade" type="number" min="18" />

era um float com minimo checado dentro de um componente e a STRING "7" sem
checagem nenhuma dentro de um `q:action` — 32 arquivos .q do repositorio
usam `type="number"`, todos nessa situacao quando estao num action.

O caso pior era `type="file"`, que 5 arquivos entregues usam:

    <q:param name="avatar" type="file" required="true" />
    <q:file action="upload" file="{avatar}" destination="..." />

O `str(value)` final transformava o objeto de upload na sua repr —
`"<FileStorage: 'foto.png' ('image/png')>"` — e o `q:file` recebia essa
string no lugar do arquivo. Upload por formulario nao funcionava, e o
sintoma nao apontava para lugar nenhum.

Este modulo e a uniao das duas: a coercao do componente mais as validacoes
de `email`/`url` que so o action tinha, mais um tipo de arquivo que nunca e
convertido para texto.
"""

import logging
import re
from typing import Any, List, Optional, Tuple

logger = logging.getLogger('quantum.param')

INT_TYPES = ('integer', 'int', 'long')
FLOAT_TYPES = ('number', 'numeric', 'decimal', 'float', 'double')
FILE_TYPES = ('file', 'binary', 'upload')
# Tipos que passam intactos: converter mudaria dado que o destino espera
# receber como veio.
PASSTHROUGH_TYPES = ('string', 'text', 'array', 'object', 'any', 'json')

_EMAIL = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_URL = re.compile(r'^https?://', re.IGNORECASE)


def is_uploaded_file(value: Any) -> bool:
    """Um upload (werkzeug FileStorage ou equivalente).

    Checado por forma, nao por import: o werkzeug e opcional, e uma checagem
    por isinstance obrigaria a importa-lo so para decidir se um valor pode
    virar texto.
    """
    return hasattr(value, 'filename') and hasattr(value, 'read')


def coerce(param_def, value: Any) -> Tuple[Any, Optional[str]]:
    """Devolve (valor_convertido, erro). Erro None quando esta tudo bem."""
    ptype = (getattr(param_def, 'type', None) or 'string').lower()
    name = getattr(param_def, 'name', '?')

    if ptype in FILE_TYPES:
        if value is None or is_uploaded_file(value):
            return value, None
        return value, (
            f"Parameter '{name}' must be an uploaded file, got "
            f"{type(value).__name__}")

    # Um arquivo nunca vira texto nem numero. Antes, `str(value)` produzia a
    # repr do FileStorage e o resto do fluxo trabalhava com ela.
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
        if isinstance(value, (int, float)):
            return value, None
        try:
            return float(str(value).strip()), None
        except (TypeError, ValueError):
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
    """min/max/minlength/maxlength/pattern/enum."""
    errors: List[str] = []
    name = getattr(param_def, 'name', '?')

    # Nada de comprimento, faixa ou padrao faz sentido sobre um arquivo; as
    # regras de upload sao maxsize/accept, que o q:file aplica.
    if is_uploaded_file(value):
        return errors

    minimo = getattr(param_def, 'min', None)
    maximo = getattr(param_def, 'max', None)
    if minimo is not None or maximo is not None:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = None
        if numeric is not None:
            for bound, comparison, word in (
                (minimo, lambda a, b: a < b, "at least"),
                (maximo, lambda a, b: a > b, "at most"),
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

    return errors
