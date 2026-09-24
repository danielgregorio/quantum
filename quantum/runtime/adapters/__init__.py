"""
Message Broker Adapters

Provides implementations of MessageBroker for different backends:
- MemoryAdapter: In-memory implementation for testing and development
- RedisAdapter: Redis pub/sub and list-based queues
- RabbitMQAdapter: Full-featured AMQP implementation

Redis and RabbitMQ adapters are imported lazily to avoid blocking
startup when their dependencies (pika, redis) are slow to load.
"""

from .memory_adapter import MemoryAdapter


def _get_redis_adapter():
    """Lazily import RedisAdapter."""
    try:
        from .redis_adapter import RedisAdapter
        return RedisAdapter
    except ImportError:
        return None


def _get_rabbitmq_adapter():
    """Lazily import RabbitMQAdapter."""
    try:
        from .rabbitmq_adapter import RabbitMQAdapter
        return RabbitMQAdapter
    except ImportError:
        return None


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
    elif adapter_type == 'sqlite':
        # The durable, server-less broker. It existed but was reachable only
        # from `quantum mq`: MESSAGE_BROKER_TYPE=sqlite raised "Unknown
        # adapter type", so the documented way to ask for it did not work.
        from quantum.runtime.adapters.sqlite_adapter import SqliteAdapter
        return SqliteAdapter()
    elif adapter_type == 'redis':
        RedisAdapter = _get_redis_adapter()
        if RedisAdapter is None:
            raise ImportError(
                "Redis adapter requires 'redis' package. "
                "Install with: pip install redis"
            )
        return RedisAdapter()
    elif adapter_type == 'rabbitmq':
        RabbitMQAdapter = _get_rabbitmq_adapter()
        if RabbitMQAdapter is None:
            raise ImportError(
                "RabbitMQ adapter requires 'pika' package. "
                "Install with: pip install pika"
            )
        return RabbitMQAdapter()
    else:
        raise ValueError(
            f"Unknown adapter type: {adapter_type}. "
            f"Known: memory, sqlite, redis, rabbitmq"
        )


def __getattr__(name):
    """Lazy access to RedisAdapter and RabbitMQAdapter by name."""
    if name == 'RedisAdapter':
        return _get_redis_adapter()
    if name == 'RabbitMQAdapter':
        return _get_rabbitmq_adapter()
    raise AttributeError(f"module 'runtime.adapters' has no attribute {name!r}")


__all__ = ['MemoryAdapter', 'RedisAdapter', 'RabbitMQAdapter', 'get_adapter']
