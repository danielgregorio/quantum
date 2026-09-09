"""
Quantum Admin - Component Test Generator

Analyzes a .q component file and generates pytest test code
based on the component's structure (actions, queries, feature tags).
"""
import os
import re
from datetime import datetime


class ComponentTestGenerator:
    def __init__(self, component_path, base_dir):
        self.component_path = component_path
        self.base_dir = base_dir
        self.full_path = os.path.join(base_dir, 'components', component_path)
        self.content = ''
        self.component_name = ''
        self.actions = []
        self.queries = []
        self.feature_tags = set()

    def analyze(self):
        """Parse the .q file and extract structure."""
        if not os.path.isfile(self.full_path):
            return

        with open(self.full_path, 'r', encoding='utf-8', errors='ignore') as f:
            self.content = f.read()

        # Component name
        m = re.search(r'<q:component\s+name="([^"]+)"', self.content)
        if m:
            self.component_name = m.group(1)
        else:
            self.component_name = os.path.splitext(os.path.basename(self.component_path))[0]

        # Actions with their params
        self.actions = []
        action_pattern = re.compile(
            r'<q:action\s+name="([^"]+)"[^>]*>(.*?)</q:action>',
            re.DOTALL
        )
        param_pattern = re.compile(
            r'<q:param\s+([^>]+)/>'
        )
        for am in action_pattern.finditer(self.content):
            action_name = am.group(1)
            action_body = am.group(2)
            params = []
            for pm in param_pattern.finditer(action_body):
                attrs = pm.group(1)
                pname = ''
                ptype = 'string'
                prequired = False
                nm = re.search(r'name="([^"]+)"', attrs)
                if nm:
                    pname = nm.group(1)
                tm = re.search(r'type="([^"]+)"', attrs)
                if tm:
                    ptype = tm.group(1)
                if 'required="true"' in attrs:
                    prequired = True
                if pname:
                    params.append({
                        'name': pname,
                        'type': ptype,
                        'required': prequired,
                    })
            self.actions.append({
                'name': action_name,
                'params': params,
            })

        # Queries
        self.queries = []
        query_pattern = re.compile(r'<q:query\s+name="([^"]+)"')
        for qm in query_pattern.finditer(self.content):
            self.queries.append(qm.group(1))

        # Feature tags
        tag_pattern = re.compile(r'<q:(\w+)')
        self.feature_tags = set(tag_pattern.findall(self.content))
        self.feature_tags.discard('component')
        self.feature_tags.discard('param')

    def generate(self):
        """Generate pytest code based on analysis."""
        lines = []
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sanitized = self.component_path.replace('/', '_').replace('.q', '')

        # Header
        lines.append(f'"""')
        lines.append(f'Auto-generated tests for {self.component_name}')
        lines.append(f'Component: components/{self.component_path}')
        lines.append(f'Generated: {ts}')
        lines.append(f'"""')
        lines.append(f'import os')
        lines.append(f'import sys')
        lines.append(f'import pytest')
        lines.append(f'')
        lines.append(f'# Setup path')
        lines.append(f"BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))")
        lines.append(f"sys.path.insert(0, os.path.join(BASE_DIR, 'src'))")
        lines.append(f'')
        lines.append(f"COMPONENT_PATH = os.path.join(BASE_DIR, 'components', '{self.component_path}')")
        lines.append(f'')

        # Smoke test class
        lines.append(f'class TestSmoke{self.component_name}:')
        lines.append(f'    """Smoke tests: verify the component parses without errors."""')
        lines.append(f'')
        lines.append(f'    def test_component_file_exists(self):')
        lines.append(f'        """Component .q file should exist on disk."""')
        lines.append(f'        assert os.path.isfile(COMPONENT_PATH), f"Component file not found: {{COMPONENT_PATH}}"')
        lines.append(f'')
        lines.append(f'    def test_parse_without_errors(self):')
        lines.append(f'        """Component should parse into a valid AST."""')
        lines.append(f'        from core.parser import QuantumParser')
        lines.append(f'        parser = QuantumParser()')
        lines.append(f'        with open(COMPONENT_PATH, "r", encoding="utf-8") as f:')
        lines.append(f'            source = f.read()')
        lines.append(f'        ast = parser.parse(source)')
        lines.append(f'        assert ast is not None, "Parser returned None"')
        lines.append(f'')

        # Action test classes
        for action in self.actions:
            aname = action['name']
            class_name = aname[0].upper() + aname[1:]
            lines.append(f'')
            lines.append(f'class TestAction{class_name}:')
            lines.append(f'    """Tests for action: {aname}"""')
            lines.append(f'')

            required_params = [p for p in action['params'] if p['required']]
            all_params = action['params']

            if all_params:
                lines.append(f'    def test_valid_params(self):')
                lines.append(f'        """Action {aname} should accept all required params."""')
                lines.append(f'        from core.parser import QuantumParser')
                lines.append(f'        parser = QuantumParser()')
                lines.append(f'        with open(COMPONENT_PATH, "r", encoding="utf-8") as f:')
                lines.append(f'            source = f.read()')
                lines.append(f'        ast = parser.parse(source)')
                lines.append(f'        # Verify the action node exists in AST')
                lines.append(f'        found = False')
                lines.append(f'        for node in getattr(ast, "children", getattr(ast, "statements", [])):')
                lines.append(f'            if hasattr(node, "name") and getattr(node, "name", None) == "{aname}":')
                lines.append(f'                found = True')
                lines.append(f'                break')
                lines.append(f'        assert found, "Action {aname} not found in AST"')
                lines.append(f'')

            for param in required_params:
                pname = param['name']
                lines.append(f'    def test_missing_{pname}(self):')
                lines.append(f'        """Omitting required param {pname} should be detectable."""')
                lines.append(f'        # The action requires "{pname}" — verifying param definition exists')
                lines.append(f'        import re')
                lines.append(f'        with open(COMPONENT_PATH, "r", encoding="utf-8") as f:')
                lines.append(f'            source = f.read()')
                lines.append(f'        pattern = r\'<q:param\\s+[^>]*name="{pname}"[^>]*required="true"\'')
                lines.append(f'        assert re.search(pattern, source), "Required param {pname} not found in component"')
                lines.append(f'')

        # Query test classes
        for qname in self.queries:
            class_name = qname[0].upper() + qname[1:]
            lines.append(f'')
            lines.append(f'class TestQuery{class_name}:')
            lines.append(f'    """Tests for query: {qname}"""')
            lines.append(f'')
            lines.append(f'    def test_query_node_exists(self):')
            lines.append(f'        """AST should contain a QueryNode with name={qname}."""')
            lines.append(f'        from core.parser import QuantumParser')
            lines.append(f'        from core.ast_nodes import QueryNode')
            lines.append(f'        parser = QuantumParser()')
            lines.append(f'        with open(COMPONENT_PATH, "r", encoding="utf-8") as f:')
            lines.append(f'            source = f.read()')
            lines.append(f'        ast = parser.parse(source)')
            lines.append(f'        # Walk AST to find QueryNode')
            lines.append(f'        def find_queries(node):')
            lines.append(f'            results = []')
            lines.append(f'            if isinstance(node, QueryNode):')
            lines.append(f'                results.append(node)')
            lines.append(f'            for child in getattr(node, "children", getattr(node, "statements", [])):')
            lines.append(f'                results.extend(find_queries(child))')
            lines.append(f'            return results')
            lines.append(f'        queries = find_queries(ast)')
            lines.append(f'        names = [getattr(q, "name", "") for q in queries]')
            lines.append(f'        assert "{qname}" in names, f"QueryNode {qname} not found. Found: {{names}}"')
            lines.append(f'')

        # Summary
        lines.append(f'')
        lines.append(f'# Summary: {len(self.actions)} action(s), {len(self.queries)} query/queries, tags: {", ".join(sorted(self.feature_tags)) or "none"}')
        lines.append(f'')

        return '\n'.join(lines)
