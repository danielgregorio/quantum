"""
Data Fetching Feature - HTML Adapter
Generates JavaScript fetch() code with state management for the HTML target.
"""

from typing import Optional
from .ast_node import FetchNode, FetchLoadingNode, FetchErrorNode, FetchSuccessNode


# JavaScript code for the fetch state management system
FETCH_STATE_JS = '''
<!-- Quantum Fetch State Management -->
<script>
(function() {
    // Fetch cache storage
    window.__qFetchCache = window.__qFetchCache || {};

    // Fetch state storage
    window.__qFetchState = window.__qFetchState || {};

    // Active abort controllers
    window.__qFetchControllers = window.__qFetchControllers || {};

    // Polling intervals
    window.__qFetchIntervals = window.__qFetchIntervals || {};

    /**
     * Execute a fetch request with state management
     * @param {string} fetchId - Unique ID for this fetch
     * @param {Object} options - Fetch configuration
     */
    window.__qFetch = function(fetchId, options) {
        const {
            name,
            url,
            method = 'GET',
            headers = {},
            body = null,
            cache = null,
            cacheKey = null,
            transform = null,
            timeout = 30000,
            retry = 0,
            retryDelay = 1000,
            interval = null,
            onSuccess = null,
            onError = null,
            credentials = null,
            responseFormat = 'auto'
        } = options;

        // Generate cache key
        const cKey = cacheKey || `${method}:${url}`;

        // Check cache first
        if (cache && window.__qFetchCache[cKey]) {
            const cached = window.__qFetchCache[cKey];
            if (Date.now() < cached.expires) {
                __qFetchSetState(fetchId, name, { loading: false, error: null, data: cached.data });
                __qFetchUpdateUI(fetchId, 'success');
                return Promise.resolve(cached.data);
            }
        }

        // Abort any existing request for this fetch
        if (window.__qFetchControllers[fetchId]) {
            window.__qFetchControllers[fetchId].abort();
        }

        // Create abort controller
        const controller = new AbortController();
        window.__qFetchControllers[fetchId] = controller;

        // Set loading state
        __qFetchSetState(fetchId, name, { loading: true, error: null });
        __qFetchUpdateUI(fetchId, 'loading');

        // Build fetch options
        const fetchOptions = {
            method: method,
            headers: { 'Content-Type': 'application/json', ...headers },
            signal: controller.signal
        };

        if (body && method !== 'GET' && method !== 'HEAD') {
            fetchOptions.body = typeof body === 'string' ? body : JSON.stringify(body);
        }

        if (credentials) {
            fetchOptions.credentials = credentials;
        }

        // Timeout promise
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        // Execute fetch with retry support
        const doFetch = (attempt = 0) => {
            return fetch(url, fetchOptions)
                .then(response => {
                    clearTimeout(timeoutId);
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }

                    // Parse response based on format
                    if (responseFormat === 'text') {
                        return response.text();
                    } else if (responseFormat === 'blob') {
                        return response.blob();
                    } else {
                        // Auto-detect: try JSON first
                        const contentType = response.headers.get('content-type');
                        if (contentType && contentType.includes('application/json')) {
                            return response.json();
                        }
                        return response.text().then(text => {
                            try { return JSON.parse(text); } catch { return text; }
                        });
                    }
                })
                .then(data => {
                    // Apply transform if specified
                    if (transform && typeof transform === 'function') {
                        data = transform(data);
                    }

                    // Cache the result
                    if (cache) {
                        const cacheSeconds = __qFetchParseDuration(cache);
                        if (cacheSeconds > 0) {
                            window.__qFetchCache[cKey] = {
                                data: data,
                                expires: Date.now() + (cacheSeconds * 1000)
                            };
                        }
                    }

                    // Update state
                    __qFetchSetState(fetchId, name, { loading: false, error: null, data: data });
                    __qFetchUpdateUI(fetchId, 'success');

                    // Call success callback
                    if (onSuccess && typeof window[onSuccess] === 'function') {
                        window[onSuccess](data);
                    }

                    return data;
                })
                .catch(error => {
                    clearTimeout(timeoutId);

                    // Handle abort
                    if (error.name === 'AbortError') {
                        return;
                    }

                    // Retry logic
                    if (attempt < retry) {
                        return new Promise(resolve => {
                            setTimeout(() => resolve(doFetch(attempt + 1)), retryDelay);
                        });
                    }

                    // Update error state
                    const errorMsg = error.message || 'Fetch failed';
                    __qFetchSetState(fetchId, name, { loading: false, error: errorMsg, data: null });
                    __qFetchUpdateUI(fetchId, 'error');

                    // Call error callback
                    if (onError && typeof window[onError] === 'function') {
                        window[onError](errorMsg);
                    }

                    throw error;
                });
        };

        const fetchPromise = doFetch();

        // Set up polling if interval specified
        if (interval) {
            const intervalMs = __qFetchParseDuration(interval) * 1000;
            if (intervalMs > 0) {
                // Clear existing interval
                if (window.__qFetchIntervals[fetchId]) {
                    clearInterval(window.__qFetchIntervals[fetchId]);
                }
                window.__qFetchIntervals[fetchId] = setInterval(() => {
                    __qFetch(fetchId, options);
                }, intervalMs);
            }
        }

        return fetchPromise;
    };

    /**
     * Set fetch state and update global variable
     */
    function __qFetchSetState(fetchId, name, state) {
        window.__qFetchState[fetchId] = { ...window.__qFetchState[fetchId], ...state };

        // Update global variable with data
        if (state.data !== undefined) {
            window[name] = state.data;
        }

        // Update error variable
        window[name + '_error'] = state.error;
        window[name + '_loading'] = state.loading;
    }

    /**
     * Update UI based on fetch state
     */
    function __qFetchUpdateUI(fetchId, state) {
        const loadingEl = document.getElementById(fetchId + '-loading');
        const errorEl = document.getElementById(fetchId + '-error');
        const successEl = document.getElementById(fetchId + '-success');

        if (loadingEl) loadingEl.style.display = state === 'loading' ? '' : 'none';
        if (errorEl) errorEl.style.display = state === 'error' ? '' : 'none';
        if (successEl) successEl.style.display = state === 'success' ? '' : 'none';
    }

    /**
     * Parse duration string to seconds
     */
    function __qFetchParseDuration(duration) {
        if (!duration) return 0;
        const str = String(duration).toLowerCase().trim();
        const match = str.match(/^(\\d+)(ms|s|m|h)?$/);
        if (match) {
            const value = parseInt(match[1]);
            const unit = match[2] || 's';
            const multipliers = { ms: 0.001, s: 1, m: 60, h: 3600 };
            return value * (multipliers[unit] || 1);
        }
        return parseInt(str) || 0;
    }

    /**
     * Abort a fetch request
     */
    window.__qFetchAbort = function(fetchId) {
        if (window.__qFetchControllers[fetchId]) {
            window.__qFetchControllers[fetchId].abort();
            delete window.__qFetchControllers[fetchId];
        }
        if (window.__qFetchIntervals[fetchId]) {
            clearInterval(window.__qFetchIntervals[fetchId]);
            delete window.__qFetchIntervals[fetchId];
        }
    };

    /**
     * Refetch data for a specific fetch
     */
    window.__qFetchRefetch = function(fetchId) {
        const state = window.__qFetchState[fetchId];
        if (state && state._options) {
            return __qFetch(fetchId, state._options);
        }
    };

})();
</script>
'''


