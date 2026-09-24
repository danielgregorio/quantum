"""admin.components.* and admin.tests.* (quantum_admin/services/components.py)."""

import json

import pytest

from quantum_admin.services import components as svc

COMPONENT = ('<q:component name="Shop" xmlns:q="https://quantum.lang/ns">'
             '<q:action name="buy" method="POST"><q:param name="item" required="true"/>'
             '<q:redirect url="/shop"/></q:action>'
             '<q:query name="items" datasource="db">SELECT 1</q:query><p>x</p></q:component>\n')


@pytest.fixture(autouse=True)
def root(isolated_admin):
    (isolated_admin / "components" / "sub").mkdir(parents=True)
    (isolated_admin / "components" / "shop.q").write_text(COMPONENT, encoding="utf-8")
    (isolated_admin / "components" / "sub" / "b.q").write_text("<q:component name='B'><q:set name='x' value='1'/></q:component>", encoding="utf-8")
    (isolated_admin / "tests").mkdir()
    (isolated_admin / "tests" / "test_ok.py").write_text("def test_one():\n    assert True\n\ndef test_two():\n    assert 1\n", encoding="utf-8")
    (isolated_admin / "tests" / "test_fails.py").write_text("def test_breaks():\n    assert False\n", encoding="utf-8")
    (isolated_admin / "tests" / "helper.py").write_text("x = 1\n", encoding="utf-8")
    return isolated_admin


def test_list_components():
    r = svc.list_components()
    assert [c["path"] for c in r["components"]] == ["shop.q", "sub/b.q"]
    shop = r["components"][0]
    assert shop["group"] == "root" and shop["feature_tags"] == ["action", "query", "redirect"]
    assert r["directories"] == 2


def test_component_detail():
    d = svc.get_component("components/shop")
    assert (d["name"], d["type"], d["actions"], d["queries"], d["test_file"]) == \
        ("Shop", "Quantum", ["buy"], ["items"], None)


@pytest.mark.parametrize("path", ["../outside.q", "components/../../outside.q"])
def test_a_detail_outside_the_root_is_an_error(path):
    with pytest.raises(svc.ComponentError, match="outside"):
        svc.get_component(path)


def test_a_neighbour_folder_with_the_same_prefix_is_refused(root):
    # the screen used realpath.startswith(base): <root>2/ got through
    neighbour = root.parent / (root.name + "2")
    neighbour.mkdir()
    (neighbour / "x.q").write_text("<q:component name='X'/>", encoding="utf-8")
    with pytest.raises(svc.ComponentError, match="outside"):
        svc.get_component(f"../{neighbour.name}/x.q")


def test_list_tests():
    r = svc.list_tests()
    assert sorted(a["path"] for a in r["files"]) == ["test_fails.py", "test_ok.py"]
    assert r["total_functions"] == 3


class TestRun:
    def test_a_file_that_passes(self, root):
        r = svc.run_tests("tests/test_ok.py")
        assert r["passed"] is True and r["summary"]["passed"] == 2
        assert {t["name"] for t in r["tests"]} == {"test_one", "test_two"}
        saved = json.loads((root / "quantum_admin" / "settings" / "last_test_result.json").read_text(encoding="utf-8"))
        assert saved["test_file"] == "tests/test_ok.py"

    def test_a_file_that_fails(self):
        r = svc.run_tests("tests/test_fails.py")
        assert r["passed"] is False and r["summary"]["failed"] == 1

    def test_an_absolute_path_outside_the_root_is_refused(self, root, tmp_path_factory):
        # the screen only blocked ".." — an absolute path ran pytest on any .py
        outside = tmp_path_factory.mktemp("outside") / "test_malicious.py"
        outside.write_text("import pathlib\npathlib.Path(__file__).with_name('ran').write_text('yes')\n", encoding="utf-8")
        with pytest.raises(svc.ComponentError, match="outside"):
            svc.run_tests(str(outside))
        assert not outside.with_name("ran").exists()

    @pytest.mark.parametrize("path", ["tests/../components/shop.q", "tests/helper.py", "tests/does_not_exist.py"])
    def test_only_test_py_inside_tests(self, path):
        with pytest.raises(svc.ComponentError):
            svc.run_tests(path)


class TestGenerate:
    def test_it_generates_and_the_generated_test_passes(self, root):
        r = svc.generate_tests("components/shop.q")
        assert r["test_file"] == "tests/test_components_shop.py"
        assert svc.get_component("components/shop.q")["test_file"] == "tests/test_components_shop.py"
        run = svc.run_tests(r["test_file"])
        assert run["passed"] is True and run["summary"]["passed"] >= 2, run["output"][-800:]

    def test_it_does_not_overwrite_an_existing_test_without_asking(self, root):
        target = root / "tests" / "test_components_shop.py"
        target.write_text("# edited by hand\n", encoding="utf-8")
        with pytest.raises(svc.ComponentError, match="already exists"):
            svc.generate_tests("components/shop.q")
        assert target.read_text(encoding="utf-8") == "# edited by hand\n"
        assert svc.generate_tests("components/shop.q", overwrite=True)["overwritten"] is True

    def test_only_q_components(self):
        with pytest.raises(svc.ComponentError):
            svc.generate_tests("tests/test_ok.py")
