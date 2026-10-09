"""`quantum run game.q --check`: Godot opens the built project, or says why not.

Godot exits 0 whether or not a script parsed, so the check reads its output
(godot_bin.script_errors). The project checked is tests/godot/fixtures/mover,
the smallest game, broken on purpose where the test needs it.
"""

from quantum.runtime.godot_bin import GODOT_VERSION, check_project, run_godot, script_errors


def test_the_pinned_version_is_the_one_in_use(godot):
    out = run_godot(['--version'], binary=godot)
    assert out.stdout.strip().startswith(GODOT_VERSION)


def test_a_clean_project_has_no_errors(godot, mover_project):
    assert check_project(mover_project, binary=godot) == []


def test_a_parse_error_is_reported_with_its_line(godot, mover_project):
    (mover_project / 'main.gd').write_text('extends Node2D\nfunc _ready():\n\tvar x = \n',
                                           encoding='utf-8')
    errors = check_project(mover_project, binary=godot)
    assert errors, 'a script that does not parse must be an error'
    assert any('Parse Error' in e and 'main.gd:3' in e for e in errors), errors


def test_a_missing_project_is_an_error(tmp_path):
    assert check_project(tmp_path) == [f'{tmp_path} has no project.godot']


def test_script_errors_reads_godots_output():
    output = (
        'Godot Engine v4.4.1.stable.official - https://godotengine.org\n'
        '\n'
        'SCRIPT ERROR: Parse Error: Expected expression.\n'
        '          at: GDScript::reload (res://main.gd:3)\n'
        'ERROR: Failed to load script "res://main.gd" with error "Parse error".\n'
        '   at: load (modules/gdscript/gdscript.cpp:3022)\n'
    )
    assert script_errors(output) == [
        'SCRIPT ERROR: Parse Error: Expected expression. at: GDScript::reload (res://main.gd:3)',
        'ERROR: Failed to load script "res://main.gd" with error "Parse error". '
        'at: load (modules/gdscript/gdscript.cpp:3022)',
    ]
    assert script_errors('Godot Engine v4.4.1\n\n') == []
