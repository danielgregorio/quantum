"""
Mail Executor - Execute q:mail statements

Handles email sending with HTML/text support.
"""

from typing import Any, List, Type
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.core.ast_nodes import MailNode


class MailExecutor(BaseExecutor):
    """
    Executor for q:mail statements.

    Supports:
    - HTML and plain text emails
    - CC, BCC, Reply-To
    - Attachments
    - Databinding in all fields
    """

    @property
    def handles(self) -> List[Type]:
        return [MailNode]

    def execute(self, node: MailNode, exec_context) -> Any:
        """
        Execute email sending.

        Args:
            node: MailNode with email configuration
            exec_context: Execution context

        Returns:
            Email send result dict
        """
        try:
            context = exec_context.get_all_variables()

            # Resolve all email properties
            to = self.apply_databinding(node.to, context)
            subject = self.apply_databinding(node.subject, context)
            body = self.apply_databinding(node.body, context)

            from_addr = None
            if node.from_addr:
                from_addr = self.apply_databinding(node.from_addr, context)

            cc = None
            if node.cc:
                cc = self.apply_databinding(node.cc, context)

            bcc = None
            if node.bcc:
                bcc = self.apply_databinding(node.bcc, context)

            reply_to = None
            if node.reply_to:
                reply_to = self.apply_databinding(node.reply_to, context)

            # Send email
            result = self.services.email.send_email(
                to=to,
                subject=subject,
                body=body,
                from_addr=from_addr,
                cc=cc,
                bcc=bcc,
                reply_to=reply_to,
                email_type=node.type,
                attachments=node.attachments
            )

        except Exception as e:
            from quantum.core.expressions import ExpressionError
            if isinstance(e, ExpressionError) or getattr(node, 'on_error', 'fail') != 'continue':
                # A page that cannot be evaluated is the page's bug, not a mail failure.
                raise ExecutorError(f"Mail execution error: {e}. Add onerror=\"continue\" to handle "
                                    f"a failure on the page (MAIL-2)" if not isinstance(e, ExpressionError)
                                    else f"Mail execution error: {e}")
            result = {'success': False, 'error': {'message': str(e)}}

        exec_context.set_variable(f"{getattr(node, 'name', None) or 'mail'}_result", result, scope="component")
        return result
