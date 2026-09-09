"""
Knowledge Executor - Execute q:knowledge statements

Handles knowledge base creation and RAG operations.
"""

import copy
from typing import Any, List, Dict, Type
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
        try:
            context = exec_context.get_all_variables()

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
                elif source.source_type == 'query' and source.sql:
                    resolved.sql = self.apply_databinding(source.sql, context)

                sources.append(resolved)

            # Index into the SAME KnowledgeService instance that
            # q:query datasource="knowledge:..." searches later
            # (runtime.knowledge_service — see component.py's
            # _execute_knowledge_query). services.knowledge is a separate
            # instance and indexing into it would leave searches empty.
            knowledge_service = self.runtime.knowledge_service
            knowledge_service.index_knowledge(
                name=node.name,
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
                'name': node.name,
                'model': node.model,
                'embed_model': node.embed_model,
            }

            # Store knowledge base reference (name resolves via q:query
            # datasource="knowledge:{name}", not by reading this variable)
            exec_context.set_variable(node.name, info, scope="component")
            exec_context.set_variable(f"{node.name}_info", info, scope="component")
            exec_context.set_variable(f"_knowledge_{node.name}", {
                'embed_model': node.embed_model,
                'model': node.model,
            }, scope="component")

            return info

        except Exception as e:
            exec_context.set_variable(f"{node.name}_info", {
                'success': False,
                'error': str(e),
                'name': node.name
            }, scope="component")
            # _execute_knowledge_query() (component.py) checks this marker to
            # return a graceful "still loading" result instead of raising
            # KnowledgeError("not found") on the next q:query for this KB.
            exec_context.set_variable(f"_knowledge_{node.name}", {
                '_failed': True,
            }, scope="component")
            raise ExecutorError(f"Knowledge base creation error: {e}")
