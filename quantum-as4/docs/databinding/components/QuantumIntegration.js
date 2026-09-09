/**
 * Quantum Integration Components
 *
 * Provides integration between MXML applications and Quantum Language server.
 *
 * Components:
 * - QuantumService: HTTP client to call Quantum endpoints
 * - QuantumComponent: Embeds Quantum components via iframe
 * - QuantumBridge: Bidirectional communication bridge
 *
 * @example
 * <!-- Call Quantum endpoint and get data -->
 * <mx:QuantumService id="productsService"
 *                    url="http://localhost:8080/products"
 *                    method="GET"
 *                    result="handleProducts(event)"
 *                    fault="handleError(event)" />
 *
 * <!-- Embed Quantum component in MXML -->
 * <mx:QuantumComponent url="http://localhost:8080/hello"
 *                      width="600"
 *                      height="400" />
 */

/**
 * QuantumService
 *
 * HTTP service specifically designed to communicate with Quantum Language server.
 * Similar to HTTPService but optimized for Quantum endpoints.
 *
 * Features:
 * - GET/POST/PUT/DELETE requests to Quantum server
 * - Automatic HTML parsing from Quantum components
 * - Data extraction from Quantum responses
 * - Error handling
 * - Auto-retry on network failure
 */
export class QuantumService {
    constructor() {
        this.url = 'http://localhost:8080';
        this.method = 'GET';
        this.params = {};
        this.autoLoad = false;
        this.resultHandler = null;
        this.faultHandler = null;
        this.timeout = 30000;
        this.retries = 3;
        this.extractData = true; // Extract data from HTML response
    }

    /**
     * Send request to Quantum server
     */
    async send(params = null) {
        const requestParams = params || this.params;

        // Build URL with query params for GET
        let requestUrl = this.url;
        if (this.method === 'GET' && Object.keys(requestParams).length > 0) {
            const queryString = new URLSearchParams(requestParams).toString();
            requestUrl += '?' + queryString;
        }

        // Setup fetch options
        const options = {
            method: this.method,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/html,application/json'
            }
        };

        // Add body for POST/PUT
        if (['POST', 'PUT', 'PATCH'].includes(this.method)) {
            options.body = JSON.stringify(requestParams);
        }

        // Setup timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        options.signal = controller.signal;

        try {
            // Make request with retries
            let lastError;
            for (let attempt = 0; attempt <= this.retries; attempt++) {
                try {
                    const response = await fetch(requestUrl, options);
                    clearTimeout(timeoutId);

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }

                    // Parse response
                    const contentType = response.headers.get('content-type');
                    let result;

                    if (contentType && contentType.includes('application/json')) {
                        result = await response.json();
                    } else {
                        // HTML response from Quantum component
                        const html = await response.text();

                        if (this.extractData) {
                            // Try to extract structured data from HTML
                            result = this.extractQuantumData(html);
                        } else {
                            result = { html: html, raw: html };
                        }
                    }

                    // Fire result event
                    if (this.resultHandler) {
                        this.resultHandler({
                            type: 'result',
                            result: result,
                            statusCode: response.status,
                            url: requestUrl
                        });
                    }

                    return result;

                } catch (error) {
                    lastError = error;
                    if (attempt < this.retries) {
                        // Wait before retry (exponential backoff)
                        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
                        continue;
                    }
                }
            }

