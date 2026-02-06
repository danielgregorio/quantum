"""
Tests for Quantum Data Fetching Feature

Tests:
- FetchNode AST nodes
- Fetch parser
- HTML adapter for fetch
"""

import pytest
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from unittest.mock import MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.features.data_fetching.src.ast_node import (
    FetchNode,
    FetchHeaderNode,
    FetchLoadingNode,
    FetchErrorNode,
    FetchSuccessNode,
)
from core.features.data_fetching.src.parser import (
    parse_fetch,
    FetchParseError,
)
from core.features.data_fetching.src.html_adapter import (
    FetchHtmlAdapter,
    FETCH_STATE_JS,
    FETCH_CSS,
)


# ============================================
# FetchHeaderNode Tests
# ============================================

class TestFetchHeaderNode:
    """Test FetchHeaderNode."""

    def test_create_header(self):
        """Test creating a header node."""
        header = FetchHeaderNode(name="Authorization", value="Bearer token123")
        assert header.name == "Authorization"
        assert header.value == "Bearer token123"

    def test_validate_valid(self):
        """Test validation passes for valid header."""
        header = FetchHeaderNode(name="Content-Type", value="application/json")
        errors = header.validate()
        assert errors == []

    def test_validate_missing_name(self):
        """Test validation fails for missing name."""
        header = FetchHeaderNode(name="", value="value")
        errors = header.validate()
        assert any("name" in e.lower() for e in errors)

    def test_validate_missing_value(self):
        """Test validation fails for missing value."""
        header = FetchHeaderNode(name="Header", value=None)
        errors = header.validate()
        assert any("value" in e.lower() for e in errors)

    def test_to_dict(self):
        """Test serialization to dict."""
        header = FetchHeaderNode(name="X-Custom", value="test")
        d = header.to_dict()
        assert d['type'] == 'fetch_header'
        assert d['name'] == 'X-Custom'

    def test_to_dict_truncates_long_value(self):
        """Test long values are truncated in dict."""
        long_value = "x" * 100
        header = FetchHeaderNode(name="Header", value=long_value)
        d = header.to_dict()
        assert "..." in d['value']


# ============================================
# FetchLoadingNode Tests
# ============================================

class TestFetchLoadingNode:
    """Test FetchLoadingNode."""

    def test_create_loading(self):
        """Test creating a loading node."""
        loading = FetchLoadingNode()
        assert loading.children == []

    def test_add_child(self):
        """Test adding children."""
        loading = FetchLoadingNode()
        child = MagicMock()
        loading.add_child(child)
        assert len(loading.children) == 1
        assert loading.children[0] is child

    def test_to_dict(self):
        """Test serialization."""
        loading = FetchLoadingNode()
        loading.add_child(MagicMock())
        loading.add_child(MagicMock())
        d = loading.to_dict()
        assert d['type'] == 'fetch_loading'
        assert d['children_count'] == 2

    def test_validate_with_children(self):
        """Test validation validates children."""
        loading = FetchLoadingNode()
        child = MagicMock()
        child.validate.return_value = ['child error']
        loading.add_child(child)

        errors = loading.validate()
        assert 'child error' in errors


# ============================================
# FetchErrorNode Tests
# ============================================

class TestFetchErrorNode:
    """Test FetchErrorNode."""

    def test_create_error(self):
        """Test creating an error node."""
        error = FetchErrorNode()
        assert error.children == []

    def test_add_child(self):
        """Test adding children."""
        error = FetchErrorNode()
        child = MagicMock()
        error.add_child(child)
        assert len(error.children) == 1

    def test_to_dict(self):
        """Test serialization."""
        error = FetchErrorNode()
        d = error.to_dict()
        assert d['type'] == 'fetch_error'


# ============================================
# FetchSuccessNode Tests
# ============================================

class TestFetchSuccessNode:
    """Test FetchSuccessNode."""

    def test_create_success(self):
        """Test creating a success node."""
        success = FetchSuccessNode()
        assert success.children == []

    def test_add_child(self):
        """Test adding children."""
        success = FetchSuccessNode()
        child = MagicMock()
        success.add_child(child)
        assert len(success.children) == 1

    def test_to_dict(self):
        """Test serialization."""
        success = FetchSuccessNode()
        d = success.to_dict()
        assert d['type'] == 'fetch_success'


# ============================================
# FetchNode Tests
# ============================================

