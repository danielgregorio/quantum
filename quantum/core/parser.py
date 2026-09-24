"""
Quantum Parser - Convert .q files (XML) to Quantum AST
"""

import re
from pathlib import Path
from xml.etree import ElementTree as ET
from typing import Optional

# Fix imports

from quantum.core.html_compat import normalise_html
from quantum.core.xml_lines import fromstring_with_lines, line_of
from quantum.core.ast_nodes import (
    QuantumNode, ComponentNode, ApplicationNode, JobNode,
    QuantumParam, QuantumReturn, QuantumRoute,
    DispatchEventNode, OnEventNode, HTMLNode, TextNode, DocTypeNode, CommentNode, ImportNode, SlotNode, ComponentCallNode,
    ActionNode, FlashNode
)
# Import feature AST nodes from their respective modules
from quantum.core.features.conditionals.src.ast_node import IfNode
from quantum.core.features.loops.src.ast_node import LoopNode
from quantum.core.features.state_management.src.ast_node import SetNode
from quantum.core.docs_links import HOW_A_PAGE_RUNS
from quantum.core.features.functions.src.ast_node import FunctionNode
from quantum.core.features.game_engine_2d.src.parser import GameParser
from quantum.core.features.game_engine_2d.src.ast_nodes import (
    SceneNode, BehaviorNode, PrefabNode, PersistentNode, EnemyNode,
)
from quantum.core.features.terminal_engine.src.parser import TerminalParser
from quantum.core.features.terminal_engine.src.ast_nodes import (
    ScreenNode as TerminalScreenNode, KeybindingNode as TerminalKeybindingNode,
    ServiceNode as TerminalServiceNode, CssNode as TerminalCssNode,
)
from quantum.core.features.ui_engine.src.parser import UIParser, UIParseError
from quantum.core.features.ui_engine.src.ast_nodes import is_ui_node
from quantum.core.features.ui_engine.src.ast_nodes import UIWindowNode
from quantum.core.features.theming.src import UIThemeNode
from quantum.core.parser_registry import ParserRegistry
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
    from quantum.core.parsers import (
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
    # New modular parsers (Phase 2 - Operacao Guilhotina)
    from quantum.core.parsers.forms import ActionParser, RedirectParser, FlashParser
    from quantum.core.parsers.composition import ImportParser, SlotParser
    from quantum.core.parsers.functions import FunctionParser
    from quantum.core.parsers.events import DispatchEventParser
    from quantum.core.parsers.messaging import MessageAckParser, MessageNackParser
    from quantum.core.parsers.scripting import PyDecoratorParser

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
        MessageAckParser(parser),
        MessageNackParser(parser),
        # Jobs
        ScheduleParser(parser),
        ThreadParser(parser),
        JobParser(parser),
        # Scripting
        PythonParser(parser),
        PyImportParser(parser),
        PyClassParser(parser),
        PyDecoratorParser(parser),
        # HTML (registers for common HTML tags)
        HTMLParser(parser),
        # Forms & Actions
        ActionParser(parser),
        RedirectParser(parser),
        FlashParser(parser),
        # Component Composition
        ImportParser(parser),
        SlotParser(parser),
        # Functions
        FunctionParser(parser),
        # Note: ReturnParser, ParamParser, RouteParser are not registered here
        # They are internal parsers used by FunctionParser and other parsers
        # Events
        DispatchEventParser(parser),
    ]

    registry.register_all(parsers)

    # Store special parsers for fallback handling
    # These are used when no specific tag parser matches
    registry.html_parser = HTMLParser(parser)
    registry.component_call_parser = ComponentCallParser(parser)

    logger.debug(f"Initialized parser registry with {registry.parser_count} parsers")

    return registry


from quantum.core.parsers.base import ParserError  # noqa: E402


class QuantumParseError(Exception):
    """Quantum parsing error"""
    pass


def _explain_xml_error(error, source: str) -> str:
    """Turn a raw ElementTree error into something actionable.

    A .q file is XML, so a bare `<` or `&` inside SQL or JavaScript breaks
    parsing with a message ("not well-formed (invalid token)") that says
    nothing about the actual cause. This has bitten the same way at least
    twice (a JS `for` loop in q:llm, a SQL `<` in q:schedule), so name it.
    """
    message = f"XML parse error: {error}"

    line_no = getattr(error, 'position', (None, None))[0]
    offending = ''
    if line_no:
        lines = source.splitlines()
        if 0 < line_no <= len(lines):
            offending = lines[line_no - 1].strip()

    if offending:
        message += f"\n  at line {line_no}: {offending}"

    if offending and ('<' in offending or '&' in offending):
        message += (
            "\n  Hint: a .q file is XML, so a bare '<' or '&' is invalid even "
            "inside SQL or JavaScript.\n"
            "  Write '&lt;' / '&amp;', or wrap the body in <![CDATA[ ... ]]>."
        )

    return message


