/**
 * Quantum Playground - Pyodide Web Worker
 *
 * Runs Pyodide in a separate thread to avoid blocking the UI.
 * This is optional but recommended for better user experience.
 */

// Pyodide instance
let pyodide = null;
let isReady = false;

// Quantum parser code
const QUANTUM_PARSER_CODE = `
# Quantum Parser - Browser version for Pyodide
# Simplified version of the full parser for playground use

import re
from xml.etree import ElementTree as ET
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# AST Nodes (simplified)

class QuantumNode:
    def to_dict(self) -> Dict[str, Any]:
        return {}

@dataclass
class TextNode(QuantumNode):
    content: str
    has_databinding: bool = False

    def __post_init__(self):
        self.has_databinding = '{' in self.content and '}' in self.content

    def to_dict(self):
        return {"type": "text", "content": self.content}

@dataclass
class HTMLNode(QuantumNode):
    tag: str
    attributes: Dict[str, str]
    children: List[QuantumNode]
    self_closing: bool = False

    def to_dict(self):
        return {
            "type": "html",
            "tag": self.tag,
            "attributes": self.attributes,
            "children": [c.to_dict() for c in self.children]
        }

@dataclass
class SetNode(QuantumNode):
    name: str
    value: Optional[str] = None
    var_type: str = "string"
    default: Optional[str] = None

    def to_dict(self):
        return {"type": "set", "name": self.name, "value": self.value}

@dataclass
class LoopNode(QuantumNode):
    loop_type: str
    var_name: str
    body: List[QuantumNode] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    step_value: int = 1
    items: Optional[str] = None
    delimiter: str = ","
    index_name: Optional[str] = None

    def __post_init__(self):
        if self.body is None:
            self.body = []

    def to_dict(self):
        return {
            "type": "loop",
            "loop_type": self.loop_type,
            "var_name": self.var_name,
            "from": self.from_value,
            "to": self.to_value,
            "items": self.items,
            "body": [s.to_dict() for s in self.body]
        }

@dataclass
class IfNode(QuantumNode):
    condition: str
    if_body: List[QuantumNode] = None
    elseif_blocks: List[tuple] = None
    else_body: List[QuantumNode] = None

    def __post_init__(self):
        if self.if_body is None:
            self.if_body = []
        if self.elseif_blocks is None:
            self.elseif_blocks = []
        if self.else_body is None:
            self.else_body = []

    def to_dict(self):
        return {
            "type": "if",
            "condition": self.condition,
            "if_body": [s.to_dict() for s in self.if_body],
            "else_body": [s.to_dict() for s in self.else_body]
        }

@dataclass
class ReturnNode(QuantumNode):
    value: str

    def to_dict(self):
        return {"type": "return", "value": self.value}

@dataclass
class ComponentNode(QuantumNode):
    name: str
    statements: List[QuantumNode] = None
    has_html: bool = False

    def __post_init__(self):
        if self.statements is None:
            self.statements = []

    def to_dict(self):
        return {
            "type": "component",
            "name": self.name,
            "statements": [s.to_dict() for s in self.statements]
        }

HTML_VOID_ELEMENTS = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr'
}

class QuantumParseError(Exception):
    pass

class QuantumParser:
    def __init__(self):
        self.quantum_ns = {'q': 'https://quantum.lang/ns'}

    def _inject_namespace(self, content: str) -> str:
        if 'xmlns:q' in content:
            return content
        pattern = r'<(q:component|q:application)(\\s+[^>]*)?>'
        def add_namespace(match):
            tag = match.group(1)
            attrs = match.group(2) or ''
            return f'<{tag}{attrs} xmlns:q="https://quantum.lang/ns">'
        return re.sub(pattern, add_namespace, content, count=1)

    def parse(self, source: str) -> QuantumNode:
        try:
            content = self._inject_namespace(source)
            root = ET.fromstring(content)
            return self._parse_root(root)
        except ET.ParseError as e:
            raise QuantumParseError(f"XML parse error: {e}")
        except Exception as e:
            raise QuantumParseError(f"Parse error: {e}")

    def _get_name(self, element: ET.Element) -> str:
        tag = element.tag
        if '}' in tag:
            return tag.split('}')[-1]
        if ':' in tag:
            return tag.split(':')[-1]
        return tag

    def _parse_root(self, root: ET.Element) -> QuantumNode:
        name = self._get_name(root)
        if name == 'component':
            return self._parse_component(root)
        else:
            raise QuantumParseError(f"Unknown root: {name}")

    def _parse_component(self, elem: ET.Element) -> ComponentNode:
        name = elem.get('name', 'Unnamed')
        comp = ComponentNode(name=name)
        for child in elem:
            stmt = self._parse_statement(child)
            if stmt:
                comp.statements.append(stmt)
                if isinstance(stmt, HTMLNode):
                    comp.has_html = True
        return comp

    def _parse_statement(self, elem: ET.Element) -> Optional[QuantumNode]:
        name = self._get_name(elem)
        if name == 'set':
            return self._parse_set(elem)
        elif name == 'loop':
            return self._parse_loop(elem)
        elif name == 'if':
            return self._parse_if(elem)
        elif name == 'return':
            return self._parse_return(elem)
        elif name in ('param', 'function'):
            return None
        elif self._is_html(elem):
            return self._parse_html(elem)
        return None

    def _parse_set(self, elem: ET.Element) -> SetNode:
        return SetNode(
            name=elem.get('name', ''),
            value=elem.get('value'),
            var_type=elem.get('type', 'string'),
            default=elem.get('default')
        )

    def _parse_loop(self, elem: ET.Element) -> LoopNode:
        loop_type = elem.get('type', 'range')
        var_name = elem.get('var', 'item')
        loop = LoopNode(loop_type=loop_type, var_name=var_name)
        if loop_type == 'range':
            loop.from_value = elem.get('from', '1')
            loop.to_value = elem.get('to', '10')
            try:
                loop.step_value = int(elem.get('step', '1'))
            except:
                loop.step_value = 1
        elif loop_type in ('array', 'list'):
            loop.items = elem.get('items')
            loop.delimiter = elem.get('delimiter', ',')
            loop.index_name = elem.get('index')
        if elem.text and elem.text.strip():
            loop.body.append(TextNode(content=elem.text))
        for child in elem:
            stmt = self._parse_statement(child)
            if stmt:
                loop.body.append(stmt)
            if child.tail and child.tail.strip():
                loop.body.append(TextNode(content=child.tail))
        return loop

    def _parse_if(self, elem: ET.Element) -> IfNode:
        condition = elem.get('condition', 'true')
        if_node = IfNode(condition=condition)
        for child in elem:
            child_name = self._get_name(child)
            if child_name == 'elseif':
                elseif_cond = child.get('condition', 'true')
                elseif_body = []
                for gc in child:
                    stmt = self._parse_statement(gc)
                    if stmt:
                        elseif_body.append(stmt)
                if_node.elseif_blocks.append((elseif_cond, elseif_body))
            elif child_name == 'else':
                for gc in child:
                    stmt = self._parse_statement(gc)
                    if stmt:
                        if_node.else_body.append(stmt)
            else:
                stmt = self._parse_statement(child)
                if stmt:
                    if_node.if_body.append(stmt)
        return if_node

    def _parse_return(self, elem: ET.Element) -> ReturnNode:
        return ReturnNode(value=elem.get('value', ''))

    def _is_html(self, elem: ET.Element) -> bool:
        tag = elem.tag
        if '{https://quantum.lang/ns}' in tag:
            return False
        if tag.startswith('q:'):
            return False
        return True

    def _parse_html(self, elem: ET.Element) -> HTMLNode:
        tag = self._get_name(elem)
        attrs = dict(elem.attrib)
        children = []
        if elem.text and elem.text.strip():
            children.append(TextNode(content=elem.text))
        for child in elem:
            stmt = self._parse_statement(child)
            if stmt:
                children.append(stmt)
            if child.tail and child.tail.strip():
                children.append(TextNode(content=child.tail))
        return HTMLNode(
            tag=tag,
            attributes=attrs,
            children=children,
            self_closing=tag.lower() in HTML_VOID_ELEMENTS
        )

class HTMLGenerator:
    def __init__(self):
        self.variables = {}

    def generate(self, ast: QuantumNode) -> str:
        if isinstance(ast, ComponentNode):
            return self._gen_component(ast)
        return ""

    def _gen_component(self, comp: ComponentNode) -> str:
        parts = []
        for stmt in comp.statements:
            html = self._gen_statement(stmt)
            if html:
                parts.append(html)
        return '\\n'.join(parts)

    def _gen_statement(self, stmt: QuantumNode) -> str:
        if isinstance(stmt, SetNode):
            value = stmt.value or stmt.default or ''
            value = self._apply_binding(value)
            if stmt.var_type == 'number':
                try:
                    value = float(value) if '.' in str(value) else int(value)
                except:
                    value = 0
            elif stmt.var_type == 'boolean':
                value = str(value).lower() in ('true', '1', 'yes')
            elif stmt.var_type == 'array':
                if isinstance(value, str):
                    value = [v.strip() for v in value.split(',')]
            self.variables[stmt.name] = value
            return ""
        elif isinstance(stmt, LoopNode):
            return self._gen_loop(stmt)
        elif isinstance(stmt, IfNode):
            return self._gen_if(stmt)
        elif isinstance(stmt, ReturnNode):
            value = self._apply_binding(stmt.value)
            return f"<!-- return: {value} -->"
        elif isinstance(stmt, HTMLNode):
            return self._gen_html(stmt)
        elif isinstance(stmt, TextNode):
            return self._apply_binding(stmt.content)
        return ""

    def _gen_loop(self, loop: LoopNode) -> str:
        parts = []
        if loop.loop_type == 'range':
            try:
                start = int(self._apply_binding(loop.from_value or '1'))
                end = int(self._apply_binding(loop.to_value or '10'))
                step = loop.step_value or 1
                for i in range(start, end + 1, step):
                    self.variables[loop.var_name] = i
                    for stmt in loop.body:
                        html = self._gen_statement(stmt)
                        if html:
                            parts.append(html)
            except ValueError:
                pass
        elif loop.loop_type in ('array', 'list'):
            items_str = self._apply_binding(loop.items or '')
            if isinstance(items_str, list):
                items = items_str
            else:
                items = [i.strip() for i in str(items_str).split(loop.delimiter)]
            for idx, item in enumerate(items):
                self.variables[loop.var_name] = item
                if loop.index_name:
                    self.variables[loop.index_name] = idx
                for stmt in loop.body:
                    html = self._gen_statement(stmt)
                    if html:
                        parts.append(html)
        return '\\n'.join(parts)

    def _gen_if(self, if_node: IfNode) -> str:
        if self._eval_condition(if_node.condition):
            parts = []
            for stmt in if_node.if_body:
                html = self._gen_statement(stmt)
                if html:
                    parts.append(html)
            return '\\n'.join(parts)
        for cond, body in if_node.elseif_blocks:
            if self._eval_condition(cond):
                parts = []
                for stmt in body:
                    html = self._gen_statement(stmt)
                    if html:
                        parts.append(html)
                return '\\n'.join(parts)
        if if_node.else_body:
            parts = []
            for stmt in if_node.else_body:
                html = self._gen_statement(stmt)
                if html:
                    parts.append(html)
            return '\\n'.join(parts)
        return ""

    def _gen_html(self, node: HTMLNode) -> str:
        attrs_str = ''
        if node.attributes:
            attr_parts = []
            for k, v in node.attributes.items():
                v = self._apply_binding(v)
                attr_parts.append(f'{k}="{self._escape(str(v))}"')
            if attr_parts:
                attrs_str = ' ' + ' '.join(attr_parts)
        if node.self_closing:
            return f'<{node.tag}{attrs_str} />'
        children_html = ''
        for child in node.children:
            children_html += self._gen_statement(child)
        return f'<{node.tag}{attrs_str}>{children_html}</{node.tag}>'

    def _apply_binding(self, text: str) -> Any:
        if not text or not isinstance(text, str):
            return text
        if '{' not in text:
            return text
        def replace_var(match):
            expr = match.group(1).strip()
            if expr in self.variables:
                return str(self.variables[expr])
            if '.' in expr:
                parts = expr.split('.')
                value = self.variables.get(parts[0])
                for part in parts[1:]:
                    if isinstance(value, dict):
                        value = value.get(part, '')
                    else:
                        value = ''
                        break
                return str(value)
            if '[' in expr and ']' in expr:
                match_arr = re.match(r'(\\w+)\\[(\\d+)\\]', expr)
                if match_arr:
                    arr_name, idx = match_arr.groups()
                    arr = self.variables.get(arr_name, [])
                    if isinstance(arr, list) and int(idx) < len(arr):
                        return str(arr[int(idx)])
            try:
                eval_expr = expr
                for var_name, var_val in self.variables.items():
                    if var_name in eval_expr and isinstance(var_val, (int, float)):
                        eval_expr = re.sub(r'\\b' + var_name + r'\\b', str(var_val), eval_expr)
                if re.match(r'^[\\d\\s\\+\\-\\*\\/\\(\\)\\.]+$', eval_expr):
                    result = eval(eval_expr)
                    return str(result)
            except:
                pass
            return '{' + expr + '}'
        return re.sub(r'\\{([^}]+)\\}', replace_var, text)

    def _eval_condition(self, condition: str) -> bool:
        try:
            expr = condition
            for var_name, var_val in self.variables.items():
                if var_name in expr:
                    if isinstance(var_val, str):
                        expr = re.sub(r'\\b' + var_name + r'\\b', f'"{var_val}"', expr)
                    else:
                        expr = re.sub(r'\\b' + var_name + r'\\b', str(var_val), expr)
            return bool(eval(expr))
        except:
            return False

    def _escape(self, text: str) -> str:
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))

def compile_quantum(source: str) -> dict:
    try:
        parser = QuantumParser()
        ast = parser.parse(source)
        generator = HTMLGenerator()
        html = generator.generate(ast)
        return {
            "success": True,
            "html": html,
            "ast": ast.to_dict()
        }
    except QuantumParseError as e:
        return {
            "success": False,
            "error": str(e),
            "html": ""
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "html": ""
        }
`;

