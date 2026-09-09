/**
 * HTTPService Component - HTTP/REST API integration
 *
 * Props:
 * - id: Service identifier
 * - url: Request URL (supports bindings)
 * - method: HTTP method (GET, POST, PUT, DELETE, PATCH) - default: GET
 * - contentType: Content-Type header - default: application/json
 * - resultFormat: Response format (json, xml, text, e4x) - default: json
 * - headers: Additional HTTP headers as Object
 * - showBusyCursor: Show loading cursor - default: false
 * - timeout: Request timeout in milliseconds - default: 30000
 * - useProxy: Use proxy for cross-domain - default: false
 *
 * Events:
 * - result: Fired when request succeeds (passes response data)
 * - fault: Fired when request fails (passes error)
 *
 * Methods:
 * - send(params): Send request with optional parameters
 * - cancel(): Cancel pending request
 *
 * Usage:
 * <s:HTTPService id="userService"
 *                url="https://api.example.com/users"
 *                method="GET"
 *                resultFormat="json"
 *                result="handleResult(event)"
 *                fault="handleFault(event)" />
 *
 * Then in ActionScript:
 * userService.send();  // or userService.send({id: 123})
 */

export function renderHTTPService(runtime, node) {
    // HTTPService is not a visual component - it's a service
    // We'll attach it to the runtime/app for access
    const serviceId = node.props.id;

    const service = {
        // Props
        url: node.props.url || '',
        method: (node.props.method || 'GET').toUpperCase(),
        contentType: node.props.contentType || 'application/json',
        resultFormat: node.props.resultFormat || 'json',
        headers: node.props.headers || {},
        showBusyCursor: node.props.showBusyCursor === 'true',
        timeout: node.props.timeout ? parseInt(node.props.timeout) : 30000,
        useProxy: node.props.useProxy === 'true',

        // State
        lastResult: null,
        lastError: null,
        isPending: false,
        abortController: null,

        // Events
        resultHandler: node.events.result,
        faultHandler: node.events.fault,

        /**
         * Send HTTP request
         * @param {Object} params - Query params (for GET) or body data (for POST/PUT)
         */
        send: async function(params = null) {
            // Cancel any pending request
            if (this.abortController) {
                this.abortController.abort();
            }

            this.abortController = new AbortController();
            this.isPending = true;

            // Show busy cursor if enabled
            if (this.showBusyCursor) {
                document.body.style.cursor = 'wait';
            }

            try {
                // Build URL with query params for GET
                let requestUrl = this.url;

                // Evaluate bindings in URL
                if (requestUrl.includes('{')) {
                    requestUrl = runtime.evaluateBinding(requestUrl);
                }

                // Add query params for GET requests
                if (params && (this.method === 'GET' || this.method === 'DELETE')) {
                    const queryString = new URLSearchParams(params).toString();
                    requestUrl += (requestUrl.includes('?') ? '&' : '?') + queryString;
                }

                // Build request options
                const options = {
                    method: this.method,
                    headers: {
                        ...this.headers
                    },
                    signal: this.abortController.signal
                };

                // Add body for POST/PUT/PATCH
                if (params && ['POST', 'PUT', 'PATCH'].includes(this.method)) {
                    if (this.contentType === 'application/json') {
                        options.headers['Content-Type'] = 'application/json';
                        options.body = JSON.stringify(params);
                    } else if (this.contentType === 'application/x-www-form-urlencoded') {
                        options.headers['Content-Type'] = 'application/x-www-form-urlencoded';
                        options.body = new URLSearchParams(params).toString();
                    } else if (this.contentType === 'multipart/form-data') {
                        // For FormData, don't set Content-Type (browser will set with boundary)
                        options.body = params instanceof FormData ? params : this._toFormData(params);
                    } else {
                        options.body = params;
                    }
                }

                // Set timeout
                const timeoutId = setTimeout(() => {
                    this.abortController.abort();
                }, this.timeout);

                // Make request
                const response = await fetch(requestUrl, options);
                clearTimeout(timeoutId);

                // Check if response is ok
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                // Parse response based on resultFormat
                let result;
                switch (this.resultFormat) {
                    case 'json':
                        result = await response.json();
                        break;
                    case 'xml':
                    case 'e4x':
                        const xmlText = await response.text();
                        result = new DOMParser().parseFromString(xmlText, 'text/xml');
                        break;
                    case 'text':
                        result = await response.text();
                        break;
                    default:
                        result = await response.text();
                }

                // Store result
                this.lastResult = result;
                this.lastError = null;
                this.isPending = false;

                // Restore cursor
                if (this.showBusyCursor) {
                    document.body.style.cursor = 'default';
                }

                // Fire result event
                if (this.resultHandler) {
                    const handlerName = this.resultHandler.replace(/\(.*?\)/, '');
                    if (runtime.app[handlerName]) {
                        // Create event object similar to Flex ResultEvent
                        const event = {
                            type: 'result',
                            result: result,
                            statusCode: response.status,
                            headers: Object.fromEntries(response.headers.entries()),
                            token: { message: params }
                        };
                        runtime.app[handlerName](event);
                    }
                }

                return result;

            } catch (error) {
                this.isPending = false;
                this.lastError = error;

                // Restore cursor
                if (this.showBusyCursor) {
                    document.body.style.cursor = 'default';
                }

                // Fire fault event
                if (this.faultHandler) {
                    const handlerName = this.faultHandler.replace(/\(.*?\)/, '');
                    if (runtime.app[handlerName]) {
                        // Create event object similar to Flex FaultEvent
                        const event = {
                            type: 'fault',
                            fault: {
                                faultString: error.message,
                                faultCode: error.name,
                                faultDetail: error.stack
                            },
                            message: error.message,
                            statusCode: error.status || 0
                        };
                        runtime.app[handlerName](event);
                    }
                }

                throw error;
            }
        },

        /**
         * Cancel pending request
         */
        cancel: function() {
            if (this.abortController) {
                this.abortController.abort();
                this.isPending = false;

                if (this.showBusyCursor) {
                    document.body.style.cursor = 'default';
                }
            }
        },

        /**
         * Convert object to FormData
         */
        _toFormData: function(obj) {
            const formData = new FormData();
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    formData.append(key, obj[key]);
                }
            }
            return formData;
        }
    };

    // Register service in runtime if it has an ID
    if (serviceId) {
        if (!runtime.services) {
            runtime.services = {};
        }
        runtime.services[serviceId] = service;

        // Also attach to app for easy access
        if (runtime.app) {
            runtime.app[serviceId] = service;
        }
    }

    // HTTPService doesn't render anything visible
    const placeholder = document.createComment('HTTPService: ' + serviceId);
    return placeholder;
}
