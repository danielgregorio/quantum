"""
JavaScript Code Generator

Generates JavaScript code from parsed MXML/AS4 AST
"""

import json
from typing import Dict
from .mxml_parser import Application, Component
from .as4_parser import AS4Parser, AS4AST, Variable, Function


class JSCodeGen:
    """Generate JavaScript from MXML/AS4 AST"""

    def generate(self, app: Application) -> Dict[str, str]:
        """
        Generate all output files

        Returns:
            Dict with file names and contents:
            - app.js: Main application JavaScript
            - index.html: HTML entry point
            - styles.css: Extracted styles
        """
        return {
            'app.js': self._generate_app_js(app),
            'index.html': self._generate_html(app),
            'styles.css': app.style
        }

    def _generate_app_js(self, app: Application) -> str:
        """Generate main JavaScript file"""
        lines = []

        # 1. Import reactive runtime
        lines.append("import { ReactiveRuntime } from './reactive-runtime.js';")
        lines.append("")

        # 2. Parse ActionScript
        as4_parser = AS4Parser()
        as4_ast = as4_parser.parse(app.script)

        # 3. Generate imports
        if as4_ast.imports:
            lines.append("// ActionScript imports")
            for imp in as4_ast.imports:
                # Convert AS4 import to JS import (simplified)
                # quantum.http.fetch → ./quantum/http/fetch.js
                js_path = imp.replace('.', '/')
                lines.append(f"import {{ {imp.split('.')[-1]} }} from './{js_path}.js';")
            lines.append("")

        # 4. Generate component tree as data
        lines.append("// UI Component Tree")
        lines.append("const componentTree = " + self._component_to_json(app.ui) + ";")
        lines.append("")

        # 5. Generate Application class
        lines.append("// Application Class (from ActionScript)")
        lines.append("class App {")
        lines.append("  constructor(runtime) {")
        lines.append("    this.runtime = runtime;")
        lines.append("")

        # Generate state variables
        for var in as4_ast.variables:
            value = var.value or 'null'
            lines.append(f"    this.{var.name} = {value};")

            # If bindable, set up reactivity
            if var.is_bindable:
                lines.append(f"    this._bindable_{var.name} = true;")

        lines.append("  }")
        lines.append("")

        # Generate methods
        for func in as4_ast.functions:
            # Convert parameters
            param_names = [p.name for p in func.params]
            param_str = ', '.join(param_names)

            # Async or regular function
            func_keyword = 'async ' if func.is_async else ''

            lines.append(f"  {func_keyword}{func.name}({param_str}) {{")

            # Transpile function body (simple for now - just copy)
            body_lines = self._transpile_body(func.body)
            for body_line in body_lines:
                lines.append(f"    {body_line}")

            lines.append("  }")
            lines.append("")

        # Add reactive setter/getter for bindable properties
        for var in as4_ast.variables:
            if var.is_bindable:
                lines.append(f"  // Reactive getter/setter for {var.name}")
                lines.append(f"  get {var.name}() {{")
                lines.append(f"    return this._{var.name};")
                lines.append(f"  }}")
                lines.append(f"  set {var.name}(value) {{")
                lines.append(f"    this._{var.name} = value;")
                lines.append(f"    this.runtime.notifyChange('{var.name}', value);")
                lines.append(f"  }}")
                lines.append("")

        lines.append("}")
        lines.append("")

        # 6. Initialize application with reactive runtime
        lines.append("// Initialize and render")
        lines.append("const runtime = new ReactiveRuntime();")
        lines.append("const app = new App(runtime);")
        lines.append("runtime.setApp(app);  // Makes app reactive with Proxy")
        lines.append("runtime.registerHealthCheck();  // Enable health monitoring")
        lines.append("runtime.render(componentTree, document.getElementById('app'));")

        return '\n'.join(lines)

    def _component_to_json(self, component: Component, indent: int = 2) -> str:
        """Convert Component tree to JSON string"""

        def component_to_dict(c: Component) -> dict:
            return {
                'type': c.type,
                'props': c.props,
                'events': c.events,
                'children': [component_to_dict(child) for child in c.children]
            }

        return json.dumps(component_to_dict(component), indent=indent)

    def _transpile_body(self, body: str) -> list:
        """
        Transpile ActionScript function body to JavaScript

        Simplified approach: Just add 'this.' to known instance variables
        More sophisticated parsing can be added later
        """
        import re

        lines = []

        for line in body.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Skip comment lines entirely
            if line.startswith('//'):
                lines.append(line)
                continue

            # Handle inline comments - split line into code and comment
            comment_part = ""
            code_part = line
            if '//' in line:
                # Find comment (but not in strings)
                parts_temp = re.split(r'("(?:[^"\\]|\\.)*")', line)
                for i, part in enumerate(parts_temp):
                    if i % 2 == 0 and '//' in part:  # Non-string part with comment
                        comment_idx = part.index('//')
                        # Reconstruct: everything before comment
                        code_part = ''.join(parts_temp[:i]) + part[:comment_idx]
                        comment_part = part[comment_idx:]
                        break

            # Simple transformations
            # trace() → console.log()
            code_part = code_part.replace('trace(', 'console.log(')

            # For now, use a simple regex approach that preserves strings
            # Replace bare identifiers with this.identifier (but not in strings)

            # Split by strings to avoid replacing inside them
            parts = re.split(r'("(?:[^"\\]|\\.)*")', code_part)

            for i in range(len(parts)):
                # Only process non-string parts (even indices)
                if i % 2 == 0:
                    # Add this. to identifiers that are NOT:
                    # - keywords
                    # - already prefixed with this.
                    # - followed by (  (function calls)
                    # - numbers

                    # JavaScript keywords that should NEVER have 'this.' prefix
                    keywords = {
                        'const', 'let', 'var', 'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break', 'continue',
                        'return', 'throw', 'try', 'catch', 'finally', 'function', 'class', 'extends', 'new', 'this', 'super',
                        'import', 'export', 'default', 'async', 'await', 'yield', 'typeof', 'instanceof', 'delete',
                        'void', 'in', 'of', 'with', 'debugger'
                    }

                    # JavaScript literals that should NEVER have 'this.' prefix
                    literals = {'true', 'false', 'null', 'undefined', 'NaN', 'Infinity'}

                    # Known global classes that are used as static members (don't prefix)
                    global_classes = {
                        'Alert', 'Math', 'Date', 'String', 'Number', 'Boolean', 'Array', 'Object',
                        'JSON', 'console', 'window', 'document', 'navigator', 'location'
                    }

                    # Match word boundaries for identifiers
                    def replace_identifier(match):
                        ident = match.group(1)
                        full_match = match.group(0)
                        start_pos = match.start()

                        # Get text before the identifier for context
                        before_text = parts[i][:start_pos]

                        # Don't prefix if preceded by dot (property access like items.length)
                        if before_text.rstrip().endswith('.'):
                            return full_match

                        # Don't prefix if after var/let/const declaration
                        words_before = before_text.strip().split()
                        if words_before and words_before[-1] in {'var', 'let', 'const'}:
                            return full_match

                        # Don't prefix JavaScript keywords
                        if ident in keywords:
                            return full_match

                        # Don't prefix JavaScript literals
                        if ident in literals:
                            return full_match

                        # Don't prefix global classes (likely static member access like Alert.show)
                        if ident in global_classes:
                            return full_match

                        # Check if already has this.
                        if full_match.startswith('this.'):
                            return full_match

                        # Add this. prefix for instance members
                        return f'this.{ident}'

                    # Replace identifiers: complete word + negative lookahead for : only
                    # This avoids adding this. to object literal keys: { id: value }
                    # But DOES add this. to function calls: myMethod() -> this.myMethod()
                    # Using \b at both ends ensures we match complete words
                    parts[i] = re.sub(r'\b([a-zA-Z_][\w]*)\b(?!\s*:)', replace_identifier, parts[i])

            line = ''.join(parts)

            # Add comment back if it was present
            if comment_part:
                line = line + ' ' + comment_part

            lines.append(line)

        return lines

    def _generate_html(self, app: Application) -> str:
        """Generate index.html"""
        title = app.ui.props.get('title', 'Quantum App')

        return f'''<!DOCTYPE html>
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


# Example usage
if __name__ == '__main__':
    from mxml_parser import MXMLParser

    mxml = '''<?xml version="1.0"?>
    <Application xmlns:fx="http://ns.adobe.com/mxml/2009"
                 xmlns:s="library://ns.adobe.com/flex/spark"
                 title="Hello World">
        <fx:Script>
            <![CDATA[
                [Bindable]
                private var message:String = "Hello World";

                private function handleClick():void {
                    message = "Button clicked!";
                }
            ]]>
        </fx:Script>

        <fx:Style>
            .title { font-size: 24px; }
        </fx:Style>

        <s:VBox padding="20" gap="15">
            <s:Label text="{message}" styleName="title"/>
            <s:Button label="Click Me" click="handleClick()"/>
        </s:VBox>
    </Application>
    '''

    # Parse MXML
    parser = MXMLParser()
    app = parser.parse_string(mxml)

    # Generate JavaScript
    codegen = JSCodeGen()
    output = codegen.generate(app)

    print("=== app.js ===")
    print(output['app.js'])
    print("\n=== index.html ===")
    print(output['index.html'])
