"""
Web Platform Compiler

Compiles Universal AST → HTML/CSS/JavaScript

Features:
- Multi-file MXML application support
- Reactive data binding
- Component-based architecture
- Optimized DOM rendering
"""

from pathlib import Path
from typing import Dict, List, Any
import json
import re

from ..universal_ast import (
    UniversalAST, UniversalComponent, ComponentProp,
    CodeAST, Variable, Function, AppInfo
)
from ..module_system import ModuleResolver, DependencyGraph


class WebCompiler:
    """Compiles Universal AST to Web (HTML/CSS/JS)"""

    def __init__(self, source_root: Path):
        self.source_root = source_root
        self.module_resolver = ModuleResolver(source_root)
        self.dep_graph = DependencyGraph()

        # Track all modules
        self.modules = {}  # file_path → Universal AST
        self.compiled_components = {}  # component_name → JS code

    def compile_application(self, entry_file: Path) -> Dict[str, str]:
        """
        Compile multi-file MXML application

        Returns:
            Dict with 'app.js', 'index.html', 'styles.css'
        """

        # 1. Resolve all modules and build dependency graph
        print(f"  → Resolving modules from {entry_file}...")
        all_files = self.module_resolver.resolve_dependencies(str(entry_file))

        print(f"     Found {len(all_files)} files")

        # 2. Parse all files to Universal AST (delegated to caller for now)
        # Note: In full implementation, we'd parse here
        # For now, we'll accept pre-parsed AST

        # 3. Compile in dependency order
        compilation_order = self.dep_graph.topological_sort()

        # 4. Generate output files
        return {
            'app.js': self._generate_app_js(entry_file),
            'index.html': self._generate_html(),
            'styles.css': self._generate_css(),
        }

    def compile_single_file(self, ast: UniversalAST) -> Dict[str, str]:
        """
        Compile single MXML file (legacy mode)

        Args:
            ast: UniversalAST from parser

        Returns:
            Dict with 'app.js', 'index.html', 'styles.css'
        """

        return {
            'app.js': self._generate_app_js_from_ast(ast),
            'index.html': self._generate_html_from_ast(ast),
            'styles.css': self._generate_css_from_ast(ast),
        }

    def _generate_app_js_from_ast(self, ast: UniversalAST) -> str:
        """Generate JavaScript from Universal AST"""

        lines = []

        # 1. Import reactive runtime
        lines.append("import { ReactiveRuntime } from './reactive-runtime.js';")
        lines.append("")

        # 2. Generate component tree (JSON)
        lines.append("// UI Component Tree")
        component_tree = self._universal_to_json_tree(ast.component_tree)
        lines.append(f"const componentTree = {json.dumps(component_tree, indent=2)};")
        lines.append("")

        # 3. Generate App class from code AST
        lines.append("// Application Class (from ActionScript)")
        lines.extend(self._generate_app_class(ast.code_ast))
        lines.append("")

        # 4. Initialize and render
        lines.append("// Initialize and render")
        lines.append("const runtime = new ReactiveRuntime();")
        lines.append("const app = new App(runtime);")
        lines.append("runtime.setApp(app);  // Makes app reactive with Proxy")
        lines.append("runtime.render(componentTree, document.getElementById('app'));")
        lines.append("")

        return '\n'.join(lines)

    def _generate_app_js(self, entry_file: Path) -> str:
        """Generate app.js for multi-file application (future)"""
        # TODO: Implement multi-file compilation
        # For now, fall back to single file
        return "// Multi-file compilation not yet implemented"

    def _universal_to_json_tree(self, component: UniversalComponent) -> Dict[str, Any]:
        """Convert UniversalComponent to JSON-serializable tree"""

        # Extract prop values
        props = {}
        for name, prop in component.props.items():
            props[name] = prop.value

        # Extract event handlers
        events = {}
        for name, handler in component.events.items():
            events[name] = handler

        # Recursively convert children
        children = [self._universal_to_json_tree(child) for child in component.children]

        return {
            'type': component.type,
            'props': props,
            'events': events,
            'children': children,
        }

    def _generate_app_class(self, code_ast: CodeAST) -> List[str]:
        """Generate JavaScript App class from CodeAST"""

        lines = []
        lines.append("class App {")
        lines.append("  constructor(runtime) {")
        lines.append("    this.runtime = runtime;")
        lines.append("")

        # Initialize variables
        for var in code_ast.variables:
            if var.initial_value:
                lines.append(f"    this.{var.name} = {self._transpile_value(var.initial_value)};")
            else:
                lines.append(f"    this.{var.name} = {self._default_value(var.type)};")

        lines.append("  }")
        lines.append("")

        # Generate methods
        for func in code_ast.functions:
            lines.extend(self._generate_method(func))
            lines.append("")

        lines.append("}")

        return lines

    def _generate_method(self, func: Function) -> List[str]:
        """Generate method from Function AST"""

        lines = []

        # Method signature
        params = ", ".join(p.name for p in func.parameters)
        async_keyword = "async " if func.is_async else ""
        lines.append(f"  {async_keyword}{func.name}({params}) {{")

        # Method body
        body_lines = self._transpile_body(func.body)
        for line in body_lines:
            lines.append(f"    {line}")

        lines.append("  }")

        return lines

    def _transpile_body(self, body: str) -> List[str]:
        """Transpile ActionScript function body to JavaScript"""

        lines = []

        for line in body.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Split by string literals to avoid replacing inside them
            parts = re.split(r'("(?:[^"\\]|\\.)*")', line)

            def replace_identifier(match):
                ident = match.group(1)

                # Don't replace keywords or built-in functions
                keywords = {'const', 'let', 'var', 'function', 'class', 'return',
                           'if', 'else', 'for', 'while', 'switch', 'case',
                           'await', 'async', 'try', 'catch', 'finally', 'throw',
                           'new', 'this', 'trace', 'console'}

                if ident in keywords:
                    return ident

                # Add 'this.' prefix for member access
                return f'this.{ident}'

            # Replace identifiers only in non-string parts
            for i in range(len(parts)):
                if i % 2 == 0:  # Non-string parts
                    # Replace variables with this.variable
                    parts[i] = re.sub(r'\b([a-zA-Z_]\w*)(?!\s*\()', replace_identifier, parts[i])

            line = ''.join(parts)

            # trace() → console.log()
            line = line.replace('trace(', 'console.log(')

            # Remove type annotations: var x:int → var x
            line = re.sub(r':(\w+)(?=\s*[=;,)])', '', line)

            lines.append(line)

        return lines

    def _transpile_value(self, value: str) -> str:
        """Transpile ActionScript value to JavaScript"""

        # String literals
        if value.startswith('"') or value.startswith("'"):
            return value

        # Numbers
        if value.replace('.', '').replace('-', '').isdigit():
            return value

        # Booleans
        if value in ('true', 'false'):
            return value

        # null/undefined
        if value == 'null':
            return 'null'

        # Arrays
        if value.startswith('['):
            return value

        # Objects
        if value.startswith('{'):
            return value

        # new Vector.<Type>() → []
        if 'new Vector' in value:
            return '[]'

        return value

    def _default_value(self, type_name: str) -> str:
        """Get default value for type"""

        defaults = {
            'int': '0',
            'Number': '0',
            'String': '""',
            'Boolean': 'false',
            'Array': '[]',
            'Vector': '[]',
            'Object': '{}',
        }

        return defaults.get(type_name, 'null')

    def _generate_html_from_ast(self, ast: UniversalAST) -> str:
        """Generate index.html from Universal AST"""

        title = ast.app_info.title or "Quantum MXML Application"

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="flex-theme.css">
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div id="app"></div>
    <script type="module" src="app.js"></script>
