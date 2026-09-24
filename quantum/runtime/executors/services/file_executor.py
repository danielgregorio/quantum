"""
File Executor - Execute q:file statements

Handles file upload and delete operations.
"""

import mimetypes
from typing import Any, List, Dict, Type
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.runtime.executors.control_flow.redirect_executor import PageRedirect
from quantum.core.ast_nodes import FileNode


class PageFile(PageRedirect):
    """Raised by q:file action="send" (FILE-2): the response is this file.

    A kind of PageRedirect, so every place that ends a page with a redirect
    (guards, actions, the page, the markup) ends it with the file the same
    way. `path` None means there is no such file: the answer is 404.
    """

    def __init__(self, path, name: str = None, mimetype: str = None):
        BaseException.__init__(self, str(path))
        self.path, self.name, self.mimetype = path, name, mimetype
        self.url, self.status, self.flash, self.flash_type = None, 200, None, None


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
            elif node.action == 'send':
                self._execute_send(node, context)
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
        # FILE-1: a folder under paths.uploads; without one, paths.uploads itself.
        destination = self.apply_databinding(node.destination, context) if node.destination else '.'

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

    def _execute_send(self, node: FileNode, context: Dict[str, Any]):
        """FILE-2: end the page with a file under paths.uploads, as a download."""
        stored = str(self.apply_databinding(node.file, context) or '')
        try:
            path = self.services.file_upload.resolve_within_root(stored)
        except Exception as exc:
            raise ExecutorError(f'<q:file action="send" file="{stored}">: {exc}') from exc
        if not path.is_file():
            raise PageFile(None)
        name = str(self.apply_databinding(node.download_name, context)) if getattr(node, 'download_name', None)             else path.name
        raise PageFile(path, name or path.name, mimetypes.guess_type(name or path.name)[0])

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
