"""Edits values of a configuration YAML while preserving comments and order.

components/admin/settings.q rewrote quantum.config.yaml with yaml.dump: every
comment in the file vanished — including the security warnings about host and
debug —, and a write error was swallowed. With no ruamel.yaml in the project,
this editor covers the admin's case: first-level keys inside a section
(`server.port`), scalar values.

It never writes anything other than what was asked: after editing the text, it
re-reads the result with yaml.safe_load and checks that (1) each requested key
has the requested value and (2) everything else stays the same. If not, it
raises and the file stays as it was. The write is atomic.
"""

import copy
import os
import re
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml


class YamlEditError(RuntimeError):
    """The edit would not produce exactly the requested file; nothing was written."""


def _format(value: Any) -> str:
    text = yaml.safe_dump(value, default_flow_style=True, allow_unicode=True).strip()
    if text.endswith("..."):
        text = text[:-3].strip()
    return text


def edit_text(text: str, values: Dict[Tuple[str, str], Any]) -> str:
    lines = text.splitlines()
    for (section, key), value in values.items():
        start = next((i for i, l in enumerate(lines) if re.match(rf"^{re.escape(section)}\s*:\s*(#.*)?$", l)), None)
        if start is None:
            if lines and lines[-1].strip():
                lines.append("")
            lines.extend([f"{section}:", f"  {key}: {_format(value)}"])
            continue
        end = next((i for i in range(start + 1, len(lines))
                    if lines[i] and not lines[i].startswith((" ", "\t", "#"))), len(lines))
        children = [i for i in range(start + 1, end) if re.match(r"^(\s+)[^\s#]", lines[i])]
        indent = re.match(r"^(\s+)", lines[children[0]]).group(1) if children else "  "
        target = next((i for i in children if re.match(rf"^{re.escape(indent)}{re.escape(key)}\s*:", lines[i])), None)
        if target is None:
            lines.insert(start + 1, f"{indent}{key}: {_format(value)}")
            continue
        m = re.match(rf"^({re.escape(indent)}{re.escape(key)}\s*:\s*)(.*?)(\s+#.*)?$", lines[target])
        lines[target] = f"{m.group(1)}{_format(value)}{m.group(3) or ''}"
    return "\n".join(lines) + ("\n" if text.endswith("\n") or not text else "")


def write_values(file: Path, values: Dict[Tuple[str, str], Any]) -> Dict:
    """Applies `values` to the file (creating it if missing) and returns the resulting YAML."""
    file = Path(file)
    original = file.read_text(encoding="utf-8") if file.is_file() else ""
    before = yaml.safe_load(original) or {}
    if not isinstance(before, dict):
        raise YamlEditError(f"{file} does not contain a mapping")

    new_text = edit_text(original, values)
    try:
        after = yaml.safe_load(new_text) or {}
    except yaml.YAMLError as exc:
        raise YamlEditError(f"editing {file} would produce invalid YAML: {exc}") from exc

    expected = copy.deepcopy(before)
    for (section, key), value in values.items():
        if not isinstance(expected.get(section), dict):
            expected[section] = {}
        expected[section][key] = value
    if after != expected:
        raise YamlEditError(f"editing {file} would change more than was asked; nothing was written")

    temporary = file.with_name(file.name + ".tmp")
    temporary.write_text(new_text, encoding="utf-8")
    os.replace(temporary, file)
    return after
