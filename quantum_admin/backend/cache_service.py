"""
Redis Caching Layer for Quantum Admin
Provides distributed caching with decorators and utilities
"""
import redis
import json
import hashlib
import functools
import logging
from typing import Any, Callable, Optional, Union
from datetime import timedelta

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis-based caching service with decorator support

    Features:
    - Automatic key generation from function args
    - TTL (Time-To-Live) support
    - Namespace isolation
    - JSON serialization
    - Cache invalidation
    - Stats tracking
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "quantum:"
    ):
        self.prefix = prefix
        self.stats = {"hits": 0, "misses": 0, "errors": 0}

        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info(f"Redis cache connected: {host}:{port}")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis unavailable, caching disabled: {e}")
            self.redis_client = None
            self.enabled = False

    def _generate_key(self, namespace: str, *args, **kwargs) -> str:
        """Generate cache key from namespace and arguments"""
        key_parts = [self.prefix, namespace]

        # Add args
        if args:
            key_parts.append(str(args))

        # Add sorted kwargs
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append(str(sorted_kwargs))

        # Create hash for long keys
        key_str = ":".join(key_parts)
        if len(key_str) > 200:
            key_hash = hashlib.md5(key_str.encode()).hexdigest()
            return f"{self.prefix}{namespace}:{key_hash}"

        return key_str

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled:
            return None

        try:
            value = self.redis_client.get(key)
            if value is None:
                self.stats["misses"] += 1
                return None

            self.stats["hits"] += 1
            return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.stats["errors"] += 1
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """Set value in cache with optional TTL"""
        if not self.enabled:
            return False

        try:
            serialized = json.dumps(value)

            if ttl:
                if isinstance(ttl, timedelta):
                    ttl = int(ttl.total_seconds())
                self.redis_client.setex(key, ttl, serialized)
            else:
                self.redis_client.set(key, serialized)

            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self.stats["errors"] += 1
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled:
            return False

        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            self.stats["errors"] += 1
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.enabled:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            self.stats["errors"] += 1
            return 0

    def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in namespace"""
        pattern = f"{self.prefix}{namespace}:*"
        return self.delete_pattern(pattern)

    def clear_all(self) -> bool:
        """Clear all cache (use with caution!)"""
        if not self.enabled:
            return False

        try:
            self.redis_client.flushdb()
            return True
        except Exception as e:
            logger.error(f"Cache clear all error: {e}")
            return False

    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            self.stats["hits"] / total_requests * 100
            if total_requests > 0
            else 0
        )

        info = {}
        if self.enabled:
            try:
                info = self.redis_client.info("stats")
            except Exception:
                pass

        return {
            "enabled": self.enabled,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "errors": self.stats["errors"],
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests,
            "redis_info": info
        }

    def cached(
        self,
        namespace: str,
        ttl: Optional[Union[int, timedelta]] = 300
    ) -> Callable:
        """
        Decorator for caching function results

        Usage:
            @cache.cached("users", ttl=600)
            def get_user(user_id: int):
                return db.query(User).filter(User.id == user_id).first()
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_key(namespace, *args, **kwargs)

                # Try to get from cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return cached_value

                # Execute function
                logger.debug(f"Cache MISS: {cache_key}")
                result = func(*args, **kwargs)

                # Store in cache
                self.set(cache_key, result, ttl)

                return result

            # Add cache control methods to function
            wrapper.cache_clear = lambda: self.clear_namespace(namespace)
            wrapper.cache_key = lambda *args, **kwargs: self._generate_key(
                namespace, *args, **kwargs
            )

            return wrapper
        return decorator


# Global cache instance (singleton)
_cache_instance: Optional[CacheService] = None


def get_cache() -> CacheService:
    """Get or create cache service instance"""
    global _cache_instance

    if _cache_instance is None:
        import os
        _cache_instance = CacheService(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD"),
            prefix=os.getenv("REDIS_PREFIX", "quantum:")
        )

    return _cache_instance


# Convenience decorator
def cached(namespace: str, ttl: Optional[Union[int, timedelta]] = 300):
    """Convenience decorator using global cache instance"""
    cache = get_cache()
    return cache.cached(namespace, ttl)


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Initialize cache
    cache = CacheService()

    # Basic operations
    cache.set("user:1", {"name": "John", "email": "john@example.com"}, ttl=60)
    user = cache.get("user:1")
    print(f"User: {user}")

    # Using decorator
    @cached("expensive_query", ttl=600)
    def expensive_query(param: str):
        print(f"Executing expensive query with param: {param}")
        return {"result": f"data for {param}"}

    # First call - cache miss
    result1 = expensive_query("test")

    # Second call - cache hit
    result2 = expensive_query("test")

    # Stats
    stats = cache.get_stats()
    print(f"\nCache Stats: {stats}")
