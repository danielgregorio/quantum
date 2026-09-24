"""The welcome page and the error pages (in development, with the source line that failed).

Part of QuantumWebServer (web_server.py), as a mixin."""

import os
import re
from html import escape as html_escape
from pathlib import Path

from flask import Response


class ErrorPages:
    def _render_welcome_page(self) -> Response:
        """
        Render welcome page when index.q doesn't exist.

        Returns:
            Flask Response with welcome HTML
        """
        components_dir = self.config['paths']['components']

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to Quantum</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                .container {{
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 15px;
                    padding: 40px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                }}
                h1 {{ margin-top: 0; font-size: 3em; }}
                code {{
                    background: rgba(0, 0, 0, 0.3);
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                }}
                .box {{
                    background: rgba(255, 255, 255, 0.1);
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                }}
                a {{
                    color: #fff;
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 Quantum is Running!</h1>
                <p>Your Quantum server is successfully running and ready to serve components.</p>

                <div class="box">
                    <h2>🎯 Quick Start</h2>
                    <p>Create your first component:</p>
                    <p><code>mkdir -p {components_dir}</code></p>
                    <p><code>nano {components_dir}/index.q</code></p>
                    <pre style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px;">
&lt;q:component name="HomePage"&gt;
  &lt;html&gt;
    &lt;body&gt;
      &lt;h1&gt;Hello from Quantum!&lt;/h1&gt;
      &lt;p&gt;This is my first component.&lt;/p&gt;
    &lt;/body&gt;
  &lt;/html&gt;
&lt;/q:component&gt;</pre>
                    <p>Then refresh this page!</p>
                </div>

                <div class="box">
                    <h2>📚 Learn More</h2>
                    <ul>
                        <li><a href="https://github.com/danielgregorio/quantum">Documentation</a></li>
                        <li><a href="/examples">Example Components</a></li>
                        <li><a href="/static">Static Files</a></li>
                    </ul>
                </div>

                <div class="box">
                    <h2>⚙️ Configuration</h2>
                    <p>Server is running with:</p>
                    <ul>
                        <li>Port: <code>{self.config['server']['port']}</code></li>
                        <li>Components directory: <code>{components_dir}</code></li>
                        <li>Debug mode: <code>{self.config['server'].get('debug', False)}</code></li>
                        <li>Auto-reload: <code>{self.config['server'].get('reload', False)}</code></li>
                    </ul>
                    <p>Edit <code>quantum.config.yaml</code> to customize.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return Response(html, mimetype='text/html')

    @staticmethod
    def _error_location(exc, default_file):
        """DEV-2: (file, line) of the .q line an error comes from, or None."""
        from quantum.core.xml_lines import error_location
        file, line = error_location(exc)
        if not line:
            return None
        return (file or str(default_file), line)

    @staticmethod
    def _source_snippet(file: str, line: int, context: int = 3) -> str:
        """The lines around `line`, the failing one marked (DEV-2)."""
        try:
            lines = Path(file).read_text(encoding='utf-8').splitlines()
        except OSError:
            return ''
        if not 0 < line <= len(lines):
            return ''
        try:
            file = os.path.relpath(file)
        except ValueError:
            pass                                    # another drive (Windows)
        rows = []
        for n in range(max(1, line - context), min(len(lines), line + context) + 1):
            css_class = ' class="marked"' if n == line else ''
            rows.append(f'<tr{css_class}><td class="ln">{n}</td>'
                          f'<td><code>{html_escape(lines[n - 1]) or " "}</code></td></tr>')
        return ('<div class="source"><div class="where">' + html_escape(file) + f', line {line}</div>'
                '<table>' + ''.join(rows) + '</table></div>')

    def _render_error_page(self, title: str, message: str, details: str, suggestion: str,
                           location=None, python_traceback: str = '') -> str:
        """
        Render error page with helpful information.

        Everything is escaped: an error message can carry what the request
        sent (a query value, a form field). In debug mode, the page also shows
        the .q lines around the one that failed (DEV-2), links the SPEC rules
        the message cites, and the Python traceback, folded.
        """
        e = html_escape
        debug = self.config['server'].get('debug')
        snippet = self._source_snippet(*location) if (location and debug) else ''
        rules = ''
        if debug:
            ids = sorted(set(re.findall(r'\b(?:PARSE|RET|LOOP|IF|FN|ACT|ROUTE|COMP|DB|SET|AUTH|DATA|IA|EXPR|INV'
                                        r'|RUN|SCOPE|ERR|CFG|APP|SVC|UI|EXEC|DEV)-\d+\b',
                                        f'{message}\n{details}')))
            if ids:
                rules = '<p class="rules">Rules: ' + ', '.join(
                    f'<a href="https://github.com/danielgregorio/quantum/blob/main/SPEC.md#:~:text={i}">{i}</a>'
                    for i in ids) + '</p>'
        rastro = (f'<details class="trace"><summary>Python traceback</summary>'
                  f'<div class="details">{e(python_traceback)}</div></details>') if (python_traceback and debug) else ''
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{e(title)}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    max-width: 900px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .error-container {{
                    background: white;
                    border-radius: 10px;
                    padding: 40px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    border-left: 5px solid #e74c3c;
                }}
                h1 {{
                    color: #e74c3c;
                    margin-top: 0;
                }}
                .details {{
                    background: #f9f9f9;
                    border: 1px solid #ddd;
                    padding: 15px;
                    border-radius: 5px;
                    font-family: 'Courier New', monospace;
                    white-space: pre-wrap;
                    overflow-x: auto;
                }}
                .suggestion {{
                    background: #e8f5e9;
                    border-left: 4px solid #4caf50;
                    padding: 15px;
                    margin-top: 20px;
                }}
                .source {{ margin: 16px 0; border: 1px solid #ddd; border-radius: 5px; overflow-x: auto; }}
                .source .where {{ background: #f0f0f0; padding: 6px 10px; font-size: 13px; color: #555; }}
                .source table {{ border-collapse: collapse; width: 100%; }}
                .source td {{ padding: 1px 10px; font: 13px/1.5 ui-monospace, 'Courier New', monospace; white-space: pre; }}
                .source td.ln {{ color: #999; text-align: right; width: 1%; user-select: none; }}
                .source tr.marked td {{ background: #fdecea; }}
                .source tr.marked td.ln {{ color: #c0392b; font-weight: bold; }}
                .trace {{ margin-top: 16px; }}
                @media (max-width: 600px) {{ body {{ margin: 0; padding: 12px; }} .error-container {{ padding: 16px; }} }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1>⚠️ {e(title)}</h1>
                <p><strong>{e(message)}</strong></p>

                {snippet}

                {f'<div class="details">{e(details)}</div>' if details else ''}

                {rules}

                {f'<div class="suggestion"><strong>💡 Suggestion:</strong> {e(suggestion)}</div>' if suggestion else ''}

                {rastro}

                <p style="margin-top: 30px;">
                    <a href="/">← Go back to home</a>
                </p>
            </div>
        </body>
        </html>
        """

        return html
