"""
Regressions found by writing a real screen in Quantum.

FRAMEWORK_PLAN.md Fase 4: rewrite one quantum_admin screen in .q and record
everything that hurts. These are the failures from that list that were bugs
rather than friction — each one was hit while building
components/admin/projects.q, not while reading code.

None of them were caught by 2,500 existing tests, which is the point: they
only appear when you use the thing end to end.
"""

import os

import pytest

from quantum.core.parser import QuantumParser
from quantum.core.features.loops.src.ast_node import LoopNode


class TestQueryLoopHonoursVar:
    """<q:loop query="projects" var="p"> silently discarded var=.

    The parser read `var` only in the non-query branch, so the row variable
    became the query name. {p.name} then rendered as literal text — no error,
    no warning, in the parser or the renderer. The page came out with every
    field showing as a placeholder.
    """

    @staticmethod
    def _loop(src_attrs):
        src = (f'<q:component name="T">'
               f'<q:loop {src_attrs}><span>x</span></q:loop>'
               f'</q:component>')
        ast = QuantumParser().parse(src)
        return next(s for s in ast.statements if isinstance(s, LoopNode))

    def test_var_is_used_when_given(self):
        loop = self._loop('query="projects" var="p"')
        assert loop.var_name == 'p'
        assert loop.query_name == 'projects'
        assert loop.loop_type == 'query'

    def test_query_name_is_still_the_default(self):
        """The established idiom is <q:loop query="users"> + {users.name},
        and it has to keep working exactly as before."""
        loop = self._loop('query="users"')
        assert loop.var_name == 'users'
        assert loop.query_name == 'users'


class TestAssetUrlsAreRootRelative:
    """A page at /admin/projects loaded no CSS and no JS.

    The server extracts inline <style>/<script> into hashed static files, but
    emitted `href="static/..."` — resolved against the current path, so the
    browser asked for /admin/static/... and got a 404. Nothing fails loudly
    when a stylesheet 404s, so the page just renders unstyled.
    """

    def test_stylesheet_link_is_root_relative(self):
        import inspect
        from quantum.runtime import web_server
        source = inspect.getsource(web_server)
        assert 'href="static/' not in source, (
            'a relative stylesheet href breaks every nested route'
        )
        assert 'href="/static/' in source

    def test_script_src_is_root_relative(self):
        import inspect
        from quantum.runtime import web_server
        source = inspect.getsource(web_server)
        assert 'src="static/' not in source
        assert 'src="/static/' in source


class TestServerStartReportsFailure:
    """`quantum start` printed its success banner and then died, exit code 0.

    Werkzeug's reloader re-executes the program in a child process. The child
    ran the port check, found the parent's own socket bound, reported "port
    already in use" and returned. Since `reload: true` is the shipped default
    in quantum.config.yaml, the documented way to start the server could not
    start it — and reported success while doing so.
    """

    @pytest.fixture
    def server(self, tmp_path):
        from quantum.runtime.web_server import QuantumWebServer
        return QuantumWebServer()

    def test_reloader_child_skips_the_port_check(self, server, monkeypatch):
        """In the child, the bound socket belongs to our own parent."""
        monkeypatch.setenv('WERKZEUG_RUN_MAIN', 'true')
        monkeypatch.setattr(server, '_check_port_available', lambda h, p: False)
        monkeypatch.setattr(server, '_print_banner', lambda: None)

        ran = {}
        monkeypatch.setattr(server.app, 'run', lambda **kw: ran.update(kw))

        server.start()
        assert ran, 'the reloader child refused to start the server'

    def test_a_taken_port_exits_non_zero(self, server, monkeypatch):
        monkeypatch.delenv('WERKZEUG_RUN_MAIN', raising=False)
        monkeypatch.setattr(server, '_check_port_available', lambda h, p: False)
        monkeypatch.setattr(server.app, 'run',
                            lambda **kw: pytest.fail('should not have started'))

        assert server.start() == 1, (
            'a dead server must not look like a clean start to a supervisor'
        )

    def test_a_failed_bind_exits_non_zero(self, server, monkeypatch):
        monkeypatch.delenv('WERKZEUG_RUN_MAIN', raising=False)
        monkeypatch.setattr(server, '_check_port_available', lambda h, p: True)
        monkeypatch.setattr(server, '_print_banner', lambda: None)
        monkeypatch.setattr(server, '_write_pid_file', lambda: None)

        def boom(**kw):
            raise OSError('address already in use')
        monkeypatch.setattr(server.app, 'run', boom)

        assert server.start() == 1


