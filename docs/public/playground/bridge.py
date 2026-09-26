"""The playground's side of Quantum, run by Pyodide in the visitor's browser.

The playground runs the real quantum-framework from PyPI, the same version as
the site. This module is the only code between the editor and Quantum: it
writes the project the visitor edits into the browser's file system, builds it
the way `quantum test` builds a test's world (a fresh SQLite database from the
migrations, a server, a session), answers the preview's requests with that
server, and runs the project's own tests.

tests/docs/test_playground.py runs it under CPython on every Cookbook recipe the
playground offers; scripts/check-playground.mjs runs it in Pyodide.
"""

import contextlib
import io
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path('/playground/project')
_MAX_REDIRECTS = 10
_STYLESHEET = re.compile(r'<link\b[^>]*\brel="stylesheet"[^>]*\bhref="(/static/[^"]+)"[^>]*>')
_SCRIPT = re.compile(r'<script\b([^>]*)\bsrc="(/static/[^"]+)"([^>]*)>\s*</script>')


class Playground:
    """One project, built again every time the visitor runs it."""

    def __init__(self, root: Path = ROOT):
        self.root = Path(root)
        self.world = None
        self.path = '/'

    # -- the project ------------------------------------------------------------

    def load(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Write the files ({relative path: text}) and build the app from them."""
        self.close()
        if self.root.exists():
            shutil.rmtree(self.root)
        for name, text in files.items():
            target = (self.root / name).resolve()
            if self.root.resolve() not in target.parents:
                return {'error': f'{name}: a file must stay inside the project'}
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8')
        if not (self.root / 'quantum.config.yaml').is_file():
            (self.root / 'quantum.config.yaml').write_text('paths:\n  components: ./components\n',
                                                           encoding='utf-8')
        from quantum.runtime.app_testing import StepFailure, TestWorld
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                self.world = TestWorld(self.root)
        except StepFailure as e:
            return {'error': str(e)}
        except Exception as e:                      # a config that does not load, a bad migration
            return {'error': f'{type(e).__name__}: {e}'}
        return {'ok': True}

    def close(self) -> None:
        if self.world is not None:
            self.world.close()
            self.world = None

    # -- the preview ------------------------------------------------------------

    def request(self, method: str, path: str, form: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """A request from the preview, answered by the project's server.

        Redirects are followed like a browser does; the answer is the last page,
        with its stylesheets and scripts written into it (the preview is a
        document of its own, with no server behind its URLs).
        """
        if self.world is None:
            return {'status': 0, 'path': path, 'html': '', 'error': 'the project is not built'}
        from quantum.runtime.app_testing import _local_url
        client = self.world.client
        headers = {'Referer': 'http://localhost' + self.path}
        if method.upper() == 'POST':
            response = client.post(path, data=form or {}, headers=headers)
        else:
            response = client.get(path, headers=headers)
        hops = 0
        while response.status_code in (301, 302, 303, 307, 308) and response.headers.get('Location'):
            hops += 1
            if hops > _MAX_REDIRECTS:
                return {'status': response.status_code, 'path': path, 'html': '',
                        'error': f'more than {_MAX_REDIRECTS} redirects in a row'}
            path = _local_url(response.headers['Location'])
            response = client.get(path, headers={'Referer': 'http://localhost' + self.path})
        self.path = path
        html = response.get_data(as_text=True)
        if 'html' in (response.content_type or ''):
            html = self._inline_assets(html)
        return {'status': response.status_code, 'path': path, 'html': html,
                'content_type': response.content_type}

    def _inline_assets(self, html: str) -> str:
        client = self.world.client

        def stylesheet(match):
            css = client.get(match.group(1))
            return f'<style>{css.get_data(as_text=True)}</style>' if css.status_code == 200 else match.group(0)

        def script(match):
            js = client.get(match.group(2))
            if js.status_code != 200:
                return match.group(0)
            return f'<script{match.group(1)}{match.group(3)}>{js.get_data(as_text=True)}</script>'

        return _SCRIPT.sub(script, _STYLESHEET.sub(stylesheet, html))

    # -- the tests --------------------------------------------------------------

    def test(self) -> Dict[str, Any]:
        """Run the project's *.test.q files, as `quantum test` does."""
        from quantum.runtime.app_testing import run_tests
        lines = []
        code = run_tests([str(self.root)], out=lines.append)
        report = '\n'.join(lines).replace(str(self.root) + '/', '').replace(str(self.root), '.')
        return {'code': code, 'report': report}


playground = Playground()
