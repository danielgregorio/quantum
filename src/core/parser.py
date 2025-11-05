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
    FunctionNode, DispatchEventNode, OnEventNode, RestConfig, QueryNode, QueryParamNode,
    InvokeNode, InvokeHeaderNode, DataNode, ColumnNode, FieldNode, TransformNode,
    FilterNode, SortNode, LimitNode, ComputeNode, HeaderNode,
    HTMLNode, TextNode, DocTypeNode, CommentNode, HTML_VOID_ELEMENTS,
    ImportNode, SlotNode, ComponentCallNode
)
from core.features.logging.src import LogNode, parse_log
from core.features.dump.src import DumpNode, parse_dump

class QuantumParseError(Exception):
    """Quantum parsing error"""
    pass

class QuantumParser:
    """Main parser for .q files"""
    
    def __init__(self):
        self.quantum_ns = {'q': 'https://quantum.lang/ns'}

    def _inject_namespace(self, content: str) -> str:
        """
        MAGIC: Automatically inject XML namespace for q: prefix

        This allows users to write clean Quantum code without ceremony:

        Instead of:  <q:component name="Foo" xmlns:q="https://quantum.lang/ns">
        Write:       <q:component name="Foo">

        Pure ColdFusion-style pragmatism!
        """
        import re

        # Check if namespace already present
        if 'xmlns:q' in content:
            return content

        # Find first q:component, q:application, or q:job tag
        pattern = r'<(q:component|q:application|q:job)(\s+[^>]*)?>'

        def add_namespace(match):
            tag = match.group(1)
            attrs = match.group(2) or ''
            # Add namespace declaration
            return f'<{tag}{attrs} xmlns:q="https://quantum.lang/ns">'

        # Replace first occurrence only
        content = re.sub(pattern, add_namespace, content, count=1)

        return content

    def parse_file(self, file_path: str) -> QuantumNode:
        """Parse .q file and return AST"""
        path = Path(file_path)

        if not path.exists():
            raise QuantumParseError(f"File not found: {file_path}")

        if not path.suffix == '.q':
            raise QuantumParseError(f"Invalid extension: {path.suffix}, expected .q")

        try:
            # Read file content
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # MAGIC: Auto-inject namespace if not present
            # This makes Quantum "just work" without ceremony
            content = self._inject_namespace(content)

            # Parse XML
            root = ET.fromstring(content)
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

        # HTML rendering & interactivity (Phase 1 & future Phase 3)
        interactive_attr = root.get('interactive', 'false').lower()
        component.interactive = interactive_attr in ['true', '1', 'yes']

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

            # Quantum tags (q:*)
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
            elif child_type == 'query':
                query_node = self._parse_query_statement(child)
                component.add_statement(query_node)
            elif child_type == 'invoke':
                invoke_node = self._parse_invoke_statement(child)
                component.add_statement(invoke_node)
            elif child_type == 'data':
                data_node = self._parse_data_statement(child)
                component.add_statement(data_node)
            elif child_type == 'log':
                log_node = parse_log(child)
                component.add_statement(log_node)
            elif child_type == 'dump':
                dump_node = parse_dump(child)
                component.add_statement(dump_node)

            # HTML elements (Phase 1 - HTML rendering)
            elif self._is_html_element(child):
                html_node = self._parse_html_element(child)
                component.add_statement(html_node)
                component.has_html = True  # Mark component as having HTML output
    
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
        # Check for query attribute first (shorthand for query iteration)
        query_attr = loop_element.get('query')

        if query_attr:
            # <q:loop query="users"> shorthand syntax
            loop_type = 'query'
            var_name = query_attr  # Query name becomes the variable name
            loop_node = LoopNode(loop_type, var_name)
            loop_node.query_name = query_attr
        else:
            # Traditional syntax
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

        elif loop_type == 'query':
            # Query loop - index is optional
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

        # Quantum tags
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
        elif element_type == 'query':
            return self._parse_query_statement(element)
        elif element_type == 'invoke':
            return self._parse_invoke_statement(element)
        elif element_type == 'data':
            return self._parse_data_statement(element)
        elif element_type == 'log':
            return parse_log(element)
        elif element_type == 'dump':
            return parse_dump(element)

        # Component Composition (Phase 2)
        elif element_type == 'import':
            return self._parse_import_statement(element)
        elif element_type == 'slot':
            return self._parse_slot_statement(element)

        # Component calls (Phase 2) - Check BEFORE HTML elements
        # Detect imported component usage by uppercase naming convention
        elif element_type and element_type[0].isupper():
            return self._parse_component_call(element)

        # HTML elements (Phase 1)
        elif self._is_html_element(element):
            return self._parse_html_element(element)

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

    def _parse_query_statement(self, query_element: ET.Element) -> QueryNode:
        """Parse q:query statement"""
        name = query_element.get('name')
        datasource = query_element.get('datasource')
        source = query_element.get('source')

        if not name:
            raise QuantumParseError("Query requires 'name' attribute")
        if not datasource and not source:
            raise QuantumParseError("Query requires either 'datasource' or 'source' attribute")

        # Extract SQL content (text between tags, excluding q:param children)
        sql_parts = []
        if query_element.text:
            sql_parts.append(query_element.text.strip())

        # Collect text between child elements (but not the q:param elements themselves)
        for child in query_element:
            if child.tail:
                sql_parts.append(child.tail.strip())

        sql = '\n'.join(part for part in sql_parts if part)

        # Create query node (datasource can be None for Query of Queries)
        query_node = QueryNode(name, datasource or '', sql)

        # Parse optional attributes
        query_node.source = source
        query_node.cache = query_element.get('cache', 'false').lower() == 'true'

        ttl_attr = query_element.get('ttl')
        if ttl_attr:
            try:
                query_node.ttl = int(ttl_attr)
            except ValueError:
                pass

        query_node.reactive = query_element.get('reactive', 'false').lower() == 'true'

        interval_attr = query_element.get('interval')
        if interval_attr:
            try:
                query_node.interval = int(interval_attr)
            except ValueError:
                pass

        query_node.paginate = query_element.get('paginate', 'false').lower() == 'true'

        page_attr = query_element.get('page')
        if page_attr:
            try:
                query_node.page = int(page_attr)
            except ValueError:
                pass

        page_size_attr = query_element.get('pageSize')
        if page_size_attr:
            try:
                query_node.page_size = int(page_size_attr)
            except ValueError:
                pass

        timeout_attr = query_element.get('timeout')
        if timeout_attr:
            try:
                query_node.timeout = int(timeout_attr)
            except ValueError:
                pass

        maxrows_attr = query_element.get('maxrows')
        if maxrows_attr:
            try:
                query_node.maxrows = int(maxrows_attr)
            except ValueError:
                pass

        query_node.result = query_element.get('result')

        # Parse q:param children
        for child in query_element:
            child_type = self._get_element_name(child)
            if child_type == 'param':
                param_node = self._parse_query_param(child)
                query_node.add_param(param_node)

        return query_node

    def _parse_query_param(self, param_element: ET.Element) -> QueryParamNode:
        """Parse q:param within q:query"""
        name = param_element.get('name')
        value = param_element.get('value')
        param_type = param_element.get('type', 'string')

        if not name:
            raise QuantumParseError("Query parameter requires 'name' attribute")
        if value is None:
            raise QuantumParseError(f"Query parameter '{name}' requires 'value' attribute")
        if not param_type:
            raise QuantumParseError(f"Query parameter '{name}' requires 'type' attribute")

        # Create param node
        param_node = QueryParamNode(name, value, param_type)

        # Parse optional attributes
        param_node.null = param_element.get('null', 'false').lower() == 'true'

        max_length_attr = param_element.get('maxLength')
        if max_length_attr:
            try:
                param_node.max_length = int(max_length_attr)
            except ValueError:
                pass

        scale_attr = param_element.get('scale')
        if scale_attr:
            try:
                param_node.scale = int(scale_attr)
            except ValueError:
                pass

        return param_node

    def _parse_invoke_statement(self, invoke_element: ET.Element) -> InvokeNode:
        """Parse q:invoke statement"""
        name = invoke_element.get('name')
        if not name:
            raise QuantumParseError("Invoke requires 'name' attribute")

        invoke_node = InvokeNode(name)

        # Parse invocation target (function, component, url, endpoint, service)
        invoke_node.function = invoke_element.get('function')
        invoke_node.component = invoke_element.get('component')
        invoke_node.url = invoke_element.get('url')
        invoke_node.endpoint = invoke_element.get('endpoint')
        invoke_node.service = invoke_element.get('service')

        # HTTP-specific attributes
        invoke_node.method = invoke_element.get('method', 'GET').upper()
        invoke_node.content_type = invoke_element.get('contentType', 'application/json')

        # Authentication
        invoke_node.auth_type = invoke_element.get('authType')
        invoke_node.auth_token = invoke_element.get('authToken')
        invoke_node.auth_header = invoke_element.get('authHeader')
        invoke_node.auth_username = invoke_element.get('authUsername')
        invoke_node.auth_password = invoke_element.get('authPassword')

        # Timeouts and retries
        timeout_attr = invoke_element.get('timeout')
        if timeout_attr:
            try:
                invoke_node.timeout = int(timeout_attr)
            except ValueError:
                pass

        retry_attr = invoke_element.get('retry')
        if retry_attr:
            try:
                invoke_node.retry = int(retry_attr)
            except ValueError:
                pass

        retry_delay_attr = invoke_element.get('retryDelay')
        if retry_delay_attr:
            try:
                invoke_node.retry_delay = int(retry_delay_attr)
            except ValueError:
                pass

        # Response handling
        invoke_node.response_format = invoke_element.get('responseFormat', 'auto')
        invoke_node.transform = invoke_element.get('transform')
        invoke_node.cache = invoke_element.get('cache', 'false').lower() == 'true'

        ttl_attr = invoke_element.get('ttl')
        if ttl_attr:
            try:
                invoke_node.ttl = int(ttl_attr)
            except ValueError:
                pass

        invoke_node.result = invoke_element.get('result')

        # Parse child elements (headers, params, body)
        for child in invoke_element:
            child_type = self._get_element_name(child)

            if child_type == 'header':
                header = self._parse_invoke_header(child)
                invoke_node.add_header(header)
            elif child_type == 'param':
                param = self._parse_param(child)
                invoke_node.add_param(param)
            elif child_type == 'body':
                # Body can be text content or databinding expression
                invoke_node.body = child.text or ""

        return invoke_node

    def _parse_invoke_header(self, header_element: ET.Element) -> InvokeHeaderNode:
        """Parse q:header within q:invoke"""
        name = header_element.get('name')
        value = header_element.get('value')

        if not name:
            raise QuantumParseError("Invoke header requires 'name' attribute")
        if value is None:
            raise QuantumParseError(f"Invoke header '{name}' requires 'value' attribute")

        return InvokeHeaderNode(name, value)

    def _parse_data_statement(self, data_element: ET.Element) -> DataNode:
        """Parse q:data statement for data import and transformation"""
        name = data_element.get('name')
        source = data_element.get('source')
        data_type = data_element.get('type', 'csv')

        if not name:
            raise QuantumParseError("Data requires 'name' attribute")
        if not source:
            raise QuantumParseError("Data requires 'source' attribute")

        data_node = DataNode(name, source, data_type)

        # Parse optional attributes
        data_node.cache = data_element.get('cache', 'true').lower() == 'true'
        ttl = data_element.get('ttl')
        if ttl:
            try:
                data_node.ttl = int(ttl)
            except ValueError:
                pass

        # CSV-specific attributes
        data_node.delimiter = data_element.get('delimiter', ',')
        data_node.quote = data_element.get('quote', '"')
        data_node.header = data_element.get('header', 'true').lower() == 'true'
        data_node.encoding = data_element.get('encoding', 'utf-8')
        skip_rows = data_element.get('skip_rows', '0')
        try:
            data_node.skip_rows = int(skip_rows)
        except ValueError:
            data_node.skip_rows = 0

        # XML-specific attributes
        data_node.xpath = data_element.get('xpath')
        data_node.namespace = data_element.get('namespace')

        # Result metadata
        data_node.result = data_element.get('result')

        # Parse child elements
        for child in data_element:
            child_type = self._get_element_name(child)

            if child_type == 'column':
                column = self._parse_column(child)
                data_node.add_column(column)
            elif child_type == 'field':
                field = self._parse_field(child)
                data_node.add_field(field)
            elif child_type == 'transform':
                transform = self._parse_transform(child)
                data_node.add_transform(transform)
            elif child_type == 'header':
                header = self._parse_data_header(child)
                data_node.add_header(header)

        return data_node

    def _parse_column(self, column_element: ET.Element) -> ColumnNode:
        """Parse q:column for CSV column definition"""
        name = column_element.get('name')
        col_type = column_element.get('type', 'string')

        if not name:
            raise QuantumParseError("Column requires 'name' attribute")

        column = ColumnNode(name, col_type)

        # Parse validation attributes
        column.required = column_element.get('required', 'false').lower() == 'true'
        column.default = column_element.get('default')
        column.validate_rule = column_element.get('validate')
        column.pattern = column_element.get('pattern')

        min_val = column_element.get('min')
        if min_val:
            try:
                column.min = float(min_val)
            except ValueError:
                column.min = min_val

        max_val = column_element.get('max')
        if max_val:
            try:
                column.max = float(max_val)
            except ValueError:
                column.max = max_val

        minlength = column_element.get('minlength')
        if minlength:
            try:
                column.minlength = int(minlength)
            except ValueError:
                pass

        maxlength = column_element.get('maxlength')
        if maxlength:
            try:
                column.maxlength = int(maxlength)
            except ValueError:
                pass

        column.range = column_element.get('range')
        column.enum = column_element.get('enum')

        return column

    def _parse_field(self, field_element: ET.Element) -> FieldNode:
        """Parse q:field for XML field mapping"""
        name = field_element.get('name')
        xpath = field_element.get('xpath')
        field_type = field_element.get('type', 'string')

        if not name:
            raise QuantumParseError("Field requires 'name' attribute")
        if not xpath:
            raise QuantumParseError("Field requires 'xpath' attribute")

        return FieldNode(name, xpath, field_type)

    def _parse_transform(self, transform_element: ET.Element) -> TransformNode:
        """Parse q:transform container for transformation operations"""
        transform = TransformNode()

        for child in transform_element:
            child_type = self._get_element_name(child)

            if child_type == 'filter':
                filter_op = self._parse_filter(child)
                transform.add_operation(filter_op)
            elif child_type == 'sort':
                sort_op = self._parse_sort(child)
                transform.add_operation(sort_op)
            elif child_type == 'limit':
                limit_op = self._parse_limit(child)
                transform.add_operation(limit_op)
            elif child_type == 'compute':
                compute_op = self._parse_compute(child)
                transform.add_operation(compute_op)

        return transform

    def _parse_filter(self, filter_element: ET.Element) -> FilterNode:
        """Parse q:filter operation"""
        condition = filter_element.get('condition')

        if not condition:
            raise QuantumParseError("Filter requires 'condition' attribute")

        return FilterNode(condition)

    def _parse_sort(self, sort_element: ET.Element) -> SortNode:
        """Parse q:sort operation"""
        by = sort_element.get('by')
        order = sort_element.get('order', 'asc')

        if not by:
            raise QuantumParseError("Sort requires 'by' attribute")

        return SortNode(by, order)

    def _parse_limit(self, limit_element: ET.Element) -> LimitNode:
        """Parse q:limit operation"""
        value = limit_element.get('value')

        if not value:
            raise QuantumParseError("Limit requires 'value' attribute")

        try:
            limit_value = int(value)
        except ValueError:
            raise QuantumParseError(f"Limit value must be an integer, got: {value}")

        return LimitNode(limit_value)

    def _parse_compute(self, compute_element: ET.Element) -> ComputeNode:
        """Parse q:compute operation"""
        field = compute_element.get('field')
        expression = compute_element.get('expression')
        comp_type = compute_element.get('type', 'string')

        if not field:
            raise QuantumParseError("Compute requires 'field' attribute")
        if not expression:
            raise QuantumParseError("Compute requires 'expression' attribute")

        return ComputeNode(field, expression, comp_type)

    def _parse_data_header(self, header_element: ET.Element) -> HeaderNode:
        """Parse q:header for HTTP headers in data sources"""
        name = header_element.get('name')
        value = header_element.get('value')

        if not name:
            raise QuantumParseError("Data header requires 'name' attribute")
        if value is None:
            raise QuantumParseError(f"Data header '{name}' requires 'value' attribute")

        return HeaderNode(name, value)

    # ============================================
    # HTML PARSING (Phase 1 - HTML Rendering)
    # ============================================

    def _is_html_element(self, element: ET.Element) -> bool:
        """
        Check if element is HTML (not a Quantum tag).

        Returns True for:
        - Regular HTML tags (div, span, p, etc.)
        - DOCTYPE declarations
        - Comments

        Returns False for:
        - Quantum tags (q:* namespace)
        - Special Quantum tags (param, return, function, etc.)
        """
        tag = element.tag

        # Skip namespace declarations and special elements
        if tag.startswith('{'):
            # Has XML namespace - check if it's Quantum namespace
            if '{https://quantum.lang/ns}' in tag:
                return False
            # Other namespaces might be HTML5 or SVG
            return True

        # Check for q: prefix (Quantum tags)
        if tag.startswith('q:'):
            return False

        # Quantum tags without prefix (when xmlns:q is set)
        quantum_tags = {
            'component', 'application', 'job', 'param', 'return', 'route',
            'if', 'elseif', 'else', 'loop', 'set', 'function', 'dispatchEvent',
            'onEvent', 'script', 'query', 'invoke', 'data', 'log', 'dump'
        }
        if tag in quantum_tags:
            return False

        # Everything else is HTML
        return True

    def _parse_html_element(self, element: ET.Element) -> HTMLNode:
        """
        Parse HTML element into HTMLNode.

        Recursively parses children (which can be HTML or Quantum tags).
        Handles text content with TextNode.
        """
        tag = self._get_element_name(element)

        # Parse attributes (will be applied databinding during rendering)
        attributes = dict(element.attrib)

        # Parse children
        children = []

        # Add text before first child
        if element.text and element.text.strip():
            children.append(TextNode(element.text))

        # Parse child elements (recursively)
        for child in element:
            # Child could be HTML or Quantum tag
            child_node = self._parse_statement(child)
            if child_node:
                children.append(child_node)

            # Add text after child (tail)
            if child.tail and child.tail.strip():
                children.append(TextNode(child.tail))

        # Create HTML node
        html_node = HTMLNode(
            tag=tag,
            attributes=attributes,
            children=children
        )

        return html_node

    # ============================================
    # COMPONENT COMPOSITION PARSING (Phase 2)
    # ============================================

    def _parse_import_statement(self, element: ET.Element) -> ImportNode:
        """
        Parse q:import statement.

        Examples:
          <q:import component="Header" />
          <q:import component="Button" from="./ui" />
          <q:import component="AdminLayout" as="Layout" />
        """
        component = element.get('component')
        from_path = element.get('from')
        alias = element.get('as')
        
        if not component:
            raise QuantumParseError("q:import requires 'component' attribute")
        
        return ImportNode(
            component=component,
            from_path=from_path,
            alias=alias
        )

    def _parse_slot_statement(self, element: ET.Element) -> SlotNode:
        """
        Parse q:slot statement.

        Examples:
          <q:slot />  <!-- Default slot -->
          <q:slot name="header" />
          <q:slot name="footer">
            <p>Default footer content</p>
          </q:slot>
        """
        name = element.get('name', 'default')
        
        # Parse default content (children of slot)
        default_content = []
        
        if element.text and element.text.strip():
            default_content.append(TextNode(element.text))
        
        for child in element:
            child_node = self._parse_statement(child)
            if child_node:
                default_content.append(child_node)
            
            if child.tail and child.tail.strip():
                default_content.append(TextNode(child.tail))
        
        return SlotNode(
            name=name,
            default_content=default_content
        )

    def _parse_component_call(self, element: ET.Element) -> ComponentCallNode:
        """
        Parse component call (imported component usage).

        Examples:
          <Header title="Products" />
          <Button label="Save" color="green" />
          <Card title="Info">
            <p>Card content</p>
          </Card>
        """
        component_name = element.tag
        
        # Parse props (all attributes)
        props = dict(element.attrib)
        
        # Parse children (content for slots)
        children = []
        
        if element.text and element.text.strip():
            children.append(TextNode(element.text))
        
        for child in element:
            child_node = self._parse_statement(child)
            if child_node:
                children.append(child_node)
            
            if child.tail and child.tail.strip():
                children.append(TextNode(child.tail))
        
        return ComponentCallNode(
            component_name=component_name,
            props=props,
            children=children
        )
