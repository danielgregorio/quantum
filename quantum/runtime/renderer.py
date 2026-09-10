"""
Quantum HTML Renderer

Converts executed AST to HTML string output.
Handles databinding, loops, conditionals, and HTML passthrough.
"""

import html
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, List

# Fix imports

from quantum.core.ast_nodes import (
    QuantumNode, ComponentNode, HTMLNode, TextNode, DocTypeNode,
    CommentNode, QueryNode, ComponentCallNode, ImportNode
)
from quantum.core.expression_diagnostics import is_absent_scope, report_unresolved
from quantum.core.expressions import (
    ExpressionEvaluator, ExpressionError, UndefinedError, is_regex_quantifier,
)
from quantum.core.features.conditionals.src.ast_node import IfNode
from quantum.core.features.loops.src.ast_node import LoopNode
from quantum.core.features.state_management.src.ast_node import SetNode
from quantum.runtime.execution_context import ExecutionContext

logger = logging.getLogger('quantum.renderer')


class HTMLRenderer:
    """
    Renders Quantum AST to HTML string.

    Phase 1: Server-side rendering only
    Phase 3: Will support hydration markers for client-side interactivity

    Handles:
    - HTML elements passthrough
    - Text with databinding {variable}
    - Quantum tags are already executed (loops expanded, conditions evaluated)
    - XSS protection via HTML escaping
    """

    # Tags whose text content should NOT be processed by databinding or HTML-escaped
    RAW_CONTENT_TAGS = {'style', 'script'}

    def __init__(self, context: ExecutionContext, components_dir: str = "./components",
                 function_resolver=None, config=None):
        """
        Initialize renderer with execution context.

        Args:
            context: ExecutionContext with all variables and query results
            components_dir: Directory where component files are located (Phase 2)
            function_resolver: the runtime's lookup for the component's
                q:functions (FN-3). Without it `<p>{dobro(2)}</p>` rendered
                the literal text: only q: attributes could call a function.
        """
        self.context = context
        self.components_dir = components_dir
        # COMP-4: child components run with the page's configuration
        # (datasources, services); None means no configuration.
        self.config = config
        # q:import of the component being rendered: name -> (component, from)
        self.imports = {}
        self._raw_mode = False
        # Shared with ComponentRuntime: one evaluator, one grammar, so a
        # {expression} means the same thing in the execute pass and the
        # render pass. They used to be two hand-rolled implementations.
        self._expressions = ExpressionEvaluator(function_resolver=function_resolver)

        # Lazy-load composer (Phase 2)
        self._composer = None
        self._resolver = None


    def render(self, node: QuantumNode) -> str:
        """
        Main render dispatch method.

        Args:
            node: AST node to render

        Returns:
            HTML string
        """

        if isinstance(node, HTMLNode):
            return self._render_html_node(node)

        elif isinstance(node, TextNode):
            return self._render_text_node(node)

        elif isinstance(node, DocTypeNode):
            return self._render_doctype(node)

        elif isinstance(node, CommentNode):
            return self._render_comment(node)

        elif isinstance(node, ComponentNode):
            self.imports = {
                imp.alias or imp.component: (imp.component, imp.from_path)
                for imp in node.statements
                if isinstance(imp, ImportNode) and imp.component
            }
            return self._render_component(node)

        # Component Composition (Phase 2)
        elif isinstance(node, ComponentCallNode):
            return self._render_component_call(node)

        elif isinstance(node, ImportNode):
            # Imports are processed at component load time, not render time
            return ''

        elif type(node).__name__ == "RenderedHTML":
            # Slot content the parent already rendered (component_composer)
            return node.html

        elif isinstance(node, LoopNode):
            return self._render_loop(node)

        elif isinstance(node, IfNode):
            return self._render_if(node)

        # SetNode and QueryNode are executed during runtime, not rendered
        elif isinstance(node, (SetNode, QueryNode)):
            return ''

        else:
            # Unknown node type - skip (includes QuantumReturn and others)
            return ''


    def render_all(self, nodes: List[QuantumNode]) -> str:
        """
        Render list of nodes and concatenate results.

        Args:
            nodes: List of AST nodes

        Returns:
            Concatenated HTML string
        """
        return ''.join(self.render(node) for node in nodes)


    def _render_html_node(self, node: HTMLNode) -> str:
        """
        Render HTML element with attributes and children.

        Example:
          HTMLNode(tag='div', attributes={'class': 'container'}, children=[...])
          → <div class="container">...</div>

        Args:
            node: HTMLNode to render

        Returns:
            HTML string
        """

        # Build opening tag
        tag_parts = [f'<{node.tag}']

        # Add attributes with databinding applied
        if node.attributes:
            for key, value in node.attributes.items():
                # Apply databinding to attribute value
                processed_value = self._apply_databinding(value)
                # Escape for HTML attribute safety (prevent XSS)
                escaped_value = html.escape(str(processed_value), quote=True)
                tag_parts.append(f'{key}="{escaped_value}"')

        opening_tag = ' '.join(tag_parts)

        # Self-closing tags (void elements)
        if node.self_closing:
            return opening_tag + ' />'

        # Regular tags with children
        opening_tag += '>'

        # Style/script tags: render children as raw text (no databinding, no escaping)
        if node.tag in self.RAW_CONTENT_TAGS:
            prev_raw = self._raw_mode
            self._raw_mode = True
            children_html = self.render_all(node.children)
            self._raw_mode = prev_raw
        else:
            children_html = self.render_all(node.children)

        closing_tag = f'</{node.tag}>'

        return opening_tag + children_html + closing_tag


    def _render_text_node(self, node: TextNode) -> str:
        """
        Render text content with databinding applied.

        Example:
          TextNode("Hello {user.name}!") with context['user']['name'] = 'John'
          → "Hello John!"

        Args:
            node: TextNode to render

        Returns:
            Text string with databinding applied and HTML escaped
        """

        text = node.content

        # Inside <style>/<script> tags: return raw content without databinding or escaping
        if self._raw_mode:
            return text

        # Apply databinding if needed
        if node.has_databinding:
            text = self._apply_databinding(text)

        # HTML escape to prevent XSS
        # NOTE: This means you can't inject raw HTML via variables (security feature)
        # Guard against non-string values (e.g., bound methods from getattr)
        if callable(text):
            text = ''
        return html.escape(str(text) if text is not None else '')


    def _render_doctype(self, node: DocTypeNode) -> str:
        """
        Render DOCTYPE declaration.

        Example:
          DocTypeNode("html") → "<!DOCTYPE html>"

        Args:
            node: DocTypeNode to render

        Returns:
            DOCTYPE string
        """
        return f'<!DOCTYPE {node.value}>'


    def _render_loop(self, node: LoopNode) -> str:
        """
        Render q:loop by iterating over items and rendering body for each.

        Args:
            node: LoopNode to render

        Returns:
            Concatenated HTML from all loop iterations
        """
        result = []

        # Get the items to iterate over
        items = self._get_loop_items(node)

        if not items:
            return ''

        # Save current context state
        original_vars = self.context.local_vars.copy()

        try:
            for index, item in enumerate(items):
                # Set loop variable in context
                self.context.set_variable(node.var_name, item, scope="local")

                # For query loops, set dotted variables (e.g., task.title, task.status)
                if node.loop_type == 'query' and isinstance(item, dict):
                    for field_name, field_value in item.items():
                        dotted_key = f"{node.var_name}.{field_name}"
                        self.context.set_variable(dotted_key, field_value, scope="local")

                # Set index if specified
                if node.index_name:
                    self.context.set_variable(node.index_name, index, scope="local")

                # Render loop body
                for child in node.body:
                    result.append(self.render(child))

        finally:
            # Restore original context
            self.context.local_vars = original_vars

        return ''.join(result)

    def _get_loop_items(self, node: LoopNode) -> list:
        """Get items to iterate over from loop node."""
        if node.loop_type == 'array':
            # Get items expression
            items_expr = node.items
            if not items_expr:
                return []

            # Apply databinding to resolve variable reference
            if '{' in items_expr and '}' in items_expr:
                resolved = self._apply_databinding(items_expr)
                if isinstance(resolved, list):
                    return resolved
                elif isinstance(resolved, str):
                    # Try to parse as JSON
                    try:
                        import json
                        return json.loads(resolved)
                    except Exception as exc:
                        # A loop that renders NOTHING is indistinguishable from
                        # an empty collection, so an unresolvable items= used
                        # to look like "no results" on the page.
                        logger.warning(
                            "q:loop items=%r is not a list and not JSON (%s); "
                            "rendering zero rows", items_expr, exc
                        )
                        return []
            logger.warning(
                "q:loop items=%r did not resolve to a list; rendering zero rows",
                items_expr
            )
            return []

        elif node.loop_type == 'range':
            # Generate range
            try:
                start = int(node.from_value) if node.from_value else 1
                end = int(node.to_value) if node.to_value else 10
                step = node.step_value if node.step_value else 1
                return list(range(start, end + 1, step))
            except Exception as exc:
                # from=/to= that did not resolve (a databinding placeholder,
                # a typo) silently produced an empty range.
                logger.warning(
                    "q:loop range from=%r to=%r step=%r is not usable (%s); "
                    "rendering zero rows",
                    node.from_value, node.to_value, node.step_value, exc
                )
                return []

        elif node.loop_type == 'query':
            # Query loop - resolve items from query result variable
            items_expr = node.items
            if not items_expr:
                # Shorthand syntax: query_name is in var_name
                query_name = getattr(node, 'query_name', node.var_name)
                try:
                    data = self.context.get_variable(query_name)
                    if isinstance(data, list):
                        return data
                    logger.warning(
                        "q:loop query=%r resolved to %s, not a list; "
                        "rendering zero rows", query_name, type(data).__name__
                    )
                except Exception:
                    logger.warning(
                        "q:loop query=%r is not defined — did the q:query run, "
                        "and is the name spelled the same? Rendering zero rows.",
                        query_name
                    )
                return []

            # Traditional syntax: items="{tasks}"
            if '{' in items_expr and '}' in items_expr:
                resolved = self._apply_databinding(items_expr)
                if isinstance(resolved, list):
                    return resolved
            return []

        elif node.loop_type == 'list':
            # Split by delimiter
            items_expr = node.items
            if not items_expr:
                return []
            resolved = self._apply_databinding(items_expr) if '{' in items_expr else items_expr
            delimiter = node.delimiter or ','
            return [item.strip() for item in str(resolved).split(delimiter)]

        return []

    def _render_if(self, node: IfNode) -> str:
        """
        Render q:if by evaluating condition and rendering appropriate branch.

        Args:
            node: IfNode to render

        Returns:
            HTML from the matching branch
        """
        # Evaluate main condition
        if self._evaluate_condition(node.condition):
            return self.render_all(node.if_body)

        # Check elseif branches.
        #
        # The parser stores these as DICTS — {"condition": ..., "body": ...} —
        # and IfExecutor reads them that way. This pass read them as objects
        # (elseif.condition), so any page using q:elseif died with
        # "'dict' object has no attribute 'condition'" during render. The two
        # passes disagreed about the same structure and only one was ever run
        # in a test. Both shapes are accepted here so a future change to
        # either side cannot resurrect the crash.
        for elseif in (node.elseif_blocks or []):
            if isinstance(elseif, dict):
                cond, body = elseif.get("condition"), elseif.get("body")
            else:
                cond, body = getattr(elseif, "condition", None), getattr(elseif, "body", None)
            if cond is not None and self._evaluate_condition(cond):
                return self.render_all(body or [])

        # Else branch
        if node.else_body:
            return self.render_all(node.else_body)

        return ''

    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition expression."""
        if not condition:
            return False

        # Evaluate the condition as an expression, without interpolating any
        # values into it first.
        #
        # This used to build a string by substituting databinding results into
        # the condition and then eval() it. That is not a comparison, it is
        # code assembly from data: a record whose name is "'; __import__(...)"
        # became executable code. Stripping the braces instead leaves the
        # variable NAMES in place and lets the evaluator resolve them, so no
        # value is ever parsed as syntax. PUBLIC_RELEASE_PLAN.md P0.1.
        stripped = re.sub(r'\{([^}]+)\}', r'\1', condition).strip()
        try:
            return bool(self._expressions.evaluate(
                stripped, self.context.get_all_variables()
            ))
        except UndefinedError:
            # EXPR-5: a missing name, key or attribute makes a condition FALSE,
            # not true. Other failures raise (see ComponentRuntime).
            #
            #
            # This used to fall through to _apply_databinding, which hands back
            # the literal placeholder '{session.user.is_admin}' — a non-empty
            # string, which the truthiness rule below then read as True. So
            #     <q:if condition="session.user.is_admin">
            # rendered its admin branch for a logged-out visitor whose session
            # had no `user`, and every q:else guarding it never fired. A
            # condition failing open is an authorization bypass by
            # construction. Reported by two audit dimensions, reproduced
            # directly. See tests/integration/test_condition_fails_closed.py.
            report_unresolved(stripped, ExpressionError(
                f"condition {condition!r} could not be evaluated; treated as false"
            ))
            return False
        except ExpressionError as exc:
            raise ExpressionError(f"condition {condition!r} could not be evaluated: {exc}") from exc

    def _render_comment(self, node: CommentNode) -> str:
        """
        Render HTML comment.

        Example:
          CommentNode("This is a comment") → "<!-- This is a comment -->"

        Args:
            node: CommentNode to render

        Returns:
            HTML comment string
        """
        return f'<!-- {node.content} -->'


    # Um handler inline: onclick="salvar()", onchange="atualizar(this)".
    _INLINE_HANDLER = re.compile(
        r'\son[a-z]+\s*=\s*"([^"]*)"|\son[a-z]+\s*=\s*\'([^\']*)\'',
        re.IGNORECASE)
    # O nome chamado dentro dele.
    _CALLED_NAME = re.compile(r'\b([A-Za-z_$][\w$]*)\s*\(')

    def _render_component(self, node: ComponentNode) -> str:
        """
        Render entire component body.

        Args:
            node: ComponentNode to render

        Returns:
            HTML string of component output
        """
        html = self.render_all(node.statements)
        script = self._explain_server_side_handlers(node, html)
        if not script:
            return html
        # Dentro do documento quando ha um: depois de `</html>` o navegador
        # reposiciona o script sozinho, mas o HTML deixa de ser valido e
        # qualquer ferramenta que leia a saida tropeca.
        for fecho in ('</body>', '</html>'):
            posicao = html.rfind(fecho)
            if posicao != -1:
                return html[:posicao] + script + '\n' + html[posicao:]
        return html + script

    def _explain_server_side_handlers(self, node: ComponentNode,
                                      html: str) -> str:
        """Um `onclick="minhaFuncao()"` que aponta para uma q:function.

        O corpo de uma q:function nunca vai para o cliente — ela roda no
        servidor, com q:set/q:query/q:invoke, e nao ha rota para chama-la do
        navegador (esse e o papel do q:action). Mesmo assim o HTML saia com
        `onclick="minhaFuncao()"` e nenhuma definicao de `minhaFuncao` em
        lugar nenhum: o clique dava `ReferenceError` no console do navegador
        e absolutamente nada na tela, no log do servidor ou em qualquer
        outro lugar. Quem escreveu nao tinha como saber.

        Traduzir o corpo para JavaScript nao e possivel em geral — ele le o
        banco. Entao o que se pode fazer com honestidade e nomear a falha:
        um aviso no log do servidor, na hora de renderizar, e uma definicao
        no cliente que levanta um erro dizendo o que fazer.
        """
        declaradas = {
            f.name for f in getattr(node, 'functions', None) or []
            if getattr(f, 'name', None)
        }
        if not declaradas or not html:
            return ''

        chamadas = set()
        for m in self._INLINE_HANDLER.finditer(html):
            corpo = m.group(1) if m.group(1) is not None else m.group(2)
            for nome in self._CALLED_NAME.findall(corpo or ''):
                if nome in declaradas:
                    chamadas.add(nome)

        if not chamadas:
            return ''

        for nome in sorted(chamadas):
            logger.warning(
                "%s: an inline handler calls q:function %r, but a q:function "
                "runs on the server and is never sent to the browser - the "
                "click will raise ReferenceError. Use <q:action> for a "
                "server-side handler, or write the JavaScript in <q:script>.",
                getattr(node, 'name', '<component>'), nome
            )

        # A mensagem sai numa variavel antes de entrar na f-string. Ter a
        # expressao quebrada em varias linhas DENTRO das chaves e PEP 701,
        # valido so no Python 3.12+ — e o pyproject declara 3.11. Rodando so
        # 3.12 aqui, isso passou despercebido ate o CI (matriz 3.11/3.12)
        # recusar o modulo inteiro com SyntaxError na coleta.
        linhas_js = []
        for nome in sorted(chamadas):
            recado = (
                f'q:function "{nome}" runs on the server and is not '
                f'available in the browser. Use <q:action> to handle this '
                f'from the page, or define the handler in <q:script>.'
            )
            alvo = json.dumps(nome)
            linhas_js.append(
                f"  window[{alvo}] = window[{alvo}] || "
                f"function () {{ throw new Error({json.dumps(recado)}); }};"
            )
        corpo_js = '\n'.join(linhas_js)
        # `</` vira `<\/`: nenhum texto dentro do script pode fechar a tag
        # antes da hora.
        corpo_js = corpo_js.replace('</', '<\\/')
        return f"\n<script>\n{corpo_js}\n</script>"


    def _apply_databinding(self, text: str) -> Any:
        """
        Replace {variable} and {expression} with actual values from context.

        Examples:
          "{name}" → "John"
          "{user.email}" → "john@example.com"
          "{price * quantity}" → "49.99"
          "{items.length}" → "5"
          "Total: ${product.price}" → "Total: $29.99"

        Args:
            text: Text with possible {expression} patterns

        Returns:
            - For pure expressions like "{items}": the actual value (list, dict, etc.)
            - For mixed content like "Hello {name}": interpolated string
        """
        if not text:
            return text

        pattern = r'\{([^}]+)\}'

        # Check if the ENTIRE text is just a single databinding expression
        full_match = re.fullmatch(pattern, text.strip())
        if full_match:
            # Pure expression - return the actual value (not converted to string)
            expression = full_match.group(1).strip()
            try:
                return self._evaluate_expression(expression)
            except Exception as exc:
                report_unresolved(expression, exc)
                # If evaluation fails, return original placeholder
                return text

        # Mixed content (text + expressions) - need string interpolation
        def replace_binding(match):
            """Replace single {expression} match"""
            expression = match.group(1).strip()

            try:
                # Evaluate expression from context
                value = self._evaluate_expression(expression)
                return str(value) if value is not None else ''

            except Exception as exc:
                report_unresolved(expression, exc)
                # The placeholder, same as the pure-expression branch above.
                # This used to emit '{ERROR: <expr>}', so the SAME broken
                # expression rendered two different ways depending on whether
                # it shared a text node with other content — and the marker
                # leaked an internal variable name onto the user's page. The
                # diagnosis belongs in the log, which now has it.
                return match.group(0)

        # Find and replace all {expression} patterns
        result = re.sub(pattern, replace_binding, text)

        return result


    def _evaluate_expression(self, expression: str) -> Any:
        """
        Evaluate databinding expression from context.

        Supports:
        - Simple variables: user
        - Nested properties: user.name, user.address.city
        - Array access: items[0], products[2].name
        - Array properties: items.length
        - Simple arithmetic: price * quantity, count + 1
        - Query results: products, products_result.recordCount

        Args:
            expression: Expression to evaluate

        Returns:
            Evaluated value

        Raises:
            Exception: If expression cannot be evaluated
        """

        # Regex quantifiers ({n}, {n,m}) are literal text, not expressions.
        if is_regex_quantifier(expression):
            raise ValueError(f"'{expression}' is a regex quantifier")

        # Try to get from context directly (simple variable)
        # get_variable() searches all scopes: local -> function -> component -> session -> parent
        # This has to come first: get_all_variables() stores scoped variables
        # under dotted KEYS ('session.user'), which is a lookup, not an
        # attribute access, so the evaluator cannot see them.
        try:
            value = self.context.get_variable(expression)
            return value
        except:
            pass  # Variable not found, try other evaluation methods

        # The shared evaluator (FRAMEWORK_PLAN.md Fase 2.1) handles arithmetic,
        # comparison, indexing, attribute access and stdlib calls in one place.
        #
        # Four hand-rolled methods used to sit below this as a fallback —
        # _evaluate_nested_property, _evaluate_array_access,
        # _evaluate_comparison and _evaluate_arithmetic. Instrumenting the
        # whole suite after the evaluator went in showed all four at zero
        # calls, so they were deleted rather than kept as reassurance. Their
        # `if value is not None: return value` shape was a bug source anyway:
        # a property that legitimately held None fell through to the next
        # guess instead of resolving.
        try:
            return self._expressions.evaluate(
                expression, self.context.get_all_variables()
            )
        except ExpressionError:
            # Absent scoped variables resolve to '', the same contract
            # ComponentRuntime honours. Without this the runtime rendered ''
            # and the renderer rendered the literal '{form.email}' for the
            # same expression — one broken thing, two outputs, which is the
            # bug this phase set out to remove.
            if is_absent_scope(expression):
                return ''
            # Otherwise raised as-is. Wrapping it in "Cannot evaluate
            # expression: <expr> (<reason>)" repeated the expression the
            # caller already reports and buried the reason — the useful half —
            # in parentheses at the end of a doubled sentence.
            raise


    # ============================================
    # COMPONENT COMPOSITION RENDERING (Phase 2)
    # ============================================

    def _get_composer(self):
        """Lazy-load component composer"""
        if self._composer is None:
            from quantum.runtime.component_resolver import ComponentResolver
            from quantum.runtime.component_composer import ComponentComposer

            self._resolver = ComponentResolver(self.components_dir)
            self._composer = ComponentComposer(self._resolver)

        return self._composer

    def _render_component_call(self, node: ComponentCallNode) -> str:
        """
        Render component call (Phase 2).

        Examples:
          <Header title="Products" />
          <Button label="Save" color="green" />
          <Card title="Info">Content here</Card>

        Args:
            node: ComponentCallNode from AST

        Returns:
            Rendered HTML from child component
        """

        # COMP-1: a component that is not found, or fails, is an error. It
        # used to become an HTML comment and the page answered 200 with the
        # section silently missing — the database being down looked like a
        # page with no results.
        return self._get_composer().compose(node, self)
