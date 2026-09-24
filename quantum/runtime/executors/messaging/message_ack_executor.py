"""
Executors for q:messageAck and q:messageNack.

These nodes parsed and produced an AST node with NO executor registered, so
inside a `<q:subscribe ack="manual">` handler they did nothing. With manual
acknowledgement the broker waits for an ack that could never arrive, so the
message was redelivered forever — the audit's most-reported critical, and the
worst kind of silent failure: an infinite loop of side effects.

MessageQueueService already had ack() and nack(); nothing called them.
"""

from typing import Any, List, Type

from quantum.core.ast_nodes import MessageAckNode, MessageNackNode
from quantum.runtime.executors.base import BaseExecutor, ExecutorError


class MessageAckExecutor(BaseExecutor):
    """Executor for q:messageAck — acknowledge the message being handled."""

    @property
    def handles(self) -> List[Type]:
        return [MessageAckNode]

    def execute(self, node: MessageAckNode, exec_context) -> Any:
        try:
            self.services.message_queue.ack()
            return {'acknowledged': True}
        except Exception as e:
            raise ExecutorError(f"q:messageAck failed: {e}")


class MessageNackExecutor(BaseExecutor):
    """Executor for q:messageNack — reject the message being handled."""

    @property
    def handles(self) -> List[Type]:
        return [MessageNackNode]

    def execute(self, node: MessageNackNode, exec_context) -> Any:
        # requeue defaults to True: rejecting without requeueing silently
        # drops the message, which should be the explicit choice.
        requeue = getattr(node, 'requeue', True)
        if isinstance(requeue, str):
            requeue = requeue.strip().lower() not in ('false', '0', 'no', 'off')
        try:
            self.services.message_queue.nack(requeue=bool(requeue))
            return {'acknowledged': False, 'requeued': bool(requeue)}
        except Exception as e:
            raise ExecutorError(f"q:messageNack failed: {e}")
