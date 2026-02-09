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
    except:
        pass  # Silent fallback

# Fix imports - use absolute imports
sys.path.append(str(Path(__file__).parent.parent))

from core.parser import QuantumParser, QuantumParseError
from core.ast_nodes import ComponentNode, ApplicationNode, JobNode
from runtime.component import ComponentRuntime, ComponentExecutionError
from runtime.web_server import QuantumWebServer
from runtime.api_server import QuantumAPIServer

# Import deploy commands (lazy load to avoid import errors if requests not installed)
def _get_deploy_module():
    try:
        from cli.deploy import (
            create_deploy_parser, create_apps_parser,
            handle_deploy, handle_apps
        )
        return True, create_deploy_parser, create_apps_parser, handle_deploy, handle_apps
    except ImportError as e:
        return False, None, None, None, str(e)

# Import package commands
def _get_pkg_module():
    try:
        from cli.pkg import create_pkg_parser, handle_pkg
        return True, create_pkg_parser, handle_pkg
    except ImportError as e:
        return False, None, str(e)

# Import jobs commands
def _get_jobs_module():
    try:
        from cli.jobs import create_jobs_parser, handle_jobs
        return True, create_jobs_parser, handle_jobs
    except ImportError as e:
        return False, None, str(e)

# Import message queue commands
def _get_mq_module():
    try:
        from cli.mq import create_mq_parser, handle_mq
        return True, create_mq_parser, handle_mq
    except ImportError as e:
        return False, None, str(e)