// Initialize Pyodide
async function initPyodide() {
    try {
        importScripts('https://cdn.jsdelivr.net/pyodide/v0.24.1/full/pyodide.js');

        pyodide = await loadPyodide({
            indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/'
        });

        // Load the Quantum parser
        await pyodide.runPythonAsync(QUANTUM_PARSER_CODE);

        isReady = true;

        self.postMessage({
            type: 'ready',
            message: 'Pyodide initialized successfully'
        });

    } catch (error) {
        self.postMessage({
            type: 'error',
            message: `Failed to initialize Pyodide: ${error.message}`
        });
    }
}

// Compile Quantum code
async function compile(source) {
    if (!isReady) {
        return {
            success: false,
            error: 'Pyodide not ready',
            html: ''
        };
    }

    try {
        // Escape single quotes in source
        const escapedSource = source.replace(/'/g, "\\'");

        const result = pyodide.runPython(`
import json
result = compile_quantum('''${escapedSource}''')
json.dumps(result)
`);

        return JSON.parse(result);

    } catch (error) {
        return {
            success: false,
            error: error.message,
            html: ''
        };
    }
}

// Handle messages from main thread
self.onmessage = async function(event) {
    const { type, payload, id } = event.data;

    switch (type) {
        case 'init':
            await initPyodide();
            break;

        case 'compile':
            const result = await compile(payload.source);
            self.postMessage({
                type: 'compiled',
                id: id,
                result: result
            });
            break;

        default:
            self.postMessage({
                type: 'error',
                message: `Unknown message type: ${type}`
            });
    }
};

// Auto-initialize
initPyodide();
