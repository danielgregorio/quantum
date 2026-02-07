"""
Quantum Function Registry - Manages function definitions across scopes
"""

from typing import Dict, Optional, List
import sys
from pathlib import Path

# Fix imports
sys.path.append(str(Path(__file__).parent.parent))

from core.ast_nodes import ComponentNode
from core.features.functions.src.ast_node import FunctionNode


class FunctionRegistry:
    """Global registry for all functions across scopes"""

    def __init__(self):
        # Escopo por container
        self.components: Dict[str, Dict[str, FunctionNode]] = {}  # component_name -> {func_name: func}

        # Index global (para funções scope="global")
        self.global_functions: Dict[str, FunctionNode] = {}

        # Imported modules (para q:import)
        self.imported_modules: List[str] = []

    def register_component(self, component: ComponentNode):
        """Register all functions from a component"""
        if component.name not in self.components:
            self.components[component.name] = {}

        for func in component.functions:
            self.register_function(func, component)

    def register_function(self, func: FunctionNode, container: ComponentNode):
        """Register function in appropriate scope"""

        if container.name not in self.components:
            self.components[container.name] = {}

        self.components[container.name][func.name] = func

        # Functions with scope="global" go to global index
        if func.scope == "global":
            qualified_name = f"{container.name}.{func.name}"
            self.global_functions[qualified_name] = func

    def resolve_function(self, name: str, current_component: Optional[ComponentNode] = None) -> Optional[FunctionNode]:
        """
        Resolve function name to FunctionNode - respects scope rules

        Resolution order:
        1. Local component functions
        2. Global functions (qualified name: Component.function)
        3. Imported module functions
        """

        # 1. Check local component first
        if current_component and current_component.name in self.components:
            component_funcs = self.components[current_component.name]
            if name in component_funcs:
                return component_funcs[name]

        # 2. Check global functions (qualified name: Component.function)
        if name in self.global_functions:
            return self.global_functions[name]

        # 3. Check if it's a qualified call (Component.function)
        if '.' in name:
            component_name, func_name = name.split('.', 1)
            if component_name in self.components:
                return self.components[component_name].get(func_name)

        return None

    def get_rest_endpoints(self) -> List[FunctionNode]:
        """Get all functions that are REST endpoints"""
        endpoints = []

        # Functions in components with endpoint attribute
        for component_funcs in self.components.values():
            for func in component_funcs.values():
                if func.is_rest_enabled() and not func.is_private():
                    endpoints.append(func)

        return endpoints

    def get_event_handlers(self, component: ComponentNode) -> List:
        """Get all event handlers for a component"""
        return component.event_handlers

    def import_module(self, module_name: str):
        """Mark module as imported (for q:import)"""
        if module_name not in self.imported_modules:
            self.imported_modules.append(module_name)

    def is_module_imported(self, module_name: str) -> bool:
        """Check if module is imported"""
        return module_name in self.imported_modules

    def list_functions(self, component_name: Optional[str] = None) -> List[FunctionNode]:
        """List all functions (optionally filtered by component)"""
        if component_name:
            return list(self.components.get(component_name, {}).values())

        # List all functions
        all_functions = []
        for component_funcs in self.components.values():
            all_functions.extend(component_funcs.values())
        return all_functions

    def clear(self):
        """Clear all registered functions"""
        self.components.clear()
        self.global_functions.clear()
        self.imported_modules.clear()
