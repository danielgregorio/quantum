"""What happens to a rendered page before it is sent: inline assets extracted to cached files, HTML prettified, hot reload and htmx injected.

Part of QuantumWebServer (web_server.py), as a mixin."""

import hashlib
import os
import re
import threading
from html import escape as html_escape
from pathlib import Path


def _write_asset(path: str, text: str) -> None:
    """Writes an extracted stylesheet or script so that it appears whole or not at all.

    The file's name is its content's hash, and a page links it as soon as the
    file exists. Written in place, it existed empty while it was being written:
    a second request in that moment linked it, and its browser got an empty
    stylesheet — an unstyled page, cached under a name that never changes.
    """
    temporary = f'{path}.{os.getpid()}.{threading.get_ident()}.tmp'
    with open(temporary, 'w', encoding='utf-8') as f:
        f.write(text)
    try:
        os.replace(temporary, path)
    except PermissionError:
        # Windows: another request wrote the same file (same name, same content)
        # and a browser is reading it. That file is already the one we meant.
        os.remove(temporary)
        if not os.path.exists(path):
            raise


class HtmlPostProcessing:
    def _get_static_dir(self) -> str:
        """Resolve and ensure the static directory exists."""
        static_dir = self.config['paths']['static']
        if not os.path.isabs(static_dir):
            static_dir = os.path.abspath(static_dir)
        os.makedirs(static_dir, exist_ok=True)
        return static_dir

    def _extract_inline_assets(self, html: str) -> str:
        """
        Extract inline <style> and <script> blocks to external files.

        Replaces inline CSS with <link rel="stylesheet"> and inline JS
        (without src attribute) with <script src="...">.

        Args:
            html: Full HTML document string

        Returns:
            HTML with inline assets replaced by external file references
        """
        static_dir = self._get_static_dir()

        # --- Extract CSS ---
        style_pattern = re.compile(r'<style[^>]*>(.*?)</style>', re.DOTALL | re.IGNORECASE)
        css_matches = style_pattern.findall(html)

        if css_matches:
            all_css = '\n'.join(css_matches)
            css_hash = hashlib.md5(all_css.encode()).hexdigest()[:10]
            css_filename = f'styles-{css_hash}.css'
            css_path = os.path.join(static_dir, css_filename)

            if not os.path.exists(css_path):
                _write_asset(css_path, all_css)

            html = style_pattern.sub('', html)

            # Root-relative on purpose. A bare "static/..." is resolved
            # against the current path, so a page at /admin/projects asked for
            # /admin/static/... and rendered with no CSS at all — silently,
            # since a 404 on a stylesheet does not fail the page.
            link_tag = f'<link rel="stylesheet" href="/static/{css_filename}">'
            if '</head>' in html:
                html = html.replace('</head>', f'    {link_tag}\n  </head>', 1)
            elif '</HEAD>' in html:
                html = html.replace('</HEAD>', f'    {link_tag}\n  </HEAD>', 1)

        # --- Extract inline JS (skip <script src="..."> tags) ---
        script_pattern = re.compile(
            r'<script(?![^>]*\bsrc\b)[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE
        )
        js_matches = script_pattern.findall(html)

        if js_matches:
            all_js = '\n'.join(m.strip() for m in js_matches)
            js_hash = hashlib.md5(all_js.encode()).hexdigest()[:10]
            js_filename = f'scripts-{js_hash}.js'
            js_path = os.path.join(static_dir, js_filename)

            if not os.path.exists(js_path):
                _write_asset(js_path, all_js)

            html = script_pattern.sub('', html)

            # Root-relative — same reason as the stylesheet above.
            script_tag = f'<script src="/static/{js_filename}"></script>'
            if '</body>' in html:
                html = html.replace('</body>', f'    {script_tag}\n  </body>', 1)
            elif '</BODY>' in html:
                html = html.replace('</BODY>', f'    {script_tag}\n  </BODY>', 1)

        return html

    def _prettify_html(self, html: str) -> str:
        """
        Pretty-print HTML with indentation for readable View Source output.

        Adds newlines and 2-space indentation around block-level elements
        while preserving content inside whitespace-sensitive elements
        (<pre>, <textarea>) verbatim.

        Args:
            html: Full HTML document string

        Returns:
            Indented HTML string
        """
        BLOCK_ELEMENTS = {
            'html', 'head', 'body', 'header', 'footer', 'main', 'section',
            'nav', 'article', 'aside', 'div', 'ul', 'ol', 'li', 'table',
            'thead', 'tbody', 'tr', 'th', 'td', 'form', 'fieldset',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'blockquote',
            'figure', 'figcaption', 'details', 'summary',
            'title', 'script', 'style', 'noscript', 'template',
        }
        VOID_ELEMENTS = {
            'br', 'hr', 'img', 'input', 'meta', 'link', 'col', 'area',
            'base', 'embed', 'source', 'track', 'wbr',
        }
        INLINE_ELEMENTS = {
            'a', 'span', 'strong', 'em', 'b', 'i', 'u', 'small', 'sub',
            'sup', 'abbr', 'cite', 'code', 'label', 'button', 'select',
            'option', 'time', 'mark',
        }
        PRESERVE_ELEMENTS = {'pre', 'textarea'}

        # Tokenize: split into tags and text segments
        token_re = re.compile(r'(<[^>]+>)')
        tokens = token_re.split(html)

        tag_name_re = re.compile(r'^<\s*/?\s*([a-zA-Z][a-zA-Z0-9]*)', re.IGNORECASE)

        depth = 0
        output = []
        preserve_depth = 0

        def _at_line_start():
            """Check if we're at the start of a line (last output ends with newline or empty)."""
            return not output or output[-1].endswith('\n')

        for token in tokens:
            if not token:
                continue

            is_tag = token.startswith('<')

            if is_tag:
                tag_match = tag_name_re.match(token)
                tag_name = tag_match.group(1).lower() if tag_match else ''
                is_closing = token.startswith('</')
                is_self_closing = token.rstrip().endswith('/>')
                is_doctype = token.upper().startswith('<!DOCTYPE')
                is_comment = token.startswith('<!--')

                # Handle preserve elements
                if tag_name in PRESERVE_ELEMENTS:
                    if is_closing:
                        preserve_depth = max(preserve_depth - 1, 0)
                        output.append(token)
                        output.append('\n')
                    elif not is_self_closing:
                        preserve_depth += 1
                        indent = '  ' * depth
                        if not _at_line_start():
                            output.append('\n')
                        output.append(f'{indent}{token}')
                    else:
                        indent = '  ' * depth
                        output.append(f'{indent}{token}\n')
                    continue

                # Inside preserved content — output verbatim
                if preserve_depth > 0:
                    output.append(token)
                    continue

                if is_doctype or is_comment:
                    indent = '  ' * depth
                    if not _at_line_start():
                        output.append('\n')
                    output.append(f'{indent}{token}\n')
                elif tag_name in BLOCK_ELEMENTS:
                    if is_closing:
                        depth = max(depth - 1, 0)
                        indent = '  ' * depth
                        if not _at_line_start():
                            output.append('\n')
                        output.append(f'{indent}{token}\n')
                    elif is_self_closing:
                        indent = '  ' * depth
                        if not _at_line_start():
                            output.append('\n')
                        output.append(f'{indent}{token}\n')
                    else:
                        indent = '  ' * depth
                        if not _at_line_start():
                            output.append('\n')
                        output.append(f'{indent}{token}\n')
                        depth += 1
                elif tag_name in VOID_ELEMENTS:
                    indent = '  ' * depth
                    if not _at_line_start():
                        output.append('\n')
                    output.append(f'{indent}{token}\n')
                elif tag_name in INLINE_ELEMENTS:
                    # Inline elements stay on same line as surrounding content
                    if _at_line_start():
                        indent = '  ' * depth
                        output.append(f'{indent}{token}')
                    else:
                        output.append(token)
                else:
                    # Unknown tags — treat as inline
                    output.append(token)
            else:
                # Text node
                if preserve_depth > 0:
                    output.append(token)
                else:
                    stripped = token.strip()
                    if stripped:
                        if _at_line_start():
                            indent = '  ' * depth
                            output.append(f'{indent}{stripped}\n')
                        else:
                            output.append(stripped)

        result = ''.join(output)
        # Clean up multiple blank lines
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result.strip() + '\n'

    def _get_hot_reload_script(self) -> str:
        """
        Get the hot reload client script.

        Returns:
            JavaScript code for hot reload client
        """
        if not self.hot_reload_enabled:
            return ''

        return f"""
    <!-- Quantum Hot Reload Client -->
    <script>
    window.__QUANTUM_HOT_RELOAD_CONFIG = {{
        host: 'localhost',
        port: {self.hot_reload_port},
        enableLogging: true,
        enableToasts: true,
        preserveState: true
    }};
    </script>
    <script>
    (function() {{
        'use strict';
        var config = window.__QUANTUM_HOT_RELOAD_CONFIG || {{}};
        var WS_URL = 'ws://' + (config.host || 'localhost') + ':' + (config.port || 35729);
        var RECONNECT_INTERVAL = 1000;
        var MAX_RECONNECT_ATTEMPTS = 30;
        var socket = null;
        var reconnectAttempts = 0;
        var overlay = null;
        var isConnected = false;
        var preservedState = {{}};

        function log(msg) {{
            if (config.enableLogging !== false) console.log('[Hot Reload] ' + msg);
        }}

        function connect() {{
            if (socket && socket.readyState === WebSocket.OPEN) return;
            try {{
                socket = new WebSocket(WS_URL);
                socket.onopen = function() {{
                    log('Connected to dev server');
                    reconnectAttempts = 0;
                    isConnected = true;
                    hideOverlay();
                    showToast('Hot reload connected', 'success');
                }};
                socket.onclose = function() {{
                    isConnected = false;
                    log('Disconnected from dev server');
                    scheduleReconnect();
                }};
                socket.onerror = function() {{ log('WebSocket error'); }};
                socket.onmessage = function(e) {{
                    try {{ handleMessage(JSON.parse(e.data)); }} catch (err) {{}}
                }};
            }} catch (e) {{
                log('Failed to connect: ' + e);
                scheduleReconnect();
            }}
        }}

        function scheduleReconnect() {{
            if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {{
                showOverlay({{type: 'connection_lost', message: 'Lost connection to dev server. Restart with: quantum start --hot-reload'}});
                return;
            }}
            reconnectAttempts++;
            setTimeout(connect, RECONNECT_INTERVAL);
        }}

        function handleMessage(data) {{
            if (data.type === 'reload') {{
                log('Reload: ' + data.reloadType);
                if (data.reloadType === 'css') {{
                    reloadCSS();
                    showToast('Styles updated', 'info');
                }} else {{
                    preserveState();
                    showToast('Reloading...', 'info');
                    setTimeout(function() {{ location.reload(); }}, 100);
                }}
            }} else if (data.type === 'error') {{
                showOverlay(data.error);
            }} else if (data.type === 'clear_error') {{
                hideOverlay();
            }}
        }}

        function reloadCSS() {{
            var links = document.querySelectorAll('link[rel="stylesheet"]');
            var ts = Date.now();
            links.forEach(function(l) {{ l.href = l.href.split('?')[0] + '?_hr=' + ts; }});
            log('CSS reloaded');
        }}

        function preserveState() {{
            preservedState = {{}};
            document.querySelectorAll('form').forEach(function(f, i) {{
                var id = f.id || 'form_' + i;
                preservedState[id] = {{}};
                f.querySelectorAll('input,textarea,select').forEach(function(inp) {{
                    if (inp.name) {{
                        preservedState[id][inp.name] = (inp.type === 'checkbox' || inp.type === 'radio') ? inp.checked : inp.value;
                    }}
                }});
            }});
            preservedState._scroll = {{x: window.scrollX, y: window.scrollY}};
            try {{ sessionStorage.setItem('__quantum_hr_state', JSON.stringify(preservedState)); }} catch(e) {{}}
        }}

        function restoreState() {{
            try {{
                var s = sessionStorage.getItem('__quantum_hr_state');
                if (!s) return;
                var state = JSON.parse(s);
                sessionStorage.removeItem('__quantum_hr_state');
                Object.keys(state).forEach(function(fid) {{
                    if (fid.startsWith('_')) return;
                    var form = document.getElementById(fid) || document.forms[fid.replace('form_', '')];
                    if (!form) return;
                    Object.keys(state[fid]).forEach(function(n) {{
                        var inp = form.querySelector('[name="' + n + '"]');
                        if (inp) {{
                            if (inp.type === 'checkbox' || inp.type === 'radio') inp.checked = state[fid][n];
                            else inp.value = state[fid][n];
                        }}
                    }});
                }});
                if (state._scroll) setTimeout(function() {{ window.scrollTo(state._scroll.x, state._scroll.y); }}, 100);
            }} catch(e) {{}}
        }}

        function showOverlay(err) {{
            hideOverlay();
            overlay = document.createElement('div');
            overlay.id = '__quantum_hr_overlay';
            overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.9);z-index:999999;display:flex;align-items:center;justify-content:center;font-family:system-ui,sans-serif;';
            var c = document.createElement('div');
            c.style.cssText = 'max-width:800px;padding:40px;background:#1e1e1e;border-radius:8px;color:#fff;';
            var titleColor = err.type === 'connection_lost' ? '#ffc107' : '#f44336';
            c.innerHTML = '<h2 style="color:' + titleColor + ';margin:0 0 16px;">' + (err.type === 'connection_lost' ? 'Connection Lost' : 'Parse Error') + '</h2>' +
                (err.file ? '<p style="color:#888;margin:0 0 12px;font-size:14px;">File: ' + err.file + '</p>' : '') +
                '<pre style="background:#2d2d2d;padding:16px;border-radius:4px;overflow:auto;max-height:400px;color:#ff6b6b;white-space:pre-wrap;">' + escapeHtml(err.message) + '</pre>' +
                '<p style="color:#888;margin:16px 0 0;font-size:13px;">Fix the error and save to reload.</p>';
            overlay.appendChild(c);
            document.body.appendChild(overlay);
            overlay.onclick = function(e) {{ if (e.target === overlay) hideOverlay(); }};
        }}

        function hideOverlay() {{
            if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
            overlay = null;
        }}

        function showToast(msg, type) {{
            if (config.enableToasts === false) return;
            var old = document.getElementById('__quantum_hr_toast');
            if (old) old.parentNode.removeChild(old);
            var t = document.createElement('div');
            t.id = '__quantum_hr_toast';
            var bg = {{success:'#4caf50',error:'#f44336',warning:'#ff9800',info:'#2196f3'}}[type] || '#2196f3';
            t.style.cssText = 'position:fixed;bottom:20px;right:20px;padding:12px 20px;background:' + bg + ';color:#fff;border-radius:4px;font-family:system-ui;font-size:14px;z-index:999998;box-shadow:0 2px 8px rgba(0,0,0,0.2);';
            t.textContent = msg;
            document.body.appendChild(t);
            setTimeout(function() {{ if (t.parentNode) {{ t.style.opacity = '0'; t.style.transition = 'opacity 0.3s'; setTimeout(function() {{ if (t.parentNode) t.parentNode.removeChild(t); }}, 300); }} }}, 2000);
        }}

        function escapeHtml(text) {{
            var d = document.createElement('div');
            d.textContent = text;
            return d.innerHTML;
        }}

        setInterval(function() {{
            if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({{type:'ping'}}));
        }}, 30000);

        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', function() {{ restoreState(); connect(); }});
        }} else {{
            restoreState(); connect();
        }}
    }})();
    </script>"""

    def _needs_htmx(self, html: str) -> bool:
        """Whether this page uses htmx at all.

        Every served page used to get `<script src="https://unpkg.com/...">`
        unconditionally. Measured across the repo: 5 of 268 .q files carry an
        htmx marker, so 98% of pages pulled a third-party CDN dependency they
        never touched — a runtime network requirement for an offline or
        homelab deployment, which is the audience the project declares
        (FRAMEWORK_PLAN Fase 0.3), and a script a restrictive CSP blocks
        outright.

        A handful of other components (htmx_counter.q, htmx_click.q,
        htmx_add_todo.q) are htmx TARGETS — fragments returned into a page
        that drives them — and carry no markers of their own. They are served
        as partials, which never got the injection either way.
        """
        return any(marker in html for marker in self._HTMX_MARKERS)

    def _inject_htmx(self, html: str) -> str:
        """
        Inject HTMX scripts into an existing full HTML document.

        Used when the component already renders a complete HTML page
        (e.g. type="page" components), to avoid double-wrapping.

        Args:
            html: Full HTML document string

        Returns:
            HTML document with HTMX script and config injected, or unchanged
            when the page does not use htmx.
        """
        if not self._needs_htmx(html):
            # Still inject hot reload, which is independent of htmx.
            return self._inject_scripts_only(html, self._get_hot_reload_script())

        htmx_head = f'\n    <script src="{self._htmx_url()}"></script>'

        # Guarded: this used to call htmx.config directly, so a CDN that was
        # slow, blocked or offline turned into "htmx is not defined" on every
        # page — an error about the framework's own injected script, in an app
        # that may not use htmx at all.
        htmx_body = """
    <script>
        if (window.htmx) {
            htmx.config.defaultSwapStyle = "innerHTML";
            htmx.config.defaultSwapDelay = 0;
            htmx.config.historyCacheSize = 10;
            if (window.location.hostname === 'localhost') {
                htmx.logAll();
            }
        } else {
            console.warn('Quantum: this page uses htmx but the library did not load.');
        }
    </script>"""

        # Add hot reload script if enabled
        hot_reload_script = self._get_hot_reload_script()

        # Inject HTMX library before </head>
        if '</head>' in html:
            html = html.replace('</head>', htmx_head + '\n  </head>', 1)
        elif '</HEAD>' in html:
            html = html.replace('</HEAD>', htmx_head + '\n  </HEAD>', 1)

        # Inject HTMX config and hot reload script before </body>
        return self._inject_scripts_only(html, htmx_body + hot_reload_script)

    def _htmx_url(self) -> str:
        """Where to load htmx from.

        Prefers a vendored copy at static/vendor/htmx.min.js so an offline or
        air-gapped deployment works; falls back to the CDN. Vendoring the file
        is the remaining half of this fix — see DOGFOOD_NOTES.md item 8.
        """
        vendored = Path(self.config['paths']['static']) / 'vendor' / 'htmx.min.js'
        if vendored.is_file():
            return '/static/vendor/htmx.min.js'
        return self.config.get('server', {}).get(
            'htmx_url', 'https://unpkg.com/htmx.org@1.9.10'
        )

    def _inject_scripts_only(self, html: str, scripts: str) -> str:
        """Append scripts before </body> and guarantee a DOCTYPE."""
        if scripts:
            if '</body>' in html:
                html = html.replace('</body>', scripts + '\n  </body>', 1)
            elif '</BODY>' in html:
                html = html.replace('</BODY>', scripts + '\n  </BODY>', 1)

        # Ensure DOCTYPE is present. A .q cannot emit one itself — a DOCTYPE is
        # only valid before the root element, and the root element is
        # <q:component>. See DOGFOOD_NOTES.md item 4.
        if not html.strip().lower().startswith('<!doctype'):
            html = '<!DOCTYPE html>\n' + html

        return html

    def _wrap_with_htmx(self, html: str, component_path: str, title: str = '') -> str:
        """
        Wrap component HTML with HTMX library support (Phase B).

        Adds:
        - HTMX library from CDN
        - Minimal CSS reset
        - HTMX configuration
        - Hot reload client (when enabled)

        Args:
            html: Rendered component HTML
            component_path: Component name for title

        Returns:
            Full HTML page with HTMX support
        """
        hot_reload_script = self._get_hot_reload_script()

        # Only when the fragment actually uses htmx — see _needs_htmx().
        #
        # The config block is emitted with the tag, not independently. Making
        # only the <script src> conditional left `htmx.config...` running on
        # every page with the library absent, which turned a page that merely
        # did not use htmx into a page that threw "htmx is not defined" — a
        # regression this path introduced and the full-document path did not,
        # because only that one had been examined.
        uses_htmx = self._needs_htmx(html)
        htmx_tag = (f'<script src="{self._htmx_url()}"></script>'
                    if uses_htmx else '')
        htmx_config = """<script>
        if (window.htmx) {
            htmx.config.defaultSwapStyle = "innerHTML";
            htmx.config.defaultSwapDelay = 0;
            htmx.config.historyCacheSize = 10;
            if (window.location.hostname === 'localhost') {
                htmx.logAll();
            }
        } else {
            console.warn('Quantum: this page uses htmx but the library did not load.');
        }
    </script>""" if uses_htmx else ''

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html_escape(title or component_path)}</title>

    {htmx_tag}

    <style>
        /* Minimal CSS reset */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
        }}

        /* HTMX Loading indicators */
        .htmx-indicator {{
            display: none;
        }}

        .htmx-request .htmx-indicator {{
            display: inline;
        }}

        .htmx-request.htmx-indicator {{
            display: inline;
        }}

        /* Loading spinner */
        .htmx-indicator:after {{
            content: "⏳";
            margin-left: 8px;
        }}
    </style>
</head>
<body>
    {html}

    {htmx_config}
    {hot_reload_script}
</body>
</html>"""
