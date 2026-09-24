"""<ui:pager for="query"> — pages over a paginated query (M14, UI-11).

The query is `paginate="true"` (DB-2); its page is the URL's `page` parameter
(DB-9). The pager draws previous, the page numbers around the current one —
first and last always, a gap where pages are skipped — and next, as links to
the same page with the other URL parameters kept. The browser and the console
draw the same items.
"""

from typing import Dict, List, Optional
from urllib.parse import urlencode


def _pagination(renderer, node) -> dict:
    name = node.for_query
    try:
        result = renderer.context.get_variable(f'{name}_result')
    except Exception:
        result = None
    if isinstance(result, dict) and isinstance(result.get('pagination'), dict):
        return result['pagination']
    raise ValueError(
        f'<ui:pager for="{name}">: there is no paginated q:query named "{name}" on this page '
        f'(it needs paginate="true" and page_size) (UI-11)')


def _href(renderer, param: str, page: int) -> str:
    context = renderer.context
    path = (getattr(context, 'request_vars', None) or {}).get('path') or ''
    try:
        current = context.get_variable('query')
    except Exception:
        current = None
    params = {k: v for k, v in (current or {}).items() if k != param} if isinstance(current, dict) else {}
    params[param] = str(page)
    return f'{path}?{urlencode(params)}'


def pager_items(renderer, node) -> List[Dict]:
    """The pager's items: {'kind': prev|page|gap|next, 'label', 'href' (None if not a link), 'current'}."""
    pagination = _pagination(renderer, node)
    total = int(pagination.get('totalPages') or 0)
    current_page = int(pagination.get('currentPage') or 1)
    if total <= 1:
        return []
    window = max(0, int(node.window))
    pages = sorted({1, total} | set(range(max(1, current_page - window), min(total, current_page + window) + 1)))
    items: List[Dict] = [{'kind': 'prev', 'label': '‹', 'aria': 'Previous page',
                          'href': _href(renderer, node.param, current_page - 1) if current_page > 1 else None,
                          'current': False}]
    previous: Optional[int] = None
    for n in pages:
        if previous is not None and n > previous + 1:
            items.append({'kind': 'gap', 'label': '…', 'href': None, 'current': False, 'aria': ''})
        items.append({'kind': 'page', 'label': str(n), 'aria': f'Page {n}', 'current': n == current_page,
                      'href': None if n == current_page else _href(renderer, node.param, n)})
        previous = n
    items.append({'kind': 'next', 'label': '›', 'aria': 'Next page',
                  'href': _href(renderer, node.param, current_page + 1) if current_page < total else None,
                  'current': False})
    return items


PAGER_CSS = """
/* UI-11: <ui:pager> */
.q-pager { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; margin: 8px 0; }
.q-pager a, .q-pager span { min-width: 32px; padding: 4px 8px; text-align: center; border-radius: 6px;
  border: 1px solid var(--q-border, #d0d7de); text-decoration: none; color: inherit; }
.q-pager a:hover { background: var(--q-surface-hover, #f3f4f6); }
.q-pager .q-page-current { background: var(--q-primary, #2563eb); border-color: var(--q-primary, #2563eb); color: #fff; }
.q-pager .q-page-disabled { opacity: .45; }
.q-pager .q-page-gap { border: none; }
"""
