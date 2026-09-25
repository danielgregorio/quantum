#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quantum CLI Runner - Main orchestrator refactored
"""

import argparse
import sys
import os
from pathlib import Path

# Fix encoding on Windows
if os.name == 'nt':  # Windows
    try:
        os.system('chcp 65001 >nul 2>&1')  # UTF-8
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass  # Silent fallback

# Fix imports - use absolute imports

from quantum.core.parser import QuantumParser, QuantumParseError
from quantum.core.ast_nodes import ComponentNode, ApplicationNode, JobNode
from quantum.runtime.component import ComponentRuntime, ComponentExecutionError
from quantum.runtime.executors.control_flow.redirect_executor import PageRedirect

# Import package commands
def _get_pkg_module():
    try:
        from quantum.cli.pkg import create_pkg_parser, handle_pkg
        return True, create_pkg_parser, handle_pkg
    except ImportError as e:
        return False, None, str(e)

# Import jobs commands
def _get_jobs_module():
    try:
        from quantum.cli.jobs import create_jobs_parser, handle_jobs
        return True, create_jobs_parser, handle_jobs
    except ImportError as e:
        return False, None, str(e)

# Import message queue commands
def _get_mq_module():
    try:
        from quantum.cli.mq import create_mq_parser, handle_mq
        return True, create_mq_parser, handle_mq
    except ImportError as e:
        return False, None, str(e)

# Import migration commands
def _get_migrate_module():
    try:
        from quantum.cli.migrations import MigrationRunner
        return True, MigrationRunner
    except ImportError as e:
        return False, str(e)

def load_config(config_path: str = 'quantum.config.yaml') -> dict:
    """Load quantum.config.yaml if present.

    The `run` command used to build a ComponentRuntime with no config at all,
    so `datasources:` declared in quantum.config.yaml were never seen and
    every q:query fell through to the optional Quantum Admin API.
    """
    from quantum.core.config_env import ConfigEnvError, expand_env
    try:
        import yaml
        path = Path(config_path)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as fh:
                return expand_env(yaml.safe_load(fh) or {})
    except ConfigEnvError:
        raise                   # CFG-1: never run with a half-read config
    except Exception as exc:
        print(f"[WARN] Could not read {config_path}: {exc}")
    return {}


class QuantumRunner:
    """Main Quantum Runner - Clean orchestration"""

    def __init__(self, config: dict = None):
        self.parser = QuantumParser()
        self.config = config if config is not None else load_config()
        self.component_runtime = ComponentRuntime(config=self.config)

    def run(self, file_path: str, debug: bool = False) -> int:
        """Execute .q file"""
        try:
            if debug:
                print(f"[DEBUG] Parsing file: {Path(file_path).name}")

            # Store source directory for asset resolution
            self._source_dir = str(Path(file_path).resolve().parent)

            # Parse file → AST
            ast_node = self.parser.parse_file(file_path)

            if debug:
                print(f"[DEBUG] AST generated: {type(ast_node).__name__}")
                print("[DEBUG] Validating AST...")

            # Validate AST
            validation_errors = ast_node.validate()
            if validation_errors:
                print("[ERROR] Validation errors:")
                for error in validation_errors:
                    print(f"  - {error}")
                return 1

            # Execute based on type
            return self._execute_ast(ast_node, debug)

        except QuantumParseError as e:
            print(f"[ERROR] Parse error: {e}")
            return 1
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            if debug:
                import traceback
                traceback.print_exc()
            return 1

    def _execute_ast(self, ast_node, debug: bool = False) -> int:
        """Execute AST based on type"""
        if isinstance(ast_node, ComponentNode):
            return self._execute_component(ast_node, debug)
        elif isinstance(ast_node, ApplicationNode):
            return self._execute_application(ast_node, debug)
        elif isinstance(ast_node, JobNode):
            return self._execute_job(ast_node, debug)
        else:
            print(f"[ERROR] Unsupported AST type: {type(ast_node)}")
            return 1

    def _execute_component(self, component: ComponentNode, debug: bool = False) -> int:
        """Execute q:component"""
        print(f"[EXEC] Executing component: {component.name}")
        if debug:
            print(f"   Type: {component.component_type}")
            print(f"   Params: {len(component.params)}")
            print(f"   Returns: {len(component.returns)}")

        try:
            result = self.component_runtime.execute_component(component)
            if result is not None:
                print(f"[SUCCESS] Result: {result}")
            else:
                print("[WARN] Component executed without return")
            return 0

        except ComponentExecutionError as e:
            print(f"[ERROR] Execution error: {e}")
            return 1
        except PageRedirect as r:
            print(f"[REDIRECT] {r.status} {r.url}")
            return 0

    def _execute_application(self, app: ApplicationNode, debug: bool = False) -> int:
        """Execute q:application"""
        print(f"[EXEC] Executing application: {app.app_id}")
        print(f"[INFO] Type: {app.app_type}")

        if debug:
            print(f"   Routes: {len(app.routes)}")
            for route in app.routes:
                print(f"     {route.method} {route.path}")

        from quantum.core.tiers import warn_app_type
        warn_app_type(app.app_type)

        if app.app_type == 'game':
            return self._build_game(app, debug)
        elif app.app_type == 'terminal':
            return self._build_terminal(app, debug)
        elif app.app_type == 'ui':
            target = getattr(self, '_ui_target', 'html')
            return self._build_ui(app, target, debug)
        else:
            print(f"[ERROR] Application type '{app.app_type}' not supported")
            return 1

    def _build_game(self, app: ApplicationNode, debug: bool = False) -> int:
        """Build game from game application using selected engine backend."""
        from quantum.runtime.game_builder import GameBuilder, GameBuildError
        engine = getattr(self, '_game_engine', 'pixi')
        try:
            source_dir = getattr(self, '_source_dir', None)
            builder = GameBuilder(engine=engine, source_dir=source_dir)
            output_path = builder.build_to_file(app)
            engine_label = 'Godot 4 project' if engine == 'godot' else 'HTML game'
            print(f"[SUCCESS] {engine_label} built: {output_path}")
            if debug:
                print(f"   Engine: {engine}")
                print(f"   Scenes: {len(getattr(app, 'scenes', []))}")
                print(f"   Behaviors: {len(getattr(app, 'behaviors', []))}")
                print(f"   Prefabs: {len(getattr(app, 'prefabs', []))}")
            return 0
        except GameBuildError as e:
            print(f"[ERROR] Game build error: {e}")
            return 1

    def _build_terminal(self, app: ApplicationNode, debug: bool = False) -> int:
        """Build standalone Python TUI app from terminal application."""
        from quantum.runtime.terminal_builder import TerminalBuilder, TerminalBuildError
        try:
            builder = TerminalBuilder()
            output_path = builder.build_to_file(app)
            print(f"[SUCCESS] Terminal app built: {output_path}")
            if debug:
                print(f"   Screens: {len(getattr(app, 'screens', []))}")
                print(f"   Keybindings: {len(getattr(app, 'keybindings', []))}")
            return 0
        except TerminalBuildError as e:
            print(f"[ERROR] Terminal build error: {e}")
            return 1

    def _build_ui(self, app: ApplicationNode, target: str = 'html', debug: bool = False) -> int:
        """Build multi-target UI app from UI application."""
        from quantum.runtime.ui_builder import UIBuilder, UIBuildError
        try:
            builder = UIBuilder()
            output_path = builder.build_to_file(app, target=target)
            print(f"[SUCCESS] UI app built ({target}): {output_path}")
            if debug:
                print(f"   Windows: {len(getattr(app, 'ui_windows', []))}")
                print(f"   UI children: {len(getattr(app, 'ui_children', []))}")
                print(f"   Target: {target}")
            return 0
        except UIBuildError as e:
            print(f"[ERROR] UI build error: {e}")
            return 1

    def _execute_job(self, job: JobNode, debug: bool = False) -> int:
        """Execute q:job"""
        print(f"[EXEC] Executing job: {job.job_id}")
        if job.schedule:
            print(f"[INFO] Schedule: {job.schedule}")

        # TODO: Implement real job execution
        print("[SUCCESS] Job executed successfully")
        return 0


def build_parser():
    """The `quantum` command line: the parser, and the optional sub-commands' handlers.

    docs/reference/cli.md is generated from this parser (scripts/generate-reference.py).
    """
    parser = argparse.ArgumentParser(
        description='Quantum CLI - Execute .q files and start servers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  quantum start                    # Start web server (magic!)
  quantum run hello.q              # Execute component
  quantum admin                    # Start the Quantum Admin
  quantum console                  # The application's pages in the terminal
  quantum desktop                  # The application's pages in a desktop window
  quantum check                    # Pages parse, SQL compiles, query fields exist
  quantum test                     # Run the app's *.test.q tests
  quantum run game.q --engine godot # Build Godot 4 project
  quantum run backup-job.q         # Execute job
  quantum pkg init ./my-component  # Initialize new package
  quantum pkg install ./package    # Install package
  quantum pkg list                 # List installed packages
  quantum jobs list                # List scheduled jobs
  quantum jobs run my-job          # Run a job manually
  quantum jobs worker start        # Start job worker
  quantum mq queues list           # List message queues
  quantum mq publish topic message # Publish to topic
  quantum mq worker --queues q1,q2 # Start message worker
        """
    )
    # --version: reads the version from the installed package's metadata (works
    # when it came from `pip install`), with a fallback for running from the source tree.
    try:
        from importlib.metadata import version as _pkg_version, PackageNotFoundError
        try:
            _version = _pkg_version("quantum-framework")
        except PackageNotFoundError:
            _version = "dev (not installed via pip)"
    except Exception:
        _version = "unknown"
    parser.add_argument('--version', action='version',
                        version=f'quantum {_version}')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Run command
    run_parser = subparsers.add_parser('run', help='Execute a .q file')
    run_parser.add_argument('file', help='.q file to execute')
    run_parser.add_argument('--debug', action='store_true', help='Debug mode')
    run_parser.add_argument('--config', default='quantum.config.yaml', help='Config file')
    run_parser.add_argument('--target', choices=['html', 'textual', 'desktop', 'mobile'], default='html',
                            help='UI target (for type="ui" apps): html, textual, desktop, or mobile')
    run_parser.add_argument('--engine', choices=['pixi', 'godot'], default='pixi',
                            help='Game engine backend: pixi (default, HTML5) or godot (Godot 4 project)')

    # Start command
    start_parser = subparsers.add_parser('start', help='Start web server')
    start_parser.add_argument('--port', type=int, help='Port (overrides config)')
    start_parser.add_argument('--config', default='quantum.config.yaml', help='Config file')
    start_parser.add_argument('--debug', action='store_true', help='Debug mode')
    start_parser.add_argument('--hot-reload', action='store_true',
                              help='Reload the open pages when a component or static file changes')
    start_parser.add_argument('--hot-reload-port', type=int, default=None,
                              help='WebSocket port for --hot-reload (default 35729)')

    # Stop command
    subparsers.add_parser('stop', help='Stop running web server')

    # Console: the application's pages in the terminal (UI-3)
    console_parser = subparsers.add_parser('console', help="Open the application's pages in the terminal")
    console_parser.add_argument('path', nargs='?', default='/', help='Page to open (default: /)')
    console_parser.add_argument('--config', default='quantum.config.yaml', help='Config file')

    # Check: pages parse, queries compile, fields exist (M8, DEV-3)
    check_parser = subparsers.add_parser('check', help='Check pages, SQL and query fields against the database')
    check_parser.add_argument('--config', default='quantum.config.yaml', help='Config file')

    # Test command (TEST-1)
    test_parser = subparsers.add_parser('test', help="Run the app's *.test.q tests")
    test_parser.add_argument('paths', nargs='*', default=['.'],
                             help='Test files or folders to search for *.test.q (default: .)')

    # Desktop: the application's pages in a native window (UI-4)
    desktop_parser = subparsers.add_parser('desktop', help="Open the application's pages in a desktop window")
    desktop_parser.add_argument('path', nargs='?', default='/', help='Page to open (default: /)')
    desktop_parser.add_argument('--config', default='quantum.config.yaml', help='Config file')
    desktop_parser.add_argument('--width', type=int, default=1024, help='Window width (default: 1024)')
    desktop_parser.add_argument('--height', type=int, default=720, help='Window height (default: 720)')

    # Admin command (the screens need the [admin] extra; checked when run)
    from quantum.cli.admin import create_admin_parser
    create_admin_parser(subparsers)

    # Package commands (if available)
    pkg_available, create_pkg_parser, handle_pkg = _get_pkg_module()

    if pkg_available:
        create_pkg_parser(subparsers)

    # Jobs commands (if available)
    jobs_available, create_jobs_parser, handle_jobs = _get_jobs_module()

    if jobs_available:
        create_jobs_parser(subparsers)

    # Message queue commands (if available)
    mq_available, create_mq_parser, handle_mq = _get_mq_module()

    if mq_available:
        create_mq_parser(subparsers)

    # Migration commands
    migrate_parser = subparsers.add_parser('migrate', help='Database migration commands')
    migrate_parser.add_argument('--datasource', help='Datasource from quantum.config.yaml (default: the only one declared)')
    migrate_subparsers = migrate_parser.add_subparsers(dest='migrate_command')

    migrate_subparsers.add_parser('status', help='Show migration status')

    migrate_up_parser = migrate_subparsers.add_parser('up', help='Apply pending migrations')
    migrate_up_parser.add_argument('-n', '--count', type=int, help='Number of migrations to apply')

    migrate_down_parser = migrate_subparsers.add_parser('down', help='Rollback migrations')
    migrate_down_parser.add_argument('-n', '--count', type=int, default=1, help='Number of migrations to rollback')

    migrate_create_parser = migrate_subparsers.add_parser('create', help='Create a new migration')
    migrate_create_parser.add_argument('name', help='Migration name')

    # M6 (DB-10): schema.sql as the source of truth
    migrate_plan_parser = migrate_subparsers.add_parser(
        'plan', help='Compare schema.sql with the migrations and plan the migration')
    migrate_plan_parser.add_argument('--schema', default='schema.sql', help='Schema file (default: schema.sql)')
    migrate_plan_parser.add_argument('--write', metavar='NAME', help='Save the plan as migration V00N_NAME')
    migrate_plan_parser.add_argument('--yes', action='store_true', help='Do not ask before writing')
    migrate_plan_parser.add_argument('--allow-data-loss', action='store_true',
                                     help='Write a plan that drops tables or columns')

    return parser, (pkg_available, handle_pkg, jobs_available, handle_jobs, mq_available, handle_mq)


