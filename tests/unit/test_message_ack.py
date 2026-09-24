"""
q:messageAck and q:messageNack parsed and then did nothing.

Both produced an AST node with NO executor registered. Inside a
`<q:subscribe ack="manual">` handler the broker waits for an acknowledgement
that could never arrive, so the message was redelivered forever — an infinite
loop of side effects, and the audit's most-reported critical (4 dimensions).

MessageQueueService already had ack() and nack(). Nothing called them.
"""

import io
import contextlib
from unittest.mock import MagicMock

import pytest

from quantum.core.ast_nodes import MessageAckNode, MessageNackNode
from quantum.runtime.component import ComponentRuntime


@pytest.fixture
def runtime():
    with contextlib.redirect_stdout(io.StringIO()):
        return ComponentRuntime()


class TestExecutorsAreRegistered:
    @pytest.mark.parametrize("cls", [MessageAckNode, MessageNackNode])
    def test_registered(self, runtime, cls):
        assert runtime._executor_registry.can_execute(cls.__new__(cls)) is True


class TestTheyReachTheService:
    def _run(self, runtime, node):
        fake = MagicMock()
        runtime._services._services['message_queue'] = fake
        result = runtime._executor_registry.execute(node, runtime.execution_context)
        return fake, result

    def test_ack_calls_ack(self, runtime):
        fake, result = self._run(runtime, MessageAckNode())
        fake.ack.assert_called_once_with()
        assert result["acknowledged"] is True

    def test_nack_requeues_by_default(self, runtime):
        """Rejecting without requeueing silently drops the message, so that
        has to be the explicit choice."""
        fake, result = self._run(runtime, MessageNackNode())
        fake.nack.assert_called_once_with(requeue=True)
        assert result["requeued"] is True

    @pytest.mark.parametrize("raw,expected", [
        ("false", False), ("FALSE", False), ("0", False), ("no", False),
        ("true", True), ("yes", True), (True, True), (False, False),
    ])
    def test_nack_requeue_attribute_is_honoured(self, runtime, raw, expected):
        node = MessageNackNode()
        node.requeue = raw
        fake, result = self._run(runtime, node)
        fake.nack.assert_called_once_with(requeue=expected)


class TestTheServiceReallyHasThoseMethods:
    """The bug class this project keeps producing is an executor calling a
    method the real service does not have. Check against the real class."""

    def test_ack_and_nack_exist(self):
        from quantum.runtime.message_queue_service import MessageQueueService
        assert callable(getattr(MessageQueueService, "ack", None))
        assert callable(getattr(MessageQueueService, "nack", None))
