"""
CLI Compiler - Compiles MXML to command-line Python applications

This compiler generates standalone Python scripts that run in the terminal
with text-based UI, maintaining full compatibility with the component architecture.

Usage:
    from compiler.compilers.cli import compile_mxml_to_cli
    compile_mxml_to_cli('examples/hello.mxml', 'dist_cli/hello.py')
"""

import os
import json
from ..mxml_parser import MXMLParser
from ..ast_bridge import ASTBridge


def generate_python_from_code_ast(code_ast) -> str:
    """
    Generate Python code from CodeAST

    Args:
        code_ast: CodeAST instance

    Returns:
        Python code as string
    """
    lines = []

    # Generate variables
    for var in code_ast.variables:
        if var.is_bindable:
            lines.append(f'        # [Bindable]')

        # Convert value
        value = var.initial_value
        if value == 'null':
            value = 'None'
        elif value == 'true':
            value = 'True'
        elif value == 'false':
            value = 'False'

        lines.append(f'        self.{var.name} = {value}')

    # Add blank line if we have functions
    if code_ast.functions:
        lines.append('')

    # Generate functions
    for func in code_ast.functions:
        # Convert function body
        body_lines = func.body.split('\n')
        python_body = []

        for line in body_lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue

            # Remove semicolons
            line = line.rstrip(';')

            # Convert ActionScript to Python
            line = line.replace('trace(', 'print(')

            # Remove var/let/const
            line = line.replace('var ', '').replace('let ', '').replace('const ', '')

            # Add self. for property references
            import re

            # Process assignment lines
            if '=' in line and not line.startswith('#'):
                parts = line.split('=', 1)
                left = parts[0].strip()
                right = parts[1].strip() if len(parts) > 1 else ''

                # Add self. to left side if it's an identifier
                if left and not left.startswith('self.') and re.match(r'^[a-zA-Z_]\w*$', left):
                    left = f'self.{left}'

                # Add self. to identifiers on right side
                def replace_ident(match):
                    ident = match.group(0)
                    keywords = {'True', 'False', 'None', 'self', 'print'}
                    if ident in keywords or ident.startswith('self.') or ident.isdigit():
                        return ident
                    return f'self.{ident}'

                # Replace identifiers in right side
                # Split by string literals to avoid replacing inside strings
                parts_to_process = []
                in_string = False
                quote_char = None
                current = ''

                for char in right:
                    if char in ('"', "'") and (not quote_char or char == quote_char):
                        if not in_string:
                            # Process what we have so far
                            if current:
                                current = re.sub(r'\b([a-zA-Z_]\w*)\b', replace_ident, current)
                                parts_to_process.append(current)
                                current = ''
                            quote_char = char
                            in_string = True
                            parts_to_process.append(char)
                        else:
                            parts_to_process.append(current + char)
                            current = ''
                            in_string = False
                            quote_char = None
                    else:
                        current += char

                # Process remaining
                if current:
                    if in_string:
                        parts_to_process.append(current)
                    else:
                        current = re.sub(r'\b([a-zA-Z_]\w*)\b', replace_ident, current)
                        parts_to_process.append(current)

                right = ''.join(parts_to_process)

                line = f'{left} = {right}'
            else:
                # For non-assignment lines, still add self. to property references
                if '"' not in line and "'" not in line:
                    def replace_ident(match):
                        ident = match.group(0)
                        keywords = {'True', 'False', 'None', 'self', 'print', 'if', 'else', 'for', 'while', 'return'}
                        if ident in keywords or ident.startswith('self.'):
                            return ident
                        return f'self.{ident}'

                    line = re.sub(r'\b([a-zA-Z_]\w*)\b', replace_ident, line)

            # Convert literals after self. processing
            line = line.replace('true', 'True')
            line = line.replace('false', 'False')
            line = line.replace('null', 'None')

            python_body.append(f'            {line}')

        # Write function definition
        lines.append(f'    def {func.name}(self, *args):')
        if python_body:
            lines.extend(python_body)
        else:
            lines.append('            pass')
        lines.append('')

    return '\n'.join(lines)


def generate_python_app(component_tree: dict, script_code: str, title: str) -> str:
    """
    Generate standalone Python CLI application

    Args:
        component_tree: Parsed MXML component tree
        script_code: ActionScript code converted to Python
        title: Application title

    Returns:
        Complete Python script as string
    """

    # Generate component tree JSON
    tree_json = json.dumps(component_tree, indent=4)

    # Generate Python script
    python_code = f'''#!/usr/bin/env python3
"""
CLI Application - Compiled from MXML

This file was automatically generated by the MXML-to-CLI compiler.
DO NOT EDIT THIS FILE MANUALLY - changes will be overwritten.
"""

import sys
import os

# Add runtime_cli to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from compiler.runtime_cli.reactive_runtime_cli import CLIReactiveRuntime, ReactiveObject


class Application:
    """Application class with user-defined methods and data"""

    def __init__(self):
        # Initialize properties
{script_code}


def main():
    """Main entry point"""

    # Component tree (parsed from MXML)
    component_tree = {tree_json}

    # Create runtime
    runtime = CLIReactiveRuntime()

    # Create application instance
    app = Application()

    # Make app reactive and bind to runtime
    runtime.app = app
    app._runtime = runtime

    # Render UI and start interactive loop
    runtime.render(component_tree, title="{title}")


if __name__ == '__main__':
    main()
'''

    return python_code


def compile_mxml_to_cli(input_file: str, output_file: str = None):
    """
    Compile MXML file to standalone CLI Python application

    Args:
        input_file: Path to .mxml file
        output_file: Path to output .py file (default: dist_cli/app.py)
    """

    print(f"🔨 Compiling {input_file} to CLI Python...")

    # Parse MXML
    parser = MXMLParser()
    legacy_app = parser.parse(input_file)

    # Convert to Universal AST
    bridge = ASTBridge()
    universal_ast = bridge.legacy_to_universal(legacy_app)

    # Extract component tree (need to convert to dict format for CLI runtime)
    component_tree = universal_ast.component_tree

    # Convert UniversalComponent to dict recursively
    def component_to_dict(comp):
        # Convert props from ComponentProp objects to simple dict
        props_dict = {}
        for key, value in comp.props.items():
            # If value is a ComponentProp object, extract its value
            if hasattr(value, 'value'):
                props_dict[key] = value.value
            else:
                props_dict[key] = value

        result = {
            'type': comp.type,
            'props': props_dict,
            'events': {e.event_name: e.handler_function for e in universal_ast.events if e.component_id == comp.id},
            'children': [component_to_dict(child) for child in comp.children]
        }
        return result

    component_tree_dict = component_to_dict(component_tree)

    # Get title from Application node
    title = universal_ast.app_info.title or "MXML Application"

    # Convert CodeAST to Python script
    python_script = generate_python_from_code_ast(universal_ast.code_ast)

    # Generate Python application
    python_app = generate_python_app(component_tree_dict, python_script, title)

    # Determine output file
    if output_file is None:
        output_file = 'dist_cli/app.py'

    # Create output directory
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)

    # Write Python file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(python_app)

    # Make executable
    os.chmod(output_file, 0o755)

    print(f"✅ CLI application compiled successfully!")
    print(f"   Output: {output_file}")
    print(f"\n   To run:")
    print(f"     python3 {output_file}")

    return output_file
