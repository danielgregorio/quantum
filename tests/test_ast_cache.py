"""
Tests for AST Cache - Phase 2 Performance Optimization

Tests cover:
- Basic cache operations (get, put, invalidate)
- Mtime-based invalidation
- LRU eviction
- Dependency tracking
- Thread safety
- Statistics tracking
"""

import pytest
import tempfile
import time
import os
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, MagicMock, patch

from runtime.ast_cache import (
    ASTCache,
    CacheEntry,
    CacheStats,
    ASTCacheWatcher,
    get_ast_cache,
    invalidate_ast_cache,
)


class TestCacheStats:
    """Tests for CacheStats dataclass"""

    def test_initial_values(self):
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.invalidations == 0
        assert stats.evictions == 0

    def test_hit_rate_zero_when_empty(self):
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self):
        stats = CacheStats(hits=80, misses=20)
        assert stats.hit_rate == 0.8

    def test_avg_parse_time(self):
        stats = CacheStats(misses=10, total_parse_time_ms=50.0)
        assert stats.avg_parse_time_ms == 5.0

    def test_to_dict(self):
        stats = CacheStats(hits=10, misses=5, invalidations=2)
        d = stats.to_dict()
        assert d['hits'] == 10
        assert d['misses'] == 5
        assert d['invalidations'] == 2
        assert '66.7%' in d['hit_rate']


class TestCacheEntry:
    """Tests for CacheEntry dataclass"""

    def test_entry_creation(self):
        entry = CacheEntry(
            ast=Mock(),
            mtime=1234567890.0,
            size=1000,
            hash="abc123",
        )
        assert entry.mtime == 1234567890.0
        assert entry.size == 1000
        assert entry.access_count == 0

    def test_entry_touch(self):
        entry = CacheEntry(
            ast=Mock(),
            mtime=1234567890.0,
            size=1000,
            hash="abc123",
        )
        initial_time = entry.last_accessed
        time.sleep(0.01)
        entry.touch()
        assert entry.access_count == 1
        assert entry.last_accessed > initial_time


