/**
 * Quantum Framework Tag and Attribute Schema
 *
 * Complete schema of all Quantum tags (q:, ui:, qg:, qt:, qtest:)
 * with their attributes, descriptions, and validation rules.
 */

export interface AttributeSchema {
    name: string;
    description: string;
    required?: boolean;
    type?: 'string' | 'number' | 'boolean' | 'expression' | 'enum';
    values?: string[];  // For enum types
    default?: string;
}

export interface TagSchema {
    name: string;
    namespace: 'q' | 'ui' | 'qg' | 'qt' | 'qtest';
    description: string;
    attributes: AttributeSchema[];
    selfClosing?: boolean;
    allowedChildren?: string[];
    category?: string;
}

// ==============================================
// QUANTUM CORE TAGS (q:)
// ==============================================

export const quantumTags: TagSchema[] = [
    // Structure
    {
        name: 'component',
        namespace: 'q',
        description: 'Root element for a Quantum component. Components are reusable building blocks.',
        category: 'Structure',
        attributes: [
            { name: 'name', description: 'Component name (PascalCase)', required: true, type: 'string' },
            { name: 'type', description: 'Component type', type: 'enum', values: ['pure', 'microservice', 'event-driven', 'worker', 'websocket', 'graphql', 'grpc', 'serverless'], default: 'pure' },
            { name: 'port', description: 'Port number for microservice', type: 'number' },
            { name: 'basePath', description: 'Base path for REST endpoints', type: 'string' },
            { name: 'require_auth', description: 'Require authentication', type: 'boolean', default: 'false' },
            { name: 'require_role', description: 'Required role(s) for access', type: 'string' },
            { name: 'interactive', description: 'Enable client-side hydration', type: 'boolean', default: 'false' },
        ]
    },
    {
        name: 'application',
        namespace: 'q',
        description: 'Root element for a Quantum application. Defines routes and application-level config.',
        category: 'Structure',
        attributes: [
            { name: 'id', description: 'Application ID', required: true, type: 'string' },
            { name: 'type', description: 'Application type', type: 'enum', values: ['html', 'ui', 'game', 'terminal', 'testing'], default: 'html' },
            { name: 'engine', description: 'Engine type (e.g., "2d" for game)', type: 'string' },
            { name: 'theme', description: 'Theme preset for UI apps', type: 'enum', values: ['light', 'dark'] },
        ]
    },
    {
        name: 'job',
        namespace: 'q',
        description: 'Scheduled job definition for background tasks.',
        category: 'Structure',
        attributes: [
            { name: 'id', description: 'Job identifier', required: true, type: 'string' },
            { name: 'schedule', description: 'Cron-like schedule expression', type: 'string' },
        ]
    },

    // Parameters & Returns
    {
        name: 'param',
        namespace: 'q',
        description: 'Define a parameter for component, function, action, or query.',
        category: 'Parameters',
        selfClosing: true,
        attributes: [
            { name: 'name', description: 'Parameter name', required: true, type: 'string' },
            { name: 'type', description: 'Parameter type', type: 'enum', values: ['string', 'integer', 'decimal', 'boolean', 'array', 'object', 'date', 'datetime', 'email', 'binary'], default: 'string' },
            { name: 'required', description: 'Whether parameter is required', type: 'boolean', default: 'false' },
            { name: 'default', description: 'Default value', type: 'string' },
            { name: 'source', description: 'REST parameter source', type: 'enum', values: ['auto', 'path', 'query', 'body', 'header', 'cookie'], default: 'auto' },
            { name: 'validate', description: 'Validation rule', type: 'string' },
            { name: 'pattern', description: 'Regex pattern for validation', type: 'string' },
            { name: 'min', description: 'Minimum value', type: 'string' },
            { name: 'max', description: 'Maximum value', type: 'string' },
            { name: 'minlength', description: 'Minimum string length', type: 'number' },
            { name: 'maxlength', description: 'Maximum string length', type: 'number' },
            { name: 'enum', description: 'Allowed values (comma-separated)', type: 'string' },
            { name: 'value', description: 'Value (for query params)', type: 'expression' },
        ]
    },
    {
        name: 'return',
        namespace: 'q',
        description: 'Define a return value from a function or route.',
        category: 'Parameters',
        selfClosing: true,
        attributes: [
            { name: 'name', description: 'Return value name', type: 'string' },
            { name: 'type', description: 'Return type', type: 'enum', values: ['string', 'integer', 'boolean', 'array', 'object', 'any'], default: 'string' },
            { name: 'value', description: 'Return value expression', required: true, type: 'expression' },
            { name: 'description', description: 'Description for documentation', type: 'string' },
        ]
    },
    {
        name: 'route',
        namespace: 'q',
        description: 'Define a route mapping for the application.',
        category: 'Routing',
        attributes: [
            { name: 'path', description: 'URL path pattern', required: true, type: 'string' },
            { name: 'method', description: 'HTTP method', type: 'enum', values: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'], default: 'GET' },
        ]
    },

    // State Management
    {
        name: 'set',
        namespace: 'q',
        description: 'Set a variable value. Supports validation, scoping, and persistence.',
        category: 'State',
        selfClosing: true,
        attributes: [
            { name: 'name', description: 'Variable name', required: true, type: 'string' },
            { name: 'value', description: 'Value to assign', type: 'expression' },
            { name: 'type', description: 'Variable type', type: 'enum', values: ['string', 'number', 'boolean', 'array', 'object', 'date'], default: 'string' },
            { name: 'scope', description: 'Variable scope', type: 'enum', values: ['local', 'component', 'session', 'application'], default: 'local' },
            { name: 'operation', description: 'Operation type', type: 'enum', values: ['assign', 'increment', 'decrement', 'append', 'prepend', 'remove', 'toggle'], default: 'assign' },
            { name: 'default', description: 'Default value if undefined', type: 'string' },
            { name: 'required', description: 'Require a value', type: 'boolean', default: 'false' },
            { name: 'pattern', description: 'Validation regex pattern', type: 'string' },
            { name: 'min', description: 'Minimum value', type: 'string' },
            { name: 'max', description: 'Maximum value', type: 'string' },
            { name: 'persist', description: 'Persistence mode', type: 'enum', values: ['local', 'session', 'sync'] },
        ]
    },
    {
        name: 'persist',
        namespace: 'q',
        description: 'Configure state persistence for variables.',
        category: 'State',
        attributes: [
            { name: 'scope', description: 'Storage scope', type: 'enum', values: ['local', 'session', 'sync'], default: 'local' },
            { name: 'prefix', description: 'Key prefix in storage', type: 'string' },
            { name: 'key', description: 'Custom storage key', type: 'string' },
            { name: 'encrypt', description: 'Encrypt stored data', type: 'boolean', default: 'false' },
            { name: 'ttl', description: 'Time-to-live in seconds', type: 'number' },
        ]
    },

    // Control Flow
    {
        name: 'if',
        namespace: 'q',
        description: 'Conditional rendering. Content is rendered only when condition is true.',
        category: 'Control Flow',
        attributes: [
            { name: 'condition', description: 'Boolean expression to evaluate', required: true, type: 'expression' },
        ]
    },
    {
        name: 'elseif',
        namespace: 'q',
        description: 'Alternative condition branch (inside q:if).',
        category: 'Control Flow',
        attributes: [
            { name: 'condition', description: 'Boolean expression to evaluate', required: true, type: 'expression' },
        ]
    },
    {
        name: 'else',
        namespace: 'q',
        description: 'Default branch when all conditions are false (inside q:if).',
        category: 'Control Flow',
        attributes: []
    },
    {
        name: 'loop',
        namespace: 'q',
        description: 'Iterate over a range, array, list, or query result.',
        category: 'Control Flow',
        attributes: [
            { name: 'type', description: 'Loop type', type: 'enum', values: ['range', 'array', 'list', 'query'], default: 'range' },
            { name: 'from', description: 'Start value (range loop)', type: 'expression' },
            { name: 'to', description: 'End value (range loop)', type: 'expression' },
            { name: 'step', description: 'Step increment (range loop)', type: 'number', default: '1' },
            { name: 'var', description: 'Loop variable name', type: 'string' },
            { name: 'index', description: 'Index variable name', type: 'string' },
            { name: 'items', description: 'Array or list to iterate', type: 'expression' },
            { name: 'query', description: 'Query name to iterate (shorthand)', type: 'string' },
            { name: 'delimiter', description: 'Delimiter for list type', type: 'string', default: ',' },
        ]
    },

    // Functions
    {
        name: 'function',
        namespace: 'q',
        description: 'Define a reusable function with parameters and return values.',
        category: 'Functions',
        attributes: [
            { name: 'name', description: 'Function name', required: true, type: 'string' },
            { name: 'returnType', description: 'Return type', type: 'enum', values: ['void', 'string', 'integer', 'boolean', 'array', 'object', 'any'], default: 'any' },
            { name: 'scope', description: 'Function scope', type: 'enum', values: ['component', 'global'], default: 'component' },
            { name: 'access', description: 'Access level', type: 'enum', values: ['public', 'private'], default: 'public' },
            { name: 'endpoint', description: 'REST endpoint path', type: 'string' },
            { name: 'method', description: 'HTTP method for REST', type: 'enum', values: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'], default: 'GET' },
            { name: 'cache', description: 'Enable caching (true or TTL like "60s")', type: 'string' },
            { name: 'async', description: 'Async function', type: 'boolean', default: 'false' },
            { name: 'validate', description: 'Validate parameters', type: 'boolean', default: 'false' },
            { name: 'pure', description: 'Pure function (no side effects)', type: 'boolean', default: 'false' },
        ]
    },

    // Database
    {
        name: 'query',
        namespace: 'q',
        description: 'Execute a SQL database query with parameterized values.',
        category: 'Database',
        attributes: [
            { name: 'name', description: 'Result variable name', required: true, type: 'string' },
            { name: 'datasource', description: 'Database connection name', type: 'string' },
            { name: 'source', description: 'Source query for Query-of-Queries', type: 'string' },
            { name: 'cache', description: 'Cache results', type: 'boolean', default: 'false' },
            { name: 'ttl', description: 'Cache TTL in seconds', type: 'number' },
            { name: 'paginate', description: 'Enable pagination', type: 'boolean', default: 'false' },
            { name: 'page', description: 'Current page number', type: 'number' },
            { name: 'pageSize', description: 'Items per page', type: 'number', default: '20' },
            { name: 'maxrows', description: 'Maximum rows to return', type: 'number' },
            { name: 'timeout', description: 'Query timeout in seconds', type: 'number' },
            { name: 'mode', description: 'Query mode (for RAG)', type: 'enum', values: ['normal', 'rag'] },
            { name: 'model', description: 'LLM model for RAG mode', type: 'string' },
        ]
    },
    {
        name: 'transaction',
        namespace: 'q',
        description: 'Group queries into an atomic transaction (all succeed or all rollback).',
        category: 'Database',
        attributes: [
            { name: 'isolationLevel', description: 'Transaction isolation level', type: 'enum', values: ['READ_UNCOMMITTED', 'READ_COMMITTED', 'REPEATABLE_READ', 'SERIALIZABLE'], default: 'READ_COMMITTED' },
        ]
    },

    // HTTP & APIs
    {
        name: 'invoke',
        namespace: 'q',
        description: 'Call an external HTTP API or internal function.',
        category: 'HTTP',
        attributes: [
            { name: 'name', description: 'Result variable name', required: true, type: 'string' },
            { name: 'url', description: 'URL to call', type: 'string' },
            { name: 'function', description: 'Function to call', type: 'string' },
            { name: 'component', description: 'Component containing function', type: 'string' },
            { name: 'method', description: 'HTTP method', type: 'enum', values: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'], default: 'GET' },
            { name: 'contentType', description: 'Request content type', type: 'string', default: 'application/json' },
            { name: 'timeout', description: 'Timeout in seconds', type: 'number' },
            { name: 'retry', description: 'Number of retries', type: 'number' },
            { name: 'cache', description: 'Cache response', type: 'boolean', default: 'false' },
            { name: 'authType', description: 'Authentication type', type: 'enum', values: ['none', 'basic', 'bearer', 'custom'] },
            { name: 'authToken', description: 'Bearer token or API key', type: 'string' },
        ]
    },
    {
        name: 'header',
        namespace: 'q',
        description: 'HTTP header for invoke or data requests.',
        category: 'HTTP',
        selfClosing: true,
        attributes: [
            { name: 'name', description: 'Header name', required: true, type: 'string' },
            { name: 'value', description: 'Header value', required: true, type: 'expression' },
        ]
    },

    // Forms & Actions
    {
        name: 'action',
        namespace: 'q',
        description: 'Define a server-side form action handler.',
        category: 'Forms',
        attributes: [
            { name: 'name', description: 'Action name', required: true, type: 'string' },
            { name: 'method', description: 'HTTP method', type: 'enum', values: ['POST', 'PUT', 'DELETE', 'PATCH'], default: 'POST' },
            { name: 'csrf', description: 'Enable CSRF protection', type: 'boolean', default: 'true' },
            { name: 'rate_limit', description: 'Rate limit (e.g., "10/minute")', type: 'string' },
            { name: 'require_auth', description: 'Require authentication', type: 'boolean', default: 'false' },
        ]
    },
    {
        name: 'redirect',
        namespace: 'q',
        description: 'Redirect to another URL after action.',
        category: 'Forms',
        selfClosing: true,
        attributes: [
            { name: 'url', description: 'Target URL', required: true, type: 'expression' },
            { name: 'flash', description: 'Flash message to display', type: 'string' },
            { name: 'status', description: 'HTTP redirect status', type: 'enum', values: ['301', '302', '303', '307', '308'], default: '302' },
        ]
    },
    {
        name: 'flash',
        namespace: 'q',
        description: 'Display a one-time flash message.',
        category: 'Forms',
        selfClosing: true,
        attributes: [
            { name: 'type', description: 'Message type', type: 'enum', values: ['info', 'success', 'warning', 'error'], default: 'info' },
            { name: 'message', description: 'Message text', required: true, type: 'expression' },
        ]
    },

    // File & Email
    {
        name: 'file',
        namespace: 'q',
        description: 'Handle file uploads and file operations.',
        category: 'Files',
        selfClosing: true,
        attributes: [
            { name: 'action', description: 'File action', type: 'enum', values: ['upload', 'delete', 'move', 'copy'], default: 'upload' },
            { name: 'file', description: 'File variable', required: true, type: 'expression' },
            { name: 'destination', description: 'Destination path', type: 'string', default: './uploads/' },
            { name: 'nameConflict', description: 'Name conflict resolution', type: 'enum', values: ['error', 'overwrite', 'skip', 'makeUnique'], default: 'error' },
            { name: 'result', description: 'Result variable name', type: 'string' },
        ]
    },
    {
        name: 'mail',
        namespace: 'q',
        description: 'Send an email (ColdFusion cfmail-inspired).',
        category: 'Email',
        attributes: [
            { name: 'to', description: 'Recipient email(s)', required: true, type: 'expression' },
            { name: 'from', description: 'Sender email', type: 'string' },
            { name: 'subject', description: 'Email subject', required: true, type: 'expression' },
            { name: 'cc', description: 'CC recipients', type: 'string' },
            { name: 'bcc', description: 'BCC recipients', type: 'string' },
            { name: 'replyTo', description: 'Reply-to address', type: 'string' },
            { name: 'type', description: 'Content type', type: 'enum', values: ['html', 'text'], default: 'html' },
        ]
    },

    // LLM
    {
        name: 'llm',
        namespace: 'q',
        description: 'Invoke an LLM (Ollama-compatible API).',
        category: 'LLM',
        attributes: [
            { name: 'name', description: 'Result variable name', required: true, type: 'string' },
            { name: 'model', description: 'Model name (e.g., phi3, mistral)', type: 'string' },
            { name: 'endpoint', description: 'Custom API endpoint', type: 'string' },
            { name: 'system', description: 'System prompt', type: 'string' },
            { name: 'temperature', description: 'Temperature (0.0-2.0)', type: 'number' },
            { name: 'maxTokens', description: 'Max tokens in response', type: 'number' },
            { name: 'responseFormat', description: 'Response format', type: 'enum', values: ['text', 'json'] },
            { name: 'cache', description: 'Cache response', type: 'boolean', default: 'false' },
            { name: 'timeout', description: 'Timeout in seconds', type: 'number', default: '30' },
        ]
    },
    {
        name: 'prompt',
        namespace: 'q',
        description: 'Prompt text for LLM completion mode.',
        category: 'LLM',
        attributes: []
    },
    {
        name: 'message',
        namespace: 'q',
        description: 'Chat message for LLM chat mode.',
        category: 'LLM',
        attributes: [
            { name: 'role', description: 'Message role', type: 'enum', values: ['system', 'user', 'assistant'], default: 'user' },
        ]
    },

    // Events
    {
        name: 'dispatchEvent',
        namespace: 'q',
        description: 'Publish an event to the message queue.',
        category: 'Events',
        selfClosing: true,
        attributes: [
            { name: 'event', description: 'Event name', required: true, type: 'string' },
            { name: 'data', description: 'Event data (JSON)', type: 'expression' },
            { name: 'queue', description: 'Target queue', type: 'string' },
            { name: 'priority', description: 'Event priority', type: 'enum', values: ['low', 'normal', 'high'], default: 'normal' },
            { name: 'delay', description: 'Delay before dispatch', type: 'string' },
        ]
    },
    {
        name: 'onEvent',
        namespace: 'q',
        description: 'Subscribe to and handle events.',
        category: 'Events',
        attributes: [
            { name: 'event', description: 'Event pattern (e.g., "user.*")', required: true, type: 'string' },
            { name: 'queue', description: 'Queue name', type: 'string' },
            { name: 'maxRetries', description: 'Max retry attempts', type: 'number', default: '0' },
            { name: 'retryDelay', description: 'Delay between retries', type: 'string' },
            { name: 'filter', description: 'Filter expression', type: 'expression' },
            { name: 'concurrent', description: 'Concurrent handlers', type: 'number', default: '1' },
        ]
    },

    // Component Composition
    {
        name: 'import',
        namespace: 'q',
        description: 'Import a component for use in this component.',
        category: 'Composition',
        selfClosing: true,
        attributes: [
            { name: 'component', description: 'Component name to import', required: true, type: 'string' },
            { name: 'from', description: 'Path to component file', type: 'string' },
            { name: 'as', description: 'Alias for imported component', type: 'string' },
        ]
    },
    {
        name: 'slot',
        namespace: 'q',
        description: 'Content projection slot for component composition.',
        category: 'Composition',
        attributes: [
            { name: 'name', description: 'Slot name', type: 'string', default: 'default' },
        ]
    },

    // Data Import
    {
        name: 'data',
        namespace: 'q',
        description: 'Import and transform data from external sources.',
        category: 'Data',
        attributes: [
            { name: 'name', description: 'Result variable name', required: true, type: 'string' },
            { name: 'source', description: 'Data source URL or path', required: true, type: 'string' },
            { name: 'type', description: 'Data type', type: 'enum', values: ['csv', 'json', 'xml', 'excel'], default: 'csv' },
            { name: 'cache', description: 'Cache data', type: 'boolean', default: 'true' },
            { name: 'ttl', description: 'Cache TTL in seconds', type: 'number' },
            { name: 'delimiter', description: 'CSV delimiter', type: 'string', default: ',' },
            { name: 'header', description: 'First row is header', type: 'boolean', default: 'true' },
            { name: 'xpath', description: 'XPath for XML data', type: 'string' },
        ]
    },

    // Knowledge Base
    {
        name: 'knowledge',
        namespace: 'q',
        description: 'Define a knowledge base for RAG (Retrieval Augmented Generation).',
        category: 'Knowledge',
        attributes: [
            { name: 'name', description: 'Knowledge base name', required: true, type: 'string' },
            { name: 'type', description: 'Knowledge base type', type: 'enum', values: ['vector', 'graph', 'hybrid'], default: 'vector' },
        ]
    },
    {
        name: 'source',
        namespace: 'q',
        description: 'Data source for knowledge base.',
        category: 'Knowledge',
        selfClosing: true,
        attributes: [
            { name: 'type', description: 'Source type', type: 'enum', values: ['file', 'url', 'database', 'api'], required: true },
            { name: 'path', description: 'Source path or URL', required: true, type: 'string' },
            { name: 'format', description: 'Data format', type: 'enum', values: ['text', 'markdown', 'pdf', 'html', 'json'] },
        ]
    },

    // Debugging
    {
        name: 'log',
        namespace: 'q',
        description: 'Log a message for debugging.',
        category: 'Debug',
        selfClosing: true,
        attributes: [
            { name: 'level', description: 'Log level', type: 'enum', values: ['debug', 'info', 'warn', 'error'], default: 'info' },
            { name: 'message', description: 'Message to log', type: 'expression' },
            { name: 'var', description: 'Variable to log', type: 'expression' },
        ]
    },
    {
        name: 'dump',
        namespace: 'q',
        description: 'Debug dump a variable (ColdFusion cfdump-inspired).',
        category: 'Debug',
        selfClosing: true,
        attributes: [
            { name: 'var', description: 'Variable to dump', required: true, type: 'expression' },
            { name: 'label', description: 'Label for output', type: 'string' },
            { name: 'expand', description: 'Expand nested objects', type: 'boolean', default: 'true' },
        ]
    },
];

// ==============================================
// UI ENGINE TAGS (ui:)
// ==============================================

// Common layout attributes shared by most UI tags
const layoutAttributes: AttributeSchema[] = [
    { name: 'gap', description: 'Gap between children (CSS value)', type: 'string' },
    { name: 'padding', description: 'Padding (CSS value)', type: 'string' },
    { name: 'margin', description: 'Margin (CSS value)', type: 'string' },
    { name: 'align', description: 'Cross-axis alignment', type: 'enum', values: ['start', 'center', 'end', 'stretch'] },
    { name: 'justify', description: 'Main-axis alignment', type: 'enum', values: ['start', 'center', 'end', 'between', 'around'] },
    { name: 'width', description: 'Width (CSS value or "fill")', type: 'string' },
    { name: 'height', description: 'Height (CSS value or "fill")', type: 'string' },
    { name: 'background', description: 'Background color', type: 'string' },
    { name: 'color', description: 'Text color', type: 'string' },
    { name: 'border', description: 'Border (CSS value)', type: 'string' },
    { name: 'id', description: 'Element ID', type: 'string' },
    { name: 'class', description: 'CSS class(es)', type: 'string' },
    { name: 'visible', description: 'Visibility condition', type: 'expression' },
];

export const uiTags: TagSchema[] = [
    // Containers
    {
        name: 'window',
        namespace: 'ui',
        description: 'Top-level window container. Root UI element.',
        category: 'Containers',
        attributes: [
            { name: 'title', description: 'Window title', type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'hbox',
        namespace: 'ui',
        description: 'Horizontal flex container. Children arranged in a row.',
        category: 'Containers',
        attributes: [...layoutAttributes]
    },
    {
        name: 'vbox',
        namespace: 'ui',
        description: 'Vertical flex container. Children arranged in a column.',
        category: 'Containers',
        attributes: [...layoutAttributes]
    },
    {
        name: 'panel',
        namespace: 'ui',
        description: 'Bordered container with optional title.',
        category: 'Containers',
        attributes: [
            { name: 'title', description: 'Panel title', type: 'string' },
            { name: 'collapsible', description: 'Allow collapsing', type: 'boolean', default: 'false' },
            ...layoutAttributes
        ]
    },
    {
        name: 'grid',
        namespace: 'ui',
        description: 'CSS Grid container for 2D layouts.',
        category: 'Containers',
        attributes: [
            { name: 'columns', description: 'Grid columns (e.g., "3" or "1fr 2fr 1fr")', type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'tabpanel',
        namespace: 'ui',
        description: 'Tabbed content container. Contains ui:tab children.',
        category: 'Containers',
        attributes: [...layoutAttributes]
    },
    {
        name: 'tab',
        namespace: 'ui',
        description: 'Individual tab inside a tabpanel.',
        category: 'Containers',
        attributes: [
            { name: 'title', description: 'Tab title', required: true, type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'accordion',
        namespace: 'ui',
        description: 'Collapsible sections container.',
        category: 'Containers',
        attributes: [...layoutAttributes]
    },
    {
        name: 'section',
        namespace: 'ui',
        description: 'Collapsible section inside accordion.',
        category: 'Containers',
        attributes: [
            { name: 'title', description: 'Section title', required: true, type: 'string' },
            { name: 'expanded', description: 'Initially expanded', type: 'boolean', default: 'false' },
            ...layoutAttributes
        ]
    },
    {
        name: 'dividedbox',
        namespace: 'ui',
        description: 'Resizable split container.',
        category: 'Containers',
        attributes: [
            { name: 'direction', description: 'Split direction', type: 'enum', values: ['horizontal', 'vertical'], default: 'horizontal' },
            ...layoutAttributes
        ]
    },
    {
        name: 'scrollbox',
        namespace: 'ui',
        description: 'Scrollable container.',
        category: 'Containers',
        attributes: [...layoutAttributes]
    },
    {
        name: 'form',
        namespace: 'ui',
        description: 'Form container with validation support.',
        category: 'Forms',
        attributes: [
            { name: 'on-submit', description: 'Submit handler function', type: 'string' },
            { name: 'validation', description: 'Validation mode', type: 'enum', values: ['client', 'server', 'both'], default: 'both' },
            { name: 'error-display', description: 'Error display mode', type: 'enum', values: ['inline', 'summary', 'both'], default: 'inline' },
            { name: 'novalidate', description: 'Disable HTML5 validation', type: 'boolean', default: 'false' },
            ...layoutAttributes
        ]
    },
    {
        name: 'formitem',
        namespace: 'ui',
        description: 'Form field with label.',
        category: 'Forms',
        attributes: [
            { name: 'label', description: 'Field label', type: 'string' },
            ...layoutAttributes
        ]
    },

    // Widgets
    {
        name: 'text',
        namespace: 'ui',
        description: 'Text display widget.',
        category: 'Widgets',
        attributes: [
            { name: 'size', description: 'Text size', type: 'enum', values: ['xs', 'sm', 'md', 'lg', 'xl', '2xl'] },
            { name: 'weight', description: 'Font weight', type: 'enum', values: ['normal', 'bold', 'light'] },
            ...layoutAttributes
        ]
    },
    {
        name: 'button',
        namespace: 'ui',
        description: 'Clickable button widget.',
        category: 'Widgets',
        attributes: [
            { name: 'on-click', description: 'Click handler function', type: 'string' },
            { name: 'variant', description: 'Button style variant', type: 'enum', values: ['primary', 'secondary', 'danger', 'success'] },
            { name: 'disabled', description: 'Disable button', type: 'boolean', default: 'false' },
            ...layoutAttributes
        ]
    },
    {
        name: 'input',
        namespace: 'ui',
        description: 'Text input field with validation.',
        category: 'Widgets',
        selfClosing: true,
        attributes: [
            { name: 'bind', description: 'Two-way data binding variable', type: 'string' },
            { name: 'type', description: 'Input type', type: 'enum', values: ['text', 'password', 'email', 'number', 'tel', 'url', 'date'], default: 'text' },
            { name: 'placeholder', description: 'Placeholder text', type: 'string' },
            { name: 'on-change', description: 'Change handler', type: 'string' },
            { name: 'on-submit', description: 'Submit handler (Enter key)', type: 'string' },
            { name: 'required', description: 'Required field', type: 'boolean', default: 'false' },
            { name: 'min', description: 'Minimum value', type: 'string' },
            { name: 'max', description: 'Maximum value', type: 'string' },
            { name: 'minlength', description: 'Minimum length', type: 'number' },
            { name: 'maxlength', description: 'Maximum length', type: 'number' },
            { name: 'pattern', description: 'Validation regex', type: 'string' },
            { name: 'error-message', description: 'Custom error message', type: 'string' },
            { name: 'validators', description: 'Validator names (comma-separated)', type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'checkbox',
        namespace: 'ui',
        description: 'Checkbox input.',
        category: 'Widgets',
        selfClosing: true,
        attributes: [
            { name: 'bind', description: 'Two-way data binding variable', type: 'string' },
            { name: 'label', description: 'Checkbox label', type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'radio',
        namespace: 'ui',
        description: 'Radio button group.',
        category: 'Widgets',
        selfClosing: true,
        attributes: [
            { name: 'bind', description: 'Two-way data binding variable', type: 'string' },
            { name: 'options', description: 'Options (comma-separated or source)', type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'switch',
        namespace: 'ui',
        description: 'Toggle switch widget.',
        category: 'Widgets',
        selfClosing: true,
        attributes: [
            { name: 'bind', description: 'Two-way data binding variable', type: 'string' },
            { name: 'label', description: 'Switch label', type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'select',
        namespace: 'ui',
        description: 'Dropdown select widget.',
        category: 'Widgets',
        attributes: [
            { name: 'bind', description: 'Two-way data binding variable', type: 'string' },
            { name: 'options', description: 'Options (comma-separated)', type: 'string' },
            { name: 'source', description: 'Data source for options', type: 'expression' },
            ...layoutAttributes
        ]
    },
    {
        name: 'option',
        namespace: 'ui',
        description: 'Option for select, menu, or dropdown.',
        category: 'Widgets',
        selfClosing: true,
        attributes: [
            { name: 'value', description: 'Option value', type: 'string' },
            { name: 'label', description: 'Display label', type: 'string' },
            { name: 'on-click', description: 'Click handler', type: 'string' },
        ]
    },
    {
        name: 'table',
        namespace: 'ui',
        description: 'Data table widget.',
        category: 'Data Display',
        attributes: [
            { name: 'source', description: 'Data source binding', type: 'expression' },
            ...layoutAttributes
        ]
    },
    {
        name: 'column',
        namespace: 'ui',
        description: 'Table column definition.',
        category: 'Data Display',
        selfClosing: true,
        attributes: [
            { name: 'key', description: 'Data key/field name', required: true, type: 'string' },
            { name: 'label', description: 'Column header label', type: 'string' },
            { name: 'width', description: 'Column width', type: 'string' },
            { name: 'align', description: 'Text alignment', type: 'enum', values: ['left', 'center', 'right'] },
        ]
    },
    {
        name: 'list',
        namespace: 'ui',
        description: 'Repeating list widget.',
        category: 'Data Display',
        attributes: [
            { name: 'source', description: 'Data source binding', type: 'expression' },
            { name: 'as', description: 'Loop variable name', type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'item',
        namespace: 'ui',
        description: 'List item container.',
        category: 'Data Display',
        attributes: [...layoutAttributes]
    },
    {
        name: 'image',
        namespace: 'ui',
        description: 'Image display widget.',
        category: 'Media',
        selfClosing: true,
        attributes: [
            { name: 'src', description: 'Image source URL', required: true, type: 'expression' },
            { name: 'alt', description: 'Alt text', type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'link',
        namespace: 'ui',
        description: 'Hyperlink widget.',
        category: 'Navigation',
        attributes: [
            { name: 'to', description: 'Target URL/path', required: true, type: 'string' },
            { name: 'external', description: 'Open in new tab', type: 'boolean', default: 'false' },
            ...layoutAttributes
        ]
    },
    {
        name: 'progress',
        namespace: 'ui',
        description: 'Progress bar widget.',
        category: 'Feedback',
        selfClosing: true,
        attributes: [
            { name: 'value', description: 'Current value', type: 'expression' },
            { name: 'max', description: 'Maximum value', type: 'string', default: '100' },
            ...layoutAttributes
        ]
    },
    {
        name: 'loading',
        namespace: 'ui',
        description: 'Loading indicator widget.',
        category: 'Feedback',
        selfClosing: true,
        attributes: [
            { name: 'text', description: 'Loading text', type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'badge',
        namespace: 'ui',
        description: 'Small status badge.',
        category: 'Feedback',
        attributes: [
            { name: 'variant', description: 'Badge style', type: 'enum', values: ['primary', 'secondary', 'danger', 'success', 'warning'] },
            ...layoutAttributes
        ]
    },
    {
        name: 'tree',
        namespace: 'ui',
        description: 'Tree view widget.',
        category: 'Data Display',
        selfClosing: true,
        attributes: [
            { name: 'source', description: 'Tree data source', type: 'expression' },
            { name: 'on-select', description: 'Selection handler', type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'menu',
        namespace: 'ui',
        description: 'Menu container.',
        category: 'Navigation',
        attributes: [...layoutAttributes]
    },
    {
        name: 'log',
        namespace: 'ui',
        description: 'Scrollable log output widget.',
        category: 'Debug',
        selfClosing: true,
        attributes: [
            { name: 'auto-scroll', description: 'Auto-scroll to bottom', type: 'boolean', default: 'true' },
            { name: 'max-lines', description: 'Max lines to display', type: 'number' },
            ...layoutAttributes
        ]
    },
    {
        name: 'markdown',
        namespace: 'ui',
        description: 'Markdown rendered content.',
        category: 'Content',
        attributes: [...layoutAttributes]
    },
    {
        name: 'header',
        namespace: 'ui',
        description: 'Page/window header.',
        category: 'Layout',
        attributes: [
            { name: 'title', description: 'Header title', type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'footer',
        namespace: 'ui',
        description: 'Page/window footer.',
        category: 'Layout',
        attributes: [...layoutAttributes]
    },
    {
        name: 'rule',
        namespace: 'ui',
        description: 'Horizontal separator line.',
        category: 'Layout',
        selfClosing: true,
        attributes: []
    },
    {
        name: 'spacer',
        namespace: 'ui',
        description: 'Flexible space filler.',
        category: 'Layout',
        selfClosing: true,
        attributes: [
            { name: 'size', description: 'Fixed size', type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'validator',
        namespace: 'ui',
        description: 'Custom validation rule.',
        category: 'Forms',
        selfClosing: true,
        attributes: [
            { name: 'name', description: 'Validator name', required: true, type: 'string' },
            { name: 'type', description: 'Rule type', type: 'enum', values: ['pattern', 'email', 'url', 'phone', 'match', 'custom'] },
            { name: 'pattern', description: 'Regex pattern', type: 'string' },
            { name: 'match', description: 'Field to match', type: 'string' },
            { name: 'expression', description: 'Custom JS expression', type: 'string' },
            { name: 'message', description: 'Error message', required: true, type: 'string' },
            { name: 'field', description: 'Target field', type: 'string' },
            { name: 'trigger', description: 'When to validate', type: 'enum', values: ['blur', 'change', 'input', 'submit'], default: 'submit' },
        ]
    },
    {
        name: 'animate',
        namespace: 'ui',
        description: 'Animation wrapper container.',
        category: 'Animation',
        attributes: [
            { name: 'type', description: 'Animation type', type: 'enum', values: ['fade', 'slide', 'scale', 'rotate', 'slide-left', 'slide-right', 'slide-up', 'slide-down', 'bounce', 'pulse', 'shake'] },
            { name: 'duration', description: 'Duration in ms', type: 'string', default: '300' },
            { name: 'delay', description: 'Delay in ms', type: 'string', default: '0' },
            { name: 'easing', description: 'Easing function', type: 'enum', values: ['ease', 'ease-in', 'ease-out', 'ease-in-out', 'linear', 'spring', 'bounce'] },
            { name: 'repeat', description: 'Repeat count', type: 'string' },
            { name: 'trigger', description: 'Animation trigger', type: 'enum', values: ['on-load', 'on-hover', 'on-click', 'on-visible'] },
            ...layoutAttributes
        ]
    },

    // Component Library
    {
        name: 'card',
        namespace: 'ui',
        description: 'Card component with header, body, footer.',
        category: 'Components',
        attributes: [
            { name: 'title', description: 'Card title', type: 'string' },
            { name: 'subtitle', description: 'Card subtitle', type: 'string' },
            { name: 'image', description: 'Header image URL', type: 'string' },
            { name: 'variant', description: 'Card style', type: 'enum', values: ['default', 'elevated', 'outlined'] },
            ...layoutAttributes
        ]
    },
    {
        name: 'card-header',
        namespace: 'ui',
        description: 'Card header section.',
        category: 'Components',
        attributes: [...layoutAttributes]
    },
    {
        name: 'card-body',
        namespace: 'ui',
        description: 'Card body section.',
        category: 'Components',
        attributes: [...layoutAttributes]
    },
    {
        name: 'card-footer',
        namespace: 'ui',
        description: 'Card footer section.',
        category: 'Components',
        attributes: [...layoutAttributes]
    },
    {
        name: 'modal',
        namespace: 'ui',
        description: 'Modal/dialog overlay.',
        category: 'Components',
        attributes: [
            { name: 'modal-id', description: 'Modal ID for targeting', type: 'string' },
            { name: 'title', description: 'Modal title', type: 'string' },
            { name: 'open', description: 'Initial open state', type: 'boolean', default: 'false' },
            { name: 'closable', description: 'Show close button', type: 'boolean', default: 'true' },
            { name: 'size', description: 'Modal size', type: 'enum', values: ['sm', 'md', 'lg', 'xl', 'full'] },
            ...layoutAttributes
        ]
    },
    {
        name: 'chart',
        namespace: 'ui',
        description: 'Simple chart widget.',
        category: 'Data Display',
        selfClosing: true,
        attributes: [
            { name: 'type', description: 'Chart type', type: 'enum', values: ['bar', 'line', 'pie', 'doughnut'], default: 'bar' },
            { name: 'source', description: 'Data source', type: 'expression' },
            { name: 'labels', description: 'Labels (comma-separated)', type: 'string' },
            { name: 'values', description: 'Values (comma-separated)', type: 'string' },
            { name: 'title', description: 'Chart title', type: 'string' },
            { name: 'colors', description: 'Colors (comma-separated)', type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'avatar',
        namespace: 'ui',
        description: 'User avatar with image/initials.',
        category: 'Components',
        selfClosing: true,
        attributes: [
            { name: 'src', description: 'Image URL', type: 'string' },
            { name: 'name', description: 'Name for initials fallback', type: 'string' },
            { name: 'size', description: 'Avatar size', type: 'enum', values: ['xs', 'sm', 'md', 'lg', 'xl'] },
            { name: 'shape', description: 'Avatar shape', type: 'enum', values: ['circle', 'square'], default: 'circle' },
            { name: 'status', description: 'Status indicator', type: 'enum', values: ['online', 'offline', 'away', 'busy'] },
            ...layoutAttributes
        ]
    },
    {
        name: 'tooltip',
        namespace: 'ui',
        description: 'Tooltip on hover.',
        category: 'Components',
        attributes: [
            { name: 'content', description: 'Tooltip text', type: 'string' },
            { name: 'position', description: 'Tooltip position', type: 'enum', values: ['top', 'bottom', 'left', 'right'], default: 'top' },
            ...layoutAttributes
        ]
    },
    {
        name: 'dropdown',
        namespace: 'ui',
        description: 'Dropdown menu.',
        category: 'Navigation',
        attributes: [
            { name: 'label', description: 'Trigger button label', type: 'string' },
            { name: 'trigger', description: 'Trigger mode', type: 'enum', values: ['click', 'hover'], default: 'click' },
            { name: 'align', description: 'Dropdown alignment', type: 'enum', values: ['left', 'right'], default: 'left' },
            ...layoutAttributes
        ]
    },
    {
        name: 'alert',
        namespace: 'ui',
        description: 'Alert/notification box.',
        category: 'Feedback',
        attributes: [
            { name: 'title', description: 'Alert title', type: 'string' },
            { name: 'variant', description: 'Alert style', type: 'enum', values: ['info', 'success', 'warning', 'danger'], default: 'info' },
            { name: 'dismissible', description: 'Allow dismissing', type: 'boolean', default: 'false' },
            { name: 'icon', description: 'Icon name', type: 'string' },
            ...layoutAttributes
        ]
    },
    {
        name: 'breadcrumb',
        namespace: 'ui',
        description: 'Navigation breadcrumbs.',
        category: 'Navigation',
        attributes: [
            { name: 'separator', description: 'Separator character', type: 'string', default: '/' },
            ...layoutAttributes
        ]
    },
    {
        name: 'breadcrumb-item',
        namespace: 'ui',
        description: 'Breadcrumb navigation item.',
        category: 'Navigation',
        selfClosing: true,
        attributes: [
            { name: 'label', description: 'Item label', type: 'string' },
            { name: 'to', description: 'Link URL', type: 'string' },
            { name: 'icon', description: 'Icon name', type: 'string' },
        ]
    },
    {
        name: 'pagination',
        namespace: 'ui',
        description: 'Pagination controls.',
        category: 'Navigation',
        selfClosing: true,
        attributes: [
            { name: 'total', description: 'Total items', type: 'expression' },
            { name: 'page-size', description: 'Items per page', type: 'string', default: '10' },
            { name: 'current', description: 'Current page', type: 'string', default: '1' },
            { name: 'bind', description: 'Binding for current page', type: 'string' },
            { name: 'on-change', description: 'Page change handler', type: 'string' },
            { name: 'show-total', description: 'Show total count', type: 'boolean', default: 'false' },
            { name: 'show-jump', description: 'Show page jump input', type: 'boolean', default: 'false' },
            ...layoutAttributes
        ]
    },
    {
        name: 'skeleton',
        namespace: 'ui',
        description: 'Loading skeleton placeholder.',
        category: 'Feedback',
        selfClosing: true,
        attributes: [
            { name: 'variant', description: 'Skeleton type', type: 'enum', values: ['text', 'circle', 'rect', 'card'], default: 'text' },
            { name: 'lines', description: 'Number of lines', type: 'number', default: '1' },
            { name: 'animated', description: 'Animate skeleton', type: 'boolean', default: 'true' },
            ...layoutAttributes
        ]
    },
    {
        name: 'theme',
        namespace: 'ui',
        description: 'Theme configuration.',
        category: 'Theming',
        attributes: [
            { name: 'name', description: 'Custom theme name', type: 'string' },
            { name: 'preset', description: 'Base theme preset', type: 'enum', values: ['light', 'dark'], default: 'light' },
            { name: 'auto-switch', description: 'Auto dark/light switching', type: 'boolean', default: 'false' },
        ]
    },
    {
        name: 'color',
        namespace: 'ui',
        description: 'Custom color definition for theme.',
        category: 'Theming',
        selfClosing: true,
        attributes: [
            { name: 'name', description: 'Color token name', required: true, type: 'string' },
            { name: 'value', description: 'CSS color value', required: true, type: 'string' },
        ]
    },
];

// Combine all tags for lookup
export const allTags: TagSchema[] = [...quantumTags, ...uiTags];

// Create lookup maps for quick access
export const tagsByName: Map<string, TagSchema> = new Map(
    allTags.map(tag => [`${tag.namespace}:${tag.name}`, tag])
);

export const tagsByNamespace: Map<string, TagSchema[]> = new Map([
    ['q', quantumTags],
    ['ui', uiTags],
]);

/**
 * Get tag schema by full name (e.g., "q:component", "ui:button")
 */
export function getTagSchema(fullName: string): TagSchema | undefined {
    return tagsByName.get(fullName);
}

/**
 * Get all tags in a namespace
 */
export function getTagsInNamespace(namespace: 'q' | 'ui' | 'qg' | 'qt' | 'qtest'): TagSchema[] {
    return tagsByNamespace.get(namespace) || [];
}

/**
 * Get attribute schema for a tag
 */
export function getAttributeSchema(tagName: string, attrName: string): AttributeSchema | undefined {
    const tag = tagsByName.get(tagName);
    if (!tag) return undefined;
    return tag.attributes.find(attr => attr.name === attrName);
}

/**
 * Get all attribute names for a tag
 */
export function getAttributeNames(tagName: string): string[] {
    const tag = tagsByName.get(tagName);
    if (!tag) return [];
    return tag.attributes.map(attr => attr.name);
}

/**
 * Check if an attribute is required
 */
export function isAttributeRequired(tagName: string, attrName: string): boolean {
    const attr = getAttributeSchema(tagName, attrName);
    return attr?.required ?? false;
}

/**
 * Get required attributes for a tag
 */
export function getRequiredAttributes(tagName: string): string[] {
    const tag = tagsByName.get(tagName);
    if (!tag) return [];
    return tag.attributes.filter(attr => attr.required).map(attr => attr.name);
}