class TestFetchNode:
    """Test FetchNode."""

    def test_create_basic(self):
        """Test creating a basic fetch node."""
        fetch = FetchNode(name="users", url="/api/users")
        assert fetch.name == "users"
        assert fetch.url == "/api/users"
        assert fetch.method == "GET"
        assert fetch.timeout == 30000

    def test_default_values(self):
        """Test default values."""
        fetch = FetchNode(name="test", url="/api")
        assert fetch.headers == []
        assert fetch.body is None
        assert fetch.cache is None
        assert fetch.interval is None
        assert fetch.retry == 0
        assert fetch.content_type == "application/json"
        assert fetch.response_format == "auto"
        assert fetch.abort_on_unmount is True
        assert fetch.lazy is False
        assert fetch.loading_node is None
        assert fetch.error_node is None
        assert fetch.success_node is None

    def test_add_header(self):
        """Test adding headers."""
        fetch = FetchNode(name="test", url="/api")
        header = FetchHeaderNode(name="Auth", value="token")
        fetch.add_header(header)
        assert len(fetch.headers) == 1

    def test_set_loading(self):
        """Test setting loading node."""
        fetch = FetchNode(name="test", url="/api")
        loading = FetchLoadingNode()
        fetch.set_loading(loading)
        assert fetch.loading_node is loading

    def test_set_error(self):
        """Test setting error node."""
        fetch = FetchNode(name="test", url="/api")
        error = FetchErrorNode()
        fetch.set_error(error)
        assert fetch.error_node is error

    def test_set_success(self):
        """Test setting success node."""
        fetch = FetchNode(name="test", url="/api")
        success = FetchSuccessNode()
        fetch.set_success(success)
        assert fetch.success_node is success

    def test_get_cache_seconds(self):
        """Test parsing cache TTL."""
        fetch = FetchNode(name="test", url="/api")

        fetch.cache = "30s"
        assert fetch.get_cache_seconds() == 30

        fetch.cache = "5m"
        assert fetch.get_cache_seconds() == 300

        fetch.cache = "1h"
        assert fetch.get_cache_seconds() == 3600

        fetch.cache = "1d"
        assert fetch.get_cache_seconds() == 86400

        fetch.cache = "0"
        assert fetch.get_cache_seconds() == 0

        fetch.cache = None
        assert fetch.get_cache_seconds() is None

    def test_get_interval_ms(self):
        """Test parsing interval."""
        fetch = FetchNode(name="test", url="/api")

        fetch.interval = "100ms"
        assert fetch.get_interval_ms() == 100

        fetch.interval = "10s"
        assert fetch.get_interval_ms() == 10000

        fetch.interval = "1m"
        assert fetch.get_interval_ms() == 60000

        fetch.interval = None
        assert fetch.get_interval_ms() is None

    def test_validate_valid(self):
        """Test validation passes for valid fetch."""
        fetch = FetchNode(name="users", url="/api/users")
        errors = fetch.validate()
        assert errors == []

    def test_validate_missing_name(self):
        """Test validation fails for missing name."""
        fetch = FetchNode(name="", url="/api")
        errors = fetch.validate()
        assert any("name" in e.lower() for e in errors)

    def test_validate_missing_url(self):
        """Test validation fails for missing url."""
        fetch = FetchNode(name="test", url="")
        errors = fetch.validate()
        assert any("url" in e.lower() for e in errors)

    def test_validate_invalid_method(self):
        """Test validation fails for invalid method."""
        fetch = FetchNode(name="test", url="/api")
        fetch.method = "INVALID"
        errors = fetch.validate()
        assert any("method" in e.lower() for e in errors)

    def test_validate_invalid_response_format(self):
        """Test validation fails for invalid response format."""
        fetch = FetchNode(name="test", url="/api")
        fetch.response_format = "invalid"
        errors = fetch.validate()
        assert any("response format" in e.lower() for e in errors)

    def test_validate_invalid_credentials(self):
        """Test validation fails for invalid credentials."""
        fetch = FetchNode(name="test", url="/api")
        fetch.credentials = "invalid"
        errors = fetch.validate()
        assert any("credentials" in e.lower() for e in errors)

    def test_valid_methods(self):
        """Test all valid HTTP methods."""
        valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        for method in valid_methods:
            fetch = FetchNode(name="test", url="/api")
            fetch.method = method
            errors = fetch.validate()
            assert not any("method" in e.lower() for e in errors)

    def test_to_dict(self):
        """Test serialization."""
        fetch = FetchNode(name="users", url="/api/users")
        fetch.cache = "5m"
        fetch.retry = 3

        d = fetch.to_dict()
        assert d['type'] == 'fetch'
        assert d['name'] == 'users'
        assert d['method'] == 'GET'
        assert d['cache'] == '5m'
        assert d['retry'] == 3

    def test_repr(self):
        """Test string representation."""
        fetch = FetchNode(name="users", url="/api/users/list/all")
        s = repr(fetch)
        assert "FetchNode" in s
        assert "users" in s


