"""What the server works out for the `ui:*` tags beyond the layout set, once for every renderer (UI-21).

A renderer is told the meaning, never left to work it out: the initials of an avatar, which item of a
breadcrumb is the current one, the blocks of a Markdown text, the bars of a chart and their share, the rows
of a tree and the lines drawn beside them, the last lines of a log. The view tree (ui_view.py) sends these;
the browser's page (ui_page_renderer.py) draws its HTML from the same functions, so both say the same.

A tag that is a composition of the Core set is sent with `as`, the Core kind a renderer draws it as (a
breadcrumb is a row of links, a date picker is a date field); one that is not (a chart, a tree, an avatar,
a skeleton, a loading mark) is a kind of its own, with its data worked out here.
"""

from __future__ import annotations

import html
import math
import re
from typing import Any, Dict, List, Optional, Tuple

# -- an avatar -----------------------------------------------------------------

AVATAR_STATUSES = ('online', 'away', 'busy', 'offline')


def initials(name: Optional[str]) -> str:
    """The first letters of the first two words of a name, in capitals; '?' with no name."""
    words = [w for w in re.split(r'\s+', str(name or '').strip()) if w]
    return ''.join(w[0].upper() for w in words[:2]) or '?'


# -- a breadcrumb --------------------------------------------------------------

def breadcrumb(items: List[Dict[str, Any]], separator: str) -> List[Dict[str, Any]]:
    """A breadcrumb's children as view nodes: a link for each item with a `to` but the last, the last (or
    one without `to`) as the current page's text, the separator between them."""
    children: List[Dict[str, Any]] = []
    for n, item in enumerate(items):
        if n:
            children.append({'type': 'text', 'props': {'text': separator or '/', 'muted': True}, 'children': []})
        last = n == len(items) - 1
        if item.get('to') and not last:
            children.append({'type': 'link', 'props': {'to': item['to'], 'text': item['label']}, 'children': []})
        else:
            children.append({'type': 'text', 'props': {'text': item['label'], 'current': True, 'weight': 'bold'},
                             'children': []})
    return children


# -- Markdown --------------------------------------------------------------------
#
# The part of Markdown a page's text needs: headings, paragraphs, lists (one level), code (fenced or
# indented), quotes, rules; inline **bold**, *italic*, `code` and [links](to). Each block is a dict:
#   {'kind': 'heading', 'level': 1..6, 'spans': [...]}     {'kind': 'paragraph', 'spans': [...]}
#   {'kind': 'list', 'ordered': bool, 'start': int, 'items': [[spans], ...]}
#   {'kind': 'code', 'text': str, 'lang': str}              {'kind': 'quote', 'spans': [...]}
#   {'kind': 'rule'}
# and a span is {'text': str} with any of 'bold', 'italic', 'code' (True) and 'to' (a link's target).

_HEADING = re.compile(r'^(#{1,6})\s+(.*?)\s*#*\s*$')
_RULE = re.compile(r'^\s{0,3}([-*_])(\s*\1){2,}\s*$')
_BULLET = re.compile(r'^\s{0,3}[-*+]\s+(.*)$')
_NUMBER = re.compile(r'^\s{0,3}(\d{1,9})[.)]\s+(.*)$')
_QUOTE = re.compile(r'^\s{0,3}>\s?(.*)$')
_FENCE = re.compile(r'^\s{0,3}(```|~~~)\s*([\w+-]*)\s*$')
_INLINE = re.compile(r'(\\[\\`*_\[\]()#+\-.!>])'                # an escaped sign
                     r'|(`+)(.+?)\2'                              # code
                     r'|\*\*(.+?)\*\*|__(.+?)__'                  # bold
                     r'|\*(?!\s)(.+?)(?<!\s)\*|(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)'   # italic
                     r'|\[([^\]]+)\]\(([^)\s]+)\)')               # a link