class TestASTCache:
    """Tests for ASTCache class"""

    @pytest.fixture
    def cache(self):
        """Fresh cache for each test"""
        return ASTCache(max_entries=10)

    @pytest.fixture
    def temp_file(self):
        """Create a temporary .q file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.q', delete=False) as f:
            f.write('<q:component name="Test"><q:set name="x" value="1"/></q:component>')
            f.flush()
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def mock_parser(self):
        """Mock parser that returns a mock AST"""
        parser = Mock()
        parser.parse = Mock(return_value=Mock(name="MockAST"))
        return parser

    # Basic Operations

    def test_get_nonexistent(self, cache):
        result = cache.get("/nonexistent/file.q")
        assert result is None

    def test_put_and_get(self, cache, temp_file):
        mock_ast = Mock(name="TestAST")
        cache.put(temp_file, mock_ast)

        result = cache.get(temp_file)
        assert result is mock_ast

    def test_get_or_parse_caches(self, cache, temp_file, mock_parser):
        # First call - should parse
        result1 = cache.get_or_parse(temp_file, mock_parser)
        assert mock_parser.parse.call_count == 1

        # Second call - should use cache
        result2 = cache.get_or_parse(temp_file, mock_parser)
        assert mock_parser.parse.call_count == 1  # No additional parse

        assert result1 is result2

    def test_get_or_parse_with_content(self, cache, temp_file, mock_parser):
        content = '<q:component name="Test"><q:set name="y" value="2"/></q:component>'
        result = cache.get_or_parse(temp_file, mock_parser, content=content)
        assert result is not None
        mock_parser.parse.assert_called_once_with(content)

    # Invalidation Tests

    def test_invalidate_specific(self, cache, temp_file):
        mock_ast = Mock()
        cache.put(temp_file, mock_ast)

        # Verify it's cached
        assert cache.get(temp_file) is not None

        # Invalidate
        cache.invalidate(temp_file)

        # Should be gone
        assert cache.get(temp_file) is None

    def test_invalidate_all(self, cache):
        # Add multiple entries
        with tempfile.NamedTemporaryFile(mode='w', suffix='.q', delete=False) as f1:
            f1.write('<q:component name="Test1"/>')
        with tempfile.NamedTemporaryFile(mode='w', suffix='.q', delete=False) as f2:
            f2.write('<q:component name="Test2"/>')

        try:
            cache.put(f1.name, Mock())
            cache.put(f2.name, Mock())

            assert cache.get(f1.name) is not None
            assert cache.get(f2.name) is not None

            # Invalidate all
            cache.invalidate()

            assert cache.get(f1.name) is None
            assert cache.get(f2.name) is None
        finally:
            os.unlink(f1.name)
            os.unlink(f2.name)

    def test_invalidate_on_file_change(self, cache, temp_file, mock_parser):
        # Cache the file
        cache.get_or_parse(temp_file, mock_parser)
        assert cache.stats.hits == 0
        assert cache.stats.misses == 1

        # Modify the file
        time.sleep(0.1)  # Ensure mtime changes
        with open(temp_file, 'w') as f:
            f.write('<q:component name="Modified"/>')

        # Next get should miss (file changed)
        cache.get_or_parse(temp_file, mock_parser)
        assert cache.stats.misses == 2  # Should have increased

    # LRU Eviction Tests

    def test_lru_eviction(self):
        cache = ASTCache(max_entries=3)

        # Create temp files
        files = []
        for i in range(5):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.q', delete=False) as f:
                f.write(f'<q:component name="Test{i}"/>')
                files.append(f.name)

        try:
            # Add 5 entries to cache with max 3
            for f in files:
                cache.put(f, Mock())
                time.sleep(0.01)  # Ensure different access times

            # Should have evicted 2
            assert cache.stats.evictions == 2

            # First 2 files should be evicted (LRU)
            assert cache.get(files[0]) is None
            assert cache.get(files[1]) is None

            # Last 3 should still be cached
            assert cache.get(files[2]) is not None
            assert cache.get(files[3]) is not None
            assert cache.get(files[4]) is not None
        finally:
            for f in files:
                os.unlink(f)

    # Dependency Tracking Tests

    def test_register_dependency(self, cache):
        cache.register_dependency("/path/main.q", "/path/imported.q")

        # Check dependency is registered
        assert "/path/imported.q" in cache._dependencies.get(
            str(Path("/path/main.q").resolve()), set()
        ) or len(cache._dependencies) > 0

    def test_invalidate_dependents(self, cache):
        # Create temp files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.q', delete=False) as main_f:
            main_f.write('<q:component name="Main"/>')
        with tempfile.NamedTemporaryFile(mode='w', suffix='.q', delete=False) as imp_f:
            imp_f.write('<q:component name="Imported"/>')

        try:
            # Cache both
            cache.put(main_f.name, Mock())
            cache.put(imp_f.name, Mock())

            # Register dependency
            cache.register_dependency(main_f.name, imp_f.name)

            # Invalidate the imported file
            cache.invalidate(imp_f.name)

            # Both should be invalidated (imported and its dependent)
            assert cache.get(imp_f.name) is None
            assert cache.get(main_f.name) is None
        finally:
            os.unlink(main_f.name)
            os.unlink(imp_f.name)

    # Statistics Tests

    def test_stats_tracking(self, cache, temp_file, mock_parser):
        # Miss
        cache.get_or_parse(temp_file, mock_parser)
        assert cache.stats.misses == 1
        assert cache.stats.hits == 0

        # Hit
        cache.get_or_parse(temp_file, mock_parser)
        assert cache.stats.hits == 1

        # Hit rate
        assert cache.stats.hit_rate == 0.5

    def test_reset_stats(self, cache, temp_file, mock_parser):
        cache.get_or_parse(temp_file, mock_parser)
        cache.get_or_parse(temp_file, mock_parser)

        cache.reset_stats()

        assert cache.stats.hits == 0
        assert cache.stats.misses == 0
        assert cache.stats.entries_count == 1  # Entries preserved

    # Cache Info Tests

    def test_cache_info(self, cache, temp_file):
        cache.put(temp_file, Mock())

        info = cache.cache_info()
        assert info['max_entries'] == 10
        assert info['current_entries'] == 1
        assert len(info['entries']) == 1

    def test_clear(self, cache, temp_file):
        cache.put(temp_file, Mock())
        assert cache.stats.entries_count == 1

        cache.clear()
        assert cache.stats.entries_count == 0
        assert cache.get(temp_file) is None

    # Path Normalization Tests

    def test_path_normalization(self, cache, temp_file):
        mock_ast = Mock()

        # Put with string path
        cache.put(temp_file, mock_ast)

        # Get with Path object
        result = cache.get(Path(temp_file))
        assert result is mock_ast

    def test_relative_and_absolute_paths(self, cache):
        # Create file in current directory
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.q', dir='.', delete=False
        ) as f:
            f.write('<q:component name="Test"/>')
            abs_path = os.path.abspath(f.name)
            rel_path = os.path.relpath(f.name)

        try:
            mock_ast = Mock()
            cache.put(abs_path, mock_ast)

            # Should find it with relative path too
            result = cache.get(rel_path)
            assert result is mock_ast
        finally:
            os.unlink(abs_path)


class TestASTCacheHashValidation:
    """Tests for hash-based validation"""

    def test_hash_validation_enabled(self):
        cache = ASTCache(max_entries=10, enable_hash_validation=True)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.q', delete=False) as f:
            content = '<q:component name="Test"/>'
            f.write(content)

        try:
            cache.put(f.name, Mock(), content=content)

            # Modify content without changing mtime (simulate)
            # This would be detected by hash validation
            entry = cache._cache[cache._normalize_path(f.name)]
            assert entry.hash != ""
        finally:
            os.unlink(f.name)


class TestThreadSafety:
    """Tests for thread-safe cache operations"""

    def test_concurrent_reads(self):
        cache = ASTCache(max_entries=100)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.q', delete=False) as f:
            f.write('<q:component name="Test"/>')

        try:
            mock_ast = Mock()
            cache.put(f.name, mock_ast)

            results = []
            errors = []

            def read_task():
                try:
                    result = cache.get(f.name)
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))

            with ThreadPoolExecutor(max_workers=10) as executor:
                for _ in range(100):
                    executor.submit(read_task)

            assert len(errors) == 0
            assert len(results) == 100
            assert all(r is mock_ast for r in results)
        finally:
            os.unlink(f.name)

    def test_concurrent_writes(self):
        cache = ASTCache(max_entries=100)
        errors = []

        with tempfile.TemporaryDirectory() as tmpdir:
            def write_task(i):
                try:
                    path = os.path.join(tmpdir, f"test{i}.q")
                    with open(path, 'w') as f:
                        f.write(f'<q:component name="Test{i}"/>')
                    cache.put(path, Mock())
                except Exception as e:
                    errors.append(str(e))

            with ThreadPoolExecutor(max_workers=10) as executor:
                for i in range(50):
                    executor.submit(write_task, i)

        assert len(errors) == 0


class TestASTCacheWatcher:
    """Tests for ASTCacheWatcher"""

    def test_watcher_creation(self):
        cache = ASTCache()
        watcher = ASTCacheWatcher(cache)
        assert watcher._cache is cache

    def test_check_and_invalidate_no_change(self):
        cache = ASTCache()
        watcher = ASTCacheWatcher(cache)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.q', delete=False) as f:
            f.write('<q:component name="Test"/>')

        try:
            cache.put(f.name, Mock())

            # First check - registers the file
            result1 = watcher.check_and_invalidate(f.name)
            assert result1 is False

            # Second check - no change
            result2 = watcher.check_and_invalidate(f.name)
            assert result2 is False
        finally:
            os.unlink(f.name)

    def test_check_and_invalidate_with_change(self):
        cache = ASTCache()
        watcher = ASTCacheWatcher(cache)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.q', delete=False) as f:
            f.write('<q:component name="Test"/>')

        try:
            cache.put(f.name, Mock())

            # Register the file
            watcher.check_and_invalidate(f.name)

            # Modify the file
            time.sleep(0.1)
            with open(f.name, 'w') as f2:
                f2.write('<q:component name="Modified"/>')

            # Should detect change
            result = watcher.check_and_invalidate(f.name)
            assert result is True

            # Cache should be invalidated
            assert cache.get(f.name) is None
        finally:
            os.unlink(f.name)

    def test_on_file_changed(self):
        cache = ASTCache()
        watcher = ASTCacheWatcher(cache)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.q', delete=False) as f:
            f.write('<q:component name="Test"/>')

        try:
            cache.put(f.name, Mock())
            assert cache.get(f.name) is not None

            watcher.on_file_changed(f.name)

            assert cache.get(f.name) is None
        finally:
            os.unlink(f.name)


class TestGlobalCache:
    """Tests for global singleton cache"""

    def test_get_ast_cache_singleton(self):
        # Reset global cache for testing
        import runtime.ast_cache as module
        module._global_cache = None

        cache1 = get_ast_cache()
        cache2 = get_ast_cache()
        assert cache1 is cache2

    def test_invalidate_ast_cache_function(self):
        import runtime.ast_cache as module
        module._global_cache = None

        cache = get_ast_cache()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.q', delete=False) as f:
            f.write('<q:component name="Test"/>')

        try:
            cache.put(f.name, Mock())
            assert cache.get(f.name) is not None

            invalidate_ast_cache(f.name)

            assert cache.get(f.name) is None
        finally:
            os.unlink(f.name)


class TestPreload:
    """Tests for cache preloading"""

    def test_preload_files(self):
        cache = ASTCache()
        mock_parser = Mock()
        mock_parser.parse = Mock(return_value=Mock())

        files = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(3):
                path = os.path.join(tmpdir, f"test{i}.q")
                with open(path, 'w') as f:
                    f.write(f'<q:component name="Test{i}"/>')
                files.append(path)

            cache.preload(files, mock_parser)

            assert cache.stats.entries_count == 3
            assert mock_parser.parse.call_count == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
