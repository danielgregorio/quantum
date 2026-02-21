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
    QuantumParam, QuantumReturn, QuantumRoute,
    DispatchEventNode, OnEventNode, QueryNode, QueryParamNode,
    InvokeHeaderNode, DataNode, ColumnNode, FieldNode, TransformNode,
    FilterNode, SortNode, LimitNode, ComputeNode, HeaderNode,
    HTMLNode, TextNode, DocTypeNode, CommentNode, HTML_VOID_ELEMENTS,
    ImportNode, SlotNode, ComponentCallNode,
    ActionNode, RedirectNode, FlashNode, FileNode, MailNode, TransactionNode,
    LLMNode, LLMMessageNode,
    ScheduleNode, ThreadNode,  # Job Execution System
    # Message Queue System
    MessageNode, MessageHeaderNode, SubscribeNode, QueueNode,
    MessageAckNode, MessageNackNode,
    # Python Scripting System
    PythonNode, PyImportNode, PyClassNode, PyDecoratorNode, PyExprNode
)
# Import feature AST nodes from their respective modules
from core.features.conditionals.src.ast_node import IfNode
from core.features.loops.src.ast_node import LoopNode
from core.features.state_management.src.ast_node import SetNode, PersistNode
from core.features.functions.src.ast_node import FunctionNode, RestConfig
from core.features.invocation.src.ast_node import InvokeNode
from core.features.logging.src import LogNode, parse_log
from core.features.dump.src import DumpNode, parse_dump
from core.features.knowledge_base.src import KnowledgeNode, KnowledgeSourceNode, parse_knowledge
from core.features.agents.src import (
    AgentNode, AgentInstructionNode, AgentToolNode, AgentToolParamNode, AgentExecuteNode,
    AgentTeamNode, AgentHandoffNode
)
from core.features.websocket.src import (
    WebSocketNode, WebSocketHandlerNode, WebSocketSendNode, WebSocketCloseNode
)
from core.features.game_engine_2d.src.parser import GameParser, GameParseError
from core.features.game_engine_2d.src.ast_nodes import (
    SceneNode, BehaviorNode, PrefabNode,
)
from core.features.terminal_engine.src.parser import TerminalParser, TerminalParseError
from core.features.terminal_engine.src.ast_nodes import (
    ScreenNode as TerminalScreenNode, KeybindingNode as TerminalKeybindingNode,
    ServiceNode as TerminalServiceNode, CssNode as TerminalCssNode,
)
from core.features.testing_engine.src.parser import TestingParser, TestingParseError
from core.features.testing_engine.src.ast_nodes import (
    QTestSuiteNode as TestingTestSuiteNode,
    BrowserConfigNode as TestingBrowserConfigNode,
    FixtureNode_Testing as TestingFixtureNode,
    MockNode_Testing as TestingMockNode,
    AuthNode as TestingAuthNode,
)
from core.features.ui_engine.src.parser import UIParser, UIParseError
from core.features.ui_engine.src.ast_nodes import UIWindowNode
from core.features.theming.src import UIThemeNode
from core.parser_registry import ParserRegistry
import logging

logger = logging.getLogger(__name__)


def _create_parser_registry(parser: 'QuantumParser') -> ParserRegistry:
    """
    Create and populate the parser registry with all modular parsers.

    This factory function creates all modular parsers and registers them.
    The registry can then dispatch parsing to the appropriate parser
    based on tag name.

    Args:
        parser: QuantumParser instance for parser initialization

    Returns:
        Populated ParserRegistry
    """
    from core.parsers import (
        # Control flow
        IfParser, LoopParser, SetParser,
        # Data
        QueryParser, InvokeParser, DataParser, TransactionParser,
        # Services
        LogParser, DumpParser, FileParser, MailParser,
        # AI
        LLMParser, AgentParser, TeamParser, KnowledgeParser,
        # Messaging
        WebSocketParser, WebSocketSendParser, WebSocketCloseParser,
        MessageParser, SubscribeParser, QueueParser,
        # Jobs
        ScheduleParser, ThreadParser, JobParser,
        # Scripting
        PythonParser, PyImportParser, PyClassParser,
        # HTML
        HTMLParser, ComponentCallParser,
    )

    registry = ParserRegistry()

    # Register all tag-based parsers
    parsers = [
        # Control flow
        IfParser(parser),
        LoopParser(parser),
        SetParser(parser),
        # Data
        QueryParser(parser),
        InvokeParser(parser),
        DataParser(parser),
        TransactionParser(parser),
        # Services
        LogParser(parser),
        DumpParser(parser),
        FileParser(parser),
        MailParser(parser),
        # AI
        LLMParser(parser),
        AgentParser(parser),
        TeamParser(parser),
        KnowledgeParser(parser),
        # Messaging
        WebSocketParser(parser),
        WebSocketSendParser(parser),
        WebSocketCloseParser(parser),
        MessageParser(parser),
        SubscribeParser(parser),
        QueueParser(parser),
        # Jobs
        ScheduleParser(parser),
        ThreadParser(parser),
        JobParser(parser),
        # Scripting
        PythonParser(parser),
        PyImportParser(parser),
        PyClassParser(parser),
        # HTML (registers for common HTML tags)
        HTMLParser(parser),
    ]

    registry.register_all(parsers)

    # Store special parsers for fallback handling
    # These are used when no specific tag parser matches
    registry.html_parser = HTMLParser(parser)
    registry.component_call_parser = ComponentCallParser(parser)

    logger.debug(f"Initialized parser registry with {registry.parser_count} parsers")

    return registry


class QuantumParseError(Exception):
    """Quantum parsing error"""
    pass


