"""
Universal AST - Platform-Agnostic Intermediate Representation

This AST can be compiled to any target platform (Web, Mobile, Desktop, CLI)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class Platform(Enum):
    """Target platforms"""
    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    CLI = "cli"


@dataclass
class AppInfo:
    """Application metadata"""
    title: str = "Quantum MXML Application"
    name: str = ""
    version: str = "1.0.0"
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    homepage: Optional[str] = None


@dataclass
class Binding:
    """Data binding expression"""
    expression: str              # e.g., "message", "user.name", "items[0]"
    target_component: str        # Component ID
    target_property: str         # Property name (e.g., "text", "value")
    two_way: bool = False        # Two-way binding


@dataclass
class EventHandler:
    """Event handler definition"""
    event_name: str              # e.g., "click", "change", "input"
    handler_function: str        # Function name to call
    component_id: str            # Component that triggers event


@dataclass
class ComponentProp:
    """Component property"""
    name: str
    value: Any
    is_binding: bool = False     # Is this a data binding?
    binding_expr: Optional[str] = None


@dataclass
class UniversalComponent:
    """
    Platform-agnostic component representation

    Describes WHAT a component does, not HOW it's rendered
    """
    type: str                            # "VBox", "Button", "Label", etc.
    id: Optional[str] = None             # Unique ID (if specified)
    props: Dict[str, ComponentProp] = field(default_factory=dict)
    events: Dict[str, str] = field(default_factory=dict)  # event_name → handler_function
    children: List['UniversalComponent'] = field(default_factory=list)
    styles: Dict[str, Any] = field(default_factory=dict)

    # Platform-specific metadata (hints for compilers)
    platform_hints: Dict[Platform, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class Variable:
    """Variable declaration"""
    name: str
    type: Optional[str]
    initial_value: Optional[str]
    is_bindable: bool = False
    is_public: bool = False
    decorators: List[str] = field(default_factory=list)


@dataclass
class Parameter:
    """Function parameter"""
    name: str
    type: str
    default_value: Optional[str] = None


@dataclass
class Function:
    """Function declaration"""
    name: str
    parameters: List[Parameter] = field(default_factory=list)
    return_type: Optional[str] = None
    body: str = ""                    # Function body code
    is_async: bool = False
    is_public: bool = False
    decorators: List[str] = field(default_factory=list)


@dataclass
class CodeAST:
    """Business logic AST"""
    imports: List[str] = field(default_factory=list)
    variables: List[Variable] = field(default_factory=list)
    functions: List[Function] = field(default_factory=list)
    classes: List[Any] = field(default_factory=list)  # TODO: Class support


@dataclass
class StyleRule:
    """CSS-like style rule"""
    selector: str                     # ".button", "#header", etc.
    properties: Dict[str, str]        # property → value


@dataclass
class StyleSheet:
    """Stylesheet"""
    rules: List[StyleRule] = field(default_factory=list)
    raw_css: Optional[str] = None     # Raw CSS string (if any)


@dataclass
class Asset:
    """Asset metadata"""
    type: str                         # "image", "font", "data", etc.
    source_path: str                  # Path in source
    target_path: Optional[str] = None # Path in output (determined by compiler)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssetManifest:
    """All assets in the application"""
    images: List[Asset] = field(default_factory=list)
    fonts: List[Asset] = field(default_factory=list)
    data: List[Asset] = field(default_factory=list)
    other: List[Asset] = field(default_factory=list)


@dataclass
class UniversalAST:
    """
    Complete platform-agnostic representation of the application

    This can be compiled to any target platform
    """
    # Application metadata
    app_info: AppInfo

    # UI component tree (platform-neutral)
    component_tree: UniversalComponent

    # Business logic
    code_ast: CodeAST

    # Styles (will be adapted per platform)
    styles: StyleSheet

    # Assets (images, fonts, etc.)
    assets: AssetManifest

    # Data bindings
    bindings: List[Binding] = field(default_factory=list)

    # Events and handlers
    events: List[EventHandler] = field(default_factory=list)

    def get_bindable_variables(self) -> List[Variable]:
        """Get all variables marked as bindable"""
        return [v for v in self.code_ast.variables if v.is_bindable]

    def get_component_by_id(self, component_id: str) -> Optional[UniversalComponent]:
        """Find component by ID"""
        def search(comp: UniversalComponent) -> Optional[UniversalComponent]:
            if comp.id == component_id:
                return comp
            for child in comp.children:
                result = search(child)
                if result:
                    return result
            return None

        return search(self.component_tree)

    def get_all_components(self) -> List[UniversalComponent]:
        """Get flat list of all components"""
        result = []

        def traverse(comp: UniversalComponent):
            result.append(comp)
            for child in comp.children:
                traverse(child)

        traverse(self.component_tree)
        return result

    def get_events_for_component(self, component_id: str) -> List[EventHandler]:
        """Get all events for a specific component"""
        return [e for e in self.events if e.component_id == component_id]


# Helper functions

def create_universal_ast_from_mxml(mxml_ast, as4_ast, app_info: AppInfo) -> UniversalAST:
    """
    Create UniversalAST from parsed MXML and AS4 ASTs

    This is the bridge between parsing and compilation
    """
    # Convert MXML component tree to UniversalComponent tree
    component_tree = _convert_component(mxml_ast.ui)

    # Convert AS4 AST to CodeAST
    code_ast = _convert_code_ast(as4_ast)

    # Extract bindings
    bindings = _extract_bindings(component_tree, code_ast)

    # Extract events
    events = _extract_events(component_tree)

    # Create stylesheet
    styles = StyleSheet(raw_css=mxml_ast.style)

    # TODO: Extract assets from configuration

    return UniversalAST(
        app_info=app_info,
        component_tree=component_tree,
        code_ast=code_ast,
        styles=styles,
        assets=AssetManifest(),
        bindings=bindings,
        events=events
    )


def _convert_component(mxml_component) -> UniversalComponent:
    """Convert MXML Component to UniversalComponent"""
    # Convert props
    props = {}
    for key, value in mxml_component.props.items():
        # Check if it's a binding (contains {})
        is_binding = '{' in value and '}' in value
        binding_expr = None

        if is_binding:
            # Extract binding expression: "{message}" → "message"
            import re
            match = re.search(r'\{([^}]+)\}', value)
            if match:
                binding_expr = match.group(1)

        props[key] = ComponentProp(
            name=key,
            value=value,
            is_binding=is_binding,
            binding_expr=binding_expr
        )

    # Convert children recursively
    children = [_convert_component(child) for child in mxml_component.children]

    return UniversalComponent(
        type=mxml_component.type,
        id=mxml_component.props.get('id'),
        props=props,
        events=mxml_component.events,
        children=children
    )


def _convert_code_ast(as4_ast) -> CodeAST:
    """Convert AS4 AST to CodeAST"""
    variables = [
        Variable(
            name=var.name,
            type=var.type,
            initial_value=var.value,
            is_bindable=var.is_bindable,
            decorators=['Bindable'] if var.is_bindable else []
        )
        for var in as4_ast.variables
    ]

    functions = [
        Function(
            name=func.name,
            parameters=func.params,
            return_type=func.return_type,
            body=func.body,
            is_async=func.is_async
        )
        for func in as4_ast.functions
    ]

    return CodeAST(
        imports=as4_ast.imports,
        variables=variables,
        functions=functions
    )


def _extract_bindings(component_tree: UniversalComponent, code_ast: CodeAST) -> List[Binding]:
    """Extract all data bindings from component tree"""
    bindings = []
    bindable_vars = {v.name for v in code_ast.variables if v.is_bindable}

    def traverse(comp: UniversalComponent):
        for prop_name, prop in comp.props.items():
            if prop.is_binding and prop.binding_expr:
                # Check if binding refers to a bindable variable
                if prop.binding_expr in bindable_vars:
                    bindings.append(Binding(
                        expression=prop.binding_expr,
                        target_component=comp.id or comp.type,
                        target_property=prop_name,
                        two_way=False  # TODO: Detect two-way bindings
                    ))

        for child in comp.children:
            traverse(child)

    traverse(component_tree)
    return bindings


def _extract_events(component_tree: UniversalComponent) -> List[EventHandler]:
    """Extract all event handlers from component tree"""
    events = []
    counter = 0

    def traverse(comp: UniversalComponent):
        nonlocal counter
        comp_id = comp.id or f"{comp.type}_{counter}"
        counter += 1

        for event_name, handler_func in comp.events.items():
            # Extract function name from "handleClick()"
            func_name = handler_func.replace('()', '').replace('(', '').strip()

            events.append(EventHandler(
                event_name=event_name,
                handler_function=func_name,
                component_id=comp_id
            ))

        for child in comp.children:
            traverse(child)

    traverse(component_tree)
    return events
