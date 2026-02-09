"""
Message Broker Adapters

Provides implementations of MessageBroker for different backends:
- MemoryAdapter: In-memory implementation for testing and development
- RedisAdapter: Redis pub/sub and list-based queues
- RabbitMQAdapter: Full-featured AMQP implementation
"""

from .memory_adapter import MemoryAdapter

# Optional imports - only if dependencies are available
try:
    from .redis_adapter import RedisAdapter
except ImportError:
    RedisAdapter = None

try:
    from .rabbitmq_adapter import RabbitMQAdapter
except ImportError:
    RabbitMQAdapter = None


def get_adapter(adapter_type: str = 'memory'):
    """
    Factory function to get the appropriate message broker adapter.

    Args:
        adapter_type: 'memory', 'redis', or 'rabbitmq'

    Returns:
        MessageBroker instance

    Raises:
        ImportError: If required dependencies are not installed
        ValueError: If adapter_type is not recognized
    """
    if adapter_type == 'memory':
        return MemoryAdapter()
    elif adapter_type == 'redis':
        if RedisAdapter is None:
            raise ImportError(
                "Redis adapter requires 'redis' package. "
                "Install with: pip install redis"
            )
        return RedisAdapter()
    elif adapter_type == 'rabbitmq':
        if RabbitMQAdapter is None:
            raise ImportError(
                "RabbitMQ adapter requires 'pika' package. "
                "Install with: pip install pika"
            )
        return RabbitMQAdapter()
    else:
        raise ValueError(f"Unknown adapter type: {adapter_type}")


__all__ = ['MemoryAdapter', 'RedisAdapter', 'RabbitMQAdapter', 'get_adapter']
