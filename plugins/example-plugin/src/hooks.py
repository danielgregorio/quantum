"""
Lifecycle Hooks for Example Plugin

Demonstrates how to use lifecycle hooks to intercept
and modify parsing, rendering, and execution phases.
"""

from typing import Any
import logging

# Import hook types
try:
    from plugins.hooks import HookContext
except ImportError:
    # Fallback for standalone testing
    class HookContext:
        pass

logger = logging.getLogger(__name__)


def on_plugin_init(ctx: HookContext) -> None:
    """
    Called when the plugin is initialized.

    This hook runs once when the plugin is first loaded.
    Use it for one-time setup tasks.

    Args:
        ctx: Hook context with plugin info
    """
    plugin_info = ctx.data.get('plugin')
    if plugin_info:
        logger.info(f"Example plugin initialized: {plugin_info.name}@{plugin_info.version}")
    else:
        logger.info("Example plugin initialized")


def on_before_parse(ctx: HookContext) -> None:
    """
    Called before XML source is parsed.

    This hook can modify the source before parsing.
    Useful for preprocessing, adding namespaces, etc.

    Args:
        ctx: Hook context with source code
    """
    source = ctx.source
    if not source:
        return

    # Example: Auto-inject ex: namespace if not present
    if 'xmlns:ex' not in source and 'ex:' in source:
        # Find the first q:component or q:application tag
        import re
        pattern = r'(<(?:q:)?(?:component|application)[^>]*)(>)'

        def add_ns(match):
            return match.group(1) + ' xmlns:ex="https://quantum.lang/example"' + match.group(2)

        modified = re.sub(pattern, add_ns, source, count=1)
        if modified != source:
            ctx.source = modified
            ctx.modified = True
            logger.debug("Injected ex: namespace declaration")


def on_after_render(ctx: HookContext) -> None:
    """
    Called after HTML is rendered.

    This hook can modify the final HTML output.
    Useful for adding analytics, modifying structure, etc.

    Args:
        ctx: Hook context with component and HTML
    """
    html = ctx.html
    if not html:
        return

    # Example: Add plugin attribution comment
    if '<html' in html.lower() or '<body' in html.lower():
        # Add comment before closing body or at end
        comment = '\n<!-- Rendered with Example Plugin -->\n'

        if '</body>' in html.lower():
            html = html.replace('</body>', f'{comment}</body>')
            ctx.html = html
            ctx.modified = True
        elif '</html>' in html.lower():
            html = html.replace('</html>', f'{comment}</html>')
            ctx.html = html
            ctx.modified = True

    # Example: Count custom tags
    ex_tags = html.count('ex-hello') + html.count('ex-counter') + html.count('ex-timestamp')
    if ex_tags > 0:
        logger.debug(f"Rendered {ex_tags} ex:* components")


def on_before_render(ctx: HookContext) -> None:
    """
    Called before a component is rendered.

    This hook can modify rendering parameters or skip rendering.

    Args:
        ctx: Hook context with component and params
    """
    component = ctx.component
    params = ctx.params or {}

    # Example: Add default params for ex:* components
    if hasattr(component, 'statements'):
        for stmt in component.statements:
            # Check if component uses example plugin tags
            stmt_type = type(stmt).__name__
            if stmt_type in ['HelloNode', 'CounterNode', 'TimestampNode']:
                if 'ex_plugin_version' not in params:
                    params['ex_plugin_version'] = '1.0.0'
                    ctx.params = params
                break


def on_after_execute(ctx: HookContext) -> None:
    """
    Called after component execution.

    This hook can modify the execution result or log metrics.

    Args:
        ctx: Hook context with component and result
    """
    result = ctx.result
    component = ctx.component

    # Example: Log execution summary
    if hasattr(component, 'name'):
        logger.debug(f"Executed component: {component.name}")


def on_error(ctx: HookContext) -> None:
    """
    Called when an error occurs.

    This hook can log errors, report to monitoring, or handle recovery.

    Args:
        ctx: Hook context with error info
    """
    error = ctx.error
    original_hook = ctx.data.get('original_hook')

    if error:
        logger.error(f"Error in {original_hook or 'unknown'}: {error}")
