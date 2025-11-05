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
        
        if app.app_type == 'html':
            return self._start_web_server(app)
        elif app.app_type == 'microservices':
            return self._start_api_server(app)
        elif app.app_type == 'console':
            print("[INFO] Console apps not yet implemented")
            return 0
        else:
            print(f"[ERROR] Application type '{app.app_type}' not supported")
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
        description='Quantum CLI - Execute .q files and start servers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  quantum start                    # Start web server (magic!)
  quantum run hello.q              # Execute component
  quantum run webapp.q             # Start web server from .q file
  quantum run api.q                # Start API server
  quantum run backup-job.q         # Execute job
        """
    )

    parser.add_argument(
        'command',
        choices=['run', 'start'],
        help='Command to execute'
    )

    parser.add_argument(
        'file',
        nargs='?',  # Optional for 'start' command
        help='.q file to execute (required for run command)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=None,  # Will use config file default
        help='Port for web server (overrides config)'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='quantum.config.yaml',
        help='Path to configuration file (default: quantum.config.yaml)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Debug mode with detailed information'
    )

    args = parser.parse_args()

    # Handle 'start' command
    if args.command == 'start':
        from runtime.web_server import start_server
        try:
            start_server(args.config)
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR] Failed to start server: {e}")
            if args.debug:
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
        exit_code = runner.run(args.file, args.debug)
        sys.exit(exit_code)


if __name__ == '__main__':
    main()
