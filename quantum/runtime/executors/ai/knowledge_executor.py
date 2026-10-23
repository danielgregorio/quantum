"""
Knowledge Executor - Execute q:knowledge statements

Handles knowledge base creation and RAG operations.
"""

import copy
from typing import Any, List, Type
from quantum.runtime.executors.base import BaseExecutor, ExecutorError

# Import from features module
try:
    from quantum.core.features.knowledge_base.src.ast_node import KnowledgeNode
except ImportError:
    from quantum.core.features.knowledge_base.src import KnowledgeNode


class KnowledgeExecutor(BaseExecutor):
    """
    Executor for q:knowledge statements.

    Supports:
    - Multiple source types (text, file, directory, URL, query)
    - Embedding generation
    - Vector storage (ChromaDB)
    - RAG queries via q:query knowledge="name"
    """

    @property
    def handles(self) -> List[Type]:
        return [KnowledgeNode]

    def execute(self, node: KnowledgeNode, exec_context) -> Any:
        """
        Execute knowledge base creation.

        Args:
            node: KnowledgeNode with knowledge base configuration
            exec_context: Execution context

        Returns:
            Knowledge base info dict
        """
        context = exec_context.get_all_variables()
        # IA-10: the name is an expression — a base per board or per user (name="cards{id}")
        name = str(self.apply_databinding(node.name, context)) if '{' in node.name else node.name
        try:

            # KnowledgeService.index_knowledge() expects KnowledgeSourceNode
            # objects (attribute access: source.content, source.path, ...),
            # not dicts — build resolved copies rather than a dict config.
            sources = []
            for source in node.sources:
                resolved = copy.copy(source)

                if source.source_type == 'text' and source.content:
                    resolved.content = self.apply_databinding(source.content, context)
                elif source.source_type in ('file', 'directory') and source.path:
                    resolved.path = self.apply_databinding(source.path, context)
                elif source.source_type == 'url' and source.url:
                    resolved.url = self.apply_databinding(source.url, context)
                elif source.source_type == 'query':
                    resolved.bound = self._bind(source, context)       # IA-10: never into the SQL

                sources.append(resolved)

            # Index into the SAME KnowledgeService instance that
            # q:query datasource="knowledge:..." searches later
            # (runtime.knowledge_service — see component.py's
            # _execute_knowledge_query). services.knowledge is a separate
            # instance and indexing into it would leave searches empty.
            knowledge_service = self.runtime.knowledge_service
            knowledge_service.index_knowledge(
                name=name,
                sources=sources,
                embed_model=node.embed_model,
                chunk_size=node.chunk_size,
                chunk_overlap=node.chunk_overlap,
                persist=node.persist,
                persist_path=node.persist_path,
                rebuild=node.rebuild,
                database_service=self.services.database,
                exec_context=exec_context,
            )

            info = {
                'success': True,
                'name': name,
                'embed_model': node.embed_model,
            }

            # Store knowledge base reference (name resolves via q:query
            # datasource="knowledge:{name}", not by reading this variable)
            exec_context.set_variable(name, info, scope="component")
            exec_context.set_variable(f"{name}_info", info, scope="component")
            exec_context.set_variable(f"_knowledge_{name}", {
                'embed_model': node.embed_model,
            }, scope="component")

            return info

        except Exception as e:
            exec_context.set_variable(f"{name}_info", {
                'success': False,
                'error': str(e),
                'name': name
            }, scope="component")
            # IA-5: a q:query on this base then fails with this reason (it used
            # to answer "Knowledge base is still loading" as if that were the
            # answer, with success=True).
            exec_context.set_variable(f"_knowledge_{name}", {
                '_failed': True, 'error': str(e),
            }, scope="component")
            if getattr(node, 'on_error', 'fail') == 'continue':
                return None
            raise ExecutorError(f"Knowledge base creation error: {e}")

    def _bind(self, source, context) -> dict:
        """The values of a query source's q:params, checked by their types as q:query's are (IA-10)."""
        from quantum.runtime.query_validators import QueryValidator, QueryValidationError
        bound = {}
        for param in getattr(source, 'params', None) or []:
            try:
                bound[param.name] = QueryValidator.validate_param(
                    self.apply_databinding(param.value, context), param.param_type,
                    {'null': param.null, 'max_length': param.max_length, 'scale': param.scale})
            except QueryValidationError as exc:
                raise ExecutorError(f'<q:source type="query"> <q:param name="{param.name}">: {exc}') from exc
        return bound