</body>
</html>'''

        return html

    def _generate_html(self) -> str:
        """Generate index.html for multi-file app"""
        return self._generate_html_from_ast(UniversalAST(
            app_info=AppInfo(title="Quantum MXML Application"),
            component_tree=UniversalComponent("Application", {}, {}, []),
            code_ast=CodeAST([], []),
            styles={},
            assets={},
            bindings=[],
            events=[]
        ))

    def _generate_css_from_ast(self, ast: UniversalAST) -> str:
        """Generate CSS from Universal AST styles"""

        lines = []

        # Default styles
        lines.append("/* Quantum MXML Styles */")
        lines.append("")
        lines.append("* {")
        lines.append("    margin: 0;")
        lines.append("    padding: 0;")
        lines.append("    box-sizing: border-box;")
        lines.append("}")
        lines.append("")
        lines.append("body {")
        lines.append("    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;")
        lines.append("    background-color: #f5f5f5;")
        lines.append("}")
        lines.append("")
        lines.append("#app {")
        lines.append("    width: 100%;")
        lines.append("    min-height: 100vh;")
        lines.append("    display: flex;")
        lines.append("    justify-content: center;")
        lines.append("    align-items: center;")
        lines.append("}")
        lines.append("")

        # Custom styles from MXML
        if ast.styles:
            lines.append("/* Custom Styles */")
            for selector, rules in ast.styles.items():
                lines.append(f"{selector} {{")
                for prop, value in rules.items():
                    lines.append(f"    {prop}: {value};")
                lines.append("}")
                lines.append("")

        return '\n'.join(lines)

    def _generate_css(self) -> str:
        """Generate CSS for multi-file app"""
        return self._generate_css_from_ast(UniversalAST(
            app_info=AppInfo(),
            component_tree=UniversalComponent("Application", {}, {}, []),
            code_ast=CodeAST([], []),
            styles={},
            assets={},
            bindings=[],
            events=[]
        ))
