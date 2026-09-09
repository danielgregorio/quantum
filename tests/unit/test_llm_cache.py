"""
Tests for the q:llm TTL cache.

The `cache` attribute existed on q:llm from the start, wired to nothing —
the audit removed the false promise, and Fase 3 of FRAMEWORK_PLAN.md made it
real. LLM calls are the slowest and most expensive thing a component does, so
the cache's correctness matters: a key collision would serve the wrong answer.
"""

import time

import pytest

from quantum.runtime.llm_cache import LLMCache, get_llm_cache, reset_llm_cache


@pytest.fixture(autouse=True)
def _clean_global_cache():
    reset_llm_cache()
    yield
    reset_llm_cache()


class TestKeying:
    def test_same_parameters_produce_the_same_key(self):
        a = LLMCache.build_key(model="phi3", prompt="hi", temperature=0.5)
        b = LLMCache.build_key(temperature=0.5, prompt="hi", model="phi3")
        assert a == b, "key must not depend on argument order"

    def test_any_differing_parameter_changes_the_key(self):
        base = dict(provider="ollama", model="phi3", prompt="hi", temperature=0.5)
        baseline = LLMCache.build_key(**base)

        for field, other in [
            ("provider", "openai"),
            ("model", "llama3"),
            ("prompt", "hello"),
            ("temperature", 0.9),
        ]:
            changed = dict(base)
            changed[field] = other
            assert LLMCache.build_key(**changed) != baseline, (
                f"changing {field} must produce a different cache key"
            )


class TestStorage:
    def test_miss_then_hit(self):
        cache = LLMCache()
        key = LLMCache.build_key(prompt="x")

        assert cache.get(key) is None
        cache.set(key, {"data": "answer"})
        assert cache.get(key)["data"] == "answer"

    def test_returns_a_copy_so_callers_cannot_poison_it(self):
        cache = LLMCache()
        key = LLMCache.build_key(prompt="x")
        cache.set(key, {"data": "answer"})

        got = cache.get(key)
        got["data"] = "mutated"

        assert cache.get(key)["data"] == "answer"

    def test_ttl_expires(self):
        cache = LLMCache()
        key = LLMCache.build_key(prompt="x")
        cache.set(key, {"data": "answer"}, ttl=1)

        assert cache.get(key) is not None
        time.sleep(1.1)
        assert cache.get(key) is None

    def test_no_ttl_means_no_expiry(self):
        cache = LLMCache()
        key = LLMCache.build_key(prompt="x")
        cache.set(key, {"data": "answer"}, ttl=None)

        time.sleep(0.05)
        assert cache.get(key) is not None

    def test_eviction_keeps_the_cache_bounded(self):
        cache = LLMCache(max_entries=3)
        for i in range(5):
            cache.set(LLMCache.build_key(prompt=f"p{i}"), {"data": str(i)}, ttl=60)

        assert len(cache._entries) <= 3


class TestStats:
    def test_hit_rate(self):
        cache = LLMCache()
        key = LLMCache.build_key(prompt="x")

        cache.get(key)              # miss
        cache.set(key, {"data": "a"})
        cache.get(key)              # hit

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hitRate"] == 0.5


class TestGlobalInstance:
    def test_singleton(self):
        assert get_llm_cache() is get_llm_cache()

    def test_reset(self):
        first = get_llm_cache()
        reset_llm_cache()
        assert get_llm_cache() is not first