def spans(text: str, style: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """The inline spans of a line of Markdown; neighbours of the same style are joined."""
    style = dict(style or {})
    out: List[Dict[str, Any]] = []
    at = 0
    for m in _INLINE.finditer(text):
        if m.start() > at:
            out.append({**style, 'text': text[at:m.start()]})
        escaped, _ticks, code, bold1, bold2, em1, em2, label, to = m.groups()
        if escaped:
            out.append({**style, 'text': escaped[1]})
        elif code is not None:
            out.append({**style, 'code': True, 'text': code.strip()})
        elif bold1 is not None or bold2 is not None:
            out.extend(spans(bold1 if bold1 is not None else bold2, {**style, 'bold': True}))
        elif em1 is not None or em2 is not None:
            out.extend(spans(em1 if em1 is not None else em2, {**style, 'italic': True}))
        else:
            out.extend(spans(label, {**style, 'to': to}))
        at = m.end()
    if at < len(text):
        out.append({**style, 'text': text[at:]})
    joined: List[Dict[str, Any]] = []
    for span in out:
        if joined and _style(joined[-1]) == _style(span):
            joined[-1]['text'] += span['text']
        elif span['text']:
            joined.append(span)
    return joined


def _style(span: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in span.items() if k != 'text'}


def plain(span_list: List[Dict[str, Any]]) -> str:
    return ''.join(s['text'] for s in span_list)


def markdown_blocks(text: str) -> List[Dict[str, Any]]:
    """The blocks of a Markdown text (see above). Indentation common to every line is taken off first, as a
    `.q` file indents the text inside its element."""
    lines = _dedent(str(text or '')).split('\n')
    blocks: List[Dict[str, Any]] = []
    paragraph: List[str] = []

    def end_paragraph() -> None:
        if paragraph:
            blocks.append({'kind': 'paragraph', 'spans': spans(' '.join(p.strip() for p in paragraph))})
            paragraph.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        fence = _FENCE.match(line)
        if fence:
            end_paragraph()
            body = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(fence.group(1)):
                body.append(lines[i])
                i += 1
            blocks.append({'kind': 'code', 'text': '\n'.join(body), 'lang': fence.group(2)})
            i += 1
            continue
        if not line.strip():
            end_paragraph()
            i += 1
            continue
        if line.startswith('    ') and not paragraph:
            body = []
            while i < len(lines) and (lines[i].startswith('    ') or not lines[i].strip()):
                body.append(lines[i][4:])
                i += 1
            blocks.append({'kind': 'code', 'text': '\n'.join(body).rstrip('\n'), 'lang': ''})
            continue
        heading = _HEADING.match(line)
        if heading:
            end_paragraph()
            blocks.append({'kind': 'heading', 'level': len(heading.group(1)), 'spans': spans(heading.group(2))})
            i += 1
            continue
        if _RULE.match(line):
            end_paragraph()
            blocks.append({'kind': 'rule'})
            i += 1
            continue
        if _QUOTE.match(line):
            end_paragraph()
            body = []
            while i < len(lines) and _QUOTE.match(lines[i]):
                body.append(_QUOTE.match(lines[i]).group(1).strip())
                i += 1
            blocks.append({'kind': 'quote', 'spans': spans(' '.join(b for b in body if b))})
            continue
        bullet, number = _BULLET.match(line), _NUMBER.match(line)
        if bullet or number:
            end_paragraph()
            ordered = number is not None
            items: List[List[str]] = []
            while i < len(lines):
                b, n = _BULLET.match(lines[i]), _NUMBER.match(lines[i])
                if (b and not ordered) or (n and ordered):
                    items.append([(n.group(2) if ordered else b.group(1)).strip()])
                elif lines[i].strip() and items and lines[i].startswith((' ', '\t')):
                    items[-1].append(lines[i].strip())             # the item goes on
                else:
                    break
                i += 1
            blocks.append({'kind': 'list', 'ordered': ordered, 'start': int(number.group(1)) if ordered else 1,
                           'items': [spans(' '.join(parts)) for parts in items]})
            continue
        paragraph.append(line)
        i += 1
    end_paragraph()
    return blocks


def _dedent(text: str) -> str:
    lines = text.expandtabs(4).split('\n')
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    margins = [len(line) - len(line.lstrip(' ')) for line in lines if line.strip()]
    if len(margins) > 1 and margins[0] == 0 and min(margins[1:]) > 0:
        # `<ui:markdown># Title` and then indented lines: the first line began right after the tag
        cut = min(margins[1:])
        return '\n'.join([lines[0], *(line[cut:] for line in lines[1:])])
    cut = min(margins) if margins else 0
    return '\n'.join(line[cut:] for line in lines)


def _text_node(span_list: List[Dict[str, Any]], **props) -> Dict[str, Any]:
    node_props = {'text': plain(span_list), **props}
    if any(set(s) - {'text'} for s in span_list):
        node_props['spans'] = span_list
    return {'type': 'text', 'props': node_props, 'children': []}


def markdown_view(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The blocks as view nodes of the Core set: a heading is a bold text with its level, a paragraph a text
    with its spans, a list a ui:list, code a text marked `code`, a quote a text marked `quote`, a rule a rule."""
    view: List[Dict[str, Any]] = []
    for block in blocks:
        kind = block['kind']
        if kind == 'heading':
            view.append(_text_node(block['spans'], heading=block['level'], weight='bold'))
        elif kind == 'paragraph':
            view.append(_text_node(block['spans']))
        elif kind == 'quote':
            view.append(_text_node(block['spans'], quote=True))
        elif kind == 'code':
            view.append({'type': 'text', 'props': {'text': block['text'], 'code': True}, 'children': []})
        elif kind == 'rule':
            view.append({'type': 'rule', 'props': {}, 'children': []})
        elif kind == 'list':
            items = []
            for n, item in enumerate(block['items']):
                marker = f"{block['start'] + n}." if block['ordered'] else None
                items.append({'type': 'item', 'props': {'marker': marker} if marker else {},
                              'children': [_text_node(item)]})
            view.append({'type': 'list', 'props': {'ordered': True} if block['ordered'] else {}, 'children': items})
    return view


def safe_link(to: str) -> Optional[str]:
    """A link's target when it is one a page may hold — http, https, mailto, or a path with no scheme —
    else None, and the text is drawn without the link (a `javascript:` target is never a link)."""
    to = (to or '').strip()
    if re.match(r'^(https?|mailto):', to, re.IGNORECASE):
        return to
    head = re.split(r'[/?#]', to, maxsplit=1)[0]
    return to if to and ':' not in head else None


def spans_html(span_list: List[Dict[str, Any]]) -> str:
    out = []
    for s in span_list:
        piece = html.escape(s['text'])
        if s.get('code'):
            piece = f'<code>{piece}</code>'
        if s.get('italic'):
            piece = f'<em>{piece}</em>'
        if s.get('bold'):
            piece = f'<strong>{piece}</strong>'
        to = safe_link(s['to']) if s.get('to') else None
        if to:
            piece = f'<a href="{html.escape(to, quote=True)}">{piece}</a>'
        out.append(piece)
    return ''.join(out)


def markdown_html(blocks: List[Dict[str, Any]]) -> str:
    """The blocks in HTML, every text escaped (a Markdown text may come from the data)."""
    out = []
    for block in blocks:
        kind = block['kind']
        if kind == 'heading':
            out.append(f"<h{block['level']}>{spans_html(block['spans'])}</h{block['level']}>")
        elif kind == 'paragraph':
            out.append(f"<p>{spans_html(block['spans'])}</p>")
        elif kind == 'quote':
            out.append(f"<blockquote>{spans_html(block['spans'])}</blockquote>")
        elif kind == 'code':
            code = html.escape(block['text']).replace('\n', '&#10;')      # one line: the page indents lines
            out.append(f"<pre><code>{code}</code></pre>")
        elif kind == 'rule':
            out.append('<hr>')
        elif kind == 'list':
            tag = 'ol' if block['ordered'] else 'ul'
            start = f' start="{block["start"]}"' if block['ordered'] and block['start'] != 1 else ''
            items = ''.join(f'<li>{spans_html(item)}</li>' for item in block['items'])
            out.append(f'<{tag}{start}>{items}</{tag}>')
    return '\n'.join(out)


# -- a chart ---------------------------------------------------------------------

CHART_TYPES = ('bar', 'line', 'pie', 'doughnut')
# The series' colours when the chart names none: the design tokens' order (ui_html_templates.CSS_THEME).
CHART_COLORS = ('primary', 'success', 'warning', 'danger', 'info', 'secondary')


def _number(value: Any, where: str) -> float:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f'{where}: "{value}" is not a number (UI-21)') from None
    if math.isnan(number) or math.isinf(number):
        raise ValueError(f'{where}: "{value}" is not a number (UI-21)')
    return number


def _shown(number: float) -> str:
    return str(int(number)) if number == int(number) else f'{number:g}'


def chart_bars(chart_type: str, labels: Any, values: Any, colors: Any = None,
               rows: Optional[list] = None) -> List[Dict[str, Any]]:
    """The bars of a chart, one per label: {'label', 'value', 'shown', 'percent', 'color'}. `percent` is of
    the largest value for a bar or a line chart and of the total for a pie or a doughnut, so every renderer
    draws the same lengths. The data is `labels` and `values` (lists, or text with commas) or the chart's
    `source` rows (dicts with `label` and `value`, or pairs)."""
    where = f'<ui:chart type="{chart_type}">'
    if chart_type not in CHART_TYPES:
        raise ValueError(f'{where}: the type is one of {", ".join(CHART_TYPES)} (UI-21)')
    if rows is not None:
        pairs = []
        for row in rows:
            if isinstance(row, dict):
                if 'label' not in row or 'value' not in row:
                    raise ValueError(f'{where} source: each row needs a `label` and a `value` (UI-21); got '
                                     f'{", ".join(map(str, row)) or "an empty row"}')
                pairs.append((row['label'], row['value']))
            elif isinstance(row, (list, tuple)) and len(row) == 2:
                pairs.append((row[0], row[1]))
            else:
                raise ValueError(f'{where} source: each row is a `label` and a `value` (UI-21)')
        names = [str(label) for label, _ in pairs]
        numbers = [_number(v, where) for _, v in pairs]
    else:
        names = _list(labels)
        numbers = [_number(v, where) for v in _list(values)]
        if len(names) != len(numbers):
            raise ValueError(f'{where}: {len(names)} labels and {len(numbers)} values (UI-21)')
    if any(n < 0 for n in numbers) and chart_type in ('pie', 'doughnut'):
        raise ValueError(f'{where}: a share cannot be negative (UI-21)')
    whole = sum(numbers) if chart_type in ('pie', 'doughnut') else max([abs(n) for n in numbers] or [0])
    palette = _list(colors)
    bars = []
    for n, (label, number) in enumerate(zip(names, numbers)):
        bars.append({'label': label, 'value': number, 'shown': _shown(number),
                     'percent': round(100 * abs(number) / whole, 1) if whole else 0.0,
                     'color': palette[n] if n < len(palette) else CHART_COLORS[n % len(CHART_COLORS)]})
    return bars


def _list(value: Any) -> List[str]:
    if value is None or value == '':
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value]
    return [v.strip() for v in str(value).split(',') if v.strip()]


# -- a tree ----------------------------------------------------------------------

def tree_rows(nodes: list, where: str = '<ui:tree>') -> List[Dict[str, Any]]:
    """A tree's rows, depth first: {'label', 'value', 'to', 'depth', 'last', 'lines'}. A node is a dict with
    a `label` (and a `value`, a `to`, `children`) or a text. `lines` says, for each level above the row,
    whether a line goes on down beside it (its ancestor at that level has a sibling after it) — what a
    renderer draws the guides with."""
    rows: List[Dict[str, Any]] = []

    def walk(items: list, depth: int, lines: List[bool]) -> None:
        if not isinstance(items, list):
            raise ValueError(f'{where} source: the children of a node are a list (UI-21)')
        for n, item in enumerate(items):
            last = n == len(items) - 1
            if isinstance(item, dict):
                if 'label' not in item:
                    raise ValueError(f'{where} source: each node needs a `label` (UI-21)')
                label, children = str(item['label']), item.get('children') or []
                value, to = item.get('value', item['label']), item.get('to')
            else:
                label, children, value, to = str(item), [], str(item), None
            rows.append({'label': label, 'value': '' if value is None else str(value), 'to': to,
                         'depth': depth, 'last': last, 'lines': list(lines)})
            walk(children, depth + 1, [*lines, not last] if depth else lines)

    walk(nodes, 0, [])
    return rows


def tree_guides(row: Dict[str, Any], ascii_only: bool = False) -> str:
    """The guides drawn before a row in cells of text: a line for each level that goes on, then the
    branch to the row (none for a row at the top)."""
    if not row['depth']:
        return ''
    on, off, mid, end = ('|  ', '   ', '|- ', '`- ') if ascii_only else ('│  ', '   ', '├─ ', '└─ ')
    return ''.join(on if line else off for line in row['lines']) + (end if row['last'] else mid)


# -- a log -----------------------------------------------------------------------

def log_lines(text: Any, rows: Optional[list], max_lines: Optional[int]) -> List[str]:
    """A log's lines: the element's text, a line each, then the `source` rows (a list of texts, or one
    text); only the last `max_lines` when it says how many — the end is what a log shows."""
    lines = [line.rstrip() for line in _dedent(str(text or '')).split('\n') if line.strip()] if text else []
    for row in rows or []:
        lines.extend(str(row).rstrip('\n').split('\n'))
    if max_lines and max_lines > 0:
        lines = lines[-int(max_lines):]
    return lines


# -- a pagination ------------------------------------------------------------------

def page_count(total: Any, page_size: Any, where: str = '<ui:pagination>') -> int:
    total_n, size = _number(total or 0, f'{where} total'), _number(page_size or 10, f'{where} page-size')
    if size <= 0:
        raise ValueError(f'{where}: page-size is more than 0 (UI-21)')
    return max(1, math.ceil(total_n / size))


# -- each tag's meaning, from its node and the page ---------------------------------------
#
# The view tree and the browser's page both start here, so what one draws the other draws.

def truthy(value: Any) -> bool:
    """A page's yes: true, 1, on, yes (and a value Python takes as true)."""
    if isinstance(value, str):
        return value.strip().lower() in ('true', '1', 'on', 'yes', 'checked')
    return bool(value)


# What a standalone build (UI-8) runs in its own script and a page cannot: in a page the state is the
# renderer's own (which slide, which step), and an action is posted by a button or a form.
_STANDALONE = {
    'on_change': 'on-change', 'on_complete': 'on-complete', 'on_close': 'on-close', 'bind': 'bind',
}


def modal_open(page, node) -> bool:
    """Whether a modal is open as the page is drawn: `open`, true or an expression that is."""
    value = node.open
    if isinstance(value, str):
        value = page._apply_databinding(value) if '{' in value else value
    return truthy(value)


def page_only_attrs(node, where: str, names) -> None:
    """UI-21: an attribute that calls the standalone build's script is an error in a page, named."""
    for name in names:
        if getattr(node, name, None):
            raise ValueError(f'<{where} {_STANDALONE[name]}=...> calls the standalone build\'s script (UI-8); '
                             f'in a page it moves by itself in every renderer, and an action is a button\'s '
                             f'or a form\'s (UI-21)')


def _value(page, text: Any) -> Any:
    """An attribute with its `{expression}`s resolved: the value itself when it is one expression (a list
    stays a list), else the text."""
    if isinstance(text, str) and '{' in text:
        return page._apply_databinding(text)
    return text


def _text(page, text: Any) -> str:
    value = _value(page, text)
    return '' if value is None else str(value)


def _rows(page, source: Optional[str], where: str) -> Optional[list]:
    if not source:
        return None
    rows = _value(page, source)
    if isinstance(rows, (list, tuple)):
        return list(rows)
    raise ValueError(f'<{where} source="{source}"> needs a list — a q:query or an array, as source="{{rows}}" '
                     f'— and got {"no {expression}" if rows == source else type(rows).__name__} (UI-21)')


def breadcrumb_items(page, node) -> List[Dict[str, Any]]:
    from quantum.core.features.ui_engine.src.ast_nodes import UIBreadcrumbItemNode
    return [{'label': _text(page, c.label), 'to': _text(page, c.to) or None}
            for c in node.children if isinstance(c, UIBreadcrumbItemNode)]


def chart_of(page, node) -> List[Dict[str, Any]]:
    rows = _rows(page, node.source, 'ui:chart')
    return chart_bars(_text(page, node.chart_type) or 'bar', _value(page, node.labels), _value(page, node.values),
                      _value(page, node.colors), rows)


def tree_of(page, node) -> List[Dict[str, Any]]:
    rows = _rows(page, node.source, 'ui:tree')
    if rows is None:
        raise ValueError('<ui:tree> needs source="{nodes}": a list of nodes, each a `label` with its '
                         '`children` (UI-21)')
    return tree_rows(rows)


def log_of(page, node) -> List[str]:
    rows = None
    if getattr(node, 'source', None):
        value = _value(page, node.source)
        rows = [value] if isinstance(value, str) and value != node.source else _rows(page, node.source, 'ui:log')
    return log_lines(_text(page, getattr(node, 'content', '')), rows, node.max_lines)


def pagination_of(page, node) -> Dict[str, Any]:
    """{'param', 'pages', 'current', 'total', 'items'}: the page is the URL's `bind` parameter (`page` when it
    names none), else `current`; the items are the pager's (UI-11)."""
    from quantum.runtime.ui_pager import page_items
    if node.on_change:
        raise ValueError('<ui:pagination on-change=...>: in a page the page number is the URL\'s parameter '
                         f'("{node.bind or "page"}"), as for ui:pager; the page reads it as '
                         f'{{query.{node.bind or "page"}}} (UI-21)')
    param = _text(page, node.bind) or 'page'
    total = _text(page, node.total) or '0'
    pages = page_count(total, _text(page, node.page_size) or '10')
    try:
        query = page.context.get_variable('query')
    except Exception:
        query = None
    asked = query.get(param) if isinstance(query, dict) else None
    try:
        current = int(str(asked if asked not in (None, '') else (_text(page, node.current) or '1')))
    except ValueError:
        current = 1
    current = min(max(1, current), pages)
    return {'param': param, 'pages': pages, 'current': current, 'total': _shown(_number(total, '<ui:pagination>')),
            'items': page_items(page, param, pages, current)}


# -- the browser's look for what the CSS theme did not have ---------------------------------

MORE_CSS = """
/* UI-21 */
.q-markdown > :first-child { margin-top: 0; }
.q-markdown blockquote { margin: 8px 0; padding-left: 12px; border-left: 3px solid var(--q-border); color: var(--q-secondary); }
.q-markdown pre { background: var(--q-light); padding: 8px 12px; border-radius: var(--q-radius); overflow-x: auto; }
.q-markdown code { font-family: 'SF Mono', 'Fira Code', monospace; font-size: .92em; }
.q-markdown ul { list-style: disc; padding-left: 20px; }
.q-markdown ol { list-style: decimal; padding-left: 20px; }
.q-tree { display: flex; flex-direction: column; font-size: var(--q-font-sm); }
.q-tree-item { display: flex; align-items: baseline; }
.q-tree-guides { font-family: 'SF Mono', 'Fira Code', monospace; color: var(--q-secondary); white-space: pre; }
.q-tree-item form { display: inline; }
.q-tree-item button, .q-menu button { background: none; border: none; padding: 0; font: inherit; color: var(--q-primary); cursor: pointer; }
.q-menu form { display: inline; }
.q-menu .q-menu-item { display: inline-block; padding: 4px 8px; }
.q-chart--line svg { display: block; max-width: 100%; }
.q-chart-track { flex: 1; min-width: 0; }
.q-chart--bar .q-chart-bar-group > .q-chart-label { flex: none; }
.q-chart-legend { display: flex; flex-wrap: wrap; gap: 4px 16px; margin-top: 8px; font-size: var(--q-font-sm); }
.q-chart-legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; }
.q-log { white-space: pre-wrap; margin: 0; }
.q-pager .q-pager-total { border: none; color: var(--q-secondary); }
.q-pager form { display: inline-flex; }
.q-pager input { width: 64px; }
.q-accordion-item { border: 1px solid var(--q-border); border-radius: var(--q-radius); margin-bottom: 4px; }
.q-accordion-title { cursor: pointer; padding: 8px 12px; font-weight: 600; }
.q-accordion-body { padding: 0 12px 8px; }
details.q-dropdown > summary { list-style: none; }
details.q-dropdown > summary::-webkit-details-marker { display: none; }
details.q-dropdown[open] .q-dropdown-menu { display: block; }
.q-dropdown-menu form { display: block; }
.q-tooltip-wrapper:focus-within .q-tooltip-text { visibility: visible; opacity: 1; }
.q-carousel-slide:not(.active) { visibility: hidden; }
"""


def css_color(color: str) -> str:
    """A chart colour for CSS: a design token's name is its custom property."""
    color = str(color or '').strip()
    if color in CHART_COLORS:
        return f'var(--q-{color})'
    return color if re.fullmatch(r'#[0-9a-fA-F]{3,8}|[a-zA-Z]+|(rgb|hsl)a?\([\d\s.,%]+\)', color) else 'var(--q-primary)'


def chart_html(chart_type: str, title: str, bars: List[Dict[str, Any]]) -> str:
    """A chart in HTML: bars as rows, a line as an SVG polyline over the labels, a pie or a doughnut as a
    conic gradient with its legend. Every text is escaped."""
    esc = html.escape
    # q-chart--TYPE: `q-chart-bar` is one bar's class (24 px tall), and a bar chart that wore it was squashed
    out = [f'<div class="q-chart q-chart--{esc(chart_type)}" role="img" '
           f'aria-label="{esc(title or chart_type + " chart", quote=True)}">']
    if title:
        out.append(f'<div class="q-chart-title">{esc(title)}</div>')
    if chart_type == 'bar':
        out.append('<div class="q-chart-container">')
        for bar in bars:
            # the bar's width is a share of its track, the room the label leaves
            out.append(f'<div class="q-chart-bar-group"><div class="q-chart-label">{esc(bar["label"])}</div>'
                       f'<div class="q-chart-track"><div class="q-chart-bar" '
                       f'style="width:{bar["percent"]}%;background:{css_color(bar["color"])}">'
                       f'<span class="q-chart-value">{esc(bar["shown"])}</span></div></div></div>')
        out.append('</div>')
    elif chart_type == 'line':
        w, h, pad = 320, 120, 8
        top = max([b['value'] for b in bars] or [0])
        low = min([b['value'] for b in bars] + [0])
        span = (top - low) or 1
        step = (w - 2 * pad) / max(1, len(bars) - 1)
        points = ' '.join(f'{pad + n * step:.1f},{h - pad - (b["value"] - low) / span * (h - 2 * pad):.1f}'
                          for n, b in enumerate(bars))
        color = css_color(bars[0]['color']) if bars else 'var(--q-primary)'
        out.append(f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
                   f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{points}"/>')
        for n, b in enumerate(bars):
            x, y = points.split(' ')[n].split(',')
            out.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{color}"><title>{esc(b["label"])}: '
                       f'{esc(b["shown"])}</title></circle>')
        out.append('</svg><div class="q-chart-legend">')
        out.extend(f'<span>{esc(b["label"])} {esc(b["shown"])}</span>' for b in bars)
        out.append('</div>')
    else:
        stops, at = [], 0.0
        for b in bars:
            stops.append(f'{css_color(b["color"])} {at:.1f}% {at + b["percent"]:.1f}%')
            at += b['percent']
        hole = ('radial-gradient(circle, var(--q-bg, #fff) 0 38%, transparent 39%), '
                if chart_type == 'doughnut' else '')
        out.append(f'<div style="width:120px;height:120px;border-radius:50%;'
                   f'background:{hole}conic-gradient({", ".join(stops) or "var(--q-light) 0 100%"})"></div>')
        out.append('<div class="q-chart-legend">')
        out.extend(f'<span><i style="background:{css_color(b["color"])}"></i>{esc(b["label"])} '
                   f'{b["percent"]:g}%</span>' for b in bars)
        out.append('</div>')
    out.append('</div>')
    return ''.join(out)


# -- a page's ui:theme -------------------------------------------------------------------

def theme_tokens(node) -> Dict[str, str]:
    """A ui:theme's colours: its preset's (light, dark), with its ui:color children over them."""
    from quantum.core.features.theming.src.presets import THEME_LIGHT, get_theme_preset
    tokens = dict(get_theme_preset(node.preset or 'light') or THEME_LIGHT)
    for color in getattr(node, 'colors', None) or []:
        if color.name and color.value:
            tokens[color.name] = color.value
    return tokens


def page_theme(statements) -> Optional[Dict[str, str]]:
    """UI-21: the colours of the page's ui:theme (the first one), or None when it has none."""
    from quantum.core.features.theming.src.ast_node import UIThemeNode
    for node in statements or []:
        if isinstance(node, UIThemeNode):
            return theme_tokens(node)
    return None


def theme_css(tokens: Dict[str, str]) -> str:
    """The colours as the page's CSS variables, over the theme's defaults (`html:root` outranks `:root`)."""
    safe = {k: v for k, v in tokens.items()
            if re.fullmatch(r'[a-z][a-z0-9-]*', k) and re.fullmatch(r'[#\w(),.%\s-]+', str(v))}
    body = ' '.join(f'--q-{k}: {v};' for k, v in safe.items())
    return f'<style data-quantum-theme>html:root {{ {body} }}</style>'


# -- a calendar ----------------------------------------------------------------------------

MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
          'October', 'November', 'December')


def calendar_field(node, ctx) -> Tuple[Any, Optional[str]]:
    """UI-9, UI-21: a calendar in a form is one of its fields: the value sent comes back in it (or the row's, in an
    edit form) and so does its field's error. A value sent that is not a date is not shown (its q:param says why)."""
    import datetime
    from quantum.runtime.ui_form_rules import prepare_field
    field, error = prepare_field(node, ctx, escape=False)
    if field is not node and field.value != node.value:
        try:
            field.value = datetime.date.fromisoformat(str(field.value or '').strip()[:10]).isoformat()
        except ValueError:
            field.value = None
    return field, error


def calendar_of(page, node) -> Dict[str, Any]:
    """UI-21: a calendar in a page is a date field shown as a month: {bind, value, month, min, max,
    disabled_dates, disabled_days, first_day, week_numbers}. The month shown first is the value's, else
    today's; picking a day sets the field, which its form sends under `bind`."""
    import datetime
    page_only_attrs(node, 'ui:calendar', ('on_change',))
    if getattr(node, 'on_month_change', None):
        raise ValueError('<ui:calendar on-month-change=...> calls the standalone build\'s script (UI-8); in a '
                         'page the month moves by itself in every renderer (UI-21)')
    mode = _text(page, node.mode) or 'single'
    if mode != 'single':
        raise ValueError(f'<ui:calendar mode="{mode}">: a page\'s calendar picks one date (mode="single"); '
                         f'a range or several dates are the standalone build\'s (UI-21)')

    def iso(text) -> str:
        text = _text(page, text).strip()
        if not text:
            return ''
        try:
            return datetime.date.fromisoformat(text).isoformat()
        except ValueError:
            raise ValueError(f'<ui:calendar>: "{text}" is not a date (YYYY-MM-DD) (UI-21)') from None

    value = iso(node.value)
    shown = datetime.date.fromisoformat(value) if value else datetime.date.today()
    days = [int(d) for d in _list(_value(page, node.disabled_days)) if str(d).strip().lstrip('-').isdigit()]
    return {'bind': _text(page, node.bind), 'value': value, 'month': shown.strftime('%Y-%m'),
            'min': iso(node.min_date), 'max': iso(node.max_date),
            'disabled_dates': [iso(d) for d in _list(_value(page, node.disabled_dates))],
            'disabled_days': [d % 7 for d in days],
            'first_day': int(_text(page, node.first_day_of_week) or 0) % 7,
            'week_numbers': truthy(_value(page, node.show_week_numbers))}