class QuantumParser:
    """Main parser for .q files"""

    def __init__(self, use_cache: bool = True, use_modular_parsers: bool = True):
        self.quantum_ns = {'q': 'https://quantum.lang/ns'}
        self._use_cache = use_cache
        self._ast_cache = None
        if use_cache:
            try:
                from runtime.ast_cache import get_ast_cache
                self._ast_cache = get_ast_cache()
            except ImportError:
                self._use_cache = False

        # === NEW: Parser Registry for modular dispatch ===
        self._use_modular_parsers = use_modular_parsers
        self._parser_registry: ParserRegistry = None
        if use_modular_parsers:
            self._parser_registry = _create_parser_registry(self)
        else:
            import warnings
            warnings.warn(
                "use_modular_parsers=False is deprecated and will be removed in v2.0. "
                "The modular ParserRegistry is now the default.",
                DeprecationWarning,
                stacklevel=2
            )

    @property
    def parser_registry(self) -> ParserRegistry:
        """Access to parser registry (may be None if not using modular parsers)"""
        return self._parser_registry

    def _inject_namespace(self, content: str) -> str:
        """
        MAGIC: Automatically inject XML namespace for q: and qg: prefixes

        This allows users to write clean Quantum code without ceremony:

        Instead of:  <q:component name="Foo" xmlns:q="https://quantum.lang/ns">
        Write:       <q:component name="Foo">

        For game apps, also injects xmlns:qg for game tags.
        Pure ColdFusion-style pragmatism!
        """
        import re

        # Check if namespace already present
        if 'xmlns:q' in content:
            # Still check for qg: namespace in game apps
            if 'xmlns:qg' not in content and ('qg:' in content or 'type="game"' in content):
                content = content.replace(
                    'xmlns:q="https://quantum.lang/ns"',
                    'xmlns:q="https://quantum.lang/ns" xmlns:qg="https://quantum.lang/game"'
                )
            # Check for qt: namespace in terminal apps
            if 'xmlns:qt' not in content and ('qt:' in content or 'type="terminal"' in content):
                content = content.replace(
                    'xmlns:q="https://quantum.lang/ns"',
                    'xmlns:q="https://quantum.lang/ns" xmlns:qt="https://quantum.lang/terminal"'
                )
            # Check for qtest: namespace in testing apps
            if 'xmlns:qtest' not in content and ('qtest:' in content or 'type="testing"' in content):
                content = content.replace(
                    'xmlns:q="https://quantum.lang/ns"',
                    'xmlns:q="https://quantum.lang/ns" xmlns:qtest="https://quantum.lang/testing"'
                )
            # Check for ui: namespace in ui apps
            if 'xmlns:ui' not in content and ('ui:' in content or 'type="ui"' in content):
                content = content.replace(
                    'xmlns:q="https://quantum.lang/ns"',
                    'xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui"'
                )
            return content

        # Find first q:component, q:application, or q:job tag
        pattern = r'<(q:component|q:application|q:job)(\s+[^>]*)?>'

        def add_namespace(match):
            tag = match.group(1)
            attrs = match.group(2) or ''
            ns_decl = ' xmlns:q="https://quantum.lang/ns"'
            # Auto-inject qg: namespace for game applications
            if 'type="game"' in content or 'qg:' in content:
                ns_decl += ' xmlns:qg="https://quantum.lang/game"'
            # Auto-inject qt: namespace for terminal applications
            if 'type="terminal"' in content or 'qt:' in content:
                ns_decl += ' xmlns:qt="https://quantum.lang/terminal"'
            # Auto-inject qtest: namespace for testing applications
            if 'type="testing"' in content or 'qtest:' in content:
                ns_decl += ' xmlns:qtest="https://quantum.lang/testing"'
            # Auto-inject ui: namespace for ui applications
            if 'type="ui"' in content or 'ui:' in content:
                ns_decl += ' xmlns:ui="https://quantum.lang/ui"'
            return f'<{tag}{attrs}{ns_decl}>'

        # Replace first occurrence only
        content = re.sub(pattern, add_namespace, content, count=1)

        return content

    def parse(self, source: str) -> QuantumNode:
        """Parse Quantum XML from a string."""
        try:
            content = self._inject_namespace(source)
            root = ET.fromstring(content)
            return self._parse_root_element(root, Path("<string>"))
        except ET.ParseError as e:
            raise QuantumParseError(f"XML parse error: {e}")
        except QuantumParseError:
            raise
        except Exception as e:
            raise QuantumParseError(f"Unexpected error: {e}")

    def parse_file(self, file_path: str, use_cache: bool = None) -> QuantumNode:
        """Parse .q file and return AST

        Args:
            file_path: Path to the .q file
            use_cache: Override cache behavior (None = use instance default)
        """
        path = Path(file_path)

        if not path.exists():
            raise QuantumParseError(f"File not found: {file_path}")

        if not path.suffix == '.q':
            raise QuantumParseError(f"Invalid extension: {path.suffix}, expected .q")

        # Determine if we should use cache
        should_cache = use_cache if use_cache is not None else self._use_cache

        try:
            # Try cache first (Phase 2 optimization)
            if should_cache and self._ast_cache is not None:
                return self._ast_cache.get_or_parse(file_path, self)

            # Fallback to direct parsing
            source = Path(file_path).read_text(encoding="utf-8")
            return self.parse(source)
        except QuantumParseError:
            raise
        except Exception as e:
            raise QuantumParseError(f"Unexpected error: {e}")

    def invalidate_cache(self, file_path: str = None):
        """Invalidate cached AST for a file or all files

        Args:
            file_path: Specific file to invalidate, or None for all
        """
        if self._ast_cache is not None:
            self._ast_cache.invalidate(file_path)
    
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

        # Phase G: Authentication & Security attributes
        require_auth_attr = root.get('require_auth', 'false').lower()
        component.require_auth = require_auth_attr in ['true', '1', 'yes']
        component.require_role = root.get('require_role')
        component.require_permission = root.get('require_permission')

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

            # Forms & Actions (Phase A)
            elif child_type == 'action':
                action_node = self._parse_action_statement(child)
                component.add_statement(action_node)
            elif child_type == 'redirect':
                redirect_node = self._parse_redirect_statement(child)
                component.add_statement(redirect_node)
            elif child_type == 'flash':
                flash_node = self._parse_flash_statement(child)
                component.add_statement(flash_node)
            elif child_type == 'file':
                file_node = self._parse_file_statement(child)
                component.add_statement(file_node)
            elif child_type == 'mail':
                mail_node = self._parse_mail_statement(child)
                component.add_statement(mail_node)
            elif child_type == 'transaction':
                transaction_node = self._parse_transaction_statement(child)
                component.add_statement(transaction_node)
            elif child_type == 'llm':
                llm_node = self._parse_llm_statement(child)
                component.add_statement(llm_node)
            elif child_type == 'knowledge':
                knowledge_node = parse_knowledge(child)
                component.add_statement(knowledge_node)
            elif child_type == 'agent':
                agent_node = self._parse_agent_statement(child)
                component.add_statement(agent_node)
            elif child_type == 'team':
                team_node = self._parse_team_statement(child)
                component.add_statement(team_node)
            elif child_type == 'websocket':
                ws_node = self._parse_websocket_statement(child)
                component.add_statement(ws_node)
            elif child_type == 'websocket-send':
                ws_send_node = self._parse_websocket_send(child)
                component.add_statement(ws_send_node)
            elif child_type == 'websocket-close':
                ws_close_node = self._parse_websocket_close(child)
                component.add_statement(ws_close_node)
            elif child_type == 'persist':
                persist_node = self._parse_persist_statement(child)
                component.add_statement(persist_node)

            # Job Execution System
            elif child_type == 'schedule':
                schedule_node = self._parse_schedule_statement(child)
                component.add_statement(schedule_node)
            elif child_type == 'thread':
                thread_node = self._parse_thread_statement(child)
                component.add_statement(thread_node)
            elif child_type == 'job':
                # Inline job definition within component
                from pathlib import Path as PathLib
                job_node = self._parse_job(child, PathLib("<inline>"))
                component.add_statement(job_node)

            # Message Queue System
            elif child_type == 'message':
                message_node = self._parse_message_statement(child)
                component.add_statement(message_node)
            elif child_type == 'subscribe':
                subscribe_node = self._parse_subscribe_statement(child)
                component.add_statement(subscribe_node)
            elif child_type == 'queue':
                queue_node = self._parse_queue_statement(child)
                component.add_statement(queue_node)
            elif child_type == 'messageAck':
                ack_node = self._parse_message_ack_statement(child)
                component.add_statement(ack_node)
            elif child_type == 'messageNack':
                nack_node = self._parse_message_nack_statement(child)
                component.add_statement(nack_node)

            # Python Scripting System
            elif child_type == 'python':
                python_node = self._parse_python_statement(child)
                component.add_statement(python_node)
            elif child_type == 'pyimport':
                pyimport_node = self._parse_pyimport_statement(child)
                component.add_statement(pyimport_node)
            elif child_type == 'class':
                pyclass_node = self._parse_pyclass_statement(child)
                component.add_statement(pyclass_node)
            elif child_type == 'decorator':
                pydecorator_node = self._parse_pydecorator_statement(child)
                component.add_statement(pydecorator_node)

            # Component Composition (Phase 2)
            elif child_type == 'import':
                import_node = self._parse_import_statement(child)
                component.add_statement(import_node)
            elif child_type == 'slot':
                slot_node = self._parse_slot_statement(child)
                component.add_statement(slot_node)

            # Component calls (Phase 2) - Uppercase tags
            elif child_type and child_type[0].isupper():
                component_call = self._parse_component_call(child)
                component.add_statement(component_call)
                component.has_html = True  # Component calls produce HTML

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

        # Parse loop body - add text content before first child
        if loop_element.text and loop_element.text.strip():
            loop_node.add_statement(TextNode(loop_element.text))

        # Parse loop body statements (child elements)
        for child in loop_element:
            statement = self._parse_statement(child)
            if statement:
                loop_node.add_statement(statement)
            # Add tail text after child element
            if child.tail and child.tail.strip():
                loop_node.add_statement(TextNode(child.tail))

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

        # State Persistence
        set_node.persist = set_element.get('persist')  # "local", "session", "sync"
        set_node.persist_key = set_element.get('persistKey')  # Custom storage key
        set_node.persist_encrypt = set_element.get('persistEncrypt', 'false').lower() == 'true'
        persist_ttl = set_element.get('persistTtl')
        if persist_ttl:
            try:
                set_node.persist_ttl = int(persist_ttl)
            except ValueError:
                pass

        return set_node

    def _parse_statement(self, element: ET.Element) -> Optional[QuantumNode]:
        """Parse individual statement (return, set, dispatchEvent, etc)"""
        element_type = self._get_element_name(element)

        # === NEW: Try modular parser registry first ===
        if self._use_modular_parsers and self._parser_registry:
            try:
                if self._parser_registry.has_parser(element_type):
                    return self._parser_registry.parse(element, element_type)
            except Exception as e:
                # Log warning and fall back to legacy parsing
                logger.warning(f"Modular parser failed for '{element_type}': {e}")

        # === LEGACY: Fall back to if-elif chain ===
        # DEPRECATION NOTE: This if-elif chain is deprecated and will be removed in v2.0
        # All parsing should go through the modular ParserRegistry
        logger.debug(f"LEGACY FALLBACK: Parsing '{element_type}' via if-elif chain (deprecated)")

        # Quantum tags
        if element_type == 'return':
            return self._parse_return(element)
        elif element_type == 'set':
            return self._parse_set_statement(element)
        elif element_type == 'loop':
            return self._parse_loop_statement(element)
        elif element_type == 'if':
            return self._parse_if_statement(element)
        elif element_type == 'function':
            return self._parse_function(element)
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

        # Forms & Actions (Phase A)
        elif element_type == 'action':
            return self._parse_action_statement(element)
        elif element_type == 'redirect':
            return self._parse_redirect_statement(element)
        elif element_type == 'flash':
            return self._parse_flash_statement(element)
        elif element_type == 'file':
            return self._parse_file_statement(element)
        elif element_type == 'mail':
            return self._parse_mail_statement(element)
        elif element_type == 'transaction':
            return self._parse_transaction_statement(element)
        elif element_type == 'llm':
            return self._parse_llm_statement(element)
        elif element_type == 'knowledge':
            return parse_knowledge(element)
        elif element_type == 'agent':
            return self._parse_agent_statement(element)
        elif element_type == 'team':
            return self._parse_team_statement(element)
        elif element_type == 'websocket':
            return self._parse_websocket_statement(element)
        elif element_type == 'websocket-send':
            return self._parse_websocket_send(element)
        elif element_type == 'websocket-close':
            return self._parse_websocket_close(element)
        elif element_type == 'persist':
            return self._parse_persist_statement(element)

        # Job Execution System
        elif element_type == 'schedule':
            return self._parse_schedule_statement(element)
        elif element_type == 'thread':
            return self._parse_thread_statement(element)
        elif element_type == 'job':
            from pathlib import Path as PathLib
            return self._parse_job(element, PathLib("<inline>"))

        # Message Queue System
        elif element_type == 'message':
            return self._parse_message_statement(element)
        elif element_type == 'subscribe':
            return self._parse_subscribe_statement(element)
        elif element_type == 'queue':
            return self._parse_queue_statement(element)
        elif element_type == 'messageAck':
            return self._parse_message_ack_statement(element)
        elif element_type == 'messageNack':
            return self._parse_message_nack_statement(element)

        # Python Scripting System
        elif element_type == 'python':
            return self._parse_python_statement(element)
        elif element_type == 'pyimport':
            return self._parse_pyimport_statement(element)
        elif element_type == 'class':
            return self._parse_pyclass_statement(element)
        elif element_type == 'decorator':
            return self._parse_pydecorator_statement(element)

        # Component Composition (Phase 2)
        elif element_type == 'import':
            return self._parse_import_statement(element)
        elif element_type == 'slot':
            return self._parse_slot_statement(element)

        # Component calls (Phase 2) - Check BEFORE HTML elements
        # Detect imported component usage by uppercase naming convention
        elif element_type and element_type[0].isupper():
            # === NEW: Try modular ComponentCallParser first ===
            if self._use_modular_parsers and self._parser_registry:
                try:
                    from core.parsers import ComponentCallParser
                    if ComponentCallParser.is_component_call(element_type):
                        return self._parser_registry.component_call_parser.parse(element)
                except Exception as e:
                    logger.warning(f"Modular ComponentCallParser failed for '{element_type}': {e}")
            # === LEGACY: Fall back to original method ===
            return self._parse_component_call(element)

        # HTML elements (Phase 1)
        elif self._is_html_element(element):
            # === NEW: Try modular HTMLParser first ===
            if self._use_modular_parsers and self._parser_registry:
                try:
                    if self._parser_registry.html_parser.can_parse(element_type):
                        return self._parser_registry.html_parser.parse(element)
                except Exception as e:
                    logger.warning(f"Modular HTMLParser failed for '{element_type}': {e}")
            # === LEGACY: Fall back to original method ===
            return self._parse_html_element(element)

        return None
    
    def _parse_application(self, root: ET.Element, path: Path) -> ApplicationNode:
        """Parse q:application"""
        app_id = root.get('id', path.stem)
        app_type = root.get('type', 'html')

        app = ApplicationNode(app_id, app_type)
        app.engine = root.get('engine')

        # Parse theme attribute for UI applications
        theme_attr = root.get('theme')
        if theme_attr and app_type == 'ui':
            app.ui_theme_preset = theme_attr
            # Create a UIThemeNode from the attribute
            theme_node = UIThemeNode()
            theme_node.preset = theme_attr
            app.ui_theme = theme_node

        # Parse q:route elements
        for route_el in self._find_all_elements(root, 'route'):
            route = self._parse_route(route_el)
            app.add_route(route)

        # Game Engine 2D: parse game children when type="game"
        if app_type == 'game':
            self._parse_game_application_children(root, app)

        # Terminal Engine: parse terminal children when type="terminal"
        if app_type == 'terminal':
            self._parse_terminal_application_children(root, app)

        # Testing Engine: parse testing children when type="testing"
        if app_type == 'testing':
            self._parse_testing_application_children(root, app)

        # UI Engine: parse ui children when type="ui"
        if app_type == 'ui':
            self._parse_ui_application_children(root, app)

        return app

    def _parse_game_application_children(self, root: ET.Element, app: ApplicationNode):
        """Parse children of a game application (qg: elements at top level)."""
        game_parser = GameParser(self)
        for child in root:
            local_name = self._get_element_name(child)
            ns = self._get_element_game_namespace(child)

            if ns == 'game':
                node = game_parser.parse_game_element(local_name, child)
                if isinstance(node, SceneNode):
                    app.scenes.append(node)
                elif isinstance(node, BehaviorNode):
                    app.behaviors.append(node)
                elif isinstance(node, PrefabNode):
                    app.prefabs.append(node)

    def _get_element_game_namespace(self, element: ET.Element) -> str:
        """Detect if element belongs to qg: (game) or q: (quantum) namespace."""
        tag = element.tag
        if '{https://quantum.lang/game}' in tag:
            return 'game'
        if '{https://quantum.lang/ns}' in tag:
            return 'quantum'
        if tag.startswith('qg:'):
            return 'game'
        if tag.startswith('q:'):
            return 'quantum'
        return 'html'

    def _parse_terminal_application_children(self, root: ET.Element, app: ApplicationNode):
        """Parse children of a terminal application (qt: elements at top level)."""
        terminal_parser = TerminalParser(self)
        for child in root:
            local_name = self._get_element_name(child)
            ns = self._get_element_terminal_namespace(child)

            if ns == 'terminal':
                node = terminal_parser.parse_terminal_element(local_name, child)
                if isinstance(node, TerminalScreenNode):
                    app.screens.append(node)
                elif isinstance(node, TerminalKeybindingNode):
                    app.keybindings.append(node)
                elif isinstance(node, TerminalServiceNode):
                    app.services.append(node)
                elif isinstance(node, TerminalCssNode):
                    app.terminal_css += node.content + '\n'

    def _get_element_terminal_namespace(self, element: ET.Element) -> str:
        """Detect if element belongs to qt: (terminal) or q: (quantum) namespace."""
        tag = element.tag
        if '{https://quantum.lang/terminal}' in tag:
            return 'terminal'
        if '{https://quantum.lang/ns}' in tag:
            return 'quantum'
        if tag.startswith('qt:'):
            return 'terminal'
        if tag.startswith('q:'):
            return 'quantum'
        return 'html'

    def _parse_testing_application_children(self, root: ET.Element, app: ApplicationNode):
        """Parse children of a testing application (qtest: elements at top level)."""
        testing_parser = TestingParser(self)
        for child in root:
            local_name = self._get_element_name(child)
            ns = self._get_element_testing_namespace(child)

            if ns == 'testing':
                node = testing_parser.parse_testing_element(local_name, child)
                if isinstance(node, TestingTestSuiteNode):
                    app.test_suites.append(node)
                elif isinstance(node, TestingBrowserConfigNode):
                    app.test_config = node
                elif isinstance(node, TestingFixtureNode):
                    app.test_fixtures.append(node)
                elif isinstance(node, TestingMockNode):
                    app.test_mocks.append(node)
                elif isinstance(node, TestingAuthNode):
                    app.test_auth_states.append(node)

    def _get_element_testing_namespace(self, element: ET.Element) -> str:
        """Detect if element belongs to qtest: (testing) or q: (quantum) namespace."""
        tag = element.tag
        if '{https://quantum.lang/testing}' in tag:
            return 'testing'
        if '{https://quantum.lang/ns}' in tag:
            return 'quantum'
        if tag.startswith('qtest:'):
            return 'testing'
        if tag.startswith('q:'):
            return 'quantum'
        return 'html'

    def _parse_ui_application_children(self, root: ET.Element, app: ApplicationNode):
        """Parse children of a UI application (ui: elements at top level)."""
        ui_parser = UIParser(self)
        for child in root:
            local_name = self._get_element_name(child)
            ns = self._get_element_ui_namespace(child)

            if ns == 'ui':
                node = ui_parser.parse_ui_element(local_name, child)
                if isinstance(node, UIWindowNode):
                    app.ui_windows.append(node)
                elif isinstance(node, UIThemeNode):
                    # ui:theme overrides any theme attribute
                    app.ui_theme = node
                else:
                    app.ui_children.append(node)
            elif ns == 'quantum':
                # Allow q: tags at the top level of a UI app (e.g. q:set)
                statement = self._parse_statement(child)
                if statement:
                    app.ui_children.append(statement)

    def _get_element_ui_namespace(self, element: ET.Element) -> str:
        """Detect if element belongs to ui: (UI engine) or q: (quantum) namespace."""
        tag = element.tag
        if '{https://quantum.lang/ui}' in tag:
            return 'ui'
        if '{https://quantum.lang/ns}' in tag:
            return 'quantum'
        if tag.startswith('ui:'):
            return 'ui'
        if tag.startswith('q:'):
            return 'quantum'
        return 'html'
    
    def _parse_job(self, root: ET.Element, path: Path) -> JobNode:
        """
        Parse q:job - Job queue for batch processing.

        Examples:
          <q:job name="sendEmail" queue="emails" priority="5">
            <q:param name="to" type="string" />
            <q:mail to="{to}" subject="Notification">...</q:mail>
          </q:job>

          <q:job name="processOrder" action="dispatch" delay="5m" />
        """
        # Support both 'name' and legacy 'id' attribute
        name = root.get('name') or root.get('id', path.stem)
        queue = root.get('queue', 'default')
        action = root.get('action', 'define')

        job_node = JobNode(name, queue, action)

        # Parse optional attributes
        job_node.delay = root.get('delay')
        job_node.timeout = root.get('timeout')
        job_node.backoff = root.get('backoff', '30s')

        priority_attr = root.get('priority')
        if priority_attr:
            try:
                job_node.priority = int(priority_attr)
            except ValueError:
                pass

        attempts_attr = root.get('attempts')
        if attempts_attr:
            try:
                job_node.attempts = int(attempts_attr)
            except ValueError:
                pass

        # Legacy support
        job_node.schedule = root.get('schedule')

        # Parse children (params and body statements)
        for child in root:
            child_type = self._get_element_name(child)

            if child_type == 'param':
                param = self._parse_param(child)
                job_node.add_param(param)
            else:
                # Parse body statements
                statement = self._parse_statement(child)
                if statement:
                    job_node.add_statement(statement)

        return job_node

    def _parse_schedule_statement(self, element: ET.Element) -> ScheduleNode:
        """
        Parse q:schedule - Scheduled task execution.

        Examples:
          <q:schedule name="dailyReport" interval="1d" timezone="America/Sao_Paulo">
            <q:query datasource="db" name="stats">SELECT * FROM daily_stats</q:query>
          </q:schedule>

          <q:schedule name="cleanup" cron="0 2 * * *" retry="3" />
        """
        name = element.get('name')
        if not name:
            raise QuantumParseError("q:schedule requires 'name' attribute")

        schedule_node = ScheduleNode(name=name)

        # Parse action
        schedule_node.action = element.get('action', 'run')

        # Parse trigger attributes
        schedule_node.interval = element.get('interval')
        schedule_node.cron = element.get('cron')
        schedule_node.at = element.get('at')
        schedule_node.timezone = element.get('timezone', 'UTC')
        schedule_node.timeout = element.get('timeout')

        # Parse behavioral attributes
        schedule_node.overlap = element.get('overlap', 'false').lower() == 'true'
        schedule_node.enabled = element.get('enabled', 'true').lower() == 'true'

        retry_attr = element.get('retry')
        if retry_attr:
            try:
                schedule_node.retry = int(retry_attr)
            except ValueError:
                pass

        # Parse body statements
        for child in element:
            statement = self._parse_statement(child)
            if statement:
                schedule_node.add_statement(statement)

        return schedule_node

    def _parse_thread_statement(self, element: ET.Element) -> ThreadNode:
        """
        Parse q:thread - Async thread execution.

        Examples:
          <q:thread name="sendEmails" priority="high">
            <q:loop query="pendingEmails">
              <q:mail to="{email}" subject="Notification">...</q:mail>
            </q:loop>
          </q:thread>

          <q:thread name="worker1" action="join" />
        """
        name = element.get('name')
        if not name:
            raise QuantumParseError("q:thread requires 'name' attribute")

        thread_node = ThreadNode(name=name)

        # Parse attributes
        thread_node.action = element.get('action', 'run')
        thread_node.priority = element.get('priority', 'normal')
        thread_node.timeout = element.get('timeout')
        thread_node.on_complete = element.get('onComplete')
        thread_node.on_error = element.get('onError')

        # Parse body statements
        for child in element:
            statement = self._parse_statement(child)
            if statement:
                thread_node.add_statement(statement)

        return thread_node
    
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

        # Knowledge base / RAG attributes
        query_node.mode = query_element.get('mode')  # None or "rag"
        query_node.rag_model = query_element.get('model')  # LLM model for RAG

        # Parse q:param children
        for child in query_element:
            child_type = self._get_element_name(child)
            if child_type == 'param':
                param_node = self._parse_query_param(child)
                query_node.add_param(param_node)

        # Validate: reject direct {var} interpolation in SQL (SQL injection risk)
        import re
        if sql and re.search(r'\{[a-zA-Z_]\w*\}', sql):
            raise QuantumParseError(
                f"Query '{name}': direct {{var}} interpolation in SQL is not allowed. "
                "Use :param_name with <q:param> for safe parameter binding"
            )

        # Validate: all :param references in SQL must have matching <q:param>
        if sql:
            sql_params = set(re.findall(r':([a-zA-Z_]\w*)', sql))
            declared_params = {p.name for p in query_node.params}
            missing = sql_params - declared_params
            if missing:
                raise QuantumParseError(
                    f"Query '{name}': SQL parameter(s) {', '.join(':' + p for p in sorted(missing))} "
                    "declared in SQL but no matching <q:param> element provided"
                )

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
            'onEvent', 'script', 'query', 'invoke', 'data', 'log', 'dump',
            'import', 'slot',  # Phase 2
            'knowledge',  # Knowledge Base / RAG
            'schedule', 'thread',  # Job Execution System
        }
        if tag in quantum_tags:
            return False

        # Component calls (Phase 2) - Uppercase tags are components, not HTML
        if tag and tag[0].isupper():
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

        Game Engine Imports:
          <q:import behavior="PlayerBehavior" from="./behaviors" />
          <q:import prefab="KoopaGreen" from="./prefabs" />
          <q:import tilemap="yi1" from="./levels" />
        """
        component = element.get('component')
        behavior = element.get('behavior')
        prefab = element.get('prefab')
        tilemap = element.get('tilemap')
        from_path = element.get('from')
        alias = element.get('as')

        if not component and not behavior and not prefab and not tilemap:
            raise QuantumParseError("q:import requires one of 'component', 'behavior', 'prefab', or 'tilemap' attribute")

        return ImportNode(
            component=component,
            from_path=from_path,
            alias=alias,
            behavior=behavior,
            prefab=prefab,
            tilemap=tilemap
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

    # ============================================
    # FORMS & ACTIONS PARSING (Phase A)
    # ============================================

    def _parse_action_statement(self, element: ET.Element) -> ActionNode:
        """
        Parse q:action statement for form handling.

        Examples:
          <q:action name="createUser" method="POST">
            <q:param name="email" type="email" required="true" />
            <q:param name="password" type="string" minlength="8" />
            <q:query datasource="db">
              INSERT INTO users (email, password) VALUES (:email, :password)
            </q:query>
            <q:redirect url="/users" flash="User created!" />
          </q:action>
        """
        name = element.get('name', '')
        method = element.get('method', 'POST')
        action_node = ActionNode(name, method)

        # Parse optional attributes
        if element.get('csrf') == 'false':
            action_node.validate_csrf = False
        if element.get('rate_limit'):
            action_node.rate_limit = element.get('rate_limit')
        if element.get('require_auth') == 'true':
            action_node.require_auth = True

        # Parse children (params, statements)
        for child in element:
            child_type = self._get_element_name(child)

            if child_type == 'param':
                param = self._parse_param(child)
                action_node.add_param(param)
            else:
                # Parse other statements (query, set, redirect, etc.)
                statement = self._parse_statement(child)
                if statement:
                    action_node.add_statement(statement)

        return action_node

    def _parse_redirect_statement(self, element: ET.Element) -> RedirectNode:
        """
        Parse q:redirect statement.

        Examples:
          <q:redirect url="/thank-you" />
          <q:redirect url="/users/{userId}" />
          <q:redirect url="/products" flash="Product created!" />
          <q:redirect url="/error" status="500" flash="Error occurred" />
        """
        url = element.get('url', '')
        flash = element.get('flash')
        status = int(element.get('status', '302'))

        return RedirectNode(url, flash, status)

    def _parse_flash_statement(self, element: ET.Element) -> FlashNode:
        """
        Parse q:flash statement for flash messages.

        Examples:
          <q:flash type="success" message="User created!" />
          <q:flash type="error" message="{errorMessage}" />
          <q:flash type="warning">Please verify your email</q:flash>
        """
        flash_type = element.get('type', 'info')
        message = element.get('message')

        # If message not in attribute, check text content
        if not message and element.text:
            message = element.text.strip()

        return FlashNode(message, flash_type)

    def _parse_file_statement(self, element: ET.Element) -> FileNode:
        """
        Parse q:file statement for file operations.
        
        Phase H: File Uploads
        
        Examples:
          <q:file action="upload" file="{avatar}" destination="./uploads/" />
          <q:file action="upload" file="{document}" destination="./files/" nameConflict="makeUnique" />
        """
        action = element.get('action', 'upload')
        file = element.get('file', '')
        destination = element.get('destination', './uploads/')
        name_conflict = element.get('nameConflict', 'error')
        result = element.get('result')
        
        return FileNode(
            action=action,
            file=file,
            destination=destination,
            name_conflict=name_conflict,
            result=result
        )

    def _parse_mail_statement(self, element: ET.Element) -> MailNode:
        """
        Parse q:mail statement for sending emails.

        Phase I: Email Sending

        Examples:
          <q:mail to="{email}" from="noreply@app.com" subject="Welcome!">
            <h1>Welcome {name}!</h1>
          </q:mail>
        """
        to = element.get('to', '')
        subject = element.get('subject', '')
        from_addr = element.get('from')
        cc = element.get('cc')
        bcc = element.get('bcc')
        reply_to = element.get('replyTo')
        mail_type = element.get('type', 'html')
        charset = element.get('charset', 'UTF-8')

        # Create mail node
        mail_node = MailNode(
            to=to,
            subject=subject,
            from_addr=from_addr,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
            type=mail_type,
            charset=charset
        )

        # Parse body content (can be text or HTML elements)
        if element.text and element.text.strip():
            mail_node.body = element.text.strip()
        else:
            # Parse child elements as HTML body
            body_parts = []
            for child in element:
                if child.tag:
                    # Reconstruct HTML from children
                    body_parts.append(ET.tostring(child, encoding='unicode', method='html'))
            if body_parts:
                mail_node.body = ''.join(body_parts)

        return mail_node

    def _parse_transaction_statement(self, element: ET.Element) -> TransactionNode:
        """
        Parse q:transaction statement for database transactions.

        Phase D: Database Backend

        Examples:
          <q:transaction>
            <q:query datasource="db" name="debit">
              UPDATE accounts SET balance = balance - :amount WHERE id = :from_id
            </q:query>
            <q:query datasource="db" name="credit">
              UPDATE accounts SET balance = balance + :amount WHERE id = :to_id
            </q:query>
          </q:transaction>

          <q:transaction isolationLevel="SERIALIZABLE">
            <!-- Critical financial operations -->
          </q:transaction>
        """
        isolation_level = element.get('isolationLevel', 'READ_COMMITTED')

        # Create transaction node
        transaction_node = TransactionNode(isolation_level=isolation_level)

        # Parse child statements (queries, sets, etc.)
        for child in element:
            statement = self._parse_statement(child)
            if statement:
                transaction_node.add_statement(statement)

        return transaction_node

    # ============================================
    # LLM PARSING (q:llm with Ollama backend)
    # ============================================

    def _parse_llm_statement(self, element: ET.Element) -> LLMNode:
        """
        Parse q:llm statement for LLM invocation via Ollama.

        Examples:
          <q:llm name="greeting" model="phi3">
            <q:prompt>Say hello to {userName}</q:prompt>
          </q:llm>

          <q:llm name="chat" model="mistral">
            <q:message role="system">You are a helpful assistant</q:message>
            <q:message role="user">{question}</q:message>
          </q:llm>

          <q:llm name="data" model="llama3" responseFormat="json" temperature="0.1">
            <q:prompt>Extract name and age from: {text}</q:prompt>
          </q:llm>
        """
        name = element.get('name')
        if not name:
            raise QuantumParseError("q:llm requires 'name' attribute")

        llm_node = LLMNode(name)

        # Parse attributes
        llm_node.model = element.get('model')
        llm_node.endpoint = element.get('endpoint')
        llm_node.system = element.get('system')
        llm_node.response_format = element.get('responseFormat')
        llm_node.cache = element.get('cache', 'false').lower() == 'true'

        temperature_attr = element.get('temperature')
        if temperature_attr:
            try:
                llm_node.temperature = float(temperature_attr)
            except ValueError:
                pass

        max_tokens_attr = element.get('maxTokens')
        if max_tokens_attr:
            try:
                llm_node.max_tokens = int(max_tokens_attr)
            except ValueError:
                pass

        timeout_attr = element.get('timeout')
        if timeout_attr:
            try:
                llm_node.timeout = int(timeout_attr)
            except ValueError:
                pass

        # Parse child elements: <q:prompt> and <q:message>
        for child in element:
            child_type = self._get_element_name(child)

            if child_type == 'prompt':
                # Extract prompt text content
                llm_node.prompt = (child.text or '').strip()

            elif child_type == 'message':
                role = child.get('role', 'user')
                content = (child.text or '').strip()
                if content:
                    llm_node.messages.append(LLMMessageNode(role, content))

        return llm_node

    # ============================================
    # AGENT PARSING (q:agent with tool use)
    # ============================================

    def _parse_agent_statement(self, element: ET.Element) -> AgentNode:
        """
        Parse q:agent statement for AI agents with tool use.

        Examples:
          <q:agent name="support" model="phi3" max_iterations="5">
            <q:instruction>You are a helpful assistant.</q:instruction>

            <q:tool name="getOrder" description="Get order by ID">
              <q:param name="orderId" type="integer" required="true" />
              <q:function name="fetch">
                <q:query name="order" datasource="db">
                  SELECT * FROM orders WHERE id = :orderId
                </q:query>
                <q:return value="{order[0]}" />
              </q:function>
            </q:tool>

            <q:execute task="{userQuestion}" />
          </q:agent>
        """
        name = element.get('name')
        if not name:
            raise QuantumParseError("q:agent requires 'name' attribute")

        # Create agent node with defaults
        agent_node = AgentNode(name=name)

        # Parse attributes
        agent_node.model = element.get('model', 'phi3')
        agent_node.endpoint = element.get('endpoint', '')
        agent_node.provider = element.get('provider', 'auto')
        agent_node.api_key = element.get('api_key') or element.get('apiKey', '')

        max_iter = element.get('max_iterations') or element.get('maxIterations')
        if max_iter:
            try:
                agent_node.max_iterations = int(max_iter)
            except ValueError:
                pass

        timeout = element.get('timeout')
        if timeout:
            try:
                agent_node.timeout = int(timeout)
            except ValueError:
                pass

        # Parse child elements
        for child in element:
            child_type = self._get_element_name(child)

            if child_type == 'instruction':
                agent_node.instruction = AgentInstructionNode(
                    content=self._get_text_content(child)
                )

            elif child_type == 'tool':
                tool_node = self._parse_agent_tool(child)
                agent_node.tools.append(tool_node)

            elif child_type == 'execute':
                task = child.get('task') or self._get_text_content(child)
                context = child.get('context', '')
                agent_node.execute = AgentExecuteNode(task=task, context=context)

        return agent_node

    def _parse_agent_tool(self, element: ET.Element) -> AgentToolNode:
        """Parse q:tool element within an agent."""
        name = element.get('name', '')
        description = element.get('description', '')
        builtin = element.get('builtin', 'false').lower() == 'true'

        tool_node = AgentToolNode(name=name, description=description, builtin=builtin)

        for child in element:
            child_type = self._get_element_name(child)

            if child_type == 'param':
                param_node = AgentToolParamNode(
                    name=child.get('name', ''),
                    type=child.get('type', 'string'),
                    required=child.get('required', 'false').lower() == 'true',
                    default=child.get('default'),
                    description=child.get('description', '')
                )
                tool_node.params.append(param_node)
            else:
                # Parse body elements (q:function, q:query, etc.)
                body_node = self._parse_statement(child)
                if body_node:
                    tool_node.body.append(body_node)

        return tool_node

    # ============================================
    # MULTI-AGENT TEAM PARSING (q:team)
    # ============================================

    def _parse_team_statement(self, element: ET.Element) -> AgentTeamNode:
        """
        Parse q:team statement for multi-agent collaboration.

        Examples:
          <q:team name="support" supervisor="router">
            <q:shared>
              <q:set name="customerId" value="123" />
            </q:shared>

            <q:agent name="router" model="gpt-4">
              <q:instruction>Route to appropriate specialist</q:instruction>
              <q:tool name="handoff" builtin="true" />
            </q:agent>

            <q:agent name="billing" model="gpt-4">
              <q:instruction>Handle billing questions</q:instruction>
              <q:tool name="readShared" builtin="true" />
            </q:agent>

            <q:execute task="{question}" entry="router" />
          </q:team>
        """
        name = element.get('name')
        if not name:
            raise QuantumParseError("q:team requires 'name' attribute")

        # Create team node with defaults
        team_node = AgentTeamNode(name=name)

        # Parse attributes
        team_node.supervisor = element.get('supervisor', '')

        max_handoffs = element.get('max_handoffs') or element.get('maxHandoffs')
        if max_handoffs:
            try:
                team_node.max_handoffs = int(max_handoffs)
            except ValueError:
                pass

        max_iterations = element.get('max_total_iterations') or element.get('maxTotalIterations')
        if max_iterations:
            try:
                team_node.max_total_iterations = int(max_iterations)
            except ValueError:
                pass

        # Parse child elements
        for child in element:
            child_type = self._get_element_name(child)

            if child_type == 'shared':
                # Parse shared state initializers
                for var in child:
                    var_type = self._get_element_name(var)
                    if var_type == 'set':
                        set_node = self._parse_set_statement(var)
                        team_node.shared.append(set_node)

            elif child_type == 'agent':
                agent_node = self._parse_agent_statement(child)
                team_node.agents.append(agent_node)

            elif child_type == 'execute':
                task = child.get('task') or self._get_text_content(child)
                context = child.get('context', '')
                entry = child.get('entry', '')
                team_node.execute = AgentExecuteNode(task=task, context=context, entry=entry)

        # If no supervisor specified, use first agent
        if not team_node.supervisor and team_node.agents:
            team_node.supervisor = team_node.agents[0].name

        return team_node

    def _get_text_content(self, element: ET.Element) -> str:
        """Get text content from an element, handling mixed content."""
        text_parts = []
        if element.text:
            text_parts.append(element.text)
        for child in element:
            if child.tail:
                text_parts.append(child.tail)
        return ''.join(text_parts).strip()

    # ============================================
    # WEBSOCKET PARSING (q:websocket)
    # ============================================

    def _parse_websocket_statement(self, element: ET.Element) -> WebSocketNode:
        """
        Parse q:websocket statement for real-time communication.

        Examples:
          <q:websocket name="chat" url="wss://api.example.com/chat"
                       auto_connect="true" reconnect="true">
            <q:on-connect>
              <q:log level="info">Connected!</q:log>
            </q:on-connect>

            <q:on-message>
              <q:set name="messages" operation="append" value="{data}" />
            </q:on-message>

            <q:on-error>
              <q:log level="error">{error}</q:log>
            </q:on-error>

            <q:on-close>
              <q:set name="connected" value="false" />
            </q:on-close>
          </q:websocket>
        """
        name = element.get('name')
        if not name:
            raise QuantumParseError("q:websocket requires 'name' attribute")

        url = element.get('url', '')
        if not url:
            raise QuantumParseError("q:websocket requires 'url' attribute")

        # Create WebSocket node
        ws_node = WebSocketNode(name=name, url=url)

        # Parse optional attributes
        auto_connect = element.get('auto_connect') or element.get('autoConnect', 'true')
        ws_node.auto_connect = auto_connect.lower() == 'true'

        reconnect = element.get('reconnect', 'true')
        ws_node.reconnect = reconnect.lower() == 'true'

        reconnect_delay = element.get('reconnect_delay') or element.get('reconnectDelay')
        if reconnect_delay:
            try:
                ws_node.reconnect_delay = int(reconnect_delay)
            except ValueError:
                pass

        max_reconnects = element.get('max_reconnects') or element.get('maxReconnects')
        if max_reconnects:
            try:
                ws_node.max_reconnects = int(max_reconnects)
            except ValueError:
                pass

        heartbeat = element.get('heartbeat')
        if heartbeat:
            try:
                ws_node.heartbeat = int(heartbeat)
            except ValueError:
                pass

        protocols = element.get('protocols', '')
        ws_node.protocols = protocols

        # Parse event handlers (q:on-connect, q:on-message, etc.)
        for child in element:
            child_type = self._get_element_name(child)

            if child_type.startswith('on-'):
                event_name = child_type[3:]  # Remove 'on-' prefix
                handler = self._parse_websocket_handler(child, event_name)
                ws_node.handlers.append(handler)

        return ws_node

    def _parse_websocket_handler(self, element: ET.Element, event: str) -> WebSocketHandlerNode:
        """Parse q:on-* event handler for WebSocket."""
        handler = WebSocketHandlerNode(event=event)

        # Parse body elements
        for child in element:
            body_node = self._parse_statement(child)
            if body_node:
                handler.body.append(body_node)

        return handler

    def _parse_websocket_send(self, element: ET.Element) -> WebSocketSendNode:
        """
        Parse q:websocket-send statement.

        Examples:
          <q:websocket-send connection="chat" message="{userInput}" type="json" />
        """
        connection = element.get('connection', '')
        if not connection:
            raise QuantumParseError("q:websocket-send requires 'connection' attribute")

        message = element.get('message', '')
        if not message:
            # Try text content
            message = self._get_text_content(element)

        msg_type = element.get('type', 'text')

        return WebSocketSendNode(
            connection=connection,
            message=message,
            type=msg_type
        )

    def _parse_websocket_close(self, element: ET.Element) -> WebSocketCloseNode:
        """
        Parse q:websocket-close statement.

        Examples:
          <q:websocket-close connection="chat" code="1000" reason="User logout" />
        """
        connection = element.get('connection', '')
        if not connection:
            raise QuantumParseError("q:websocket-close requires 'connection' attribute")

        code = 1000
        code_str = element.get('code')
        if code_str:
            try:
                code = int(code_str)
            except ValueError:
                pass

        reason = element.get('reason', '')

        return WebSocketCloseNode(
            connection=connection,
            code=code,
            reason=reason
        )

    # ============================================
    # STATE PERSISTENCE PARSING (q:persist)
    # ============================================

    def _parse_persist_statement(self, element: ET.Element) -> PersistNode:
        """
        Parse q:persist statement for explicit persistence configuration.

        Examples:
          <q:persist scope="local" prefix="myapp_">
            <q:var name="theme" />
            <q:var name="locale" />
          </q:persist>

          <q:persist scope="sync" key="user_prefs" encrypt="true">
            <q:var name="darkMode" />
            <q:var name="fontSize" />
          </q:persist>
        """
        scope = element.get('scope', 'local')
        prefix = element.get('prefix')
        key = element.get('key')
        encrypt = element.get('encrypt', 'false').lower() == 'true'
        storage = element.get('storage')

        ttl = None
        ttl_attr = element.get('ttl')
        if ttl_attr:
            try:
                ttl = int(ttl_attr)
            except ValueError:
                pass

        persist_node = PersistNode(
            scope=scope,
            prefix=prefix,
            key=key,
            encrypt=encrypt,
            ttl=ttl,
            storage=storage
        )

        # Parse q:var children
        for child in element:
            child_type = self._get_element_name(child)
            if child_type == 'var':
                var_name = child.get('name')
                if var_name:
                    persist_node.add_variable(var_name)

        return persist_node

    # ============================================
    # MESSAGE QUEUE SYSTEM PARSERS
    # ============================================

    def _parse_message_statement(self, element: ET.Element) -> MessageNode:
        """
        Parse q:message statement for publishing/sending messages.

        Examples:
          <!-- Publish to topic -->
          <q:message name="result" topic="orders.created" type="publish">
            <q:header name="priority" value="high" />
            <q:body>{orderData}</q:body>
          </q:message>

          <!-- Send to queue -->
          <q:message name="taskId" queue="email-queue" type="send">
            <q:body>{"to": "{email}", "subject": "Welcome!"}</q:body>
          </q:message>

          <!-- Request/reply -->
          <q:message name="response" queue="calculator" type="request" timeout="5000">
            <q:body>{"operation": "add", "a": 5, "b": 3}</q:body>
          </q:message>
        """
        name = element.get('name')
        topic = element.get('topic')
        queue = element.get('queue')
        msg_type = element.get('type', 'publish')
        timeout = element.get('timeout')

        message_node = MessageNode(
            name=name,
            topic=topic,
            queue=queue,
            type=msg_type,
            timeout=timeout
        )

        # Parse child elements (headers and body)
        for child in element:
            child_type = self._get_element_name(child)

            if child_type == 'header':
                header_name = child.get('name', '')
                header_value = child.get('value', '')
                header_node = MessageHeaderNode(name=header_name, value=header_value)
                message_node.add_header(header_node)

            elif child_type == 'body':
                # Body can be text content or the element's text
                body_text = child.text
                if body_text:
                    message_node.body = body_text.strip()

        # If no q:body child, check for direct text content
        if not message_node.body and element.text:
            message_node.body = element.text.strip()

        return message_node

    def _parse_subscribe_statement(self, element: ET.Element) -> SubscribeNode:
        """
        Parse q:subscribe statement for subscribing to topics or consuming from queues.

        Examples:
          <!-- Subscribe to topic -->
          <q:subscribe name="orderHandler" topic="orders.*" ack="auto">
            <q:onMessage>
              <q:set name="order" value="{message.body}" />
              <q:log message="Received order: {order.id}" />
            </q:onMessage>
            <q:onError>
              <q:log level="error" message="Failed to process: {error}" />
            </q:onError>
          </q:subscribe>

          <!-- Consume from queue with manual ack -->
          <q:subscribe name="emailWorker" queue="email-queue" ack="manual" prefetch="10">
            <q:onMessage>
              <q:mail to="{message.body.to}" subject="{message.body.subject}" />
              <q:messageAck />
            </q:onMessage>
          </q:subscribe>
        """
        name = element.get('name', '')
        topic = element.get('topic')
        topics = element.get('topics')
        queue = element.get('queue')
        ack = element.get('ack', 'auto')
        prefetch = int(element.get('prefetch', '1'))

        subscribe_node = SubscribeNode(
            name=name,
            topic=topic,
            topics=topics,
            queue=queue,
            ack=ack,
            prefetch=prefetch
        )

        # Parse child elements (onMessage and onError handlers)
        for child in element:
            child_type = self._get_element_name(child)

            if child_type == 'onMessage':
                # Parse statements inside onMessage
                for stmt_element in child:
                    statement = self._parse_statement(stmt_element)
                    if statement:
                        subscribe_node.add_on_message_statement(statement)

            elif child_type == 'onError':
                # Parse statements inside onError
                for stmt_element in child:
                    statement = self._parse_statement(stmt_element)
                    if statement:
                        subscribe_node.add_on_error_statement(statement)

        return subscribe_node

    def _parse_queue_statement(self, element: ET.Element) -> QueueNode:
        """
        Parse q:queue statement for queue declaration and management.

        Examples:
          <!-- Declare a durable queue -->
          <q:queue name="email-queue" action="declare" durable="true" />

          <!-- Declare with dead letter queue -->
          <q:queue name="orders" action="declare" durable="true"
                   deadLetterQueue="orders-dlq" ttl="86400000" />

          <!-- Purge messages -->
          <q:queue name="temp-queue" action="purge" />

          <!-- Get queue info -->
          <q:queue name="orders" action="info" result="queueInfo" />
        """
        name = element.get('name', '')
        action = element.get('action', 'declare')
        durable = element.get('durable', 'true').lower() == 'true'
        exclusive = element.get('exclusive', 'false').lower() == 'true'
        auto_delete = element.get('autoDelete', 'false').lower() == 'true'
        dead_letter_queue = element.get('deadLetterQueue')
        ttl_str = element.get('ttl')
        ttl = int(ttl_str) if ttl_str else None
        result = element.get('result')

        return QueueNode(
            name=name,
            action=action,
            durable=durable,
            exclusive=exclusive,
            auto_delete=auto_delete,
            dead_letter_queue=dead_letter_queue,
            ttl=ttl,
            result=result
        )

    def _parse_message_ack_statement(self, element: ET.Element) -> MessageAckNode:
        """
        Parse q:messageAck statement for acknowledging messages.

        Example:
          <q:subscribe name="worker" queue="tasks" ack="manual">
            <q:onMessage>
              <q:set name="processed" value="true" />
              <q:messageAck />
            </q:onMessage>
          </q:subscribe>
        """
        return MessageAckNode()

    def _parse_message_nack_statement(self, element: ET.Element) -> MessageNackNode:
        """
        Parse q:messageNack statement for negative acknowledgment.

        Examples:
          <!-- Reject and requeue -->
          <q:messageNack requeue="true" />

          <!-- Reject without requeue (send to DLQ) -->
          <q:messageNack requeue="false" />
        """
        requeue = element.get('requeue', 'true').lower() == 'true'
        return MessageNackNode(requeue=requeue)

    # =========================================================================
    # Python Scripting System
    # =========================================================================

    def _parse_python_statement(self, element: ET.Element) -> PythonNode:
        """
        Parse q:python statement for embedded Python code.

        Examples:
          <!-- Simple Python block -->
          <q:python>
              import pandas as pd
              df = pd.read_csv('data.csv')
              q.total = df['sales'].sum()
          </q:python>

          <!-- Async execution -->
          <q:python async="true" timeout="30s">
              import aiohttp
              async with aiohttp.ClientSession() as session:
                  response = await session.get(url)
                  q.data = await response.json()
          </q:python>

          <!-- With result capture -->
          <q:python result="calculation">
              return sum([1, 2, 3, 4, 5])
          </q:python>
        """
        import textwrap

        # Get the code content
        code = element.text or ""

        # Clean up indentation (remove common leading whitespace)
        code = textwrap.dedent(code).strip()

        # Parse attributes
        scope = element.get('scope', 'component')
        async_mode = element.get('async', 'false').lower() == 'true'
        timeout = element.get('timeout')
        result = element.get('result')

        return PythonNode(
            code=code,
            scope=scope,
            async_mode=async_mode,
            timeout=timeout,
            result=result
        )

    def _parse_pyimport_statement(self, element: ET.Element) -> PyImportNode:
        """
        Parse q:pyimport statement for Python module imports.

        Examples:
          <!-- Import with alias -->
          <q:pyimport module="pandas" as="pd" />

          <!-- Import specific names -->
          <q:pyimport module="sklearn.ensemble" names="RandomForestClassifier, GradientBoostingClassifier" />

          <!-- Simple import -->
          <q:pyimport module="json" />
        """
        module = element.get('module', '')
        alias = element.get('as')
        names_str = element.get('names', '')

        # Parse comma-separated names
        names = [n.strip() for n in names_str.split(',') if n.strip()]

        return PyImportNode(
            module=module,
            alias=alias,
            names=names
        )

    def _parse_pyclass_statement(self, element: ET.Element) -> PyClassNode:
        """
        Parse q:class statement for inline Python class definitions.

        Examples:
          <q:class name="OrderProcessor">
              def __init__(self, db):
                  self.db = db

              def process(self, order_id):
                  order = self.db.get(order_id)
                  return self.validate(order)

              def validate(self, order):
                  return order.total > 0
          </q:class>

          <!-- With inheritance -->
          <q:class name="AdminUser" bases="User, Permissions">
              role = 'admin'

              def has_permission(self, perm):
                  return True
          </q:class>
        """
        import textwrap

        name = element.get('name', '')
        code = element.text or ""
        code = textwrap.dedent(code).strip()

        # Parse bases (comma-separated)
        bases_str = element.get('bases', '')
        bases = [b.strip() for b in bases_str.split(',') if b.strip()]

        # Parse decorators (comma-separated)
        decorators_str = element.get('decorators', '')
        decorators = [d.strip() for d in decorators_str.split(',') if d.strip()]

        return PyClassNode(
            name=name,
            code=code,
            bases=bases,
            decorators=decorators
        )

    def _parse_pydecorator_statement(self, element: ET.Element) -> PyDecoratorNode:
        """
        Parse q:decorator statement for Python decorator definitions.

        Examples:
          <!-- Caching decorator -->
          <q:decorator name="cached">
              from functools import wraps
              def decorator(func):
                  cache = {}
                  @wraps(func)
                  def wrapper(*args):
                      if args in cache:
                          return cache[args]
                      result = func(*args)
                      cache[args] = result
                      return result
                  return wrapper
              return decorator
          </q:decorator>

          <!-- Decorator with parameters -->
          <q:decorator name="retry" params="attempts, delay">
              import time
              def decorator(func):
                  def wrapper(*args, **kwargs):
                      for i in range(attempts):
                          try:
                              return func(*args, **kwargs)
                          except Exception as e:
                              if i == attempts - 1:
                                  raise
                              time.sleep(delay)
                  return wrapper
              return decorator
          </q:decorator>
        """
        import textwrap

        name = element.get('name', '')
        code = element.text or ""
        code = textwrap.dedent(code).strip()

        # Parse params (comma-separated)
        params_str = element.get('params', '')
        params = [p.strip() for p in params_str.split(',') if p.strip()]

        return PyDecoratorNode(
            name=name,
            code=code,
            params=params
        )
