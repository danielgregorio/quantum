"""
Redirect Executor - q:redirect outside a q:action (ACT-7)

Inside a q:action the ActionHandler ends the action itself. Anywhere else —
the page's statements, a guard, a q:function — q:redirect ends the page:
nothing after it runs and the response is the redirect. It used to be skipped
silently, so `<q:if condition="not session.authenticated"><q:redirect .../>`
rendered the page it was meant to protect.
"""

from typing import Any, List, Type

from quantum.core.ast_nodes import RedirectNode
from quantum.runtime.executors.base import BaseExecutor


class PageRedirect(BaseException):
    """Raised by q:redirect to end the page; the web server turns it into the response.

    A BaseException, like GeneratorExit: the layers between an executor and
    the server catch `Exception` to report errors, and a redirect is not one.
    """

    def __init__(self, url: str, status: int = 302, flash: str = None, flash_type: str = None):
        super().__init__(url)
        self.url = url
        self.status = status
        self.flash = flash
        self.flash_type = flash_type or 'success'


class RedirectExecutor(BaseExecutor):
    """Executor for q:redirect outside a q:action."""

    @property
    def handles(self) -> List[Type]:
        return [RedirectNode]

    def execute(self, node: RedirectNode, exec_context) -> Any:
        context = exec_context.get_all_variables()
        url = str(self.apply_databinding(node.url, context))
        flash = str(self.apply_databinding(node.flash, context)) if node.flash else None
        raise PageRedirect(url, node.status, flash, getattr(node, 'flash_type', None))