def main():
    """CLI entry point"""
    parser, (pkg_available, handle_pkg, jobs_available, handle_jobs, mq_available, handle_mq) = build_parser()

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Handle 'start' command
    if args.command == 'start':
        from quantum.runtime.web_server import start_server
        try:
            # Exit with whatever the server reports: a taken port or a failed
            # bind must not look like a clean start to a supervisor or CI.
            sys.exit(start_server(args.config, port=getattr(args, 'port', None),
                                  hot_reload=getattr(args, 'hot_reload', False),
                                  hot_reload_port=getattr(args, 'hot_reload_port', None)) or 0)
        except Exception as e:
            print(f"[ERROR] Failed to start server: {e}")
            if getattr(args, 'debug', False):
                import traceback
                traceback.print_exc()
            sys.exit(1)

    elif args.command == 'console':
        from quantum.runtime.ui_console import run_console
        sys.exit(run_console(args.config, args.path))

    elif args.command == 'check':
        from quantum.cli.check import run_check
        sys.exit(run_check(args.config))

    elif args.command == 'test':
        from quantum.runtime.app_testing import run_tests
        sys.exit(run_tests(args.paths))

    elif args.command == 'desktop':
        from quantum.runtime.ui_desktop import run_desktop
        sys.exit(run_desktop(args.config, args.path, width=args.width, height=args.height))

    elif args.command == 'admin':
        from quantum.cli.admin import handle_admin
        sys.exit(handle_admin(args))

    # Handle 'stop' command
    elif args.command == 'stop':
        from quantum.cli.server_process import stop_server
        sys.exit(stop_server())

    # Handle 'run' command
    elif args.command == 'run':
        if not args.file:
            print("[ERROR] File argument is required for 'run' command")
            print("Usage: quantum run <file.q>")
            sys.exit(1)

        runner = QuantumRunner(config=load_config(getattr(args, 'config', 'quantum.config.yaml')))
        runner._ui_target = getattr(args, 'target', 'html')
        runner._game_engine = getattr(args, 'engine', 'pixi')
        exit_code = runner.run(args.file, getattr(args, 'debug', False))
        sys.exit(exit_code)

    # Handle 'jobs' command
    elif args.command == 'jobs':
        if not jobs_available:
            print("[ERROR] Jobs functionality not available.")
            print(f"Error: {handle_jobs}")
            sys.exit(1)
        sys.exit(handle_jobs(args))

    # Handle 'mq' command
    elif args.command == 'mq':
        if not mq_available:
            print("[ERROR] Message queue functionality not available.")
            print(f"Error: {handle_mq}")
            sys.exit(1)
        sys.exit(handle_mq(args))

    # Handle 'pkg' command
    elif args.command == 'pkg':
        if not pkg_available:
            print("[ERROR] Package functionality not available.")
            print(f"Error: {handle_pkg}")
            sys.exit(1)
        sys.exit(handle_pkg(args))

    # Handle 'migrate' command
    elif args.command == 'migrate':
        migrate_available, result = _get_migrate_module()
        if not migrate_available:
            print(f"[ERROR] Migration functionality not available: {result}")
            sys.exit(1)

        MigrationRunner = result

        try:
            runner = MigrationRunner(datasource=getattr(args, 'datasource', None))

            if args.migrate_command == 'status':
                status = runner.status()
                print(f"\nDatabase: {status['database_type']}")
                print(f"Applied migrations: {status['total_applied']}")
                print(f"Pending migrations: {status['total_pending']}")

                if status['applied']:
                    print("\nApplied:")
                    for m in status['applied']:
                        print(f"  {m['version']}: {m['name']} (applied: {m['applied_at']})")

                if status['pending']:
                    print("\nPending:")
                    for m in status['pending']:
                        print(f"  {m['version']}: {m['name']}")

            elif args.migrate_command == 'up':
                results = runner.up(count=getattr(args, 'count', None))
                applied = sum(1 for r in results if r.get('status') == 'applied')
                failed = sum(1 for r in results if r.get('status') == 'failed')
                print(f"\nApplied: {applied}, Failed: {failed}")
                if failed:
                    sys.exit(1)

            elif args.migrate_command == 'down':
                results = runner.down(count=getattr(args, 'count', 1))
                rolled_back = sum(1 for r in results if r.get('status') == 'rolled_back')
                failed = sum(1 for r in results if r.get('status') == 'failed')
                print(f"\nRolled back: {rolled_back}, Failed: {failed}")
                if failed:
                    sys.exit(1)

            elif args.migrate_command == 'plan':
                from quantum.cli.schema_plan import run_plan
                sys.exit(run_plan(Path.cwd(), args.schema, args.write, args.yes, args.allow_data_loss,
                                  interactive=sys.stdin.isatty()))

            elif args.migrate_command == 'create':
                filepath = runner.create(args.name)
                print(f"Created migration: {filepath}")
                print(f"Also created rollback: {filepath.with_suffix('.down.sql')}")

            else:
                print("Usage: quantum migrate <status|up|down|create|plan> [options]")
                sys.exit(1)

            sys.exit(0)

        except Exception as e:
            print(f"[ERROR] Migration failed: {e}")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
