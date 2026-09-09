"""
Message Executor - Execute q:message statements

Handles message queue publish/send/request operations.
"""

from typing import Any, List, Dict, Type
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.core.ast_nodes import MessageNode, SubscribeNode


class MessageExecutor(BaseExecutor):
    """
    Executor for q:message statements.

    Supports:
    - Pub/Sub (publish to topic)
    - Direct queue send
    - Request/reply pattern
    - Message headers
    """

    @property
    def handles(self) -> List[Type]:
        return [MessageNode]

    def execute(self, node: MessageNode, exec_context) -> Any:
        """
        Execute message publish/send.

        Args:
            node: MessageNode with message configuration
            exec_context: Execution context

        Returns:
            Message operation result dict
        """
        try:
            context = exec_context.get_all_variables()

            # Resolve body
            body = None
            if node.body:
                body = self.apply_databinding(node.body, context)

            # Resolve headers
            headers = {}
            for header in node.headers:
                header_name = header.name
                header_value = self.apply_databinding(header.value, context)
                headers[header_name] = header_value

            # Resolve target
            topic = None
            queue = None
            if node.topic:
                topic = self.apply_databinding(node.topic, context)
            if node.queue:
                queue = self.apply_databinding(node.queue, context)

            # Execute based on message type
            if node.type == 'publish':
                result = self.services.message_queue.publish(
                    topic=topic,
                    body=body,
                    headers=headers
                )
            elif node.type == 'send':
                result = self.services.message_queue.send(
                    queue=queue,
                    body=body,
                    headers=headers
                )
            elif node.type == 'request':
                timeout = int(node.timeout) if node.timeout else 30000
                result = self.services.message_queue.request(
                    queue=queue,
                    body=body,
                    headers=headers,
                    timeout=timeout
                )
            else:
                raise ExecutorError(f"Unknown message type: {node.type}")

            # Store result
            if node.name:
                exec_context.set_variable(node.name, result, scope="component")

            return result

        except Exception as e:
            if node.name:
                exec_context.set_variable(node.name, {
                    'success': False,
                    'error': str(e)
                }, scope="component")
            raise ExecutorError(f"Message operation error: {e}")


class SubscribeExecutor(BaseExecutor):
    """
    Executor for q:subscribe statements.

    Subscribes to topics or queues and handles incoming messages.
    """

    @property
    def handles(self) -> List[Type]:
        return [SubscribeNode]

    def execute(self, node: SubscribeNode, exec_context) -> Any:
        """
        Execute subscription setup.

        Args:
            node: SubscribeNode with subscription configuration
            exec_context: Execution context

        Returns:
            Subscription info dict
        """
        try:
            context = exec_context.get_all_variables()

            # Resolve topics/queue
            topics = []
            if node.topic:
                topics = [self.apply_databinding(node.topic, context)]
            elif node.topics:
                topics_str = self.apply_databinding(node.topics, context)
                topics = [t.strip() for t in topics_str.split(',')]

            queue = None
            if node.queue:
                queue = self.apply_databinding(node.queue, context)

            # MessageQueueService.subscribe() takes a single `handler`
            # callable, not a handlers config dict, and `topics` as a
            # comma-separated string.
            on_message_body = node.on_message
            on_error_body = node.on_error

            def handle_message(message):
                payload = message if isinstance(message, dict) else {'message': message}
                try:
                    return self.run_body_in_child_context(on_message_body, payload)
                except Exception as exc:  # noqa: BLE001 - routed to on_error body
                    if on_error_body:
                        return self.run_body_in_child_context(
                            on_error_body, {**payload, 'error': str(exc)}
                        )
                    raise

            # Create subscription
            result = self.services.message_queue.subscribe(
                name=node.name,
                topics=','.join(topics) if topics else None,
                queue=queue,
                handler=handle_message,
                ack=node.ack,
                prefetch=node.prefetch,
            )

            # Store subscription reference
            exec_context.set_variable(node.name, result, scope="component")

            return result

        except Exception as e:
            exec_context.set_variable(node.name, {
                'active': False,
                'error': str(e)
            }, scope="component")
            raise ExecutorError(f"Subscription error: {e}")