# ============================================
# Parse Fetch Tests
# ============================================

# XML namespace for q: prefix
Q_NS = 'xmlns:q="http://quantum.dev/components"'


class TestParseFetch:
    """Test fetch parser."""

    def test_parse_basic(self):
        """Test parsing basic fetch."""
        xml = f'<q:fetch {Q_NS} name="users" url="/api/users" />'
        element = ET.fromstring(xml)
        node = parse_fetch(element, None)

        assert node.name == "users"
        assert node.url == "/api/users"
        assert node.method == "GET"

    def test_parse_with_method(self):
        """Test parsing with HTTP method."""
        xml = f'<q:fetch {Q_NS} name="create" url="/api/users" method="POST" />'
        element = ET.fromstring(xml)
        node = parse_fetch(element, None)

        assert node.method == "POST"

    def test_parse_with_body(self):
        """Test parsing with body."""
        xml = f'<q:fetch {Q_NS} name="create" url="/api/users" method="POST" body="{{userData}}" />'
        element = ET.fromstring(xml)
        node = parse_fetch(element, None)

        assert node.body == "{userData}"

    def test_parse_with_cache(self):
        """Test parsing with cache."""
        xml = f'<q:fetch {Q_NS} name="users" url="/api/users" cache="5m" cacheKey="users-list" />'
        element = ET.fromstring(xml)
        node = parse_fetch(element, None)

        assert node.cache == "5m"
        assert node.cache_key == "users-list"

    def test_parse_with_interval(self):
        """Test parsing with polling interval."""
        xml = f'<q:fetch {Q_NS} name="status" url="/api/status" interval="10s" />'
        element = ET.fromstring(xml)
        node = parse_fetch(element, None)

        assert node.interval == "10s"

    def test_parse_with_timeout_and_retry(self):
        """Test parsing with timeout and retry."""
        xml = f'<q:fetch {Q_NS} name="slow" url="/api/slow" timeout="60000" retry="3" retryDelay="2000" />'
        element = ET.fromstring(xml)
        node = parse_fetch(element, None)

        assert node.timeout == 60000
        assert node.retry == 3
        assert node.retry_delay == 2000

    def test_parse_with_callbacks(self):
        """Test parsing with callbacks."""
        xml = f'<q:fetch {Q_NS} name="data" url="/api/data" onSuccess="handleSuccess" onError="handleError" />'
        element = ET.fromstring(xml)
        node = parse_fetch(element, None)

        assert node.on_success == "handleSuccess"
        assert node.on_error == "handleError"

    def test_parse_with_credentials(self):
        """Test parsing with credentials."""
        xml = f'<q:fetch {Q_NS} name="secure" url="/api/secure" credentials="include" />'
        element = ET.fromstring(xml)
        node = parse_fetch(element, None)

        assert node.credentials == "include"

    def test_parse_with_response_format(self):
        """Test parsing with response format."""
        xml = f'<q:fetch {Q_NS} name="text" url="/api/text" responseFormat="text" />'
        element = ET.fromstring(xml)
        node = parse_fetch(element, None)

        assert node.response_format == "text"

    def test_parse_lazy(self):
        """Test parsing lazy attribute."""
        xml = f'<q:fetch {Q_NS} name="lazy" url="/api/lazy" lazy="true" />'
        element = ET.fromstring(xml)
        node = parse_fetch(element, None)

        assert node.lazy is True

    def test_parse_abort_on_unmount(self):
        """Test parsing abortOnUnmount attribute."""
        xml = f'<q:fetch {Q_NS} name="persist" url="/api/persist" abortOnUnmount="false" />'
        element = ET.fromstring(xml)
        node = parse_fetch(element, None)

        assert node.abort_on_unmount is False

    def test_parse_missing_name(self):
        """Test parsing fails without name."""
        xml = f'<q:fetch {Q_NS} url="/api/users" />'
        element = ET.fromstring(xml)

        with pytest.raises(FetchParseError, match="name"):
            parse_fetch(element, None)

    def test_parse_missing_url(self):
        """Test parsing fails without url."""
        xml = f'<q:fetch {Q_NS} name="users" />'
        element = ET.fromstring(xml)

        with pytest.raises(FetchParseError, match="url"):
            parse_fetch(element, None)

    def test_parse_with_headers(self):
        """Test parsing with header children."""
        xml = '''
        <q:fetch name="auth" url="/api/auth" xmlns:q="http://quantum.dev/components">
            <q:header name="Authorization" value="Bearer token" />
            <q:header name="X-Custom" value="custom" />
        </q:fetch>
        '''
        element = ET.fromstring(xml)
        node = parse_fetch(element, None)

        assert len(node.headers) == 2
        assert node.headers[0].name == "Authorization"
        assert node.headers[1].name == "X-Custom"


