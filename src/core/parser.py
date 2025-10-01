"""
Quantum Parser - Convert .q files (XML) to Quantum AST
"""

import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from typing import Union, Optional, List

# Fix imports
sys.path.append(str(Path(__file__).parent.parent))

from core.ast_nodes import (
    QuantumNode, ComponentNode, ApplicationNode, JobNode,
    QuantumParam, QuantumReturn, QuantumRoute, IfNode, LoopNode, SetNode
)

class QuantumParseError(Exception):
    """Quantum parsing error"""
    pass

class QuantumParser:
    """Main parser for .q files"""
    
    def __init__(self):
        self.quantum_ns = {'q': 'https://quantum.lang/ns'}
    
    def parse_file(self, file_path: str) -> QuantumNode:
        """Parse .q file and return AST"""
        path = Path(file_path)
        
        if not path.exists():
            raise QuantumParseError(f"File not found: {file_path}")
        
        if not path.suffix == '.q':
            raise QuantumParseError(f"Invalid extension: {path.suffix}, expected .q")
        
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            return self._parse_root_element(root, path)
        
        except ET.ParseError as e:
            raise QuantumParseError(f"XML parse error: {e}")
        except Exception as e:
            raise QuantumParseError(f"Unexpected error: {e}")
    
    def _parse_root_element(self, root: ET.Element, path: Path) -> QuantumNode:
        """Parse root element based on type"""
        root_type = self._get_element_name(root)
        
        if root_type == 'component':
            return self._parse_component(root, path)
        elif root_type == 'application':
            return self._parse_application(root, path)
        elif root_type == 'job':
            return self._parse_job(root, path)
        else:
            raise QuantumParseError(f"Unknown root element: {root_type}")
    
    def _get_element_name(self, element: ET.Element) -> str:
        """Extract element name removing namespace"""
        return element.tag.split('}')[-1] if '}' in element.tag else element.tag.split(':')[-1]
    
    def _find_element(self, parent: ET.Element, tag_name: str) -> Optional[ET.Element]:
        """Find element considering namespace"""
        # Try with namespace
        element = parent.find(f"q:{tag_name}", self.quantum_ns)
        if element is not None:
            return element
        
        # Try without namespace (fallback)
        return parent.find(tag_name)
    
    def _find_all_elements(self, parent: ET.Element, tag_name: str) -> list:
        """Find all elements considering namespace"""
        # Try with namespace
        elements = parent.findall(f"q:{tag_name}", self.quantum_ns)
        if elements:
            return elements
        
        # Try without namespace (fallback)
        return parent.findall(tag_name)
    
    def _parse_component(self, root: ET.Element, path: Path) -> ComponentNode:
        """Parse q:component"""
        name = root.get('name', path.stem)
        component_type = root.get('type', 'module')
        
        component = ComponentNode(name, component_type)
        
        # Parse q:param elements
        for param_el in self._find_all_elements(root, 'param'):
            param = self._parse_param(param_el)
            component.add_param(param)
        
        # Parse q:return elements
        for return_el in self._find_all_elements(root, 'return'):
            return_node = self._parse_return(return_el)
            component.add_return(return_node)
        
        # Parse q:script elements
        for script_el in self._find_all_elements(root, 'script'):
            script_content = script_el.text or ""
            component.add_script(script_content.strip())
        
        # Parse control flow statements (if, loop, set, etc)
        self._parse_control_flow_statements(root, component)
        
        return component
    
    def _parse_control_flow_statements(self, parent: ET.Element, component: ComponentNode):
        """Parse control flow statements like if, loop, set - ONLY direct children"""

        # Parse only direct children to avoid duplicates (children of loops/ifs are parsed separately)
        for child in parent:
            child_type = self._get_element_name(child)

            if child_type == 'if':
                if_node = self._parse_if_statement(child)
                component.add_statement(if_node)
            elif child_type == 'loop':
                loop_node = self._parse_loop_statement(child)
                component.add_statement(loop_node)
            elif child_type == 'set':
                set_node = self._parse_set_statement(child)
                component.add_statement(set_node)
    
    def _parse_if_statement(self, if_element: ET.Element) -> IfNode:
        """Parse q:if statement with elseif and else blocks"""
        condition = if_element.get('condition', '')
        if_node = IfNode(condition)
        
        current_block = 'if'  # Track which block we're in
        current_elseif_body = None
        
        for child in if_element:
            child_type = self._get_element_name(child)
            
            if child_type == 'elseif':
                # Start new elseif block and process its children
                elseif_condition = child.get('condition', '')
                current_elseif_body = []
                
                # Process children of elseif block
                for elseif_child in child:
                    statement = self._parse_statement(elseif_child)
                    if statement:
                        current_elseif_body.append(statement)
                
                if_node.add_elseif_block(elseif_condition, current_elseif_body)
                current_block = 'elseif'
            
            elif child_type == 'else':
                # Process children of else block
                for else_child in child:
                    statement = self._parse_statement(else_child)
                    if statement:
                        if_node.add_else_statement(statement)
                current_block = 'else'
            
            else:
                # This is a statement in the main if block
                statement = self._parse_statement(child)
                if statement:
                    if_node.add_if_statement(statement)
        
        return if_node
    
    def _parse_loop_statement(self, loop_element: ET.Element) -> LoopNode:
        """Parse q:loop statement with various types"""
        loop_type = loop_element.get('type', 'range')
        var_name = loop_element.get('var')
        
        if not var_name:
            raise QuantumParseError("Loop requires 'var' attribute")
        
        loop_node = LoopNode(loop_type, var_name)
        
        # Configure based on loop type
        if loop_type == 'range':
            loop_node.from_value = loop_element.get('from')
            loop_node.to_value = loop_element.get('to')
            step = loop_element.get('step', '1')
            try:
                loop_node.step_value = int(step)
            except ValueError:
                loop_node.step_value = 1
        
        elif loop_type == 'array':
            loop_node.items = loop_element.get('items')
            loop_node.index_name = loop_element.get('index')
        
        elif loop_type == 'list':
            loop_node.items = loop_element.get('items')
            loop_node.delimiter = loop_element.get('delimiter', ',')
            loop_node.index_name = loop_element.get('index')
        
        # Parse loop body statements
        for child in loop_element:
            statement = self._parse_statement(child)
            if statement:
                loop_node.add_statement(statement)
        
        return loop_node

    def _parse_set_statement(self, set_element: ET.Element) -> SetNode:
        """Parse q:set statement"""
        name = set_element.get('name')

        if not name:
            raise QuantumParseError("Set requires 'name' attribute")

        set_node = SetNode(name)

        # Tipo e valor
        set_node.type = set_element.get('type', 'string')
        set_node.value = set_element.get('value')
        set_node.default = set_element.get('default')

        # Validação
        set_node.required = set_element.get('required', 'false').lower() == 'true'
        set_node.nullable = set_element.get('nullable', 'true').lower() == 'true'
        set_node.validate_rule = set_element.get('validate')
        set_node.pattern = set_element.get('pattern')
        set_node.mask = set_element.get('mask')
        set_node.range = set_element.get('range')
        set_node.enum = set_element.get('enum')
        set_node.unique = set_element.get('unique')
        set_node.min = set_element.get('min')
        set_node.max = set_element.get('max')
        set_node.minlength = set_element.get('minlength')
        set_node.maxlength = set_element.get('maxlength')

        # Comportamento
        set_node.scope = set_element.get('scope', 'local')
        set_node.operation = set_element.get('operation', 'assign')

        # Step para increment/decrement
        step = set_element.get('step', '1')
        try:
            set_node.step = int(step)
        except ValueError:
            set_node.step = 1

        # Para operações em collections
        set_node.index = set_element.get('index')
        set_node.key = set_element.get('key')
        set_node.source = set_element.get('source')

        return set_node

    def _parse_statement(self, element: ET.Element) -> Optional[QuantumNode]:
        """Parse individual statement (return, set, etc)"""
        element_type = self._get_element_name(element)

        if element_type == 'return':
            return self._parse_return(element)
        elif element_type == 'set':
            return self._parse_set_statement(element)
        elif element_type == 'loop':
            return self._parse_loop_statement(element)
        elif element_type == 'if':
            return self._parse_if_statement(element)

        return None
    
    def _parse_application(self, root: ET.Element, path: Path) -> ApplicationNode:
        """Parse q:application"""
        app_id = root.get('id', path.stem)
        app_type = root.get('type', 'html')
        
        app = ApplicationNode(app_id, app_type)
        
        # Parse q:route elements
        for route_el in self._find_all_elements(root, 'route'):
            route = self._parse_route(route_el)
            app.add_route(route)
        
        return app
    
    def _parse_job(self, root: ET.Element, path: Path) -> JobNode:
        """Parse q:job"""
        job_id = root.get('id', path.stem)
        schedule = root.get('schedule')
        
        return JobNode(job_id, schedule)
    
    def _parse_param(self, element: ET.Element) -> QuantumParam:
        """Parse q:param"""
        return QuantumParam(
            name=element.get('name', ''),
            type=element.get('type', 'string'),
            required=element.get('required', 'false').lower() == 'true',
            default=element.get('default'),
            validation=element.get('validation'),
            description=element.get('description')
        )
    
    def _parse_return(self, element: ET.Element) -> QuantumReturn:
        """Parse q:return"""
        return QuantumReturn(
            name=element.get('name'),
            type=element.get('type', 'string'),
            value=element.get('value', ''),
            description=element.get('description')
        )
    
    def _parse_route(self, element: ET.Element) -> QuantumRoute:
        """Parse q:route"""
        path = element.get('path', '/')
        method = element.get('method', 'GET').upper()
        
        route = QuantumRoute(path, method)
        
        # Parse q:return inside the route
        for return_el in self._find_all_elements(element, 'return'):
            return_node = self._parse_return(return_el)
            route.returns.append(return_node)
        
        return route
