"""
Quantum LLM Cache - TTL cache for q:llm responses.

q:llm has carried a `cache` attribute since it was written, wired to nothing.
LLM calls are the slowest and most expensive thing a Quantum component can do,
so a cache is not a nicety — a repeated prompt during development costs seconds
and, on a paid provider, money.

Keyed on everything that can change the answer: provider, model, endpoint, the
full message list (or prompt+system), temperature, max_tokens and the requested
response format. Two calls that differ in any of those are different calls.
"""

import hashlib
import json
import threading
import time
from typing import Any, Dict, Optional


class LLMCache:
    """In-process TTL cache for LLM responses."""

    def __init__(self, max_entries: int = 500):
        self._entries: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self.max_entries = max_entries
        self.hits = 0
        self.misses = 0

    @staticmethod
    def build_key(**parts: Any) -> str:
        """Build a stable key from the call's distinguishing parameters."""
        payload = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Return a cached response, or None if absent or expired."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self.misses += 1
                return None

            expires_at = entry['expires_at']
            if expires_at is not None and time.time() > expires_at:
                del self._entries[key]
                self.misses += 1
                return None

            self.hits += 1
            # Copy so a caller mutating the result cannot poison the cache
            return dict(entry['value'])

    def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None):
        """Store a response. ttl in seconds; None means no expiry."""
        with self._lock:
            if len(self._entries) >= self.max_entries:
                # Evict the entry closest to expiry (None sorts last)
                oldest = min(
                    self._entries.items(),
                    key=lambda kv: (kv[1]['expires_at'] is None, kv[1]['expires_at'] or 0),
                )
                del self._entries[oldest[0]]

            self._entries[key] = {
                'value': dict(value),
                'expires_at': (time.time() + ttl) if ttl else None,
            }

    def clear(self):
        with self._lock:
            self._entries.clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self.hits + self.misses
            return {
                'entries': len(self._entries),
                'hits': self.hits,
                'misses': self.misses,
                'hitRate': round(self.hits / total, 4) if total else 0.0,
            }


_llm_cache: Optional[LLMCache] = None


def get_llm_cache() -> LLMCache:
    """Get the process-wide LLM cache."""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache()
    return _llm_cache


def reset_llm_cache():
    """Reset the global cache (for tests)."""
    global _llm_cache
    _llm_cache = None
