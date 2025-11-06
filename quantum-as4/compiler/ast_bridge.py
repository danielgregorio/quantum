"""
AST Bridge - Convert legacy parser output to Universal AST

Converts:
- mxml_parser.Application → UniversalAST
- as4_parser output → CodeAST
"""

from .mxml_parser import Application as LegacyApplication, Component as LegacyComponent
from .as4_parser import AS4Parser
from .universal_ast import (
    UniversalAST, UniversalComponent, ComponentProp,
    CodeAST, Variable, Function, Parameter, AppInfo,
    Binding, EventHandler
)
from typing import Dict, List
import re


class ASTBridge:
    """Bridge between legacy parsers and Universal AST"""

    def __init__(self):
        self.as4_parser = AS4Parser()

    def legacy_to_universal(self, legacy_app: LegacyApplication) -> UniversalAST:
        """
        Convert legacy Application to UniversalAST

        Args:
            legacy_app: Application from mxml_parser

        Returns:
            UniversalAST
        """

        # Parse ActionScript code
        code_ast = self._parse_code(legacy_app.script)

        # Convert component tree
        component_tree = self._convert_component(legacy_app.ui)

        # Parse styles
        styles = self._parse_styles(legacy_app.style)

        # Extract app title from root component
        app_title = legacy_app.ui.props.get('title', 'Quantum MXML Application')

        # Extract bindings
        bindings = self._extract_bindings(component_tree, code_ast)

        # Extract events
        events = self._extract_events(component_tree)

        return UniversalAST(
            app_info=AppInfo(
                title=app_title,
                version="1.0.0",
                description="",
                author=""
            ),
            component_tree=component_tree,
            code_ast=code_ast,
            styles=styles,
            assets={},
            bindings=bindings,
            events=events
        )

    def _convert_component(self, legacy: LegacyComponent) -> UniversalComponent:
        """Convert legacy Component to UniversalComponent"""

        # Convert props to ComponentProp objects
        props = {}
        for name, value in legacy.props.items():
            props[name] = ComponentProp(
                name=name,
                value=value,
                is_binding=self._is_binding(value)
            )

        # Convert children recursively
        children = [self._convert_component(child) for child in legacy.children]

        return UniversalComponent(
            type=legacy.type,
            props=props,
            events=legacy.events,
            children=children,
            styles={},
            platform_hints={}
        )

    def _parse_code(self, script: str) -> CodeAST:
        """Parse ActionScript code to CodeAST"""

        if not script or not script.strip():
            return CodeAST(variables=[], functions=[])

        # Parse variables
        variables = self.as4_parser._parse_variables(script)

        # Parse functions
        functions = self.as4_parser._parse_functions(script)

        # Convert to Universal AST format
        universal_vars = []
        for var in variables:
            universal_vars.append(Variable(
                name=var.name,
                type=var.type or 'Object',
                initial_value=var.value,
                is_bindable=var.is_bindable,
                is_public=True  # Assume public for now
            ))

        universal_funcs = []
        for func in functions:
            # Parse parameters
            params = []
            if func.params:
                for param_str in func.params.split(','):
                    param_str = param_str.strip()
                    if ':' in param_str:
                        param_name, param_type = param_str.split(':')
                        params.append(Parameter(
                            name=param_name.strip(),
                            type=param_type.strip(),
                            default_value=None
                        ))
                    else:
                        params.append(Parameter(
                            name=param_str,
                            type='Object',
                            default_value=None
                        ))

            universal_funcs.append(Function(
                name=func.name,
                parameters=params,
                return_type=func.return_type or 'void',
                body=func.body,
                is_async=func.is_async,
                is_public=True
            ))

        return CodeAST(
            variables=universal_vars,
            functions=universal_funcs
        )

    def _parse_styles(self, style_str: str) -> Dict:
        """Parse CSS string to style dictionary"""

        styles = {}

        if not style_str or not style_str.strip():
            return styles

        # Simple CSS parser - matches .class { prop: value; }
        pattern = r'([.#]?[\w-]+)\s*\{([^}]+)\}'

        for match in re.finditer(pattern, style_str):
            selector = match.group(1).strip()
            rules_str = match.group(2).strip()

            # Parse rules
            rules = {}
            for rule in rules_str.split(';'):
                rule = rule.strip()
                if ':' in rule:
                    prop, value = rule.split(':', 1)
                    rules[prop.strip()] = value.strip()

            styles[selector] = rules

        return styles

    def _infer_prop_type(self, value: str) -> str:
        """Infer property type from value"""

        if not value:
            return 'String'

        # Binding expression
        if self._is_binding(value):
            return 'Binding'

        # Number
        if value.replace('.', '').replace('-', '').isdigit():
            return 'Number'

        # Boolean
        if value in ('true', 'false'):
            return 'Boolean'

        # Default to string
        return 'String'

    def _is_binding(self, value: str) -> bool:
        """Check if value is a binding expression {variable}"""
        return bool(re.match(r'^\{.+\}$', value))

    def _extract_bindings(self, component: UniversalComponent, code_ast: CodeAST) -> List[Binding]:
        """Extract all bindings from component tree"""

        bindings = []

        # Check component props for bindings
        for prop_name, prop in component.props.items():
            if prop.is_binding:
                # Extract variable name from {variable}
                var_match = re.match(r'^\{(.+)\}$', prop.value)
                if var_match:
                    var_name = var_match.group(1).strip()
                    bindings.append(Binding(
                        expression=var_name,
                        target_component=component.type,
                        target_property=prop_name,
                        two_way=False
                    ))

        # Recursively extract from children
        for child in component.children:
            bindings.extend(self._extract_bindings(child, code_ast))

        return bindings

    def _extract_events(self, component: UniversalComponent) -> List[EventHandler]:
        """Extract all event handlers from component tree"""

        events = []

        # Check component events
        for event_name, handler_code in component.events.items():
            events.append(EventHandler(
                event_name=event_name,
                handler_function=handler_code,
                component_id=component.type
            ))

        # Recursively extract from children
        for child in component.children:
            events.extend(self._extract_events(child))

        return events
