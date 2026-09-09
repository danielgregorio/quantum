"""
Quantum Plugin Hook System

Provides lifecycle hooks that plugins can use to intercept and modify
the parsing, rendering, and execution phases.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class HookType(Enum):
    """Available hook types in the Quantum lifecycle"""

    # Parsing phase
    BEFORE_PARSE = "before_parse"     # Before XML is parsed
    AFTER_PARSE = "after_parse"       # After AST is created

    # Rendering phase
    BEFORE_RENDER = "before_render"   # Before HTML generation
    AFTER_RENDER = "after_render"     # After HTML generation

    # Execution phase
    BEFORE_EXECUTE = "before_execute"  # Before component execution
    AFTER_EXECUTE = "after_execute"    # After component execution

    # Error handling
    ON_ERROR = "on_error"             # When an error occurs

    # Lifecycle
    ON_INIT = "on_init"               # Plugin initialization
    ON_SHUTDOWN = "on_shutdown"        # Application shutdown


@dataclass
class HookRegistration:
    """A registered hook callback"""
    hook_type: HookType
    callback: Callable
    plugin_name: str
    priority: int = 100  # Lower = earlier execution

    def __lt__(self, other):
        """Allow sorting by priority"""
        return self.priority < other.priority


@dataclass
class HookContext:
    """Context passed to hook callbacks"""
    hook_type: HookType
    plugin_name: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    # Parsing context
    source: Optional[str] = None       # Original source code
    ast: Optional[Any] = None          # Parsed AST

    # Rendering context
    component: Optional[Any] = None    # Component being rendered
    html: Optional[str] = None         # Rendered HTML

    # Execution context
    params: Optional[Dict] = None      # Execution parameters
    result: Optional[Any] = None       # Execution result

    # Error context
    error: Optional[Exception] = None  # Error that occurred

    # Control flow
    skip: bool = False                 # Skip remaining processing
    modified: bool = False             # Data was modified

    def set_result(self, value: Any):
        """Set result and mark as modified"""
        self.result = value
        self.modified = True

    def set_html(self, value: str):
        """Set HTML and mark as modified"""
        self.html = value
        self.modified = True

    def set_ast(self, value: Any):
        """Set AST and mark as modified"""
        self.ast = value
        self.modified = True

    def skip_remaining(self):
        """Skip remaining hooks and processing"""
        self.skip = True


class HookManager:
    """
    Manages plugin lifecycle hooks.

    Example usage:
        manager = HookManager()

        # Register a hook
        def my_before_render(ctx: HookContext):
            print(f"Rendering: {ctx.component}")
            ctx.data['custom'] = 'value'

        manager.register(HookType.BEFORE_RENDER, my_before_render, "my-plugin")

        # Execute hooks
        ctx = HookContext(hook_type=HookType.BEFORE_RENDER)
        ctx.component = my_component
        manager.execute(HookType.BEFORE_RENDER, ctx)
    """

    def __init__(self):
        self._hooks: Dict[HookType, List[HookRegistration]] = {
            hook_type: [] for hook_type in HookType
        }
        self._enabled = True

    def register(
        self,
        hook_type: HookType,
        callback: Callable[[HookContext], None],
        plugin_name: str,
        priority: int = 100
    ) -> None:
        """
        Register a hook callback.

        Args:
            hook_type: Type of hook to register
            callback: Function to call when hook is triggered
            plugin_name: Name of the plugin registering the hook
            priority: Execution priority (lower = earlier)
        """
        registration = HookRegistration(
            hook_type=hook_type,
            callback=callback,
            plugin_name=plugin_name,
            priority=priority
        )
        self._hooks[hook_type].append(registration)
        # Keep sorted by priority
        self._hooks[hook_type].sort()

        logger.debug(f"Registered hook: {hook_type.value} from {plugin_name} (priority={priority})")

    def unregister(self, hook_type: HookType, plugin_name: str) -> int:
        """
        Unregister all hooks of a type for a plugin.

        Returns:
            Number of hooks removed
        """
        original_count = len(self._hooks[hook_type])
        self._hooks[hook_type] = [
            h for h in self._hooks[hook_type]
            if h.plugin_name != plugin_name
        ]
        removed = original_count - len(self._hooks[hook_type])
        if removed:
            logger.debug(f"Unregistered {removed} hooks for {plugin_name}")
        return removed

    def unregister_all(self, plugin_name: str) -> int:
        """
        Unregister all hooks for a plugin.

        Returns:
            Total number of hooks removed
        """
        total_removed = 0
        for hook_type in HookType:
            total_removed += self.unregister(hook_type, plugin_name)
        return total_removed

    def execute(self, hook_type: HookType, context: HookContext) -> HookContext:
        """
        Execute all registered hooks of a type.

        Args:
            hook_type: Type of hook to execute
            context: Context to pass to callbacks

        Returns:
            Modified context after all hooks execute
        """
        if not self._enabled:
            return context

        hooks = self._hooks.get(hook_type, [])
        if not hooks:
            return context

        logger.debug(f"Executing {len(hooks)} hooks for {hook_type.value}")

        for registration in hooks:
            if context.skip:
                logger.debug(f"Skipping remaining hooks after {context.plugin_name}")
                break

            try:
                context.plugin_name = registration.plugin_name
                registration.callback(context)
            except Exception as e:
                logger.error(f"Hook error in {registration.plugin_name}: {e}")
                # Don't propagate hook errors unless it's an ON_ERROR hook
                if hook_type != HookType.ON_ERROR:
                    # Execute error hooks
                    error_ctx = HookContext(
                        hook_type=HookType.ON_ERROR,
                        error=e,
                        data={'original_hook': hook_type.value}
                    )
                    self.execute(HookType.ON_ERROR, error_ctx)

        return context

    def execute_before_parse(self, source: str) -> str:
        """Execute before_parse hooks and return potentially modified source"""
        ctx = HookContext(hook_type=HookType.BEFORE_PARSE, source=source)
        ctx = self.execute(HookType.BEFORE_PARSE, ctx)
        return ctx.source if ctx.modified else source

    def execute_after_parse(self, ast: Any) -> Any:
        """Execute after_parse hooks and return potentially modified AST"""
        ctx = HookContext(hook_type=HookType.AFTER_PARSE, ast=ast)
        ctx = self.execute(HookType.AFTER_PARSE, ctx)
        return ctx.ast if ctx.modified else ast

    def execute_before_render(self, component: Any, params: Dict = None) -> HookContext:
        """Execute before_render hooks"""
        ctx = HookContext(
            hook_type=HookType.BEFORE_RENDER,
            component=component,
            params=params or {}
        )
        return self.execute(HookType.BEFORE_RENDER, ctx)

    def execute_after_render(self, component: Any, html: str) -> str:
        """Execute after_render hooks and return potentially modified HTML"""
        ctx = HookContext(
            hook_type=HookType.AFTER_RENDER,
            component=component,
            html=html
        )
        ctx = self.execute(HookType.AFTER_RENDER, ctx)
        return ctx.html if ctx.modified else html

    def execute_before_execute(self, component: Any, params: Dict = None) -> HookContext:
        """Execute before_execute hooks"""
        ctx = HookContext(
            hook_type=HookType.BEFORE_EXECUTE,
            component=component,
            params=params or {}
        )
        return self.execute(HookType.BEFORE_EXECUTE, ctx)

    def execute_after_execute(self, component: Any, result: Any) -> Any:
        """Execute after_execute hooks and return potentially modified result"""
        ctx = HookContext(
            hook_type=HookType.AFTER_EXECUTE,
            component=component,
            result=result
        )
        ctx = self.execute(HookType.AFTER_EXECUTE, ctx)
        return ctx.result if ctx.modified else result

    def get_hooks(self, hook_type: HookType) -> List[HookRegistration]:
        """Get all registered hooks of a type"""
        return self._hooks.get(hook_type, [])

    def get_all_hooks(self) -> Dict[HookType, List[HookRegistration]]:
        """Get all registered hooks"""
        return self._hooks

    def enable(self):
        """Enable hook execution"""
        self._enabled = True

    def disable(self):
        """Disable hook execution"""
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """Check if hooks are enabled"""
        return self._enabled

    def clear(self):
        """Clear all registered hooks"""
        for hook_type in HookType:
            self._hooks[hook_type] = []

    def count(self, hook_type: HookType = None) -> int:
        """
        Count registered hooks.

        Args:
            hook_type: Specific type to count, or None for total

        Returns:
            Number of registered hooks
        """
        if hook_type:
            return len(self._hooks.get(hook_type, []))
        return sum(len(hooks) for hooks in self._hooks.values())


# Global hook manager instance
_global_hook_manager: Optional[HookManager] = None


def get_hook_manager() -> HookManager:
    """Get the global hook manager instance"""
    global _global_hook_manager
    if _global_hook_manager is None:
        _global_hook_manager = HookManager()
    return _global_hook_manager


def set_hook_manager(manager: HookManager) -> None:
    """Set the global hook manager instance"""
    global _global_hook_manager
    _global_hook_manager = manager