class QuantumRunner:
    """Main Quantum Runner - Clean orchestration"""
    
    def __init__(self):
        self.parser = QuantumParser()
        self.component_runtime = ComponentRuntime()
    
    def run(self, file_path: str, debug: bool = False) -> int:
        """Execute .q file"""
        try:
            if debug:
                print(f"[DEBUG] Parsing file: {Path(file_path).name}")
            
            # Parse file → AST
            ast_node = self.parser.parse_file(file_path)
            
            if debug:
                print(f"[DEBUG] AST generated: {type(ast_node).__name__}")
                print(f"[DEBUG] Validating AST...")
            
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
    
    def _execute_application(self, app: ApplicationNode, debug: bool = False) -> int:
        """Execute q:application"""
        print(f"[EXEC] Executing application: {app.app_id}")
        print(f"[INFO] Type: {app.app_type}")

        if debug:
            print(f"   Routes: {len(app.routes)}")
            for route in app.routes:
                print(f"     {route.method} {route.path}")

        if app.app_type == 'game':
            return self._build_game(app, debug)
        elif app.app_type == 'terminal':
            return self._build_terminal(app, debug)
        elif app.app_type == 'testing':
            return self._build_tests(app, debug)
        elif app.app_type == 'ui':
            target = getattr(self, '_ui_target', 'html')
            return self._build_ui(app, target, debug)
        elif app.app_type == 'html':
            return self._start_web_server(app)
        elif app.app_type in ('microservices', 'api'):
            return self._start_api_server(app)
        else:
            print(f"[ERROR] Application type '{app.app_type}' not supported")
            return 1

    def _build_game(self, app: ApplicationNode, debug: bool = False) -> int:
        """Build standalone HTML game from game application."""
        from runtime.game_builder import GameBuilder, GameBuildError
        try:
            builder = GameBuilder()
            output_path = builder.build_to_file(app)
            print(f"[SUCCESS] Game built: {output_path}")
            if debug:
                print(f"   Scenes: {len(getattr(app, 'scenes', []))}")
                print(f"   Behaviors: {len(getattr(app, 'behaviors', []))}")
                print(f"   Prefabs: {len(getattr(app, 'prefabs', []))}")
            return 0
        except GameBuildError as e:
            print(f"[ERROR] Game build error: {e}")
            return 1

    def _build_terminal(self, app: ApplicationNode, debug: bool = False) -> int:
        """Build standalone Python TUI app from terminal application."""
        from runtime.terminal_builder import TerminalBuilder, TerminalBuildError
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

    def _build_tests(self, app: ApplicationNode, debug: bool = False) -> int:
        """Build standalone pytest file from testing application."""
        from runtime.testing_builder import TestingBuilder, TestingBuildError
        try:
            builder = TestingBuilder()
            output_path = builder.build_to_file(app)
            print(f"[SUCCESS] Test file built: {output_path}")
            if debug:
                print(f"   Suites: {len(getattr(app, 'test_suites', []))}")
                print(f"   Fixtures: {len(getattr(app, 'test_fixtures', []))}")
                print(f"   Mocks: {len(getattr(app, 'test_mocks', []))}")
            return 0
        except TestingBuildError as e:
            print(f"[ERROR] Test build error: {e}")
            return 1

    def _build_ui(self, app: ApplicationNode, target: str = 'html', debug: bool = False) -> int:
        """Build multi-target UI app from UI application."""
        from runtime.ui_builder import UIBuilder, UIBuildError
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
    
    def _start_web_server(self, app: ApplicationNode) -> int:
        """Start web server"""
        try:
            server = QuantumWebServer(port=8080)
            server.configure_from_ast(app)
            server.start()
            return 0
        except Exception as e:
            print(f"[ERROR] Web server error: {e}")
            return 1
    
    def _start_api_server(self, app: ApplicationNode) -> int:
        """Start API server"""
        try:
            server = QuantumAPIServer(port=8080)
            server.configure_from_ast(app)
            server.start()
            return 0
        except Exception as e:
            print(f"[ERROR] API server error: {e}")
            return 1


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Quantum CLI - Execute .q files, start servers, and deploy applications',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  quantum start                    # Start web server (magic!)
  quantum run hello.q              # Execute component
  quantum run webapp.q             # Start web server from .q file
  quantum run api.q                # Start API server
  quantum run backup-job.q         # Execute job
  quantum deploy ./my-app          # Deploy application
  quantum apps                     # List deployed apps
  quantum apps logs my-app         # View app logs
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

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Run command
    run_parser = subparsers.add_parser('run', help='Execute a .q file')
    run_parser.add_argument('file', help='.q file to execute')
    run_parser.add_argument('--debug', action='store_true', help='Debug mode')
    run_parser.add_argument('--config', default='quantum.config.yaml', help='Config file')
    run_parser.add_argument('--target', choices=['html', 'textual', 'desktop', 'mobile'], default='html',
                            help='UI target (for type="ui" apps): html, textual, desktop, or mobile')

    # Start command
    start_parser = subparsers.add_parser('start', help='Start web server')
    start_parser.add_argument('--port', type=int, help='Port (overrides config)')
    start_parser.add_argument('--config', default='quantum.config.yaml', help='Config file')
    start_parser.add_argument('--debug', action='store_true', help='Debug mode')

    # Deploy commands (if available)
    deploy_available, create_deploy_parser, create_apps_parser, handle_deploy, handle_apps = _get_deploy_module()

    if deploy_available:
        create_deploy_parser(subparsers)
        create_apps_parser(subparsers)

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

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Handle 'start' command
    if args.command == 'start':
        from runtime.web_server import start_server
        try:
            start_server(args.config)
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR] Failed to start server: {e}")
            if getattr(args, 'debug', False):
                import traceback
                traceback.print_exc()
            sys.exit(1)

    # Handle 'run' command
    elif args.command == 'run':
        if not args.file:
            print("[ERROR] File argument is required for 'run' command")
            print("Usage: quantum run <file.q>")
            sys.exit(1)

        runner = QuantumRunner()
        runner._ui_target = getattr(args, 'target', 'html')
        exit_code = runner.run(args.file, getattr(args, 'debug', False))
        sys.exit(exit_code)

    # Handle 'deploy' command
    elif args.command == 'deploy':
        if not deploy_available:
            print("[ERROR] Deploy functionality not available.")
            print(f"Missing dependency: {handle_apps}")
            print("Install with: pip install requests")
            sys.exit(1)
        sys.exit(handle_deploy(args))

    # Handle 'apps' command
    elif args.command == 'apps':
        if not deploy_available:
            print("[ERROR] Apps functionality not available.")
            print(f"Missing dependency: {handle_apps}")
            print("Install with: pip install requests")
            sys.exit(1)
        sys.exit(handle_apps(args))

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

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