# ============================================
# FetchHtmlAdapter Tests
# ============================================

class TestFetchHtmlAdapter:
    """Test FetchHtmlAdapter."""

    @pytest.fixture
    def adapter(self):
        """Fresh adapter for each test."""
        return FetchHtmlAdapter()

    def test_init(self, adapter):
        """Test adapter initialization."""
        assert adapter._fetch_counter == 0
        assert adapter._has_fetch is False

    def test_get_fetch_js_no_fetch(self, adapter):
        """Test no JS returned when no fetch rendered."""
        js = adapter.get_fetch_js()
        assert js == ''

    def test_get_fetch_js_with_fetch(self, adapter):
        """Test JS returned after fetch rendered."""
        adapter._has_fetch = True
        js = adapter.get_fetch_js()
        assert js == FETCH_STATE_JS
        assert '__qFetch' in js

    def test_fetch_state_js_contents(self):
        """Test fetch state JS contains required functions."""
        assert 'window.__qFetch' in FETCH_STATE_JS
        assert '__qFetchCache' in FETCH_STATE_JS
        assert '__qFetchState' in FETCH_STATE_JS
        assert '__qFetchAbort' in FETCH_STATE_JS
        assert '__qFetchRefetch' in FETCH_STATE_JS

    def test_fetch_css_contents(self):
        """Test fetch CSS contains required styles."""
        assert '.q-fetch' in FETCH_CSS
        assert '.q-fetch-loading' in FETCH_CSS
        assert '.q-fetch-error' in FETCH_CSS
        assert '.q-fetch-success' in FETCH_CSS
        assert '.q-loading-spinner' in FETCH_CSS


# ============================================
# Integration Tests
# ============================================

class TestFetchIntegration:
    """Integration tests for fetch feature."""

    def test_full_fetch_with_states(self):
        """Test creating a complete fetch with all states."""
        fetch = FetchNode(name="users", url="/api/users")
        fetch.method = "GET"
        fetch.cache = "5m"
        fetch.retry = 3

        # Add header
        header = FetchHeaderNode(name="Authorization", value="Bearer token")
        fetch.add_header(header)

        # Add loading state
        loading = FetchLoadingNode()
        fetch.set_loading(loading)

        # Add error state
        error = FetchErrorNode()
        fetch.set_error(error)

        # Add success state
        success = FetchSuccessNode()
        fetch.set_success(success)

        # Validate
        errors = fetch.validate()
        assert errors == []

        # Check structure
        assert len(fetch.headers) == 1
        assert fetch.loading_node is not None
        assert fetch.error_node is not None
        assert fetch.success_node is not None

    def test_parse_complete_fetch(self):
        """Test parsing a complete fetch element."""
        xml = '''
        <q:fetch name="orders" url="/api/orders" method="POST"
                 cache="5m" timeout="60000" retry="2"
                 onSuccess="handleOrders" onError="handleError"
                 xmlns:q="http://quantum.dev/components">
            <q:header name="Authorization" value="Bearer {token}" />
            <q:header name="Content-Type" value="application/json" />
            <q:loading>Loading orders...</q:loading>
            <q:error>Failed to load orders</q:error>
            <q:success>Orders loaded</q:success>
        </q:fetch>
        '''
        element = ET.fromstring(xml)
        node = parse_fetch(element, None)

        assert node.name == "orders"
        assert node.url == "/api/orders"
        assert node.method == "POST"
        assert node.cache == "5m"
        assert node.timeout == 60000
        assert node.retry == 2
        assert len(node.headers) == 2
        assert node.loading_node is not None
        assert node.error_node is not None
        assert node.success_node is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
