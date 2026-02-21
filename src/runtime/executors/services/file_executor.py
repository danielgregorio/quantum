"""
File Executor - Execute q:file statements

Handles file upload and delete operations.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError
from core.ast_nodes import FileNode


class FileExecutor(BaseExecutor):
    """
    Executor for q:file statements.

    Supports:
    - File upload with conflict handling
    - File deletion
    - Result storage in context
    """

    @property
    def handles(self) -> List[Type]:
        return [FileNode]

    def execute(self, node: FileNode, exec_context) -> Any:
        """
        Execute file operation.

        Args:
            node: FileNode with file operation configuration
            exec_context: Execution context

        Returns:
            File operation result dict
        """
        try:
            context = exec_context.get_all_variables()

            if node.action == 'upload':
                return self._execute_upload(node, context, exec_context)
            elif node.action == 'delete':
                return self._execute_delete(node, context, exec_context)
            else:
                raise ExecutorError(f"Unsupported file action: {node.action}")

        except Exception as e:
            raise ExecutorError(f"File execution error: {e}")

    def _execute_upload(self, node: FileNode, context: Dict[str, Any], exec_context) -> Dict:
        """Execute file upload"""
        # Resolve file variable
        file_var = node.file.strip('{}')
        file_obj = context.get(file_var)

        if not file_obj:
            raise ExecutorError(f"File variable '{file_var}' not found")

        # Resolve destination
        destination = self.apply_databinding(node.destination, context)

        # Upload file
        result = self.services.file_upload.upload_file(
            file=file_obj,
            destination=destination,
            name_conflict=node.name_conflict
        )

        # Store results
        if node.result:
            exec_context.set_variable(node.result, result, scope="component")

        exec_context.set_variable(f"{file_var}_upload", result, scope="component")

        return result

    def _execute_delete(self, node: FileNode, context: Dict[str, Any], exec_context) -> Dict:
        """Execute file deletion"""
        # Resolve filepath
        filepath = self.apply_databinding(node.file, context)

        # Delete file
        result = self.services.file_upload.delete_file(filepath)

        # Store result
        if node.result:
            exec_context.set_variable(node.result, result, scope="component")

        return result