class FetchHtmlAdapter:
    """Generates HTML/JS for q:fetch nodes."""

    def __init__(self, html_adapter=None):
        """
        Initialize the fetch HTML adapter.

        Args:
            html_adapter: Reference to the parent UIHtmlAdapter for rendering children
        """
        self._html_adapter = html_adapter
        self._fetch_counter = 0
        self._has_fetch = False

    def render_fetch(self, node: FetchNode, builder) -> str:
        """
        Render a FetchNode to HTML with JavaScript fetch code.

        Args:
            node: FetchNode to render
            builder: HtmlBuilder instance

        Returns:
            Generated HTML string
        """
        self._has_fetch = True
        self._fetch_counter += 1

        fetch_id = f"qfetch-{self._fetch_counter}"

        # Build container div
        builder.open_tag('div', {'class': 'q-fetch', 'id': fetch_id, 'data-fetch-name': node.name})
        builder.indent()

        # Render loading state
        loading_id = f"{fetch_id}-loading"
        builder.open_tag('div', {'id': loading_id, 'class': 'q-fetch-loading', 'style': 'display: none'})
        builder.indent()
        if node.loading_node:
            self._render_children(node.loading_node.children, builder)
        else:
            # Default loading indicator
            builder.open_tag('div', {'class': 'q-loading-spinner'})
            builder.text('Loading...')
            builder.close_tag('div')
        builder.dedent()
        builder.close_tag('div')

        # Render error state
        error_id = f"{fetch_id}-error"
        builder.open_tag('div', {'id': error_id, 'class': 'q-fetch-error', 'style': 'display: none'})
        builder.indent()
        if node.error_node:
            self._render_children(node.error_node.children, builder)
        else:
            # Default error display
            builder.open_tag('div', {'class': 'q-error-message'})
            builder.text('{' + node.name + '_error}')
            builder.close_tag('div')
        builder.dedent()
        builder.close_tag('div')

        # Render success state
        success_id = f"{fetch_id}-success"
        builder.open_tag('div', {'id': success_id, 'class': 'q-fetch-success', 'style': 'display: none'})
        builder.indent()
        if node.success_node:
            self._render_children(node.success_node.children, builder)
        elif node.fallback_children:
            self._render_children(node.fallback_children, builder)
        builder.dedent()
        builder.close_tag('div')

        builder.dedent()
        builder.close_tag('div')

        # Generate fetch invocation script
        builder.raw_html(self._generate_fetch_script(fetch_id, node))

    def _render_children(self, children, builder):
        """Render child nodes using the parent HTML adapter."""
        if self._html_adapter:
            for child in children:
                self._html_adapter._render_node(child, builder)
        else:
            # Fallback: render as text
            for child in children:
                if hasattr(child, 'content'):
                    builder.text(child.content)

    def _generate_fetch_script(self, fetch_id: str, node: FetchNode) -> str:
        """Generate JavaScript to execute the fetch on load."""
        # Build headers object
        headers_js = '{'
        header_parts = []
        for header in node.headers:
            header_parts.append(f"'{header.name}': '{header.value}'")
        headers_js += ', '.join(header_parts) + '}'

        # Build options object
        options = []
        options.append(f"name: '{node.name}'")
        options.append(f"url: '{node.url}'")
        options.append(f"method: '{node.method}'")
        options.append(f"headers: {headers_js}")

        if node.body:
            options.append(f"body: {node.body}")

        if node.cache:
            options.append(f"cache: '{node.cache}'")

        if node.cache_key:
            options.append(f"cacheKey: '{node.cache_key}'")

        if node.interval:
            options.append(f"interval: '{node.interval}'")

        if node.timeout != 30000:
            options.append(f"timeout: {node.timeout}")

        if node.retry > 0:
            options.append(f"retry: {node.retry}")
            options.append(f"retryDelay: {node.retry_delay}")

        if node.transform:
            options.append(f"transform: {node.transform}")

        if node.on_success:
            options.append(f"onSuccess: '{node.on_success}'")

        if node.on_error:
            options.append(f"onError: '{node.on_error}'")

        if node.credentials:
            options.append(f"credentials: '{node.credentials}'")

        if node.response_format != 'auto':
            options.append(f"responseFormat: '{node.response_format}'")

        options_js = '{' + ', '.join(options) + '}'

        # Generate script
        script = f'''
<script>
document.addEventListener('DOMContentLoaded', function() {{
    __qFetch('{fetch_id}', {options_js});
}});
</script>
'''
        return script

    def get_fetch_js(self) -> str:
        """Get the fetch state management JavaScript if needed."""
        if self._has_fetch:
            return FETCH_STATE_JS
        return ''


# CSS for fetch states
FETCH_CSS = '''
/* Quantum Fetch Styles */
.q-fetch {
    position: relative;
}

.q-fetch-loading {
    opacity: 0.7;
}

.q-loading-spinner {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    color: var(--q-text-secondary, #666);
}

.q-loading-spinner::before {
    content: '';
    width: 1rem;
    height: 1rem;
    margin-right: 0.5rem;
    border: 2px solid currentColor;
    border-top-color: transparent;
    border-radius: 50%;
    animation: q-spin 0.75s linear infinite;
}

@keyframes q-spin {
    to { transform: rotate(360deg); }
}

.q-fetch-error {
    color: var(--q-error, #dc2626);
    padding: 0.5rem;
    background: var(--q-error-bg, #fef2f2);
    border-radius: var(--q-radius, 4px);
}

.q-fetch-success {
    /* Success state - no specific styles needed */
}
'''
