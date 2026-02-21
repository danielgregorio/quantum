"""
Knowledge Executor - Execute q:knowledge statements

Handles knowledge base creation and RAG operations.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError

# Import from features module
try:
    from core.features.knowledge_base.src.ast_node import KnowledgeNode
except ImportError:
    from core.features.knowledge_base.src import KnowledgeNode


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

            # Build sources list
            sources = []
            for source in node.sources:
                source_config = {
                    'type': source.source_type,
                    'chunk_size': source.chunk_size or node.chunk_size,
                    'chunk_overlap': source.chunk_overlap or node.chunk_overlap
                }

                if source.source_type == 'text':
                    content = self.apply_databinding(source.content, context)
                    source_config['content'] = content

                elif source.source_type == 'file':
                    path = self.apply_databinding(source.path, context)
                    source_config['path'] = path

                elif source.source_type == 'directory':
                    path = self.apply_databinding(source.path, context)
                    source_config['path'] = path
                    source_config['pattern'] = source.pattern or '*.md'

                elif source.source_type == 'url':
                    url = self.apply_databinding(source.url, context)
                    source_config['url'] = url

                elif source.source_type == 'query':
                    datasource = source.datasource
                    sql = self.apply_databinding(source.sql, context)
                    source_config['datasource'] = datasource
                    source_config['sql'] = sql

                sources.append(source_config)

            # Build knowledge base configuration
            kb_config = {
                'name': node.name,
                'model': node.model,
                'embed_model': node.embed_model,
                'chunk_size': node.chunk_size,
                'chunk_overlap': node.chunk_overlap,
                'sources': sources,
                'persist': node.persist,
                'persist_path': node.persist_path,
                'rebuild': node.rebuild
            }

            # Create/load knowledge base
            result = self.services.knowledge.create(kb_config)

            # Store knowledge base reference
            exec_context.set_variable(node.name, result, scope="component")
            exec_context.set_variable(f"{node.name}_info", {
                'success': True,
                'name': node.name,
                'sources': len(sources),
                'documents': result.get('document_count', 0),
                'chunks': result.get('chunk_count', 0)
            }, scope="component")

            return result

        except Exception as e:
            exec_context.set_variable(f"{node.name}_info", {
                'success': False,
                'error': str(e),
                'name': node.name
            }, scope="component")
            raise ExecutorError(f"Knowledge base creation error: {e}")