class TestHtmxIsOnlyInjectedWhenUsed:
    """Every served page carried <script src="https://unpkg.com/htmx...">.

    Measured across the repo: 5 of 268 .q files carry an htmx marker, so 98%
    of pages pulled a third-party CDN at runtime for a library they never
    touched.
    That is a network dependency for the offline/homelab deployment the
    project targets (FRAMEWORK_PLAN Fase 0.3), and a script a restrictive CSP
    blocks outright. DOGFOOD_NOTES.md item 8.
    """

    @pytest.fixture
    def server(self):
        from quantum.runtime.web_server import QuantumWebServer
        return QuantumWebServer()

    @pytest.mark.parametrize("html,expected", [
        ('<div>plain</div>', False),
        ('<div hx-get="/x">go</div>', True),
        ('<div data-hx-post="/x">go</div>', True),
        ('<script>htmx.ajax("GET", "/x")</script>', True),
        ('<table><tr><td>hxx</td></tr></table>', False),
    ])
    def test_detection(self, server, html, expected):
        assert server._needs_htmx(html) is expected

    def test_a_page_without_htmx_gets_no_external_script(self, server):
        out = server._inject_htmx(
            '<html><head></head><body><p>hi</p></body></html>'
        )
        assert 'unpkg.com' not in out
        assert 'htmx' not in out.lower()

    def test_a_page_with_htmx_still_gets_it(self, server):
        out = server._inject_htmx(
            '<html><head></head><body><div hx-get="/x">go</div></body></html>'
        )
        assert 'htmx' in out

    def test_the_config_script_is_guarded(self, server):
        """It called htmx.config directly, so a CDN that was blocked or
        offline produced "htmx is not defined" on every page."""
        out = server._inject_htmx(
            '<html><head></head><body><div hx-get="/x">go</div></body></html>'
        )
        assert 'window.htmx' in out, 'the config script must check it loaded'

    def test_the_doctype_survives_the_no_htmx_path(self, server):
        """A .q cannot emit its own DOCTYPE, so the server has to."""
        out = server._inject_htmx('<html><head></head><body></body></html>')
        assert out.strip().lower().startswith('<!doctype')

    def test_a_vendored_copy_is_preferred_over_the_cdn(self, server, tmp_path, monkeypatch):
        vendor = tmp_path / 'vendor'
        vendor.mkdir()
        (vendor / 'htmx.min.js').write_text('// htmx', encoding='utf-8')
        server.config['paths']['static'] = str(tmp_path)
        assert server._htmx_url() == '/static/vendor/htmx.min.js'

    def test_the_cdn_is_the_fallback(self, server, tmp_path):
        server.config['paths']['static'] = str(tmp_path)
        assert server._htmx_url().startswith('http')

    # The fragment path is the one 233 of 268 .q files take, and it is the one
    # the first pass at this fix broke: only the <script src> was made
    # conditional, so the config block kept calling htmx.config with the
    # library absent. A page that merely did not use htmx started throwing
    # "htmx is not defined" — the fix introduced the failure it was meant to
    # prevent. Found by an independent verification pass, not by these tests.

    def test_a_fragment_without_htmx_gets_neither_library_nor_config(self, server):
        out = server._wrap_with_htmx('<div>plain</div>', 'demo')
        assert 'unpkg' not in out
        assert 'htmx.config' not in out, (
            'the config block must not run with the library omitted'
        )

    def test_a_fragment_with_htmx_gets_both_and_the_guard(self, server):
        out = server._wrap_with_htmx('<div hx-get="/x">go</div>', 'demo')
        assert 'htmx' in out
        assert 'htmx.config' in out
        assert 'window.htmx' in out
