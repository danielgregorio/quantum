"""Conformance: SPEC.md section 3b (Component composition)."""

import re

import pytest

LAYOUT = ('<q:component name="Frame" xmlns:q="https://quantum.lang/ns">'
          '<q:param name="title" required="true"/><q:param name="active" default=""/>'
          '<html><body><nav class="{\'sel\' if active == \'a\' else \'\'}">NAV</nav>'
          '<h1>{title}</h1><main><q:slot/></main></body></html></q:component>')


def text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


@pytest.fixture
def site(serve_pages, tmp_path):
    def build(**pages):
        (tmp_path / "components" / "parts").mkdir(parents=True, exist_ok=True)
        (tmp_path / "components" / "parts" / "Frame.q").write_text(LAYOUT, encoding="utf-8")
        return serve_pages(**pages)
    return build


def page(name, body):
    return f'<q:component name="{name}" xmlns:q="https://quantum.lang/ns">{body}</q:component>'


class TestComposition:
    def test_from_and_paths_components_of_the_config(self, site):
        # COMP-1 (before: it looked in the process directory's ./components and ignored from=)
        c = site(p=page("p", '<q:import component="Frame" from="parts"/><Frame title="Hi">x</Frame>'))
        r = c.get("/p")
        assert r.status_code == 200 and "Hi" in text(r.get_data(as_text=True))

    def test_a_missing_component_is_an_error(self, site):
        # COMP-1 (before: an HTML comment and a 200)
        c = site(p=page("p", '<q:import component="Ghost" from="parts"/><Ghost/>'))
        r = c.get("/p")
        assert r.status_code == 500

    def test_a_prop_is_an_expression_and_a_required_prop(self, site):
        # COMP-2
        c = site(p=page("p", '<q:import component="Frame" from="parts"/><q:set name="n" value="2" type="number"/>'
                             '<Frame title="Total {n + 1}" active="a">x</Frame>'),
                 q=page("q", '<q:import component="Frame" from="parts"/><Frame>x</Frame>'))
        html = c.get("/p").get_data(as_text=True)
        assert "Total 3" in text(html) and 'class="sel"' in html
        assert c.get("/q").status_code == 500

    def test_the_slot_sees_the_page_variables(self, site):
        # COMP-3 (before: the slot ran in the child's scope and the loop did not see the data)
        c = site(p=page("p", '<q:import component="Frame" from="parts"/>'
                             '<q:set name="items" type="array" value=\'["one", "two"]\'/>'
                             '<Frame title="List"><ul><q:loop items="{items}" var="i"><li>{i}</li></q:loop></ul>'
                             '<q:if condition="len(items) == 2"><p>TWO ITEMS</p></q:if></Frame>'))
        content = text(c.get("/p").get_data(as_text=True))
        assert "one two" in content and "TWO ITEMS" in content

    def test_one_request_content_does_not_leak_into_the_next(self, site):
        # COMP-3 (before: the graft mutated the layout's AST in the resolver's cache)
        c = site(a=page("a", '<q:import component="Frame" from="parts"/><Frame title="A">SECRET OF PAGE A</Frame>'),
                 b=page("b", '<q:import component="Frame" from="parts"/><Frame title="B">content of b</Frame>'))
        assert "SECRET OF PAGE A" in c.get("/a").get_data(as_text=True)
        second = c.get("/b").get_data(as_text=True)
        assert "SECRET OF PAGE A" not in second and "content of b" in second

    def test_the_child_uses_the_page_configuration(self, site, tmp_path):
        # COMP-4 (before: ComponentRuntime() without config — a q:query in the child had no datasource)
        import sqlite3
        db = tmp_path / "c.db"
        sqlite3.connect(db).executescript("create table t (v text); insert into t values ('FROM THE DB');")
        (tmp_path / "components" / "parts").mkdir(parents=True, exist_ok=True)
        (tmp_path / "components" / "parts" / "Row.q").write_text(
            page("Row", '<q:query name="r" datasource="db">SELECT v FROM t</q:query><span>{r.v}</span>'),
            encoding="utf-8")
        c = site(datasources_yaml=f"datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n",
                 p=page("p", '<q:import component="Row" from="parts"/><div><Row/></div>'))
        r = c.get("/p")
        assert r.status_code == 200 and "FROM THE DB" in r.get_data(as_text=True)

    def test_the_child_sees_the_page_session(self, site, tmp_path):
        # COMP-4 (before: the child got an empty session — the layout did not show the user)
        (tmp_path / "components" / "parts").mkdir(parents=True, exist_ok=True)
        (tmp_path / "components" / "parts" / "User.q").write_text(
            page("User", '<span>USER={session.name}</span>'), encoding="utf-8")
        c = site(p=page("p", '<q:import component="User" from="parts"/>'
                             '<q:set name="session.name" value="ana"/><div><User/></div>'))
        c.get("/p")
        assert "USER=ana" in c.get("/p").get_data(as_text=True)

    def test_a_component_that_fails_is_an_error_of_the_page(self, site, tmp_path):
        # COMP-1: never a section that disappears
        (tmp_path / "components" / "parts").mkdir(parents=True, exist_ok=True)
        (tmp_path / "components" / "parts" / "Boom.q").write_text(
            page("Boom", '<q:set name="x" value="{1 / 0}"/><p>{x}</p>'), encoding="utf-8")
        c = site(p=page("p", '<q:import component="Boom" from="parts"/><p>before</p><Boom/>'))
        assert c.get("/p").status_code == 500

    def test_a_prop_whose_expression_fails_is_an_error(self, site):
        # COMP-2
        c = site(p=page("p", '<q:import component="Frame" from="parts"/><Frame title="{missing + 1}">x</Frame>'))
        assert c.get("/p").status_code == 500