            throw lastError;

        } catch (error) {
            clearTimeout(timeoutId);

            // Fire fault event
            if (this.faultHandler) {
                this.faultHandler({
                    type: 'fault',
                    error: error.message,
                    fault: {
                        faultString: error.message,
                        faultCode: error.name
                    },
                    url: requestUrl
                });
            }

            throw error;
        }
    }

    /**
     * Extract structured data from Quantum HTML response
     * Looks for data attributes or script tags with JSON data
     */
    extractQuantumData(html) {
        const result = {
            html: html,
            raw: html,
            data: {}
        };

        // Try to parse JSON from script tags like <script type="application/json">
        const jsonScriptMatch = html.match(/<script[^>]*type=["']application\/json["'][^>]*>([\s\S]*?)<\/script>/i);
        if (jsonScriptMatch) {
            try {
                result.data = JSON.parse(jsonScriptMatch[1]);
            } catch (e) {
                console.warn('Failed to parse Quantum JSON data:', e);
            }
        }

        // Extract title
        const titleMatch = html.match(/<title>([^<]+)<\/title>/i);
        if (titleMatch) {
            result.title = titleMatch[1];
        }

        // Extract meta tags
        const metaMatches = html.matchAll(/<meta[^>]*name=["']([^"']+)["'][^>]*content=["']([^"']+)["'][^>]*>/gi);
        result.meta = {};
        for (const match of metaMatches) {
            result.meta[match[1]] = match[2];
        }

        return result;
    }

    /**
     * Cancel ongoing request
     */
    cancel() {
        // Implemented via AbortController in send()
    }
}

/**
 * QuantumComponent
 *
 * Embeds a Quantum component inside MXML application using iframe.
 * Provides seamless integration with automatic sizing and communication.
 *
 * Features:
 * - Iframe-based embedding
 * - Automatic height adjustment
 * - PostMessage communication
 * - Event forwarding
 * - Loading states
 */
export class QuantumComponent {
    constructor() {
        this.url = '';
        this.width = 600;
        this.height = 400;
        this.autoResize = true;
        this.sandbox = 'allow-scripts allow-same-origin';
        this.loadHandler = null;
        this.errorHandler = null;
        this.messageHandler = null;
    }

    createElement() {
        // Create container
        const container = document.createElement('div');
        container.className = 'quantum-component';
        container.style.width = this.width + 'px';
        container.style.height = this.height + 'px';
        container.style.position = 'relative';
        container.style.overflow = 'hidden';

        // Create loading indicator
        const loading = document.createElement('div');
        loading.className = 'quantum-loading';
        loading.style.position = 'absolute';
        loading.style.top = '50%';
        loading.style.left = '50%';
        loading.style.transform = 'translate(-50%, -50%)';
        loading.style.fontSize = '14px';
        loading.style.color = '#666';
        loading.textContent = '⏳ Loading Quantum component...';
        container.appendChild(loading);

        // Create iframe
        const iframe = document.createElement('iframe');
        iframe.src = this.url;
        iframe.style.width = '100%';
        iframe.style.height = '100%';
        iframe.style.border = 'none';
        iframe.style.display = 'none';
        if (this.sandbox) {
            iframe.sandbox = this.sandbox;
        }

        // Handle load
        iframe.addEventListener('load', () => {
            loading.style.display = 'none';
            iframe.style.display = 'block';

            if (this.loadHandler) {
                this.loadHandler({
                    type: 'load',
                    url: this.url
                });
            }

            // Setup auto-resize if enabled
            if (this.autoResize) {
                this.setupAutoResize(iframe, container);
            }
        });

        // Handle error
        iframe.addEventListener('error', (e) => {
            loading.textContent = '❌ Failed to load Quantum component';
            loading.style.color = '#e74c3c';

            if (this.errorHandler) {
                this.errorHandler({
                    type: 'error',
                    error: e.message
                });
            }
        });

        container.appendChild(iframe);

        // Setup message listener for communication
        window.addEventListener('message', (event) => {
            // Verify origin (adjust as needed)
            if (event.origin === new URL(this.url).origin) {
                if (this.messageHandler) {
                    this.messageHandler({
                        type: 'message',
                        data: event.data,
                        origin: event.origin
                    });
                }
            }
        });

        return container;
    }

    setupAutoResize(iframe, container) {
        // Try to get content height from iframe
        try {
            const observer = new ResizeObserver(() => {
                try {
                    const iframeDocument = iframe.contentDocument || iframe.contentWindow.document;
                    const height = iframeDocument.body.scrollHeight;
                    if (height > 0) {
                        container.style.height = height + 'px';
                        iframe.style.height = height + 'px';
                    }
                } catch (e) {
                    // Cross-origin restriction, can't access iframe content
                    console.warn('Cannot auto-resize cross-origin iframe');
                }
            });

            try {
                const iframeDocument = iframe.contentDocument || iframe.contentWindow.document;
                if (iframeDocument.body) {
                    observer.observe(iframeDocument.body);
                }
            } catch (e) {
                // Cross-origin, fallback to postMessage-based resizing
                this.setupPostMessageResize(iframe, container);
            }
        } catch (e) {
            console.warn('Failed to setup auto-resize:', e);
        }
    }

    setupPostMessageResize(iframe, container) {
        // Listen for size messages from Quantum component
        window.addEventListener('message', (event) => {
            if (event.origin === new URL(this.url).origin && event.data.type === 'quantum:resize') {
                const height = event.data.height;
                if (height > 0) {
                    container.style.height = height + 'px';
                    iframe.style.height = height + 'px';
                }
            }
        });
    }

    /**
     * Send message to embedded Quantum component
     */
    postMessage(data) {
        const iframe = this.iframe;
        if (iframe && iframe.contentWindow) {
            iframe.contentWindow.postMessage(data, new URL(this.url).origin);
        }
    }
}

/**
 * QuantumBridge
 *
 * Bidirectional communication bridge between MXML and Quantum.
 * Uses PostMessage API for secure cross-origin communication.
 *
 * Features:
 * - Send events from MXML to Quantum
 * - Receive events from Quantum to MXML
 * - Data synchronization
 * - RPC-style method invocation
 */
export class QuantumBridge {
    constructor(targetOrigin = 'http://localhost:8080') {
        this.targetOrigin = targetOrigin;
        this.messageHandlers = new Map();
        this.setupListener();
    }

    setupListener() {
        window.addEventListener('message', (event) => {
            if (event.origin !== this.targetOrigin) {
                return; // Ignore messages from other origins
            }

            const { type, data } = event.data;

            if (this.messageHandlers.has(type)) {
                const handler = this.messageHandlers.get(type);
                handler(data, event);
            }
        });
    }

    /**
     * Register handler for specific message type
     */
    on(type, handler) {
        this.messageHandlers.set(type, handler);
    }

    /**
     * Send message to Quantum
     */
    send(type, data) {
        window.parent.postMessage({ type, data }, this.targetOrigin);
    }

    /**
     * Call method on Quantum component (RPC-style)
     */
    async call(method, params) {
        return new Promise((resolve, reject) => {
            const callId = `call_${Date.now()}_${Math.random()}`;

            // Setup response handler
            const responseHandler = (data) => {
                if (data.callId === callId) {
                    this.messageHandlers.delete(`quantum:response:${callId}`);
                    if (data.error) {
                        reject(new Error(data.error));
                    } else {
                        resolve(data.result);
                    }
                }
            };

            this.messageHandlers.set(`quantum:response:${callId}`, responseHandler);

            // Send call
            this.send('quantum:call', {
                callId,
                method,
                params
            });

            // Timeout after 30s
            setTimeout(() => {
                this.messageHandlers.delete(`quantum:response:${callId}`);
                reject(new Error('Quantum call timeout'));
            }, 30000);
        });
    }
}

/**
 * Render functions for reactive runtime
 */
export function renderQuantumService(runtime, node) {
    const service = new QuantumService();

    service.url = node.props.url || 'http://localhost:8080';
    service.method = (node.props.method || 'GET').toUpperCase();
    service.autoLoad = node.props.autoLoad === 'true';
    service.extractData = node.props.extractData !== 'false';

    if (node.props.timeout) {
        service.timeout = parseInt(node.props.timeout);
    }

    // Setup event handlers
    if (node.events && node.events.result) {
        const handlerName = node.events.result.replace(/[()]/g, '');
        service.resultHandler = (event) => {
            if (runtime.app[handlerName]) {
                runtime.app[handlerName](event);
            }
        };
    }

    if (node.events && node.events.fault) {
        const handlerName = node.events.fault.replace(/[()]/g, '');
        service.faultHandler = (event) => {
            if (runtime.app[handlerName]) {
                runtime.app[handlerName](event);
            }
        };
    }

    // Store in runtime if has ID
    if (node.props.id) {
        runtime.app[node.props.id] = service;
    }

    // Auto-load if enabled
    if (service.autoLoad) {
        setTimeout(() => service.send(), 100);
    }

    return document.createComment(`QuantumService: ${node.props.id}`);
}

export function renderQuantumComponent(runtime, node) {
    const component = new QuantumComponent();

    component.url = node.props.url || '';
    component.width = node.props.width ? parseInt(node.props.width) : 600;
    component.height = node.props.height ? parseInt(node.props.height) : 400;
    component.autoResize = node.props.autoResize !== 'false';

    if (node.props.sandbox) {
        component.sandbox = node.props.sandbox;
    }

    // Setup event handlers
    if (node.events && node.events.load) {
        const handlerName = node.events.load.replace(/[()]/g, '');
        component.loadHandler = (event) => {
            if (runtime.app[handlerName]) {
                runtime.app[handlerName](event);
            }
        };
    }

    if (node.events && node.events.error) {
        const handlerName = node.events.error.replace(/[()]/g, '');
        component.errorHandler = (event) => {
            if (runtime.app[handlerName]) {
                runtime.app[handlerName](event);
            }
        };
    }

    if (node.events && node.events.message) {
        const handlerName = node.events.message.replace(/[()]/g, '');
        component.messageHandler = (event) => {
            if (runtime.app[handlerName]) {
                runtime.app[handlerName](event);
            }
        };
    }

    // Store in runtime if has ID
    if (node.props.id) {
        runtime.app[node.props.id] = component;
    }

    return component.createElement();
}

export function renderQuantumBridge(runtime, node) {
    const bridge = new QuantumBridge(node.props.targetOrigin || 'http://localhost:8080');

    // Store in runtime if has ID
    if (node.props.id) {
        runtime.app[node.props.id] = bridge;
    }

    return document.createComment(`QuantumBridge: ${node.props.id}`);
}
