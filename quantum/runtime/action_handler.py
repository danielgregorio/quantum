"""
Quantum Action Handler - Process server-side actions from forms

Phase A: Forms & Actions
Handles POST/PUT/DELETE requests, validates parameters, executes action body,
manages flash messages, and performs redirects.
"""

from typing import Dict, Any, Optional, List, Tuple
from flask import request, session, redirect as flask_redirect
from quantum.core.ast_nodes import (
    ActionNode, RedirectNode, FlashNode, QuantumParam, QueryNode, PythonNode,
    HTMLNode, TextNode, CommentNode
)
from quantum.core.features.state_management.src.ast_node import SetNode
from quantum.core.features.conditionals.src.ast_node import IfNode
from quantum.runtime.execution_context import ExecutionContext
from quantum.runtime.component import ComponentExecutionError, ComponentRuntime
from quantum.runtime import param_validation
import re
import logging

logger = logging.getLogger('quantum.action')


class ValidationError(Exception):
    """Parameter validation error"""
    pass


class ActionHandler:
    """
    Handles server-side action execution.

    Workflow:
    1. Extract form data from request
    2. Validate against q:param definitions
    3. Execute action body statements
    4. Handle flash messages
    5. Perform redirect
    """

    def __init__(self, component_runtime: Optional[ComponentRuntime] = None):
        self.component_runtime = component_runtime or ComponentRuntime()

    def handle_action(
        self,
        action: ActionNode,
        context: Optional[ExecutionContext] = None,
        route_params: Optional[Dict[str, str]] = None
    ) -> Tuple[Optional[str], int]:
        """
        Handle action execution.

        Returns:
            Tuple[redirect_url, status_code] or None if no redirect
        """

        # Use provided context or create new one, seeded with the live Flask session
        # so `q:set name="session.x"` persists and require_auth sees it on the next
        # request. Without this, an action's ExecutionContext started empty and any
        # session mutation made during the action was silently discarded.
        owns_context = context is None
        if context is None:
            context = ExecutionContext()
            context.session_vars = session.get('quantum_session', {})

        try:
            # 1. Extract form data
            form_data = self._extract_form_data()

            # 2. Validate parameters
            validated_params = self._validate_parameters(action.params, form_data)

            # 3. Add validated params to context
            for key, value in validated_params.items():
                context.set_variable(key, value)

            # Os arquivos enviados entram no contexto mesmo sem um q:param
            # que os declare. `_extract_form_data` ja os coleta e a
            # documentacao promete `q.files`, mas so os parametros validados
            # chegavam ao contexto — entao `<q:file action="upload"
            # file="{avatar}">` sem um `<q:param name="avatar">` acima dizia
            # "File variable 'avatar' not found". Um q:param declarado ganha:
            # ele passou pela validacao.
            for key, value in form_data.items():
                if key in validated_params:
                    continue
                if key == 'files' or param_validation.is_uploaded_file(value):
                    context.set_variable(key, value)

            # ACT-6: the submitted fields as `form`, raw, like the page render
            # gets them. {form.campo} inside an action used to evaluate to
            # empty — only declared q:params reached the action — while the
            # docs (data-fetching.md) and pages (rag.q) use {form.campo}.
            context.set_variable('form', {
                key: value for key, value in form_data.items()
                if key != 'files' and not param_validation.is_uploaded_file(value)
            })

            # ROUTE-2: the page's route segments ([nome], [...caminho]) are
            # variables of the action too, set last so a form field with the
            # same name cannot replace them. A POST to /admin/app/loja used to
            # run without `name`, so every form had to repeat it in a hidden
            # field — one the browser can change.
            for key, value in (route_params or {}).items():
                context.set_variable(key, value)

            # 4. Execute action body
            redirect_info = self._execute_action_body(action, context)

            # 5. Sync session mutations back to Flask (mirrors web_server.py's
            # render path, which does the same after execute_component()).
            if owns_context:
                session['quantum_session'] = context.session_vars
                session.modified = True

            # 6. Return redirect if present
            if redirect_info:
                return redirect_info

            return None, 200

        except ValidationError as e:
            # Validation failed - set error flash and redirect back
            self._set_flash_message(str(e), 'error')
            # Redirect to referer or home
            referer = request.referrer or '/'
            return referer, 302

        except Exception as e:
            # Unexpected error. Sync whatever session state changed before the
            # failure, and report a real error instead of a redirect disguised
            # as one (a 500 with a Location header confuses clients into
            # thinking the action succeeded).
            #
            # And LOG it, with the traceback. The 500 page tells the user to
            # "check server logs for details" and the logs recorded absolutely
            # nothing — the failure existed only as a flash message the user
            # might never see. Whoever is debugging gets the action name, the
            # exception and the stack.
            logger.exception(
                "q:action %r failed: %s", getattr(action, 'name', '?'), e
            )
            if owns_context:
                session['quantum_session'] = context.session_vars
                session.modified = True
            self._set_flash_message(f'Action error: {str(e)}', 'error')
            return None, 500

    def _extract_form_data(self) -> Dict[str, Any]:
        """Extract data from POST/PUT/DELETE request, uploaded files included.

        This returned request.form only. Uploaded files never entered the
        context, so

            <q:file action="upload" file="{avatar}" destination="..." />

        raised "File variable 'avatar' not found" for every web request:
        q:file action="upload" could not be reached from a browser at all,
        which is the only place a file upload comes from.
        """
        data: Dict[str, Any] = {}

        if request.method in ['POST', 'PUT', 'PATCH']:
            if request.is_json:
                data = request.get_json() or {}
            else:
                data = request.form.to_dict()

        elif request.method == 'DELETE':
            if request.is_json:
                data = request.get_json() or {}

        try:
            uploaded = request.files
        except Exception:
            uploaded = None

        if uploaded:
            files = {}
            for field, storage in uploaded.items(multi=False):
                if not storage or not storage.filename:
                    continue        # an empty file input posts a blank part
                files[field] = storage
                if field in data:
                    logger.warning(
                        "the upload field %r has the same name as a form "
                        "field; the file wins", field)
                data[field] = storage
            if files:
                # Also as a group, which is what q.files documents.
                data.setdefault('files', files)

        return data

    def _validate_parameters(
        self,
        params: List[QuantumParam],
        form_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate form data against q:param definitions.

        Raises ValidationError if validation fails.
        """

        validated = {}

        for param in params:
            value = form_data.get(param.name)

            # Check required
            if param.required and (value is None or value == ''):
                raise ValidationError(f"Parameter '{param.name}' is required")

            # Skip validation if optional and not provided
            if value is None or value == '':
                if param.default is not None:
                    validated[param.name] = param.default
                continue

            # Type validation and conversion
            validated_value = self._validate_type(param, value)

            # Additional validation rules
            self._validate_rules(param, validated_value)

            validated[param.name] = validated_value

        return validated

    def _validate_type(self, param: QuantumParam, value: Any) -> Any:
        """Converte o valor para o tipo declarado, ou levanta ValidationError.

        Delega para quantum.runtime.param_validation, a MESMA implementacao
        que o ComponentRuntime usa. Havia duas copias divergentes: esta so
        conhecia `integer`, `decimal` e `float`, e o resto caia num
        `return str(value)` final — `type="number"` (32 usos no repositorio)
        virava string sem checar min/max, e `type="file"` (5 usos, incluindo
        components/upload_demo.q) transformava o objeto de upload na sua
        repr, `"<FileStorage: 'foto.png' ('image/png')>"`, que era o que o
        <q:file action="upload"> recebia no lugar do arquivo.
        """
        convertido, erro = param_validation.coerce(param, value)
        if erro:
            raise ValidationError(erro)
        return convertido

    def _validate_rules(self, param: QuantumParam, value: Any):
        """min/max/minlength/maxlength/pattern/enum — a mesma implementacao
        que o ComponentRuntime aplica."""
        erros = param_validation.check_rules(param, value)
        if erros:
            raise ValidationError(erros[0])

    def _execute_action_body(
        self,
        action: ActionNode,
        context: ExecutionContext
    ) -> Optional[Tuple[str, int]]:
        """
        Execute action body statements.

        Returns redirect info if redirect encountered, None otherwise.
        """

        return self._execute_statements(action.body, context)

    def _execute_statements(
        self,
        statements,
        context: ExecutionContext
    ) -> Optional[Tuple[str, int]]:
        """Execute a list of action statements, returning a redirect if one fires.

        This used to be a hand-maintained if-elif chain listing the node types
        an action was allowed to contain — Redirect, Flash, Set, Python, If —
        with `QueryNode: pass  # TODO` and NO else. Everything it did not
        recognise was dropped without a word:

          - q:query inside q:action did nothing at all, so a form handler
            could not write to the database. That is the entire point of an
            action.
          - q:mail, q:log, q:file, q:dump, q:invoke, q:loop, q:llm — all
            silently ignored, while the action returned HTTP 302 as if it had
            worked.

        Now everything except the two control-flow nodes goes through the SAME
        ExecutorRegistry the rest of the engine uses, so an action can contain
        whatever a component can, and anything genuinely unhandled is LOGGED
        rather than dropped.
        """
        for statement in statements:
            result = self._execute_one(statement, context)
            if result:
                return result
        return None

    def _execute_one(
        self,
        statement,
        context: ExecutionContext
    ) -> Optional[Tuple[str, int]]:
        """Execute one statement; return redirect info if it was a redirect."""

        # --- control flow that only makes sense inside an action ---
        if isinstance(statement, RedirectNode):
            url = self._resolve_databinding(statement.url, context)
            if statement.flash:
                flash_msg = self._resolve_databinding(statement.flash, context)
                # flashType on q:redirect used to be ignored and hardcoded to
                # 'success', so a failed login's message rendered green.
                self._set_flash_message(
                    flash_msg, getattr(statement, 'flash_type', None) or 'success'
                )
            return url, statement.status

        if isinstance(statement, FlashNode):
            message = self._resolve_databinding(statement.message, context)
            self._set_flash_message(message, statement.flash_type)
            return None

        if isinstance(statement, IfNode):
            return self._execute_if(statement, context)

        # --- everything else: the same registry the rest of the engine uses ---
        registry = getattr(self.component_runtime, 'executor_registry', None)
        if registry is not None and registry.can_execute(statement):
            registry.execute(statement, context)
            return None

        if isinstance(statement, PythonNode):
            # q:python has its own bridge here (q.form), and is gated by
            # security.python_scripting.
            self._execute_python(statement, context)
            return None

        # Render-only nodes legitimately do nothing in an action body.
        if isinstance(statement, (HTMLNode, TextNode, CommentNode)):
            return None

        # Never drop something silently again.
        logger.warning(
            "q:action: no executor for %s — statement ignored. If this tag is "
            "meant to work inside an action, it needs an executor in the "
            "registry.", type(statement).__name__
        )
        return None

    def _execute_if(
        self,
        statement: IfNode,
        context: ExecutionContext
    ) -> Optional[Tuple[str, int]]:
        """q:if inside an action, including elseif/else."""
        evaluate = self.component_runtime._evaluate_condition

        if evaluate(statement.condition, context.get_all_variables()):
            return self._execute_statements(statement.if_body, context)

        # elseif_blocks are DICTS ({"condition":..., "body":...}). This used to
        # unpack them as 2-tuples, which iterates the dict's KEYS — so the
        # literal strings "condition" and "body" were used as the condition
        # and the body. The same dict-versus-object mismatch that crashed the
        # renderer's q:elseif.
        for block in (statement.elseif_blocks or []):
            if isinstance(block, dict):
                cond, body = block.get('condition'), block.get('body')
            else:
                cond, body = getattr(block, 'condition', None), getattr(block, 'body', None)
            if cond is not None and evaluate(cond, context.get_all_variables()):
                return self._execute_statements(body or [], context)

        return self._execute_statements(statement.else_body or [], context)

    def _execute_python(self, node: PythonNode, context: ExecutionContext):
        """
        Execute a q:python block within an action.

        Uses the same QuantumBridge pattern as the PythonExecutor
        so that q.form, q.variable etc. work inside actions.
        """
        from quantum.runtime.executors.scripting.python_executor import QuantumBridge

        # Honour security.python_scripting, the same as q:python outside an
        # action. This check was missing, so the switch an operator flips to
        # stop in-process Python execution could be walked around by putting
        # the same q:python block inside a q:action — and a security switch
        # that does not switch everything off is worse than none, because the
        # operator believes they are covered. Found by an independent
        # verification pass over this session's claims.
        if not self.component_runtime.services.python_scripting_enabled:
            raise ComponentExecutionError(
                "q:python is disabled by security.python_scripting=false in "
                "quantum.config.yaml (reached through q:action)"
            )

        all_vars = context.get_all_variables()

        # Make form data available via q.form
        form_data = {}
        try:
            form_data = request.form.to_dict()
        except Exception:
            pass
        all_vars['form'] = form_data

        bridge = QuantumBridge(context, all_vars)
        bridge._exports['form'] = form_data

        namespace = {
            'q': bridge,
            '__quantum_context__': all_vars,
        }
        namespace.update(all_vars)

        # Dedented, for the same reason as q:python's own executor: .strip()
        # unindents only the first line, so markup-indented code raised
        # "unexpected indent" on line 2.
        from quantum.runtime.executors.scripting.python_executor import (
            normalise_python_source,
        )
        exec(normalise_python_source(node.code), namespace)

        # Export bridge changes back to context
        for key, value in bridge._exports.items():
            context.set_variable(key, value, scope="component")

    def _resolve_databinding(self, text: str, context: ExecutionContext) -> str:
        """Resolve {expressions} in a redirect URL or flash message (ACT-3).

        This looked each {name} up with get_variable, so anything but a plain
        name failed — `flash="{result.error}"` or `{len(itens)} saved` ended
        the action with "Variable 'result.error' not found in any scope" and a
        500. It now goes through the same evaluator as every q: attribute.
        """
        if not text or '{' not in text:
            return text
        valor = self.component_runtime._apply_databinding(text, context.get_all_variables())
        return '' if valor is None else str(valor)

    def _set_flash_message(self, message: str, flash_type: str = 'info'):
        """Set flash message in session"""
        if 'flash' not in session:
            session['flash'] = {}

        session['flash'] = {
            'message': message,
            'type': flash_type
        }
        session.modified = True

    def get_flash_message(self) -> Optional[Dict[str, str]]:
        """Get and clear flash message from session"""
        if 'flash' in session:
            flash = session.pop('flash')
            session.modified = True
            return flash
        return None