def _at(error: 'QuantumParseError', where) -> 'QuantumParseError':
    """The error belongs to this node's (or element's) line."""
    error.line = line_of(where)
    return error


def _with_line(error: 'QuantumParseError', source: str, line: Optional[int] = None) -> 'QuantumParseError':
    """DEV-2: a parse error says where it is — `at line N: <the line>`."""
    line = line or getattr(error, 'line', None)
    error.line = line
    if line and ' at line ' not in str(error):
        lines = source.splitlines()
        snippet = lines[line - 1].strip() if 0 < line <= len(lines) else ''
        error.args = (f"{error}\n  at line {line}: {snippet}" if snippet else f"{error} (line {line})",)
    return error


class QuantumParser:
    """Main parser for .q files"""

    def __init__(self, use_cache: bool = True, use_modular_parsers: bool = True):
        self.quantum_ns = {'q': 'https://quantum.lang/ns'}
        self._use_cache = use_cache
        self._source_path: Optional[str] = None  # Path of the file being parsed
        self._ast_cache = None
        if use_cache:
            try:
                from quantum.runtime.ast_cache import get_ast_cache
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

    # Prefix -> URI the framework injects by itself.
    _NAMESPACES = {
        'q': 'https://quantum.lang/ns',
        'qg': 'https://quantum.lang/game',
        'qt': 'https://quantum.lang/terminal',
        # APP-2: the removed testing engine's prefix is still declared, so a
        # qtest: tag reaches the removal message instead of "unbound prefix".
        'qtest': 'https://quantum.lang/testing',
        'ui': 'https://quantum.lang/ui',
    }

    # The document's first element, whatever it is.
    _FIRST_ELEMENT = re.compile(r'<([A-Za-z_][\w.:-]*)((?:\s[^<>]*?)?)(/?)>')

    def _inject_namespace(self, content: str) -> str:
        """Declares the framework namespaces the author did not declare.

        This allows writing `<q:component name="Foo">` without ceremony,
        instead of `<q:component name="Foo" xmlns:q="https://quantum.lang/ns">`.

        Two things were wrong:

        1. **The detection was by SUBSTRING.** `if 'xmlns:q' in content`
           matches `xmlns:qt=`, `xmlns:qg=` and `xmlns:qtest=`. A file that
           declared only its engine's namespace fell into the "already has a
           namespace" branch, and in there every injection was a
           `content.replace('xmlns:q="https://quantum.lang/ns"', ...)` that
           found nothing. Result: NO namespace was declared and the file died
           with "unbound prefix" — with the message pointing to line 1,
           column 0, which tells nobody anything.

        2. **Only three roots were recognised** (`q:component`,
           `q:application`, `q:job`). A file whose root is `<q:behavior>` or
           `<qg:scene>` — the scenes and behaviours scene-include loads, 16
           files shipped in the repository — did not match the pattern and
           got no namespace either.

        Now the detection is by the EXACT prefix (`xmlns:q=`) and the
        injection goes on the first element, whatever it is. A root the
        framework does not support now fails in `_parse_root_element`, with
        the element's name in the message, instead of "unbound prefix".
        """
        missing = {}
        for prefix, uri in self._NAMESPACES.items():
            if f'xmlns:{prefix}=' in content:
                continue          # the author declared it; respect the choice
            # Only what the document really uses.
            if f'<{prefix}:' in content or f'</{prefix}:' in content:
                missing[prefix] = uri

        # `type="game"` implies qg: even before any qg: tag appears, and so
        # on — behaviour that already existed.
        for attribute, prefix in (('type="game"', 'qg'),
                                  ('type="terminal"', 'qt'),
                                  ('type="ui"', 'ui')):
            if attribute in content and f'xmlns:{prefix}=' not in content:
                missing[prefix] = self._NAMESPACES[prefix]

        if not missing:
            return content

        declarations = ''.join(f' xmlns:{p}="{u}"' for p, u in
                              sorted(missing.items()))

        def declare(match):
            name, attrs, close = match.groups()
            return f'<{name}{attrs}{declarations}{close}>'

        # Only on the first ELEMENT. The prolog — XML declaration, doctype and
        # comments — is skipped whole: examples/python-scripting.q opens with a
        # comment that mentions `<cfscript>`, and matching there would inject
        # the namespaces inside the comment, leaving the real component with
        # none.
        offset = self._first_element_offset(content)
        replaced = self._FIRST_ELEMENT.sub(
            declare, content[offset:], count=1)
        return content[:offset] + replaced

    @staticmethod
    def _first_element_offset(content: str) -> int:
        """Where the first real element starts."""
        i = 0
        n = len(content)
        while i < n:
            while i < n and content[i].isspace():
                i += 1
            if content.startswith('<?', i):
                end = content.find('?>', i)
                if end == -1:
                    return i
                i = end + 2
            elif content.startswith('<!--', i):
                end = content.find('-->', i)
                if end == -1:
                    return i
                i = end + 3
            elif content.startswith('<!', i):        # DOCTYPE
                end = content.find('>', i)
                if end == -1:
                    return i
                i = end + 1
            else:
                return i
        return 0

    def parse(self, source: str) -> QuantumNode:
        """Parse Quantum XML from a string."""
        try:
            # Accept the HTML people actually write: boolean attributes
            # (<input required />) and bare ampersands (Forms & Actions) are
            # valid HTML and invalid XML. Ten of the forty-eight components
            # shipped with this framework — login.q among them — failed to
            # parse for exactly those two reasons and returned HTTP 400.
            content = normalise_html(source)
            content = self._inject_namespace(content)
            root = fromstring_with_lines(content)
            self._refuse_removed_namespaces(root)
            self._nest_else_siblings(root)
            return self._parse_root_element(root, Path("<string>"))
        except ET.ParseError as e:
            error = QuantumParseError(_explain_xml_error(e, source))
            error.line = getattr(e, 'position', (None, None))[0]
            raise error
        except QuantumParseError as e:
            raise _with_line(e, source)
        except ParserError as e:
            # A tag parser's own error is a parse error with a message meant
            # for the author, not an "Unexpected error".
            raise _with_line(QuantumParseError(str(e)), source, getattr(e, 'line', None)) from e
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
                self._source_path = str(path.resolve())
                return self._ast_cache.get_or_parse(file_path, self)

            # Fallback to direct parsing
            self._source_path = str(path.resolve())
            source = Path(file_path).read_text(encoding="utf-8")
            return self.parse(source)
        except QuantumParseError as e:
            if getattr(e, 'file', None) is None:
                e.file = str(path.resolve())                  # DEV-2
            raise
        except ParserError as e:
            # A tag parser's own error is a parse error with a message meant
            # for the author, not an "Unexpected error".
            raise QuantumParseError(str(e)) from e
        except Exception as e:
            raise QuantumParseError(f"Unexpected error: {e}")

    def invalidate_cache(self, file_path: str = None):
        """Invalidate cached AST for a file or all files

        Args:
            file_path: Specific file to invalidate, or None for all
        """
        if self._ast_cache is not None:
            self._ast_cache.invalidate(file_path)

    @staticmethod
    def _refuse_removed_namespaces(root: ET.Element) -> None:
        """APP-2: a tag of a removed engine (qtest:) is a parse error that
        says so, wherever it is in the file."""
        from quantum.core.tiers import REMOVED_NAMESPACES, removed_testing_engine_message
        for prefix, uri in REMOVED_NAMESPACES.items():
            for element in root.iter():
                if not str(element.tag).startswith(f'{{{uri}}}'):
                    continue
                name = element.tag.split('}', 1)[1]
                raise _at(QuantumParseError(removed_testing_engine_message(f'<{prefix}:{name}>')), element)

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

    def _nest_else_siblings(self, root: ET.Element) -> None:
        """Move each `<q:else>` / `<q:elseif>` written right after `</q:if>`
        into that if, so both spellings reach IfParser as the nested form.

        The sibling form used to be paired only in the component body and in
        BaseTagParser.parse_statements. Every other body — q:loop, q:function,
        q:transaction, HTML elements and a dozen more — walks its children one
        by one, so there the else was dropped without a word:
        `<q:loop>...<q:if>..</q:if><q:else>..</q:else></q:loop>` never ran the
        else, and a q:function with a sibling q:elseif returned None. Doing it
        once on the XML tree covers every parser, including future ones.

        A direct else child of a q:if is already the nested form and stays
        where it is. An else with no q:if right before it is an error.
        """
        parents = list(root.iter())
        # IF-4 looks at the else children as written: before any sibling-form
        # else is moved into its q:if below (which is not ambiguous).
        for parent in parents:
            if self._get_element_name(parent) == 'if':
                self._check_dangling_else(parent)
        for parent in parents:
            if self._get_element_name(parent) == 'if':
                continue
            previous = None
            for child in list(parent):
                if not isinstance(child.tag, str):
                    continue                      # comments, processing instructions
                name = self._get_element_name(child)
                if name in ('else', 'elseif') and self._is_quantum_tag(child):
                    if previous is None:
                        raise QuantumParseError(
                            f"<q:{name}> has no matching <q:if> before it. "
                            f"Put it inside the if, or right after it: "
                            f"<q:if ...>...</q:if> <q:{name}>...</q:{name}>"
                        )
                    parent.remove(child)
                    previous.tail = (previous.tail or '') + (child.tail or '')
                    child.tail = None
                    previous.append(child)
                    continue
                previous = child if name == 'if' and self._is_quantum_tag(child) else None

    def _check_dangling_else(self, if_element: ET.Element) -> None:
        """IF-4: inside a q:if, a q:else/q:elseif right after an inner </q:if> is ambiguous.

        IF-1 gives it to the outer q:if (a direct child belongs to its if), but
        written right after an inner if it reads as that if's else — the
        sibling form. A page built that way drew the else branch of the inner
        if when the OUTER condition was false. Refused, with both fixes."""
        previous = None
        for child in if_element:
            if not isinstance(child.tag, str):
                continue
            name = self._get_element_name(child)
            if (name in ('else', 'elseif') and self._is_quantum_tag(child) and previous is not None):
                error = QuantumParseError(
                    f"<q:{name}> right after an inner </q:if>, inside another <q:if>, is ambiguous "
                    f"(IF-4): it would belong to the OUTER q:if (IF-1). If it is the inner q:if's, "
                    f"write it inside that q:if; if it is the outer's, put it before the inner q:if.")
                error.line = getattr(child, 'sourceline', None)
                raise error
            previous = child if name == 'if' and self._is_quantum_tag(child) else None

    # Tags that existed and were removed, with what to use instead.
    REMOVED_TAGS = {
        'persist': ('was removed in Quantum 0.16 (SET-2): it kept variables in the browser, '
                    'and a page\'s variables live on the server, for one request. Keep what must '
                    'last in session.x (per user) or in the database.'),
    }

    def _unknown_tag_message(self, name: str) -> str:
        if name in self.REMOVED_TAGS:
            return f"<q:{name}> {self.REMOVED_TAGS[name]}"
        import difflib
        # Only Quantum tags: the registry also holds the HTML tag names, which
        # made <q:try> suggest <q:tr>.
        conhecidas = {tag for tag in self._parser_registry.registered_tags
                      if type(self._parser_registry.get_parser(tag)).__name__ != 'HTMLParser'}
        conhecidas |= {'return', 'else', 'elseif'}
        parecidas = difflib.get_close_matches(name, sorted(conhecidas), n=3, cutoff=0.6)
        dica = (" Did you mean " + " or ".join(f"<q:{p}>" for p in parecidas) + "?") if parecidas else ""
        return f"<q:{name}> is not a Quantum tag (PARSE-1).{dica}"

    @staticmethod
    def _is_quantum_tag(element: ET.Element) -> bool:
        return element.tag.startswith('{https://quantum.lang/ns}') or element.tag.startswith('q:')

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

    def _parse_component(self, root: ET.Element, path: Path) -> ComponentNode:
        """Parse q:component"""
        name = root.get('name', path.stem)
        component_type = root.get('type', 'pure')

        component = ComponentNode(name, component_type)

        # Parse component-level attributes
        component.port = root.get('port')
        # A2: accepted and never read by anything — refused, like FN-2/DB-5.
        for attr in ('basePath', 'health', 'metrics', 'trace'):
            if root.get(attr) is not None:
                raise QuantumParseError(
                    f'<q:component name="{name}"> {attr}= is not supported: it was accepted '
                    f'and never did anything.')

        # Phase G: Authentication & Security attributes
        require_auth_attr = root.get('require_auth', 'false').lower()
        component.require_auth = require_auth_attr in ['true', '1', 'yes']
        component.require_role = root.get('require_role')
        # AUTH-4: where this component sends a visitor without a session.
        component.login_url = root.get('login_url')
        if component.login_url is not None and (not component.login_url.startswith('/')
                                                or component.login_url.startswith('//')):
            raise QuantumParseError(
                f'<q:component name="{component.name}"> login_url must be a path on this server, '
                f'like /login; got {component.login_url!r}')
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

        self._check_statements_in_markup(component)
        self._check_flash_in_actions(component)
        self._check_guards(component)

        return component

    def _check_guards(self, component: ComponentNode) -> None:
        """AUTH-6: a guard of a page with actions reads only what exists before the page runs.

        Guards also run before each q:action, and an action does not run the
        page's other statements. A guard reading a page variable would find it
        missing there, read the condition as false, and let the action run.
        """
        from quantum.core.guards import guard_conditions, mark_guards, page_guards
        from quantum.core.expressions import names_read

        mark_guards(component)
        if not any(isinstance(s, ActionNode) for s in component.statements):
            return
        guards = page_guards(component)
        if not guards:
            return

        defined = {p.name for p in getattr(component, 'params', []) or []}

        def define(nodes):
            for node in nodes:
                if isinstance(node, (ActionNode, FunctionNode, HTMLNode, TextNode, CommentNode)):
                    continue
                if isinstance(node, IfNode):
                    body = list(node.if_body) + list(node.else_body)
                    for block in node.elseif_blocks:
                        body += list(block.get('body', []))
                    define(body)
                    continue
                if isinstance(node, LoopNode):
                    define(node.body)
                    continue
                name = getattr(node, 'name', None)
                if isinstance(name, str) and name and '.' not in name:
                    defined.update({name, f'{name}_result'})

        define([s for s in component.statements if not any(s is g for g in guards)])

        for guard in guards:
            for condition in guard_conditions(guard):
                read_names = names_read(re.sub(r'\{([^{}]*)\}', r'\1', condition)) & defined
                if read_names:
                    name = sorted(read_names)[0]
                    raise _at(QuantumParseError(
                        f'<q:if condition="{condition}"> in <q:component name="{component.name}"> '
                        f'redirects (AUTH-6), so it also runs before the page\'s q:action — where the page '
                        f'has not run and {{{name}}} does not exist, and the guard would let the '
                        f'action through. Read the scope directly (e.g. session.x), or protect the '
                        f'page with require_auth / require_role. See {HOW_A_PAGE_RUNS}'), guard)

    def _check_flash_in_actions(self, component: ComponentNode) -> None:
        """ACT-3: q:flash works inside a q:action. Anywhere else it was skipped
        without a word — the page ran and no flash ever appeared."""
        def walk(nodes, in_action):
            for node in nodes or []:
                if isinstance(node, FlashNode) and not in_action:
                    raise _at(QuantumParseError(
                        f'<q:flash> in <q:component name="{component.name}"> is outside a q:action, '
                        f'where it does nothing: q:flash sets the flash for the next page, and only '
                        f'a q:action (before its q:redirect) does that (ACT-3). On a page, use '
                        f'<q:redirect url="..." flash="..."/>.'), node)
                if isinstance(node, ActionNode):
                    walk(node.body, True)
                    continue
                if isinstance(node, IfNode):
                    walk(node.if_body, in_action)
                    for block in node.elseif_blocks:
                        walk(block.get('body', []), in_action)
                    walk(node.else_body, in_action)
                    continue
                for attribute in ('body', 'children'):
                    walk(getattr(node, attribute, None) if isinstance(getattr(node, attribute, None), list)
                         else None, in_action)

        walk(component.statements, False)

    # Nodes the HTML renderer draws. Anything else inside markup is a statement,
    # and statements run in the execution pass, before the render pass sees
    # the markup around them.
    _RENDERED = (HTMLNode, TextNode, CommentNode, DocTypeNode, LoopNode, IfNode,
                 ComponentCallNode, SlotNode, ImportNode)

    def _check_statements_in_markup(self, component: ComponentNode) -> None:
        """PARSE-2: a statement where it would never run, or run with the wrong values.

        Execution walks the component's statements and skips markup; the
        renderer walks the markup and skips statements. So a q:set inside a
        <ul> never ran — `<li>{y}</li>` printed the literal `{y}` — and a q:set
        in a q:loop that also renders rows ran once per row in the execution
        pass, leaving every row to render with the LAST value. Both were
        silent.
        """
        def children_of(node):
            if isinstance(node, IfNode):
                body = list(node.if_body)
                for block in node.elseif_blocks:
                    body += list(block.get('body', []))
                return body + list(node.else_body)
            if isinstance(node, LoopNode):
                return list(node.body)
            if isinstance(node, (HTMLNode, ComponentCallNode)) or is_ui_node(node):
                return list(getattr(node, 'children', None) or [])
            return []

        def renders(nodes):
            for node in nodes:
                if isinstance(node, TextNode):
                    if node.content.strip():
                        return True
                elif isinstance(node, (HTMLNode, ComponentCallNode)) or is_ui_node(node):
                    return True
                elif isinstance(node, (IfNode, LoopNode)) and renders(children_of(node)):
                    return True
            return False

        def tag(node):
            name = type(node).__name__
            name = name[:-4] if name.endswith('Node') else name
            label = f"q:{name[:1].lower()}{name[1:]}"
            attribute = getattr(node, 'name', None)
            return f'<{label} name="{attribute}">' if isinstance(attribute, str) else f'<{label}>'

        def expressions_under(nodes):
            """The text the renderer evaluates under `nodes`: contents, attributes, conditions."""
            parts = []
            for node in nodes:
                if isinstance(node, TextNode):
                    parts.append(node.content)
                elif isinstance(node, HTMLNode):
                    parts.extend(str(v) for v in (node.attributes or {}).values())
                elif isinstance(node, ComponentCallNode):
                    parts.extend(str(v) for v in (node.props or {}).values())
                elif isinstance(node, IfNode):
                    parts.append('{%s}' % node.condition)
                    parts.extend('{%s}' % b.get('condition', '') for b in node.elseif_blocks)
                elif isinstance(node, LoopNode):
                    parts.append('{%s}' % (node.items or ''))
                parts.append(expressions_under(children_of(node)))
            return '\n'.join(parts)

        def used_in(name, text):
            pattern = re.compile(r'(?<![\w.])' + re.escape(name) + r'(?![\w])')
            return any(pattern.search(m) for m in re.findall(r'\{([^{}]*)\}', text))

        def walk(nodes, where):
            for node in nodes:
                if not isinstance(node, self._RENDERED) and not is_ui_node(node):
                    if where and where[0] == 'markup':
                        raise _at(QuantumParseError(
                            f'{tag(node)} inside {where[1]} in <q:component name="{component.name}"> '
                            f'never runs (PARSE-2): statements run before the page is rendered, and markup '
                            f'is only rendered. Move it above the markup (or into a q:action). '
                            f'See {HOW_A_PAGE_RUNS}'), node)
                    name = getattr(node, 'name', None)
                    # A running total read AFTER the loop is fine; a value the
                    # loop's own rows read is not.
                    if where and isinstance(name, str) and used_in(name, where[1]):
                        raise _at(QuantumParseError(
                            f'{tag(node)} inside a q:loop whose rows use {{{name}}} in '
                            f'<q:component name="{component.name}">: the loop runs for every item '
                            f'before any row is rendered, so every row would show the last value (PARSE-2). '
                            f'Compute it in the expression instead, e.g. {{item.price * item.qty}}. '
                            f'See {HOW_A_PAGE_RUNS}'), node)
                    continue
                if isinstance(node, HTMLNode):
                    walk(children_of(node), where if where and where[0] == 'markup' else ('markup', f'<{node.tag}>'))
                elif is_ui_node(node):
                    label = f'<ui:{type(node).__name__[2:-4].lower()}>'
                    walk(children_of(node), where if where and where[0] == 'markup' else ('markup', label))
                elif isinstance(node, ComponentCallNode):
                    walk(children_of(node), where if where and where[0] == 'markup'
                          else ('markup', f'the content of <{node.component_name}>'))
                elif isinstance(node, LoopNode):
                    body = children_of(node)
                    walk(body, where or (('loop', expressions_under(body)) if renders(body) else None))
                elif isinstance(node, IfNode):
                    walk(children_of(node), where)

        walk(component.statements, None)

    def _parse_control_flow_statements(self, parent: ET.Element, component: ComponentNode):
        """Parse control flow statements - delegates to modular parser registry"""
        for child in parent:
            child_type = self._get_element_name(child)

            # Collected by _parse_component above, not statements.
            if child_type in ('param', 'onEvent', 'script') and self._is_quantum_tag(child):
                continue

            # Special case: inline job definition (needs path parameter)
            if child_type == 'job':
                from pathlib import Path as PathLib
                job_node = self._parse_job(child, PathLib("<inline>"))
                component.add_statement(job_node)
                continue

            # A `<q:else>` / `<q:elseif>` SIBLING of a `<q:if>` in the
            # component body: attach it to the previous if. The sibling form
            # had no parser and vanished silently — the documentation taught
            # it and shipped files used it (see base.parse_statements for the
            # full reason).
            if child_type in ('else', 'elseif'):
                previous = component.statements[-1] if component.statements else None
                if isinstance(previous, IfNode):
                    self._attach_else_sibling(previous, child_type, child)
                    continue
                raise QuantumParseError(
                    f"<q:{child_type}> has no matching <q:if> before it. "
                    f"Put it inside the if, or right after it: "
                    f"<q:if ...>...</q:if> <q:{child_type}>...</q:{child_type}>"
                )

            # Delegate to modular parser registry via _parse_statement
            node = self._parse_statement(child)
            if node is not None:
                component.add_statement(node)
                # Check if this produces HTML
                if self._is_html_element(child) or (child_type and child_type[0].isupper()):
                    component.has_html = True

    def _attach_else_sibling(self, if_node: 'IfNode', kind: str, element: ET.Element):
        """Attaches a SIBLING else/elseif to the previous IfNode — the same
        result as the nested form IfParser already builds, text included (IF-3)."""
        body = self._parser_registry.get_parser('if')._body(element)
        if kind == 'elseif':
            if_node.add_elseif_block(element.get('condition', ''), body)
        else:
            for stmt in body:
                if_node.add_else_statement(stmt)

    def _parse_statement(self, element: ET.Element) -> Optional[QuantumNode]:
        """Parse one statement, and remember where it is in the file (DEV-2).

        The node gets `source_line`, which runtime errors report; a parse
        error from this element — or from inside it, if nothing deeper
        claimed it — gets `line`.
        """
        try:
            node = self._parse_statement_node(element)
        except (QuantumParseError, ParserError) as exc:
            if getattr(exc, 'line', None) is None:
                exc.line = getattr(element, 'sourceline', None)
            raise
        if node is not None and getattr(element, 'sourceline', None):
            try:
                node.source_line = element.sourceline
                node.source_file = self._source_path
            except AttributeError:
                pass                                  # a node with __slots__
        return node

    def _parse_statement_node(self, element: ET.Element) -> Optional[QuantumNode]:
        """Parse individual statement (return, set, dispatchEvent, etc)"""
        element_type = self._get_element_name(element)

        # === MODULAR PARSER REGISTRY (no fallback) ===
        # PHASE 1 DIAGNOSTIC: Legacy fallback disabled to test modular coverage
        if self._use_modular_parsers and self._parser_registry:
            # UI-1: a ui:* element inside a page is a UI node, drawn by
            # UIPageRenderer with the page's runtime doing the logic. First,
            # before the registry: ui:button would otherwise be the HTML <button>.
            if self._get_element_ui_namespace(element) == 'ui':
                try:
                    return UIParser(self, page_mode=True).parse_ui_element(element_type, element)
                except UIParseError as exc:
                    error = QuantumParseError(str(exc))
                    error.line = getattr(exc, 'line', None)          # the inner ui:* element's line
                    raise error from exc

            # PARSE-1: <q:html>, <q:div> — an HTML element name in the q:
            # namespace. The registry answered for it with the HTML parser, so
            # <q:html value="{post.content}"/> became an empty <html> element
            # instead of an unknown tag.
            # q:script is a Quantum tag on purpose: client JavaScript, kept as
            # an HTML node (see ui_desktop_adapter).
            if (self._is_quantum_tag(element) and element_type != 'script'
                    and element_type in self._parser_registry.html_parser.tag_names):
                raise QuantumParseError(
                    f"<q:{element_type}> is not a Quantum tag: HTML elements are written "
                    f"without the q: prefix (<{element_type}>)")
            if self._parser_registry.has_parser(element_type):
                return self._parser_registry.parse(element, element_type)

            # Component calls (uppercase naming convention)
            if element_type and element_type[0].isupper():
                from quantum.core.parsers import ComponentCallParser
                if ComponentCallParser.is_component_call(element_type):
                    return self._parser_registry.component_call_parser.parse(element)

            # HTML elements
            # A nested <q:return>. There is no parser registered for 'return'
            # — the component level collects it separately, with
            # _find_all_elements — so here it fell into the `return None` at
            # the end and was DROPPED silently. `<q:if ...><q:return
            # value="X"/></q:if>` did not return X: the component went on and
            # returned the next return, or nothing. The same held inside
            # q:loop and q:else.
            if element_type == 'return':
                return self._parse_return(element)

            if self._is_html_element(element):
                if self._parser_registry.html_parser.can_parse(element_type):
                    return self._parser_registry.html_parser.parse(element)

            # PARSE-1: a q: tag nobody parses is an error. It used to return
            # None here and vanish — <q:sett>, <q:retrun> and <q:iff> ran as if
            # they were not there, and so did tags the documentation described
            # but that never existed (q:try/q:catch, q:storedproc).
            if self._is_quantum_tag(element):
                raise QuantumParseError(self._unknown_tag_message(element_type))
            return None

        # If modular parsers are disabled, raise an error
        raise QuantumParseError("Modular parsers are disabled but legacy fallback has been removed")

    def _parse_application(self, root: ET.Element, path: Path) -> ApplicationNode:
        """Parse q:application"""
        app_id = root.get('id', path.stem)
        app_type = root.get('type', 'html')

        from quantum.core.tiers import REMOVED_APP_TYPES, removed_app_type_message
        if app_type in REMOVED_APP_TYPES:
            raise QuantumParseError(removed_app_type_message(app_type, 'type' in root.attrib))

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

        # q:set and q:function at the top of <q:application>, for any engine.
        # The per-engine parsers only look at children of their own namespace
        # (qt:, qg:, ui:), so these were silently dropped — including the
        # function an on-click pointed to.
        self._parse_application_quantum_children(root, app)

        # Game Engine 2D: parse game children when type="game"
        if app_type == 'game':
            self._parse_game_application_children(root, app)

        # Terminal Engine: parse terminal children when type="terminal"
        if app_type == 'terminal':
            self._parse_terminal_application_children(root, app)

        # UI Engine: parse ui children when type="ui"
        if app_type == 'ui':
            self._parse_ui_application_children(root, app)

        return app

    def _parse_application_quantum_children(self, root: ET.Element,
                                            app: ApplicationNode):
        """Coleta <q:function> e <q:set> escritos direto no q:application."""
        for child in root:
            local_name = self._get_element_name(child)
            if local_name not in ('function', 'set'):
                continue
            tag = child.tag
            # Only the q: namespace. A <ui:set> or <qg:set> belongs to its own
            # parser, and an element without a prefix is not a framework tag.
            if not (tag.startswith('q:')
                    or tag.startswith('{https://quantum.lang/ns}')):
                continue
            try:
                node = self._parse_statement(child)
            except QuantumParseError:
                raise
            except Exception:
                continue
            if node is None:
                continue
            if isinstance(node, FunctionNode):
                app.functions.append(node)
            elif isinstance(node, SetNode):
                app.state_vars.append(node)

    def _parse_game_application_children(self, root: ET.Element, app: ApplicationNode):
        """Parse children of a game application (qg: elements at top level)."""
        game_parser = GameParser(self)
        for child in root:
            local_name = self._get_element_name(child)
            ns = self._get_element_game_namespace(child)

            if ns == 'game':
                # Handle scene-include specially (resolved at parse time)
                if local_name == 'scene-include':
                    self._parse_scene_include(child, app, game_parser)
                    continue

                node = game_parser.parse_game_element(local_name, child)
                if isinstance(node, SceneNode):
                    app.scenes.append(node)
                elif isinstance(node, BehaviorNode):
                    app.behaviors.append(node)
                elif isinstance(node, PrefabNode):
                    app.prefabs.append(node)
                elif isinstance(node, EnemyNode):
                    app.enemies.append(node)
                elif isinstance(node, PersistentNode):
                    app.persistent.append(node)

    def _parse_scene_include(self, element: ET.Element, app: ApplicationNode, game_parser):
        """Parse <qg:scene-include src="..."> - Include a scene from external .q file.

        The external file should contain a <qg:scene> element (with or without
        a <q:application> wrapper). The scene is added to the application's scene list.
        """
        src = element.get('src', '')
        if not src:
            raise QuantumParseError("scene-include requires a 'src' attribute")

        # Resolve relative path from the source file being parsed
        base_path = getattr(self, '_source_path', None)
        if base_path:
            include_path = Path(base_path).parent / src
        else:
            include_path = Path(src)

        if not include_path.exists():
            raise QuantumParseError(f"scene-include: file not found: {include_path}")

        content = include_path.read_text(encoding='utf-8')

        # The same HTML tolerated in any other .q. This path reads a .q file
        # and went straight to the ET.fromstring below, without passing
        # through here: a `<br>`, a raw `&`, a boolean attribute or a `<`
        # inside a value gave "scene-include: parse error" on a file the
        # normal parser accepts without complaint.
        content = normalise_html(content)

        # Strip XML processing instruction if present
        import re
        content = re.sub(r'<\?xml[^?]*\?>\s*', '', content)
        # Strip XML comments at the top level
        content = re.sub(r'<!--[\s\S]*?-->\s*', '', content, count=1)
        content = content.strip()

        # Wrap in a root element with namespace declarations
        # This handles bare <qg:scene> files that don't have <q:application>
        if 'xmlns:qg' not in content:
            ns_attrs = 'xmlns:qg="https://quantum.lang/game"'
            if 'q:' in content:
                ns_attrs += ' xmlns:q="https://quantum.lang/ns"'
            content = f'<_root {ns_attrs}>{content}</_root>'

        try:
            include_root = ET.fromstring(content)
        except ET.ParseError as e:
            raise QuantumParseError(f"scene-include: parse error in {src}: {e}")

        # Find scene element(s) in the included file
        self._extract_scenes_from_include(include_root, app, game_parser)

    def _extract_scenes_from_include(self, root: ET.Element, app: ApplicationNode, game_parser):
        """Extract SceneNode(s) from an included file's parsed XML."""
        tag = root.tag
        # Strip namespace
        if '}' in tag:
            local = tag.split('}')[-1]
        elif ':' in tag:
            local = tag.split(':')[-1]
        else:
            local = tag

        if local == 'scene':
            # Root element is the scene itself
            node = game_parser.parse_game_element('scene', root)
            if isinstance(node, SceneNode):
                app.scenes.append(node)
        else:
            # Root is a wrapper — look for scene children
            for child in root:
                child_ns = self._get_element_game_namespace(child)
                child_local = self._get_element_name(child)
                if child_ns == 'game' and child_local == 'scene':
                    node = game_parser.parse_game_element('scene', child)
                    if isinstance(node, SceneNode):
                        app.scenes.append(node)

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

    def _parse_param(self, element: ET.Element) -> QuantumParam:
        """Parse q:param"""
        param = QuantumParam(
            name=element.get('name', ''),
            type=element.get('type', 'string'),
            required=element.get('required', 'false').lower() == 'true',
            default=element.get('default'),
            description=element.get('description')
        )
        if element.get('validation') is not None:
            # A2: accepted and never read. The rules are validate=, type=,
            # pattern=, min/max, minlength/maxlength and enum=.
            from quantum.core.parser import QuantumParseError
            raise QuantumParseError(
                f'<q:param name="{element.get("name", "")}"> validation= is not supported: it was '
                f'accepted and never did anything. Use type=, pattern=, min/max, '
                f'minlength/maxlength or enum=.')

        # REST-specific
        param.source = element.get('source', 'auto')

        # value= is how a CALL SITE passes an argument — <q:job> dispatch,
        # <q:invoke>, <q:query>. This function read only default=, so every
        # <q:param name="to" value="a@b.c" /> inside a q:job arrived with no
        # value at all and each dispatched job got nulls. Declaration sites
        # (q:function, q:action) use default= and are unaffected.
        param.value = element.get('value')

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
        from quantum.core.parsers.functions.param_parser import check_upload_rules
        check_upload_rules(element, param)
        from quantum.runtime.param_validation import check_param_type
        check_param_type(f'<q:param name="{param.name}">', element.get('type'), element=element)

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
            elif child_type == 'return':
                # ReturnParser is intentionally not in the tag registry, so
                # _parse_statement() returns None for <q:return> — which
                # silently dropped the return from every function body,
                # making every q:function return nothing.
                from quantum.core.parsers.functions.return_parser import ReturnParser
                func_node.add_statement(ReturnParser(self).parse(child))
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

