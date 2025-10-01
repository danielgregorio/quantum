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
    QuantumParam, QuantumReturn, QuantumRoute, IfNode, LoopNode, SetNode,
    FunctionNode, DispatchEventNode, OnEventNode, RestConfig
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
        component_type = root.get('type', 'pure')

        component = ComponentNode(name, component_type)

        # Parse component-level attributes
        component.port = root.get('port')
        component.base_path = root.get('basePath')
        component.health_endpoint = root.get('health')
        component.metrics_provider = root.get('metrics')
        component.trace_provider = root.get('trace')

        # Parse q:param elements (component-level params)
        for param_el in self._find_all_elements(root, 'param'):
            param = self._parse_param(param_el)
            component.add_param(param)

        # Parse q:return elements (component-level returns)
        for return_el in self._find_all_elements(root, 'return'):
            return_node = self._parse_return(return_el)
            component.add_return(return_node)

        # Parse q:function elements
        for func_el in self._find_all_elements(root, 'function'):
            func = self._parse_function(func_el)
            component.add_function(func)

        # Parse q:onEvent elements
        for event_el in self._find_all_elements(root, 'onEvent'):
            event_handler = self._parse_on_event(event_el)
            component.add_event_handler(event_handler)

        # Parse q:script elements
        for script_el in self._find_all_elements(root, 'script'):
            script_content = script_el.text or ""
            component.add_script(script_content.strip())

        # Parse control flow statements (if, loop, set, dispatchEvent, etc)
        self._parse_control_flow_statements(root, component)

        return component
    
    def _parse_control_flow_statements(self, parent: ET.Element, component: ComponentNode):
        """Parse control flow statements like if, loop, set, dispatchEvent - ONLY direct children"""

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
            elif child_type == 'dispatchEvent':
                dispatch_node = self._parse_dispatch_event(child)
                component.add_statement(dispatch_node)
    
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
        """Parse individual statement (return, set, dispatchEvent, etc)"""
        element_type = self._get_element_name(element)

        if element_type == 'return':
            return self._parse_return(element)
        elif element_type == 'set':
            return self._parse_set_statement(element)
        elif element_type == 'loop':
            return self._parse_loop_statement(element)
        elif element_type == 'if':
            return self._parse_if_statement(element)
        elif element_type == 'dispatchEvent':
            return self._parse_dispatch_event(element)

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
        param = QuantumParam(
            name=element.get('name', ''),
            type=element.get('type', 'string'),
            required=element.get('required', 'false').lower() == 'true',
            default=element.get('default'),
            validation=element.get('validation'),
            description=element.get('description')
        )

        # REST-specific
        param.source = element.get('source', 'auto')

        # Validation
        param.validate_rule = element.get('validate')
        param.pattern = element.get('pattern')
        param.min = element.get('min')
        param.max = element.get('max')

        minlength_str = element.get('minlength')
        if minlength_str:
            try:
                param.minlength = int(minlength_str)
            except ValueError:
                pass

        maxlength_str = element.get('maxlength')
        if maxlength_str:
            try:
                param.maxlength = int(maxlength_str)
            except ValueError:
                pass

        param.range = element.get('range')
        param.enum = element.get('enum')

        # File upload
        param.maxsize = element.get('maxsize')
        param.accept = element.get('accept')

        return param
    
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

    def _parse_function(self, func_element: ET.Element) -> FunctionNode:
        """Parse q:function statement"""
        name = func_element.get('name')

        if not name:
            raise QuantumParseError("Function requires 'name' attribute")

        func_node = FunctionNode(name)

        # Core attributes
        func_node.return_type = func_element.get('returnType', 'any')
        func_node.scope = func_element.get('scope', 'component')
        func_node.access = func_element.get('access', 'public')
        func_node.description = func_element.get('description')
        func_node.hint = func_element.get('hint')

        # Validation
        func_node.validate_params = func_element.get('validate', 'false').lower() == 'true'

        # Performance
        cache_attr = func_element.get('cache')
        if cache_attr:
            if cache_attr.lower() == 'true':
                func_node.cache = True
            elif cache_attr.endswith('s'):  # "60s"
                func_node.cache = True
                try:
                    func_node.cache_ttl = int(cache_attr[:-1])
                except ValueError:
                    pass

        func_node.memoize = func_element.get('memoize', 'false').lower() == 'true'
        func_node.pure = func_element.get('pure', 'false').lower() == 'true'

        # Behavior
        func_node.async_func = func_element.get('async', 'false').lower() == 'true'

        retry_attr = func_element.get('retry')
        if retry_attr:
            try:
                func_node.retry = int(retry_attr)
            except ValueError:
                pass

        timeout_attr = func_element.get('timeout')
        if timeout_attr:
            func_node.timeout = timeout_attr

        # REST API (optional)
        endpoint = func_element.get('endpoint')
        if endpoint:
            method = func_element.get('method', 'GET')
            func_node.enable_rest(endpoint, method)

            # REST-specific attributes
            if func_element.get('produces'):
                func_node.rest_config.produces = func_element.get('produces')

            if func_element.get('consumes'):
                func_node.rest_config.consumes = func_element.get('consumes')

            if func_element.get('auth'):
                func_node.rest_config.auth = func_element.get('auth')

            if func_element.get('roles'):
                roles_str = func_element.get('roles')
                func_node.rest_config.roles = [r.strip() for r in roles_str.split(',')]

            if func_element.get('rateLimit'):
                func_node.rest_config.rate_limit = func_element.get('rateLimit')

            cors_attr = func_element.get('cors')
            if cors_attr and cors_attr.lower() == 'true':
                func_node.rest_config.cors = True

            status_attr = func_element.get('status')
            if status_attr:
                try:
                    func_node.rest_config.status = int(status_attr)
                except ValueError:
                    pass

        # Parse function params and body
        for child in func_element:
            child_type = self._get_element_name(child)

            if child_type == 'param':
                param = self._parse_param(child)
                func_node.add_param(param)
            else:
                # Parse body statements
                statement = self._parse_statement(child)
                if statement:
                    func_node.add_statement(statement)

        return func_node

    def _parse_dispatch_event(self, event_element: ET.Element) -> DispatchEventNode:
        """Parse q:dispatchEvent statement"""
        event = event_element.get('event')

        if not event:
            raise QuantumParseError("dispatchEvent requires 'event' attribute")

        dispatch_node = DispatchEventNode(event)

        # Optional attributes
        dispatch_node.data = event_element.get('data')
        dispatch_node.queue = event_element.get('queue')
        dispatch_node.exchange = event_element.get('exchange')
        dispatch_node.routing_key = event_element.get('routingKey')
        dispatch_node.priority = event_element.get('priority', 'normal')
        dispatch_node.delay = event_element.get('delay')
        dispatch_node.ttl = event_element.get('ttl')
        dispatch_node.metadata = event_element.get('metadata')

        return dispatch_node

    def _parse_on_event(self, event_element: ET.Element) -> OnEventNode:
        """Parse q:onEvent handler"""
        event = event_element.get('event')

        if not event:
            raise QuantumParseError("onEvent requires 'event' attribute")

        event_node = OnEventNode(event)

        # Optional attributes
        event_node.queue = event_element.get('queue')

        max_retries_attr = event_element.get('maxRetries')
        if max_retries_attr:
            try:
                event_node.max_retries = int(max_retries_attr)
            except ValueError:
                pass

        event_node.retry_delay = event_element.get('retryDelay')
        event_node.dead_letter = event_element.get('deadLetter')
        event_node.filter = event_element.get('filter')

        concurrent_attr = event_element.get('concurrent')
        if concurrent_attr:
            try:
                event_node.concurrent = int(concurrent_attr)
            except ValueError:
                pass

        prefetch_attr = event_element.get('prefetch')
        if prefetch_attr:
            try:
                event_node.prefetch = int(prefetch_attr)
            except ValueError:
                pass

        event_node.timeout = event_element.get('timeout')

        # Parse event handler body
        for child in event_element:
            statement = self._parse_statement(child)
            if statement:
                event_node.add_statement(statement)

        return event_node
