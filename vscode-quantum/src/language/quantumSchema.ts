/**
 * Quantum Framework Tag and Attribute Schema
 *
 * Complete schema of all Quantum tags (q:, ui:, qg:, qt:)
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
    namespace: 'q' | 'ui' | 'qg' | 'qt';
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
    // BEGIN GENERATED: Core and AI tags — python scripts/generate-editor-schemas.py (do not edit)
    {
        name: 'component',
        namespace: 'q',
        description: 'A page or a reusable component. A file of `components/` is served at its path (ROUTE-1).',
        category: 'Core',
        attributes: [
            { name: 'name', description: 'Component name', required: true, type: 'string' },
            { name: 'require_auth', description: 'Only an authenticated, unexpired session sees it (AUTH-1)', type: 'boolean', default: 'false' },
            { name: 'require_role', description: 'Comma-separated roles, one of which `session.userRole` must have (AUTH-2)', type: 'string' },
            { name: 'login_url', description: 'Where an unauthenticated visitor is sent; a local path (AUTH-4)', type: 'string' },
            { name: 'require_permission', description: 'Required permission(s)', type: 'string' },
            { name: 'interactive', description: 'Client-side hydration', type: 'boolean', default: 'false' },
            { name: 'type', description: 'Component type', type: 'string', default: 'pure' },
            { name: 'port', description: 'Port', type: 'number' },
        ]
    },
    {
        name: 'param',
        namespace: 'q',
        description: 'A parameter of a component, function, action, query or tool, converted to `type` and checked against its rules (FN-1, ACT-2, DB-1)',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'name', description: 'Parameter name', required: true, type: 'string' },
            { name: 'type', description: 'Type the value is converted to. `datetime` and `time` exist only for a q:query\'s param; in a q:query the type is one of string, integer, decimal, boolean, datetime, date, time, array, json (PARSE-5)', type: 'enum', values: ['string', 'text', 'number', 'integer', 'int', 'long', 'numeric', 'decimal', 'float', 'double', 'boolean', 'email', 'url', 'date', 'array', 'object', 'json', 'any', 'file', 'binary', 'upload', 'datetime', 'time'], default: 'string' },
            { name: 'default', description: 'Value when none is given', type: 'string' },
            { name: 'value', description: 'The value bound (in a q:query, q:invoke)', type: 'expression' },
            { name: 'description', description: 'What it is (shown to the model in a q:tool)', type: 'string' },
            { name: 'validate', description: 'A named validator, or a regular expression starting with `^`', type: 'string', values: ['email', 'url', 'phone', 'cep', 'cpf', 'cnpj', 'uuid', 'creditcard', 'ipv4', 'ipv6'] },
            { name: 'accept', description: 'Accepted uploads: `image/*`, `.pdf`, `application/pdf` (ACT-11)', type: 'string' },
            { name: 'maxsize', description: 'Largest upload: `500KB`, `5MB`, `1GB` (FILE-1)', type: 'string' },
            { name: 'maxLength', description: 'Longest text bound to a query (DB-1)', type: 'number' },
            { name: 'scale', description: 'Decimal places a query value is rounded to (DB-1)', type: 'number' },
            { name: 'null', description: 'Bind an empty value as NULL (q:query)', type: 'boolean' },
            { name: 'source', description: 'Where the value comes from', type: 'string' },
            { name: 'required', description: 'The value must be given and not empty', type: 'boolean', default: 'false' },
            { name: 'min', description: 'Smallest number accepted', type: 'number' },
            { name: 'max', description: 'Largest number accepted', type: 'number' },
            { name: 'minlength', description: 'Shortest text accepted', type: 'number' },
            { name: 'maxlength', description: 'Longest text accepted', type: 'number' },
            { name: 'pattern', description: 'Regular expression the text must match', type: 'string' },
            { name: 'enum', description: 'Comma-separated list of the values accepted', type: 'string' },
            { name: 'range', description: 'Inclusive range, e.g. `1..10`', type: 'string' },
        ]
    },
    {
        name: 'return',
        namespace: 'q',
        description: 'Ends the component or function with a value (RET-1, RET-2)',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'value', description: 'The value; exactly one expression keeps its type', type: 'expression' },
            { name: 'name', description: 'Name of the returned value', type: 'string' },
            { name: 'type', description: 'Type of the returned value', type: 'string' },
            { name: 'description', description: 'What it is', type: 'string' },
        ]
    },
    {
        name: 'set',
        namespace: 'q',
        description: 'Stores a variable, converted to `type`, checked and changed by `operation` (ERR-1, SET-1, SET-3, SET-4)',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'name', description: 'Variable name (`session.x`, `application.x` for the scopes)', required: true, type: 'string' },
            { name: 'value', description: 'The value', type: 'expression' },
            { name: 'type', description: 'Type the value is converted to (ERR-1); without it, a value that is one expression keeps its type (SET-5)', type: 'enum', values: ['string', 'number', 'integer', 'decimal', 'boolean', 'array', 'object', 'json', 'text', 'int', 'long', 'numeric', 'float', 'double'] },
            { name: 'default', description: 'Stored when value resolves to nothing (SET-1)', type: 'string' },
            { name: 'operation', description: 'What to do with the variable (SET-3)', type: 'enum', values: ['assign', 'increment', 'decrement', 'add', 'multiply', 'append', 'prepend', 'remove', 'removeAt', 'clear', 'sort', 'reverse', 'unique', 'merge', 'setProperty', 'deleteProperty', 'clone', 'uppercase', 'lowercase', 'trim', 'format'], default: 'assign' },
            { name: 'step', description: 'Step of increment/decrement', type: 'number', default: '1' },
            { name: 'index', description: 'Position for removeAt', type: 'number' },
            { name: 'key', description: 'Key for setProperty/deleteProperty', type: 'string' },
            { name: 'source', description: 'Variable clone copies', type: 'string' },
            { name: 'scope', description: 'Where the variable lives', type: 'enum', values: ['local', 'function', 'component', 'session', 'application', 'request'], default: 'local' },
            { name: 'nullable', description: '`false`: a null value is an error', type: 'boolean', default: 'true' },
            { name: 'validate', description: 'A named validator, or a regular expression starting with `^` (SET-4)', type: 'string', values: ['email', 'url', 'phone', 'cep', 'cpf', 'cnpj', 'uuid', 'creditcard', 'ipv4', 'ipv6'] },
            { name: 'required', description: 'The value must be given and not empty', type: 'boolean', default: 'false' },
            { name: 'min', description: 'Smallest number accepted', type: 'number' },
            { name: 'max', description: 'Largest number accepted', type: 'number' },
            { name: 'minlength', description: 'Shortest text accepted', type: 'number' },
            { name: 'maxlength', description: 'Longest text accepted', type: 'number' },
            { name: 'pattern', description: 'Regular expression the text must match', type: 'string' },
            { name: 'enum', description: 'Comma-separated list of the values accepted', type: 'string' },
            { name: 'range', description: 'Inclusive range, e.g. `1..10`', type: 'string' },
        ]
    },
    {
        name: 'if',
        namespace: 'q',
        description: 'Runs its body when the condition is true (IF-1..IF-4)',
        category: 'Core',
        allowedChildren: ['q:elseif', 'q:else'],
        attributes: [
            { name: 'condition', description: 'An expression; a missing name makes it false (EXPR-5)', required: true, type: 'expression' },
        ]
    },
    {
        name: 'elseif',
        namespace: 'q',
        description: 'Another branch of the q:if before it',
        category: 'Core',
        attributes: [
            { name: 'condition', description: 'An expression', required: true, type: 'expression' },
        ]
    },
    {
        name: 'else',
        namespace: 'q',
        description: 'The branch when no condition was true',
        category: 'Core',
        attributes: [
        ]
    },
    {
        name: 'loop',
        namespace: 'q',
        description: 'Repeats its body (LOOP-1..LOOP-5)',
        category: 'Core',
        attributes: [
            { name: 'type', description: 'Loop type; inferred when missing', type: 'enum', values: ['range', 'array', 'list', 'query'] },
            { name: 'var', description: 'The loop variable', type: 'string' },
            { name: 'from', description: 'First number (range)', type: 'expression' },
            { name: 'to', description: 'Last number, included (range)', type: 'expression' },
            { name: 'step', description: 'Step (range)', type: 'number', default: '1' },
            { name: 'items', description: 'The list (array) or text (list)', type: 'expression' },
            { name: 'index', description: 'Name of the position variable, from 0', type: 'string' },
            { name: 'delimiter', description: 'Separator of a list loop', type: 'string', default: ',' },
            { name: 'query', description: 'Name of the query to loop over (LOOP-4)', type: 'string' },
        ]
    },
    {
        name: 'function',
        namespace: 'q',
        description: 'A function the component\'s expressions can call (FN-1..FN-4)',
        category: 'Core',
        allowedChildren: ['q:param', 'q:return'],
        attributes: [
            { name: 'name', description: 'Function name', required: true, type: 'string' },
            { name: 'returnType', description: 'Type the returned value is converted to (FN-4)', type: 'enum', values: ['any', 'void', 'string', 'text', 'number', 'integer', 'int', 'long', 'numeric', 'decimal', 'float', 'double', 'boolean', 'email', 'url', 'array', 'object', 'json'], default: 'any' },
            { name: 'description', description: 'What it does', type: 'string' },
            { name: 'hint', description: 'A hint for readers', type: 'string' },
        ]
    },
    {
        name: 'query',
        namespace: 'q',
        description: 'Runs SQL on a declared datasource, binding `:name` to q:param (DB-1..DB-5, DB-9, UI-13)',
        category: 'Core',
        allowedChildren: ['q:param'],
        attributes: [
            { name: 'name', description: 'Result variable (`<name>`, `<name>_result`)', type: 'string' },
            { name: 'datasource', description: 'Datasource declared in quantum.config.yaml, or `knowledge:<name>` (IA-3)', type: 'string' },
            { name: 'source', description: 'Query of queries: an earlier query\'s name (DB-3)', type: 'string' },
            { name: 'result', description: 'Another name for `<name>_result`', type: 'string' },
            { name: 'paginate', description: 'Return one page (DB-2)', type: 'boolean', default: 'false' },
            { name: 'page', description: 'Page number, an expression (DB-9)', type: 'expression' },
            { name: 'pageSize', description: 'Rows per page', type: 'number' },
            { name: 'page_size', description: 'Rows per page', type: 'number' },
            { name: 'sortable', description: 'Sort by the URL\'s ?sort=/&dir= (UI-13)', type: 'boolean', default: 'false' },
            { name: 'onerror', description: '`fail` stops the page with the error; `continue` hands it to `<name>_result` (INV-2, IA-5)', type: 'enum', values: ['fail', 'continue'], default: 'fail' },
        ]
    },
    {
        name: 'transaction',
        namespace: 'q',
        description: 'Its queries commit together or roll back together (DB-4)',
        category: 'Core',
        allowedChildren: ['q:query'],
        attributes: [
            { name: 'datasource', description: 'Datasource of the queries that declare none', type: 'string' },
            { name: 'isolationLevel', description: 'Isolation level', type: 'enum', values: ['READ_UNCOMMITTED', 'READ_COMMITTED', 'REPEATABLE_READ', 'SERIALIZABLE'], default: 'READ_COMMITTED' },
            { name: 'isolation', description: 'Isolation level (same as isolationLevel)', type: 'enum', values: ['READ_UNCOMMITTED', 'READ_COMMITTED', 'REPEATABLE_READ', 'SERIALIZABLE'] },
        ]
    },
    {
        name: 'invoke',
        namespace: 'q',
        description: 'Calls a URL, a declared service or a function (INV-1, INV-2, SVC-3)',
        category: 'Core',
        allowedChildren: ['q:param', 'q:header', 'q:body'],
        attributes: [
            { name: 'name', description: 'Result variable', required: true, type: 'string' },
            { name: 'url', description: 'URL to request', type: 'string' },
            { name: 'service', description: 'Name registered with @service (SVC-3)', type: 'string' },
            { name: 'function', description: 'Function to call', type: 'string' },
            { name: 'component', description: 'Component to call', type: 'string' },
            { name: 'method', description: 'HTTP method', type: 'enum', values: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'], default: 'GET' },
            { name: 'timeout', description: 'Seconds to wait', type: 'number', default: '30' },
            { name: 'contentType', description: 'Type of the body', type: 'string', default: 'application/json' },
            { name: 'authType', description: 'Authentication', type: 'enum', values: ['bearer', 'apikey', 'basic'] },
            { name: 'authToken', description: 'Token for bearer/apikey', type: 'string' },
            { name: 'authHeader', description: 'Header for apikey', type: 'string' },
            { name: 'authUsername', description: 'User for basic', type: 'string' },
            { name: 'authPassword', description: 'Password for basic', type: 'string' },
            { name: 'retry', description: 'More attempts when it times out or cannot connect', type: 'number', default: '0' },
            { name: 'retryDelay', description: 'Milliseconds between attempts', type: 'number', default: '1000' },
            { name: 'responseFormat', description: 'How to read the response', type: 'string', default: 'auto' },
            { name: 'cache', description: 'Cache the response', type: 'boolean' },
            { name: 'ttl', description: 'Cache seconds', type: 'number' },
            { name: 'result', description: 'Another name for `<name>_result`', type: 'string' },
            { name: 'onerror', description: '`fail` stops the page with the error; `continue` hands it to `<name>_result` (INV-2, IA-5)', type: 'enum', values: ['fail', 'continue'], default: 'fail' },
        ]
    },
    {
        name: 'header',
        namespace: 'q',
        description: 'A header of a q:invoke or q:data request',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'name', description: 'Header name', required: true, type: 'string' },
            { name: 'value', description: 'Header value', type: 'expression' },
        ]
    },
    {
        name: 'body',
        namespace: 'q',
        description: 'The body of a q:invoke request (with expressions)',
        category: 'Core',
        attributes: [
        ]
    },
    {
        name: 'data',
        namespace: 'q',
        description: 'Imports CSV, JSON or XML as a list of records (DATA-1..DATA-4)',
        category: 'Core',
        allowedChildren: ['q:column', 'q:field', 'q:transform', 'q:header'],
        attributes: [
            { name: 'name', description: 'Result variable', required: true, type: 'string' },
            { name: 'source', description: 'File or URL', required: true, type: 'string' },
            { name: 'type', description: 'Format', type: 'enum', values: ['csv', 'json', 'xml'], default: 'csv' },
            { name: 'delimiter', description: 'CSV separator', type: 'string', default: ',' },
            { name: 'quote', description: 'CSV quote character', type: 'string', default: '"' },
            { name: 'header', description: 'The first CSV line is the header', type: 'boolean', default: 'true' },
            { name: 'encoding', description: 'Encoding of the file or response', type: 'string', default: 'utf-8' },
            { name: 'skip_rows', description: 'Lines to skip before the header', type: 'number', default: '0' },
            { name: 'xpath', description: 'XPath of the records (xml)', type: 'string' },
            { name: 'namespace', description: 'XML namespace', type: 'string' },
            { name: 'cache', description: 'Cache the import', type: 'boolean', default: 'true' },
            { name: 'ttl', description: 'Cache seconds', type: 'number' },
            { name: 'result', description: 'Another name for `<name>_result`', type: 'string' },
            { name: 'onerror', description: '`fail` stops the page with the error; `continue` hands it to `<name>_result` (INV-2, IA-5)', type: 'enum', values: ['fail', 'continue'], default: 'fail' },
        ]
    },
    {
        name: 'column',
        namespace: 'q',
        description: 'A CSV column converted to `type` (DATA-1)',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'name', description: 'Column name', required: true, type: 'string' },
            { name: 'type', description: 'Type', type: 'enum', values: ['string', 'integer', 'decimal', 'boolean', 'json', 'array'], default: 'string' },
        ]
    },
    {
        name: 'field',
        namespace: 'q',
        description: 'A field of a JSON/XML record (DATA-2)',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'name', description: 'Field name', required: true, type: 'string' },
            { name: 'xpath', description: 'Path relative to the record', type: 'string' },
            { name: 'path', description: 'Path relative to the record', type: 'string' },
            { name: 'type', description: 'Type', type: 'string' },
        ]
    },
    {
        name: 'transform',
        namespace: 'q',
        description: 'Operations applied in order (DATA-3)',
        category: 'Core',
        allowedChildren: ['q:filter', 'q:sort', 'q:limit', 'q:compute'],
        attributes: [
        ]
    },
    {
        name: 'filter',
        namespace: 'q',
        description: 'Keeps the records for which the condition is true',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'condition', description: 'An expression over the record\'s fields', required: true, type: 'expression' },
        ]
    },
    {
        name: 'sort',
        namespace: 'q',
        description: 'Sorts the records',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'by', description: 'Field', required: true, type: 'string' },
            { name: 'order', description: 'Order', type: 'enum', values: ['asc', 'desc'], default: 'asc' },
        ]
    },
    {
        name: 'limit',
        namespace: 'q',
        description: 'Keeps the first records',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'value', description: 'How many', required: true, type: 'number' },
        ]
    },
    {
        name: 'compute',
        namespace: 'q',
        description: 'Adds a computed field',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'field', description: 'New field', required: true, type: 'string' },
            { name: 'expression', description: 'Its value', required: true, type: 'expression' },
            { name: 'type', description: 'Type', type: 'string' },
        ]
    },
    {
        name: 'action',
        namespace: 'q',
        description: 'Runs on a POST with the `action` field; its q:params are the validated form fields (ACT-1..ACT-11)',
        category: 'Core',
        allowedChildren: ['q:param', 'q:set', 'q:query', 'q:if', 'q:loop', 'q:file', 'q:mail', 'q:flash', 'q:redirect'],
        attributes: [
            { name: 'name', description: 'Action name', required: true, type: 'string' },
            { name: 'method', description: 'HTTP method', type: 'enum', values: ['POST', 'GET'], default: 'POST' },
            { name: 'table', description: 'Take the q:params from this table\'s schema (UI-10)', type: 'string' },
            { name: 'datasource', description: 'Datasource of `table`', type: 'string' },
            { name: 'columns', description: 'Only these columns, in this order (UI-10)', type: 'string' },
            { name: 'require_role', description: 'Only these roles (comma-separated) may run it; others get 403 (AUTH-8)', type: 'string' },
        ]
    },
    {
        name: 'redirect',
        namespace: 'q',
        description: 'Ends the action or page with a redirect (ACT-3, ACT-7)',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'url', description: 'Where to', type: 'expression' },
            { name: 'to', description: 'Where to (same as url)', type: 'expression' },
            { name: 'flash', description: 'Message for the next page', type: 'expression' },
            { name: 'status', description: 'HTTP status', type: 'number', default: '302' },
        ]
    },
    {
        name: 'flash',
        namespace: 'q',
        description: 'Inside a q:action: a flash of another kind for the next page (ACT-3)',
        category: 'Core',
        attributes: [
            { name: 'type', description: 'Kind', type: 'enum', values: ['info', 'success', 'warning', 'error'], default: 'info' },
            { name: 'message', description: 'The message (or the tag\'s text)', type: 'expression' },
        ]
    },
    {
        name: 'file',
        namespace: 'q',
        description: 'Saves an upload, sends a stored file or deletes one (FILE-1, FILE-2)',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'action', description: 'What to do', required: true, type: 'enum', values: ['upload', 'send', 'delete'] },
            { name: 'file', description: 'The upload, or the stored file\'s name', required: true, type: 'expression' },
            { name: 'destination', description: 'Folder inside paths.uploads', type: 'string' },
            { name: 'nameConflict', description: 'On a clash', type: 'enum', values: ['makeUnique', 'overwrite', 'skip', 'error'], default: 'makeUnique' },
            { name: 'name', description: 'File name the browser gets (send)', type: 'string' },
            { name: 'result', description: 'Result variable', type: 'string' },
        ]
    },
    {
        name: 'mail',
        namespace: 'q',
        description: 'Sends a message through `mail:` in quantum.config.yaml (MAIL-1, MAIL-2)',
        category: 'Core',
        allowedChildren: ['q:attachment'],
        attributes: [
            { name: 'to', description: 'Recipients', required: true, type: 'expression' },
            { name: 'subject', description: 'Subject', required: true, type: 'expression' },
            { name: 'from', description: 'Sender (else mail.from)', type: 'string' },
            { name: 'cc', description: 'Copy', type: 'string' },
            { name: 'bcc', description: 'Hidden copy', type: 'string' },
            { name: 'replyTo', description: 'Reply address', type: 'string' },
            { name: 'type', description: 'Body format', type: 'enum', values: ['html', 'text'], default: 'html' },
            { name: 'body', description: 'Body, when the tag has no content', type: 'expression' },
            { name: 'name', description: 'Result name (`<name>_result`)', type: 'string', default: 'mail' },
            { name: 'onerror', description: '`fail` stops the page with the error; `continue` hands it to `<name>_result` (INV-2, IA-5)', type: 'enum', values: ['fail', 'continue'], default: 'fail' },
        ]
    },
    {
        name: 'attachment',
        namespace: 'q',
        description: 'A file attached to a q:mail',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'file', description: 'Path of the file', required: true, type: 'string' },
        ]
    },
    {
        name: 'import',
        namespace: 'q',
        description: 'Makes a component usable as `<Name/>` (COMP-1)',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'component', description: 'Component name', type: 'string' },
            { name: 'from', description: 'Folder under paths.components', type: 'string' },
            { name: 'as', description: 'Local name', type: 'string' },
            { name: 'behavior', description: 'Game behavior (Laboratory)', type: 'string' },
            { name: 'prefab', description: 'Game prefab (Laboratory)', type: 'string' },
            { name: 'tilemap', description: 'Game tilemap (Laboratory)', type: 'string' },
        ]
    },
    {
        name: 'slot',
        namespace: 'q',
        description: 'Where the content between `<Name>` and `</Name>` goes (COMP-3)',
        category: 'Core',
        attributes: [
            { name: 'name', description: 'Slot name', type: 'string' },
        ]
    },
    {
        name: 'script',
        namespace: 'q',
        description: 'Client-side JavaScript of the page',
        category: 'Core',
        attributes: [
        ]
    },
    {
        name: 'llm',
        namespace: 'q',
        description: 'A model call; with knowledge=, an answer that cites its sources (IA-1, IA-5..IA-9)',
        category: 'Core',
        allowedChildren: ['q:prompt', 'q:message', 'q:system'],
        attributes: [
            { name: 'name', description: 'Result variable', required: true, type: 'string' },
            { name: 'model', description: 'Model, an expression; else QUANTUM_LLM_DEFAULT_MODEL / llm.model (IA-1)', type: 'expression' },
            { name: 'endpoint', description: 'Another model server for this tag', type: 'expression' },
            { name: 'apiKey', description: 'API key', type: 'expression' },
            { name: 'provider', description: 'Provider', type: 'enum', values: ['ollama', 'openai', 'anthropic', 'claude', 'lmstudio', 'auto'] },
            { name: 'temperature', description: 'Temperature', type: 'number' },
            { name: 'maxTokens', description: 'Most tokens to generate', type: 'number' },
            { name: 'responseFormat', description: '`json`: the value is the parsed object', type: 'enum', values: ['text', 'json'], default: 'text' },
            { name: 'timeout', description: 'Seconds to wait for the model', type: 'number', default: '60' },
            { name: 'knowledge', description: 'Answer from this q:knowledge, citing it (IA-6)', type: 'string' },
            { name: 'top', description: 'Chunks to retrieve', type: 'number', default: '4' },
            { name: 'minRelevance', description: 'Chunks below it are not retrieved, 0 to 1 (IA-9)', type: 'number', default: '0' },
            { name: 'stream', description: 'In a web request, the answer arrives as it is written (IA-7)', type: 'boolean', default: 'false' },
            { name: 'cache', description: 'Cache the answer', type: 'boolean', default: 'false' },
            { name: 'ttl', description: 'Cache seconds', type: 'number' },
            { name: 'onerror', description: '`fail` stops the page with the error; `continue` hands it to `<name>_result` (INV-2, IA-5)', type: 'enum', values: ['fail', 'continue'], default: 'fail' },
        ]
    },
    {
        name: 'prompt',
        namespace: 'q',
        description: 'The prompt of a q:llm (with expressions)',
        category: 'Core',
        attributes: [
        ]
    },
    {
        name: 'system',
        namespace: 'q',
        description: 'The system message of a q:llm',
        category: 'Core',
        attributes: [
        ]
    },
    {
        name: 'message',
        namespace: 'q',
        description: 'A chat message of a q:llm',
        category: 'Core',
        attributes: [
            { name: 'role', description: 'Who says it', type: 'enum', values: ['system', 'user', 'assistant'], default: 'user' },
        ]
    },
    {
        name: 'knowledge',
        namespace: 'q',
        description: 'A base of text chunks that q:llm knowledge= answers from (IA-2, IA-6, IA-8)',
        category: 'Core',
        allowedChildren: ['q:source'],
        attributes: [
            { name: 'name', description: 'Base name', required: true, type: 'string' },
            { name: 'embedModel', description: 'Embedding model', type: 'string', default: 'nomic-embed-text' },
            { name: 'chunkSize', description: 'Characters per chunk', type: 'number', default: '500' },
            { name: 'chunkOverlap', description: 'Characters shared by neighbouring chunks', type: 'number', default: '50' },
            { name: 'persist', description: 'Keep the index on disk', type: 'boolean', default: 'true' },
            { name: 'persistPath', description: 'Where', type: 'string', default: './.quantum/knowledge' },
            { name: 'rebuild', description: 'Index again', type: 'boolean', default: 'false' },
            { name: 'onerror', description: '`fail` stops the page with the error; `continue` hands it to `<name>_result` (INV-2, IA-5)', type: 'enum', values: ['fail', 'continue'], default: 'fail' },
        ]
    },
    {
        name: 'source',
        namespace: 'q',
        description: 'A source of a q:knowledge, read whole (IA-8); a query\'s values are q:params (IA-10)',
        category: 'Core',
        attributes: [
            { name: 'type', description: 'Kind', required: true, type: 'enum', values: ['text', 'file', 'directory', 'query'] },
            { name: 'path', description: 'File or folder', type: 'string' },
            { name: 'pattern', description: 'Files of the folder, e.g. `*.md`', type: 'string' },
            { name: 'datasource', description: 'Datasource of a query source', type: 'string' },
            { name: 'chunkSize', description: 'Characters per chunk for this source', type: 'number' },
            { name: 'chunkOverlap', description: 'Overlap for this source', type: 'number' },
        ]
    },
    {
        name: 'agent',
        namespace: 'q',
        description: 'A model that uses the declared tools to do a task (IA-4, IA-5)',
        category: 'Core',
        allowedChildren: ['q:instruction', 'q:tool', 'q:execute'],
        attributes: [
            { name: 'name', description: 'Result variable', required: true, type: 'string' },
            { name: 'model', description: 'Model, an expression; else QUANTUM_LLM_DEFAULT_MODEL / llm.model (IA-1)', type: 'expression' },
            { name: 'endpoint', description: 'Another model server', type: 'expression' },
            { name: 'apiKey', description: 'API key', type: 'expression' },
            { name: 'provider', description: 'Provider', type: 'enum', values: ['ollama', 'openai', 'anthropic', 'claude', 'lmstudio', 'auto'], default: 'auto' },
            { name: 'maxIterations', description: 'Most reasoning steps', type: 'number', default: '10' },
            { name: 'timeout', description: 'Milliseconds for the whole run', type: 'number', default: '60000' },
            { name: 'onerror', description: '`fail` stops the page with the error; `continue` hands it to `<name>_result` (INV-2, IA-5)', type: 'enum', values: ['fail', 'continue'], default: 'fail' },
        ]
    },
    {
        name: 'instruction',
        namespace: 'q',
        description: 'The agent\'s instruction',
        category: 'Core',
        attributes: [
        ]
    },
    {
        name: 'tool',
        namespace: 'q',
        description: 'A tool the agent can call; its body runs with the arguments as variables',
        category: 'Core',
        allowedChildren: ['q:param', 'q:function'],
        attributes: [
            { name: 'name', description: 'Tool name', required: true, type: 'string' },
            { name: 'description', description: 'What it does (shown to the model)', type: 'string' },
            { name: 'builtin', description: 'A built-in tool (q:team)', type: 'boolean', default: 'false' },
        ]
    },
    {
        name: 'execute',
        namespace: 'q',
        description: 'The agent\'s task',
        category: 'Core',
        selfClosing: true,
        attributes: [
            { name: 'task', description: 'The task', required: true, type: 'expression' },
            { name: 'context', description: 'Extra text for the model', type: 'expression' },
            { name: 'entry', description: 'First agent (q:team)', type: 'string' },
        ]
    },
    // END GENERATED

    // Laboratory and Experimental q: tags (SUPPORT_TIERS.md), hand-written
    {
        name: 'application',
        namespace: 'q',
        description: 'Root element for a Quantum application. Defines routes and application-level config.',
        category: 'Structure',
        attributes: [
            { name: 'id', description: 'Application ID', required: true, type: 'string' },
            { name: 'type', description: 'Application type', type: 'enum', values: ['html', 'ui', 'game', 'terminal'], default: 'html' },
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

// ==============================================
// GAME TAGS (qg:), from the game compiler's schema
// ==============================================

export const gameTags: TagSchema[] = [
    // BEGIN GENERATED: game tags — python scripts/generate-editor-schemas.py (do not edit)
    {
        name: 'tileset',
        namespace: 'qg',
        description: 'A sheet of equal tiles; tilemaps and sprites name it. With shape="hex" its tiles are hexes with their points up, every other row of a map half a hex to the right (a strategy map); with shape="iso", diamonds, every other row half a diamond on. The rows of a qg:tilemap are the rows seen; a walker\'s neighbours, its way and the cell at a point follow the shape.',
        category: 'Game',
        allowedChildren: ['qg:tile'],
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'src', description: 'the image, relative to the .q or a folder above it', required: true, type: 'string' },
            { name: 'tile', description: 'tile size in pixels: 18 (square), or WxH for hexes and diamonds (28x32)', required: true, type: 'string' },
            { name: 'shape', description: 'square tiles, hexes or diamonds', type: 'enum', values: ['square', 'hex', 'iso'], default: 'square' },
        ]
    },
    {
        name: 'tile',
        namespace: 'qg',
        description: 'One tile of a qg:tileset that is not a full solid square, for the tilemap layers with collision: a lower top, a thin ledge, a slope, a tile to jump through from below, or no collision at all. A flipped tile (a negative number in the tilemap) flips its shape too.',
        category: 'Game',
        attributes: [
            { name: 'frame', description: 'which tile: its number in the tilemap is frame+1', required: true, type: 'number' },
            { name: 'shape', description: 'the solid part, as x,y points from the tile\'s top-left corner separated by semicolons (0,10; 64,10; 64,64; 0,64); none: not solid', type: 'string' },
            { name: 'one-way', description: 'stood on from above, jumped through from below', type: 'boolean', default: 'false' },
            { name: 'kind', description: 'ladder: passed through, climbed with up and down, let go of with jump; water: passed through, slow to sink in, a jump is a stroke, slower to walk; ice: slid on (a solid tile to stand on in a platformer, a floor in a top-down game); hurt: a character\'s qg:on-tile kind="hurt" runs while it touches one. In a Tiled tileset: a tile\'s class, or its kind property', type: 'enum', values: ['ladder', 'water', 'ice', 'hurt'] },
            { name: 'frames', description: 'an animated tile (water, lava, a torch): how many frames it shows in turn, itself and the ones after it in the sheet\'s row, which are then not tiles of their own. Only seen', type: 'number', default: '1' },
            { name: 'fps', description: 'frames a second, with frames=', type: 'number', default: '4' },
            { name: 'cost', description: 'what a step onto it costs a walker finding its way (ai="pathfind", qg:seek, a pointer\'s click, qg:travel, cost()): a forest 2, a marsh 3. The way found is the cheapest', type: 'number', default: '1' },
        ]
    },
    {
        name: 'spritesheet',
        namespace: 'qg',
        description: 'A sheet of equal frames for characters and items. With slice=, it is a frame that stretches to a box (a dialogue\'s box=): its corners stay as drawn, its edges and middle stretch.',
        category: 'Game',
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'src', description: '', required: true, type: 'string' },
            { name: 'tile', description: 'frame size in pixels: 24, or 8x32 for frames that are not square', required: true, type: 'string' },
            { name: 'slice', description: 'how wide its edges are, in pixels, that do not stretch: 16, or left, top, right, bottom (16, 8, 16, 8); its first frame is the frame', type: 'string' },
        ]
    },
    {
        name: 'input',
        namespace: 'qg',
        description: 'The keys of an action, instead of the defaults (arrows/WASD to move, space/Z/X to jump). A second player has no defaults: every action it uses is declared with player="2".',
        category: 'Game',
        attributes: [
            { name: 'action', description: 'left, right, up, down, jump, select, cancel — or a name of the game\'s own (buy, pause): qg:on-input reads it', required: true, type: 'string' },
            { name: 'keys', description: 'comma-separated: Godot key names (Space, Left, A, Enter...) and joypad names — JoyA JoyB JoyX JoyY JoyL JoyR JoyL2 JoyR2 JoyStart JoySelect, JoyUp JoyDown JoyLeft JoyRight (the pad), JoyLeftStickUp/Down/Left/Right, JoyRightStickUp/Down/Left/Right; MouseLeft, MouseRight, MouseMiddle. Player n reads joypad n-1', required: true, type: 'string' },
            { name: 'player', description: 'whose keys: the character with the same player=', type: 'number', default: '1' },
        ]
    },
    {
        name: 'multiplayer',
        namespace: 'qg',
        description: 'The game is played by several people, each on their own machine, in lockstep: every peer runs the whole game and a tick runs when every player\'s input for it has arrived. One hosts (`--q-host=PORT`, player 1), the others join (`--q-join=HOST:PORT`, players 2.. in order, or the seat `--q-seat=N` asks for). The players\' characters are told apart by player=; nobody declares keys for players 2... A player who leaves can come back: the others wait, and the next to join takes the seat, catching up the game so far (not under rollback=, where the game ends).',
        category: 'Game',
        attributes: [
            { name: 'players', description: 'how many, 2 or more: the game starts by itself as the last of them joins', required: true, type: 'number' },
            { name: 'min-players', description: 'fewer may play: once this many are there, the host may start the game (qg:start-now, or the lobby\'s Start now) with those who are; `net_players()` then says how many play', type: 'number' },
            { name: 'delay', description: 'ticks between a press and its effect, everywhere: hides the round trip', type: 'number', default: '3' },
            { name: 'check-every', description: 'ticks between comparisons of the whole state across peers; a difference is a desync, reported and fatal (0: never)', type: 'number', default: '60' },
            { name: 'rollback', description: 'rollback instead of waiting: up to this many ticks run ahead on a guess of the others\' input and are run again when it was wrong (0: plain lockstep). The scenes the networked game reaches may only hold fighters, timers, menus, the HUD, pictures and a camera — nothing that goes through physics', type: 'number', default: '0' },
            { name: 'start', description: 'the scene the networked game starts in, on every peer, once all the players are there (the first scene when not given); the scenes before it — a title, a lobby — run on each machine alone', type: 'string' },
            { name: 'transport', description: 'enet (desktop to desktop), or websocket (a browser build can join a desktop host)', type: 'enum', values: ['enet', 'websocket'], default: 'enet' },
        ]
    },
    {
        name: 'sound',
        namespace: 'qg',
        description: 'A sound the game can play (qg:play).',
        category: 'Game',
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'src', description: 'an .ogg or .wav', required: true, type: 'string' },
            { name: 'loop', description: 'plays until qg:stop (music)', type: 'boolean', default: 'false' },
            { name: 'bus', description: 'the bus it is heard on (music, effects...): how loud a bus is, qg:volume and a menu\'s qg:slider set, kept between runs', type: 'string' },
        ]
    },
    {
        name: 'particles',
        namespace: 'qg',
        description: 'A particle effect the game can show: a preset and a few overrides. qg:emit plays it once where a thing is; qg:emitter keeps it going in a scene. Only seen: the game\'s state never depends on it.',
        category: 'Game',
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'preset', description: 'puff, sparks, smoke, dust, confetti and stars play once; fire, rain and snow keep going', required: true, type: 'enum', values: ['puff', 'sparks', 'smoke', 'dust', 'fire', 'rain', 'snow', 'confetti', 'stars'] },
            { name: 'color', description: 'the preset\'s own when not given (confetti is every colour)', type: 'string' },
            { name: 'amount', description: 'how many particles', type: 'number' },
            { name: 'lifetime', description: 'seconds each one lives', type: 'number' },
            { name: 'speed', description: 'pixels a second, about', type: 'number' },
            { name: 'size', description: 'pixels, about', type: 'number' },
        ]
    },
    {
        name: 'language',
        namespace: 'qg',
        description: 'The game\'s texts in another language: each qg:phrase gives one text as written in the game, and what it is in this language. A text with no phrase stays as written. The language is ?lang= in a web page, --q-lang= on the command line, else the system\'s, when the game has it; `tr(text)` translates a text an expression puts together, and `tr_n(one, other, n)` a count\'s word (1 potion, 2 potions) by the language\'s plural rule. In pt and es, a qg:lobby\'s own texts come translated. A qg:asset gives a picture or a sound drawn or spoken in the language.',
        category: 'Game',
        allowedChildren: ['qg:phrase', 'qg:asset'],
        attributes: [
            { name: 'lang', description: 'a language code: pt, es, zh, pt_BR...', required: true, type: 'string' },
            { name: 'name', description: 'its own name for it (Português)', type: 'string', default: '' },
            { name: 'font', description: 'a .ttf with the letters of its alphabet that the game\'s fonts lack (Cyrillic, Greek, Japanese): every text draws them from it', type: 'string' },
        ]
    },
    {
        name: 'phrase',
        namespace: 'qg',
        description: 'One text of the game, in a qg:language. The plural word of a count (`tr_n(\'potion\', \'potions\', n)`) takes the forms its language has: in Russian, 1 зелье, 2 зелья, 5 зелий.',
        category: 'Game',
        attributes: [
            { name: 'text', description: 'the text exactly as the game shows it (a button, a line, a HUD text)', required: true, type: 'string' },
            { name: 'as', description: 'what it is in this language; for a plural word, the form of the counts the others are not (5 зелий)', required: true, type: 'string' },
            { name: 'one', description: 'a plural word\'s form for one (1, 21, 31 in ru, uk, be; 1 elsewhere); when not given, the phrase of the word for one', type: 'string' },
            { name: 'few', description: 'its form for a few: 2 to 4 (22 to 24...) in ru, uk, be and pl; 2 to 4 in cs and sk', type: 'string' },
            { name: 'many', description: 'its form for many (5 to 20, 25...) in ru, uk, be and pl; as= when not given', type: 'string' },
        ]
    },
    {
        name: 'asset',
        namespace: 'qg',
        description: 'A picture or a sound of the game as it is in a qg:language: the banner with its words in the language, a voice. The scenes that start while the language is shown draw the picture; the sound plays from the moment it is chosen.',
        category: 'Game',
        attributes: [
            { name: 'name', description: 'a qg:spritesheet, qg:tileset or qg:sound of the game', required: true, type: 'string' },
            { name: 'src', description: 'its file in this language, relative to the .q or a folder above it; a picture has the same frame size', required: true, type: 'string' },
        ]
    },
    {
        name: 'item',
        namespace: 'qg',
        description: 'A kind of thing the players carry: keys, gems, potions. How many they hold is the game\'s state, kept across scenes and in a qg:save; `held(\'key\')` reads it. A prefab with gives= is picked up as one; a solid prefab with opens-with= opens for one; qg:give and qg:take add and spend them; qg:inventory shows them.',
        category: 'Game',
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'label', description: 'what a player reads (else its name), in the HUD', type: 'string' },
            { name: 'sheet', description: 'a qg:spritesheet or qg:tileset: its picture in qg:inventory', type: 'string' },
            { name: 'frame', description: '', type: 'number', default: '0' },
            { name: 'max', description: 'the most they can hold (0: no limit)', type: 'number', default: '0' },
            { name: 'start', description: 'how many they hold when the game starts', type: 'number', default: '0' },
            { name: 'sound', description: 'a qg:sound, played as one is picked up', type: 'string' },
            { name: 'particles', description: 'a qg:particles, burst where one is picked up', type: 'string' },
        ]
    },
    {
        name: 'prefab',
        namespace: 'qg',
        description: 'A kind of thing the scene places with qg:instance. With ai= it moves.',
        category: 'Game',
        allowedChildren: ['qg:state', 'qg:animation', 'qg:on-separate', 'qg:on-screen-exit', 'qg:on-screen-enter', 'qg:on-collision', 'qg:on-damage', 'qg:on-death', 'qg:label', 'qg:light', 'qg:behavior', 'qg:on-animation-end', 'qg:on-locked'],
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'tag', description: 'what collisions see it as (`with="coin"`)', type: 'string' },
            { name: 'sheet', description: 'a qg:spritesheet or qg:tileset', required: true, type: 'string' },
            { name: 'frame', description: '', type: 'number', default: '0' },
            { name: 'hitbox', description: '', required: true, type: 'string' },
            { name: 'ai', description: 'patrol: walks under gravity, turns at walls (and at edges with turns-at); wander: top-down, changes direction now and then (from the scene seed); chase: top-down, goes for the character within sight=, straight at it; pathfind: as chase, but around the walls, by the shortest way over the tilemap\'s free cells; fly: straight along heading=; sway: side to side across the scene; shuttle: a solid that goes dx=,dy= and back every period= ticks, carrying what stands on it; path: follows the qg:path it was spawned on (qg:spawn at="path"), then stands at its end; turret: stands, and fires fire-prefab at the nearest targets= within range= every fire-every; behavior: top-down, made of the parts its qg:behavior lists (qg:seek, qg:flee...)', type: 'enum', values: ['patrol', 'wander', 'chase', 'pathfind', 'fly', 'sway', 'shuttle', 'path', 'turret', 'behavior'] },
            { name: 'range', description: 'turret: pixels', type: 'number', default: '100' },
            { name: 'targets', description: 'turret: the tag it shoots at', type: 'string' },
            { name: 'attack', description: 'turret: shoot spawns fire-prefab headed at the target; area damages every target in range by damage=', type: 'enum', values: ['shoot', 'area'], default: 'shoot' },
            { name: 'damage', description: 'turret attack="area": the damage', type: 'number', default: '1' },
            { name: 'dx', description: 'shuttle: how far it goes, pixels', type: 'number', default: '0' },
            { name: 'dy', description: 'shuttle: how far it goes, pixels', type: 'number', default: '0' },
            { name: 'period', description: 'shuttle: ticks for there and back', type: 'number', default: '240' },
            { name: 'one-way', description: 'solid: can be jumped through from below and stood on', type: 'boolean', default: 'false' },
            { name: 'shape', description: 'solid: the solid part as x,y points from its centre, separated by semicolons (-96,-21; 96,-21; 96,6; -96,6), instead of the hitbox', type: 'string' },
            { name: 'scale', description: 'the picture\'s size, times its frame (the hitbox stays as given)', type: 'number', default: '1' },
            { name: 'walls', description: 'fly: pass goes through the tiles; stop is gone on touching one; bounce turns off it, as a ball off a wall (the way across it reverses)', type: 'enum', values: ['pass', 'stop', 'bounce'], default: 'pass' },
            { name: 'trail', description: 'a line it leaves behind it as it moves, fading (a shot\'s streak, a ship\'s wake): only seen', type: 'string' },
            { name: 'pushable', description: 'solid: a character controller="grid" or "pointer" that steps into it pushes it a cell on, if that cell is free (no wall, no thing): a crate', type: 'boolean', default: 'false' },
            { name: 'extends', description: 'another prefab it is made from: it has all of it (attributes, animations, states, handlers) but what it says itself; a qg:animation or qg:state of the same name, a handler with the same with= and side=, a qg:behavior, replace the other\'s', type: 'string' },
            { name: 'spacing', description: 'things of its tag keep at least this many pixels apart as they move: a crowd, not a pile (0: they may overlap)', type: 'number', default: '0' },
            { name: 'sight', description: 'chase, pathfind, and the parts of a behavior: pixels', type: 'number', default: '80' },
            { name: 'heading', description: 'fly: up, down, left, right, or a direction as x,y (-1,0.5)', type: 'string', default: 'down' },
            { name: 'accel', description: 'fly: pixels per second added to its speed every second', type: 'number', default: '0' },
            { name: 'lifetime', description: 'fly: gone after this many ticks (0: never); any fly is gone off-screen', type: 'number', default: '0' },
            { name: 'particles', description: 'a qg:particles kept going where it is, as it moves (a fire, an engine\'s flame, a torch carried): only seen', type: 'string' },
            { name: 'visible', description: 'shown only while this is true, read every tick (`me` is it): blinking while hurt, hidden in the dark; it still collides', type: 'expression' },
            { name: 'flip-v', description: 'its picture upside down', type: 'boolean', default: 'false' },
            { name: 'layer', description: 'drawn over things of a lower layer and under those of a higher one, whatever y-sort says', type: 'number', default: '0' },
            { name: 'health', description: 'hits it takes (qg:damage); at 0 its qg:on-death runs and it is gone', type: 'number', default: '1' },
            { name: 'fire-prefab', description: 'what it shoots, placed below it (or above, when heading is up)', type: 'string' },
            { name: 'fire-every', description: 'ticks between shots (0: never)', type: 'number', default: '0' },
            { name: 'fire-sound', description: '', type: 'string' },
            { name: 'speed', description: 'pixels per second, for ai=; or a range, 150..250, drawn from the scene seed as each instance is placed', type: 'string', default: '30' },
            { name: 'rotate', description: 'fly: the sprite turns to face the heading', type: 'boolean', default: 'false' },
            { name: 'direction', description: 'where it walks first', type: 'enum', values: ['left', 'right'], default: 'left' },
            { name: 'turns-at', description: 'edge: also turns before falling off', type: 'enum', values: ['wall', 'edge'], default: 'wall' },
            { name: 'gravity', description: '', type: 'number', default: '900' },
            { name: 'solid', description: 'characters stand on it and bump it (a block)', type: 'boolean', default: 'false' },
            { name: 'gives', description: 'a qg:item: a character that touches it picks it up (amount= of them) and it is gone; a named instance stays gone when the scene is entered again', type: 'string' },
            { name: 'amount', description: 'gives=: how many', type: 'number', default: '1' },
            { name: 'opens-with', description: 'solid: a qg:item. A character that bumps it holding one spends it and it opens (it is gone; a named one stays gone); without one, its qg:on-locked runs', type: 'string' },
            { name: 'keeps', description: 'opens-with=: the item is not spent (a key for every door)', type: 'boolean', default: 'false' },
        ]
    },
    {
        name: 'state',
        namespace: 'qg',
        description: 'A form of a character or a prefab (small, big; calm, angry): hitbox, frame, animations, and for a prefab its speed and fire-every. `me.state` reads it; qg:become changes it.',
        category: 'Game',
        allowedChildren: ['qg:animation'],
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'hitbox', description: 'a character needs one; a prefab keeps its own', type: 'string' },
            { name: 'frame', description: 'its picture in this state (its own frame when not given)', type: 'number' },
            { name: 'speed', description: 'prefab: overrides its speed', type: 'number' },
            { name: 'fire-every', description: 'prefab: overrides its fire-every', type: 'number' },
            { name: 'fire-prefab', description: 'prefab: overrides its fire-prefab', type: 'string' },
            { name: 'range', description: 'turret: overrides its range', type: 'number' },
            { name: 'initial', description: 'the state it starts in (else the first one)', type: 'boolean', default: 'false' },
        ]
    },
    {
        name: 'animation',
        namespace: 'qg',
        description: 'Frames of the sheet, cycled. A character plays "idle", "walk" and "jump" by what it does (a platformer "fall" while it comes down, when it has one; a topdown one "walk-up" and "walk-down" when it has them, "walk-up" upside down for down, and while it swings "attack", or "attack-up" and "attack-down" by where it faces); a prefab plays "walk".',
        category: 'Game',
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'frames', description: 'comma-separated frame numbers', required: true, type: 'string' },
            { name: 'fps', description: '', type: 'number', default: '8' },
            { name: 'loop', description: 'false: it plays once, stays on its last frame, and its qg:on-animation-end runs (an attack, a fall, a death)', type: 'boolean', default: 'true' },
        ]
    },
    {
        name: 'scene',
        namespace: 'qg',
        description: 'A screen of the game. The first one is where the game starts.',
        category: 'Game',
        allowedChildren: ['qg:tilemap', 'qg:character', 'qg:instance', 'qg:cursor', 'qg:path', 'qg:on-select', 'qg:menu', 'qg:dialogue', 'qg:on-screen-exit', 'qg:on-screen-enter', 'qg:zone', 'qg:parallax', 'qg:sprite', 'qg:emitter', 'qg:exit', 'qg:camera', 'qg:hud', 'qg:on-death', 'qg:label', 'qg:light', 'qg:when', 'qg:timer', 'qg:spawner', 'qg:map-node', 'qg:map-path', 'qg:on-input', 'qg:play', 'qg:music', 'qg:stop', 'qg:lobby', 'qg:touch-button', 'qg:touch-stick'],
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'width', description: '', type: 'number', default: '256' },
            { name: 'height', description: '', type: 'number', default: '224' },
            { name: 'background', description: '', type: 'string', default: '#000000' },
            { name: 'seed', description: 'the random seed, a number or an expression of the game\'s state read as the scene is entered (a world\'s number); the same seed gives the same game, so a scene entered again and again draws the same each time unless its seed is read from the state (seed="{round}")', type: 'expression', default: '0' },
            { name: 'save', description: 'entering the scene saves the game to continue here (qg:save), as a room of an adventure does', type: 'boolean', default: 'false' },
            { name: 'y-sort', description: 'characters and things are drawn by how low they stand, the lower in front: depth seen from above (a layer= still comes first)', type: 'boolean', default: 'false' },
            { name: 'ambient', description: 'a dark scene: the light where no qg:light reaches (#000000 is black, #ffffff as drawn); its solid tiles cast the shadows of the lights with shadows="true"', type: 'string' },
        ]
    },
    {
        name: 'tilemap',
        namespace: 'qg',
        description: 'The level: CSV rows of tile numbers (0 is empty, n is tile n-1 of the tileset), or a Tiled map (src=) whose tile layers draw it and whose object layers place prefabs by class. Several in a scene are layers of one map, drawn in order (a floor, a path, the walls), on one tileset. A Tiled map may use several tilesets (each layer draws from one, which is the qg:tileset of the game with the same image) and flipped or turned tiles; an object\'s state property is the qg:state it starts in; objects of class zone (a tag property), exit (to and at properties) and path (a polyline) are the scene\'s qg:zone, qg:exit and qg:path; the map\'s own properties are read with tiled(\'name\').',
        category: 'Game',
        attributes: [
            { name: 'tileset', description: '', required: true, type: 'string' },
            { name: 'collision', description: 'every tile is solid (a Tiled layer says so with a collision property)', type: 'boolean', default: 'false' },
            { name: 'src', description: 'a .tmx, relative to the .q or a folder above it', type: 'string' },
        ]
    },
    {
        name: 'character',
        namespace: 'qg',
        description: 'A body the player moves: a platformer, or a walker on a world map.',
        category: 'Game',
        allowedChildren: ['qg:state', 'qg:animation', 'qg:on-separate', 'qg:on-screen-exit', 'qg:on-screen-enter', 'qg:on-collision', 'qg:label', 'qg:light', 'qg:on-hit', 'qg:on-fall', 'qg:move', 'qg:behavior', 'qg:on-tile', 'qg:on-animation-end', 'qg:on-ko'],
        attributes: [
            { name: 'id', description: '', required: true, type: 'string' },
            { name: 'controller', description: 'grid: steps from cell to cell of the tilemap; the tiles of a layer with collision, and the things, stop it, and stepping into a thing runs its qg:on-collision with the thing\'s tag; `me.col` and `me.row` are its cell. pointer: as grid, and a click (its player\'s qg:cursor) walks it to that cell by the shortest way around the walls and things. behavior: made of the parts its qg:behavior lists', required: true, type: 'enum', values: ['platformer', 'map', 'topdown', 'ship', 'fighter', 'grid', 'pointer', 'behavior'] },
            { name: 'step-frames', description: 'grid: ticks to walk one cell (a bump takes as long)', type: 'number', default: '15' },
            { name: 'diagonal', description: 'grid: two directions held at once step diagonally', type: 'boolean', default: 'false' },
            { name: 'player', description: 'whose keys move it (qg:input player=); 1 has the defaults', type: 'number', default: '1' },
            { name: 'health', description: 'fighter: hits it takes; at 0 it is KO and qg:on-ko runs', type: 'number', default: '100' },
            { name: 'facing', description: 'fighter: where it looks at first', type: 'enum', values: ['left', 'right'], default: 'right' },
            { name: 'bounds', description: 'kept inside the scene: a ship unless none, a topdown character when scene', type: 'enum', values: ['scene', 'none'] },
            { name: 'axis', description: 'ship: which way it can move', type: 'enum', values: ['both', 'vertical', 'horizontal'], default: 'both' },
            { name: 'fire-action', description: 'ship, platformer: the action that shoots (jump, or one a qg:input declares)', type: 'string' },
            { name: 'fire-prefab', description: 'ship: what it shoots, placed above it; platformer: in front of it, a fly prefab heading the way it faces', type: 'string' },
            { name: 'fire-every', description: 'ship: ticks between shots while the action is held; platformer: the fewest ticks between two presses that shoot', type: 'number', default: '10' },
            { name: 'fire-sound', description: '', type: 'string' },
            { name: 'at', description: 'map: the qg:map-node it starts on (a name, or an expression)', type: 'expression' },
            { name: 'speed', description: 'map, topdown: pixels per second', type: 'number', default: '60' },
            { name: 'attack-action', description: 'topdown: the action that swings in front', type: 'enum', values: ['jump'] },
            { name: 'attack-reach', description: 'topdown: how far the swing reaches, pixels', type: 'number', default: '16' },
            { name: 'attack-frames', description: 'topdown: how many ticks the swing lasts', type: 'number', default: '12' },
            { name: 'attack-sound', description: 'a qg:sound, played on the swing', type: 'string' },
            { name: 'sheet', description: '', required: true, type: 'string' },
            { name: 'frame', description: '', type: 'number', default: '0' },
            { name: 'x', description: '', required: true, type: 'number' },
            { name: 'y', description: '', required: true, type: 'number' },
            { name: 'hitbox', description: '', required: true, type: 'string' },
            { name: 'run-speed', description: 'pixels per second', type: 'number', default: '90' },
            { name: 'jump-height', description: 'pixels, with the button held', type: 'number', default: '64' },
            { name: 'variable-jump', description: 'releasing the button cuts the jump', type: 'boolean', default: 'true' },
            { name: 'coyote-frames', description: 'ticks after leaving a ledge in which a jump still works', type: 'number', default: '6' },
            { name: 'buffer-frames', description: 'platformer: a jump pressed up to this many ticks before landing jumps as it lands (0: only a press on the floor)', type: 'number', default: '0' },
            { name: 'gravity', description: 'pixels per second squared', type: 'number', default: '900' },
            { name: 'max-fall', description: 'terminal velocity, pixels per second', type: 'number', default: '300' },
            { name: 'jump-sound', description: 'a qg:sound, played on take-off', type: 'string' },
            { name: 'jump-speed', description: 'platformer: the take-off speed, pixels per second, instead of jump-height', type: 'number' },
            { name: 'accel', description: 'platformer: pixels per second squared towards the run speed (0: at once)', type: 'number', default: '0' },
            { name: 'air-jumps', description: 'platformer: jumps it may take in the air before landing again', type: 'number', default: '0' },
            { name: 'air-jump-boost', description: 'platformer: an air jump multiplies the speed across by this', type: 'number', default: '1' },
            { name: 'jump-cut', description: 'platformer: releasing the button while rising multiplies the rise by this, once (0: the extra gravity of variable-jump instead)', type: 'number', default: '0' },
            { name: 'scale', description: 'the picture\'s size, times its frame (the hitbox stays as given)', type: 'number', default: '1' },
            { name: 'if', description: 'placed only when this is true as the scene is built: a second player\'s character only in a networked game, `net_status() != \'offline\'`', type: 'expression' },
            { name: 'particles', description: 'a qg:particles kept going where it is, as it moves (a fire, an engine\'s flame, a torch carried): only seen', type: 'string' },
            { name: 'visible', description: 'shown only while this is true, read every tick (`me` is it): blinking while hurt, hidden in the dark; it still collides', type: 'expression' },
            { name: 'flip-v', description: 'its picture upside down', type: 'boolean', default: 'false' },
            { name: 'layer', description: 'drawn over things of a lower layer and under those of a higher one, whatever y-sort says', type: 'number', default: '0' },
        ]
    },
    {
        name: 'instance',
        namespace: 'qg',
        description: 'A prefab placed in the scene.',
        category: 'Game',
        attributes: [
            { name: 'prefab', description: '', required: true, type: 'string' },
            { name: 'x', description: '', required: true, type: 'number' },
            { name: 'y', description: '', required: true, type: 'number' },
            { name: 'name', description: 'the node name (`other.name` in a handler); the prefab name otherwise', type: 'string' },
            { name: 'if', description: 'placed only when this is true as the scene is built', type: 'expression' },
        ]
    },
    {
        name: 'cursor',
        namespace: 'qg',
        description: 'A player\'s pointer in the scene: the mouse, moved also by that player\'s left/right/up/down by step= pixels. `cursor.x`, `cursor.y` (and, with grid=, `cursor.col`, `cursor.row`, snapped) in qg:on-select; with sheet= it is drawn. Under qg:multiplayer every player\'s cursor travels with their input.',
        category: 'Game',
        attributes: [
            { name: 'id', description: 'its name in expressions, as a character\'s: `aim.x`, `aim.y` (with grid=, `aim.col`, `aim.row`), and a target of qg:beam', type: 'string' },
            { name: 'player', description: '', type: 'number', default: '1' },
            { name: 'step', description: 'pixels per tick while a direction is held', type: 'number', default: '16' },
            { name: 'grid', description: 'cell size: the cursor snaps to cell centres', type: 'number' },
            { name: 'cells', description: 'it snaps to the middles of the cells of the scene\'s qg:tilemap, whatever their shape (a hex map\'s); `cursor.col`, `cursor.row` are the cell', type: 'boolean', default: 'false' },
            { name: 'sheet', description: '', type: 'string' },
            { name: 'frame', description: '', type: 'number', default: '0' },
        ]
    },
    {
        name: 'path',
        namespace: 'qg',
        description: 'A route through the scene, straight from point to point, that ai="path" prefabs follow (qg:spawn at="path" path=).',
        category: 'Game',
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'points', description: 'x,y pairs separated by semicolons: 0,100; 200,100; 200,300', required: true, type: 'string' },
        ]
    },
    {
        name: 'on-select',
        namespace: 'qg',
        description: 'What happens when a player presses select with their qg:cursor somewhere (or another action: action= with a qg:input of the right mouse button, MouseRight, is a right click on a thing). Holds actions and statements; `cursor` is where (x, y, col, row, player), `other` the thing under it, or null. `hovered()` reads the thing under a cursor at any time.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'player', description: 'only this player\'s cursor (any, when not given)', type: 'number' },
            { name: 'action', description: 'the action that chooses: select (the left button, Enter), or one a qg:input declares (keys="MouseRight", "WheelUp", "WheelDown")', type: 'string', default: 'select' },
        ]
    },
    {
        name: 'menu',
        namespace: 'qg',
        description: 'A list of buttons (and text fields) over the scene. A player moves through it with up/down and chooses with select (Enter, the joypad\'s A: the button that has the focus), or points at a button with the mouse and clicks it (a click away from the buttons chooses nothing) — the pointer is that player\'s qg:cursor and the click its "click" action, so a click is replayed and travels in the lockstep like a key.',
        category: 'Game',
        allowedChildren: ['qg:button', 'qg:field', 'qg:slider', 'qg:rebind'],
        attributes: [
            { name: 'player', description: 'whose keys and pointer choose', type: 'number', default: '1' },
            { name: 'local', description: 'the menu of whoever plays at this machine (its seat, in a networked game); it holds only shared fields, whose texts reach the others', type: 'boolean', default: 'false' },
            { name: 'if', description: 'shown, and choosable, only while this is true: paused(), a q:set...', type: 'expression' },
            { name: 'position', description: '', type: 'enum', values: ['top-left', 'top-center', 'top-right', 'center', 'bottom-center'], default: 'center' },
            { name: 'x', description: 'with y=, its top-left corner on the screen, in pixels (in place of position=)', type: 'number' },
            { name: 'y', description: '', type: 'number' },
            { name: 'source', description: 'a list: the menu holds one qg:button, and shows it once for each row of it, read every frame (a squad to choose from, the clubs, a shop\'s goods); the row is as= in its label=, if= and what it runs', type: 'expression' },
            { name: 'as', description: 'with source=: the name of the row', type: 'string' },
            { name: 'font', description: 'a .ttf, relative to the .q or a folder above it', type: 'string' },
            { name: 'size', description: 'font size', type: 'number', default: '16' },
            { name: 'box', description: 'a qg:spritesheet with slice=: the buttons are in a box drawn with it, stretched (a frame)', type: 'string' },
            { name: 'columns', description: 'its items in a grid of so many columns: left and right move along a row', type: 'number', default: '1' },
            { name: 'rows', description: 'how many rows show at once; the others scroll into view with the focus (0: all of them)', type: 'number', default: '0' },
        ]
    },
    {
        name: 'button',
        namespace: 'qg',
        description: 'A button of a qg:menu. What it holds runs when it is chosen: actions and statements, like a handler.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'label', description: 'its text, or an expression ({...}) read every frame', required: true, type: 'string' },
            { name: 'if', description: 'shown, and choosable, only while this is true', type: 'expression' },
        ]
    },
    {
        name: 'field',
        namespace: 'qg',
        description: 'A text box of a qg:menu, bound to a string state: what is typed is the state. Typing is local to the machine (an address) — the lockstep does not carry it. A shared field (shared="true") is a draft until Enter sends it: the text goes with the player\'s input for a tick, and on that tick, on every machine of a networked game, it becomes the bound state and what the field holds runs, with `sender` (the seat that sent it) and `text` — names, a short chat. While a field is typed in, the keys type and play nothing.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'bind', description: 'a q:set of the scene or the game', required: true, type: 'string' },
            { name: 'label', description: 'text before the box', type: 'string', default: '' },
            { name: 'max-length', description: '', type: 'number', default: '64' },
            { name: 'shared', description: 'sent to every machine with the inputs, on Enter', type: 'boolean', default: 'false' },
        ]
    },
    {
        name: 'slider',
        namespace: 'qg',
        description: 'A value of a qg:menu that left and right change while it has the focus: how loud a bus is (bus=, from 0 to 100, kept between runs), or a number of the scene or the game (bind=).',
        category: 'Game',
        attributes: [
            { name: 'label', description: 'text before it', type: 'string', default: '' },
            { name: 'bus', description: 'a bus of the game\'s sounds (qg:sound bus=), or bind=', type: 'string' },
            { name: 'bind', description: 'a number q:set of the scene or the game, or bus=', type: 'string' },
            { name: 'min', description: '', type: 'number', default: '0' },
            { name: 'max', description: '', type: 'number', default: '100' },
            { name: 'step', description: 'how much a press of left or right changes it', type: 'number', default: '10' },
            { name: 'if', description: 'shown, and choosable, only while this is true', type: 'expression' },
        ]
    },
    {
        name: 'rebind',
        namespace: 'qg',
        description: 'A key of a qg:menu: it shows the action\'s key, and once chosen, the next key, mouse button or joypad button pressed becomes the action\'s (Escape keeps the old one). Kept between runs. Local to the machine, as a field is: the replay and the lockstep carry the actions, not the keys.',
        category: 'Game',
        attributes: [
            { name: 'action', description: 'an action of the game (qg:input, or a default one)', required: true, type: 'string' },
            { name: 'label', description: 'text before the key; the action\'s name when not given', type: 'string', default: '' },
            { name: 'player', description: 'whose action', type: 'number', default: '1' },
            { name: 'if', description: 'shown, and choosable, only while this is true', type: 'expression' },
        ]
    },
    {
        name: 'dialogue',
        namespace: 'qg',
        description: 'Lines someone says, shown one at a time in a box at the bottom of the screen (qg:say opens it).',
        category: 'Game',
        allowedChildren: ['qg:line', 'qg:on-end'],
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'font', description: 'a .ttf, relative to the .q or a folder above it', type: 'string' },
            { name: 'size', description: 'font size', type: 'number', default: '24' },
            { name: 'speed', description: 'letters a second, typed in as each line shows (select shows it whole at once); 0: the whole line at once', type: 'number', default: '0' },
            { name: 'sheet', description: 'a qg:spritesheet of faces: a line\'s portrait= is a frame of it', type: 'string' },
            { name: 'box', description: 'a qg:spritesheet with slice=: the box is drawn with it, stretched (a frame)', type: 'string' },
        ]
    },
    {
        name: 'line',
        namespace: 'qg',
        description: 'One line of a qg:dialogue: who says it, and what. With qg:choice inside, the player chooses (up and down, select, or a click), and the choice\'s actions run before the next line.',
        category: 'Game',
        allowedChildren: ['qg:choice'],
        attributes: [
            { name: 'who', description: 'the name over the text, or an expression ({...})', type: 'string', default: '' },
            { name: 'text', description: 'the line, or an expression ({...}) read as it is shown', required: true, type: 'string' },
            { name: 'portrait', description: 'a frame of the dialogue\'s sheet=, beside the text', type: 'number' },
        ]
    },
    {
        name: 'choice',
        namespace: 'qg',
        description: 'One answer to a qg:line: what the player reads, and what happens when it is chosen (then the next line). Holds actions and statements: a qg:say opens another dialogue, a q:set remembers the answer.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'label', description: 'what it says, or an expression ({...})', required: true, type: 'string' },
            { name: 'if', description: 'offered only when this is true as the line shows', type: 'expression' },
        ]
    },
    {
        name: 'on-end',
        namespace: 'qg',
        description: 'What happens when a qg:dialogue has shown its last line, or when a qg:tween is done (the last of its repeats; `me` is the thing it moved, and another tween in it plays after: a sequence). Holds actions and statements.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
        ]
    },
    {
        name: 'on-separate',
        namespace: 'qg',
        description: 'What happens when this character or prefab stops touching something it touched: a plate stepped off, a door that closes behind. Holds actions and statements; `me` is the one that touched, `other` what it touched. Not when the other is destroyed: it left nothing.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'with', description: 'the tag of what it stops touching', required: true, type: 'string' },
        ]
    },
    {
        name: 'on-screen-exit',
        namespace: 'qg',
        description: 'What happens when this character or prefab leaves the screen: the camera\'s view, or the scene when it has no camera. In a scene, with of=, when any thing of that tag does (`other` is the thing). Holds actions and statements; it runs in the game\'s tick, the same on every peer.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'of', description: 'scene: the tag', type: 'string' },
            { name: 'side', description: 'the edge it left by', type: 'enum', values: ['any', 'top', 'bottom', 'left', 'right'], default: 'any' },
        ]
    },
    {
        name: 'on-screen-enter',
        namespace: 'qg',
        description: 'What happens when this character or prefab comes onto the screen from outside it (one placed on the screen has not come onto it). In a scene, with of=, when any thing of that tag does.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'of', description: 'scene: the tag', type: 'string' },
            { name: 'side', description: 'the edge it came in by', type: 'enum', values: ['any', 'top', 'bottom', 'left', 'right'], default: 'any' },
        ]
    },
    {
        name: 'zone',
        namespace: 'qg',
        description: 'An invisible rectangle with a tag: what touches it runs its qg:on-collision with= that tag.',
        category: 'Game',
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'tag', description: '', required: true, type: 'string' },
            { name: 'x', description: '', required: true, type: 'number' },
            { name: 'y', description: '', required: true, type: 'number' },
            { name: 'width', description: '', required: true, type: 'number' },
            { name: 'height', description: '', required: true, type: 'number' },
        ]
    },
    {
        name: 'parallax',
        namespace: 'qg',
        description: 'A backdrop behind the level that the camera scrolls slower than the level: a sky, distant hills. Its picture is one frame of a sheet, placed on the screen, repeating across. Several are drawn in order.',
        category: 'Game',
        attributes: [
            { name: 'sheet', description: '', required: true, type: 'string' },
            { name: 'frame', description: '', type: 'number', default: '0' },
            { name: 'y', description: 'where its top is on the screen', type: 'number', default: '0' },
            { name: 'scroll', description: 'how fast it scrolls across with the camera: 0 stays still, 1 moves with the level', type: 'number', default: '0' },
            { name: 'repeat', description: 'repeats across, so it never ends', type: 'boolean', default: 'true' },
        ]
    },
    {
        name: 'sprite',
        namespace: 'qg',
        description: 'A picture in the scene, with no behaviour: a backdrop, a divider, a sign.',
        category: 'Game',
        attributes: [
            { name: 'sheet', description: '', required: true, type: 'string' },
            { name: 'frame', description: 'a number, or an expression the picture follows tick by tick: `{1 if hurt > 0 else 0}`', type: 'expression', default: '0' },
            { name: 'x', description: '', required: true, type: 'number' },
            { name: 'y', description: '', required: true, type: 'number' },
        ]
    },
    {
        name: 'emitter',
        namespace: 'qg',
        description: 'A qg:particles effect that keeps going in the scene: rain across its width, a fire on a spot.',
        category: 'Game',
        attributes: [
            { name: 'particles', description: '', required: true, type: 'string' },
            { name: 'x', description: '', required: true, type: 'number' },
            { name: 'y', description: '', required: true, type: 'number' },
            { name: 'width', description: 'rain and snow: the band they fall across, pixels (0: a point)', type: 'number', default: '0' },
        ]
    },
    {
        name: 'exit',
        namespace: 'qg',
        description: 'A rectangle that leads to another scene; the character arrives at the exit named at= there.',
        category: 'Game',
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'x', description: '', required: true, type: 'number' },
            { name: 'y', description: '', required: true, type: 'number' },
            { name: 'width', description: '', required: true, type: 'number' },
            { name: 'height', description: '', required: true, type: 'number' },
            { name: 'to', description: '', required: true, type: 'string' },
            { name: 'at', description: '', required: true, type: 'string' },
        ]
    },
    {
        name: 'camera',
        namespace: 'qg',
        description: 'What the screen shows: it follows a character, or the middle of several, in the game\'s ticks (a replay and every peer frame the same). Only seen: nothing in the game\'s state depends on it.',
        category: 'Game',
        attributes: [
            { name: 'follow', description: 'a character id, or several: "p1, p2" (their middle)', required: true, type: 'string' },
            { name: 'bounds', description: '', type: 'enum', values: ['tilemap', 'none'], default: 'tilemap' },
            { name: 'zoom', description: '2: twice as close', type: 'number', default: '1' },
            { name: 'dead-zone', description: 'WxH: the box about the middle of the screen in which the followed one moves before the camera does', type: 'string' },
            { name: 'lead', description: 'pixels it looks ahead, the way the followed one goes', type: 'number', default: '0' },
            { name: 'smooth', description: 'how fast it catches up, per second (0: at once)', type: 'number', default: '0' },
            { name: 'fit', description: 'several followed: it zooms out to keep them all on the screen, down to zoom-min, and back in as they come together', type: 'boolean', default: 'false' },
            { name: 'zoom-min', description: 'fit: as far out as it goes', type: 'number', default: '0.5' },
            { name: 'player', description: 'one view per player: this is that player\'s. On one machine the screen splits (side by side for two, quarters for three or four); over the network each machine shows its own player\'s. A camera that follows no one present has no view', type: 'number' },
        ]
    },
    {
        name: 'hud',
        namespace: 'qg',
        description: 'Text and pictures over the game.',
        category: 'Game',
        allowedChildren: ['qg:table', 'qg:icon', 'qg:counter', 'qg:text', 'qg:inventory', 'qg:bar'],
        attributes: [
            { name: 'position', description: '', type: 'enum', values: ['top-left', 'top-center', 'top-right', 'center', 'bottom-left', 'bottom-center', 'bottom-right'], default: 'top-left' },
            { name: 'x', description: 'with y=, its top-left corner on the screen, in pixels (in place of position=): a panel of a screen laid out by hand', type: 'number' },
            { name: 'y', description: '', type: 'number' },
            { name: 'box', description: 'a qg:spritesheet with slice=: what it shows is in a box drawn with it, stretched (a frame)', type: 'string' },
            { name: 'font', description: 'a .ttf, relative to the .q or a folder above it', type: 'string' },
            { name: 'size', description: 'the font size of its items, unless an item says otherwise', type: 'number', default: '8' },
            { name: 'if', description: 'shown only while this is true', type: 'expression' },
        ]
    },
    {
        name: 'table',
        namespace: 'qg',
        description: 'Rows from the state in the HUD, a line each, in columns: a squad, a league table, a shop, the best scores. source= is read every frame; each qg:column is an expression of the row (as=). With a monospaced font the columns line up as on a text screen.',
        category: 'Game',
        allowedChildren: ['qg:column'],
        attributes: [
            { name: 'source', description: 'a list: of records, numbers, texts', required: true, type: 'expression' },
            { name: 'as', description: 'the name of the row in the columns\' expressions', required: true, type: 'string' },
            { name: 'rows', description: 'at most so many rows shown, from the first (0: all of them)', type: 'number', default: '0' },
        ]
    },
    {
        name: 'column',
        namespace: 'qg',
        description: 'A column of a qg:table: its heading and, for each row, what it shows.',
        category: 'Game',
        attributes: [
            { name: 'value', description: 'an expression of the row', required: true, type: 'expression' },
            { name: 'label', description: 'its heading (a table whose columns have none has no heading row)', type: 'string', default: '' },
            { name: 'width', description: 'how many characters wide: a longer text is cut, a shorter one padded', type: 'number', default: '8' },
            { name: 'align', description: 'right: numbers', type: 'enum', values: ['left', 'right'], default: 'left' },
            { name: 'color', description: '#rrggbb, or an expression of the row giving one (red when negative)', type: 'string' },
        ]
    },
    {
        name: 'icon',
        namespace: 'qg',
        description: 'A picture in the HUD: a frame of a sheet (a heart before the hearts, a logo on a title).',
        category: 'Game',
        attributes: [
            { name: 'sheet', description: 'a qg:spritesheet or qg:tileset', required: true, type: 'string' },
            { name: 'frame', description: 'a frame of it, or an expression read every frame', type: 'expression', default: '0' },
            { name: 'scale', description: 'how large: 2 is twice its size', type: 'number', default: '1' },
        ]
    },
    {
        name: 'counter',
        namespace: 'qg',
        description: 'A number from the scene state, or how many of an item the players hold, in the HUD.',
        category: 'Game',
        attributes: [
            { name: 'bind', description: 'a q:set of the scene or the game (or item=)', type: 'string' },
            { name: 'item', description: 'a qg:item: how many are held (or bind=)', type: 'string' },
            { name: 'label', description: 'text before the number', type: 'string', default: '' },
            { name: 'size', description: 'font size', type: 'number' },
            { name: 'color', description: 'its colour (#rrggbb)', type: 'string' },
        ]
    },
    {
        name: 'text',
        namespace: 'qg',
        description: 'A string from the scene state, in the HUD.',
        category: 'Game',
        attributes: [
            { name: 'bind', description: 'a q:set of the scene (or value=)', type: 'string' },
            { name: 'value', description: 'an expression, read every frame (or bind=)', type: 'expression' },
            { name: 'size', description: 'font size', type: 'number' },
            { name: 'color', description: 'its colour: #rrggbb, or an expression giving one, read every frame (red when a balance is below zero)', type: 'string' },
        ]
    },
    {
        name: 'on-collision',
        namespace: 'qg',
        description: 'What happens when this character or prefab touches something. Holds actions and statements; `me` is the toucher, `other` what it touched. In a prefab, only the game state is in reach.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'with', description: 'the tag of what it touches', required: true, type: 'string' },
            { name: 'side', description: 'top: landing on it; bottom: hitting it from below; left: hitting it from its left (it is to the right); right: from its right. A side handler runs before the "any" one, which then does not', type: 'enum', values: ['any', 'top', 'bottom', 'left', 'right'], default: 'any' },
            { name: 'cooldown', description: 'ticks before this handler can fire again', type: 'number', default: '0' },
        ]
    },
    {
        name: 'on-damage',
        namespace: 'qg',
        description: 'What happens when this prefab takes qg:damage and lives (`me.health` is what is left).',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
        ]
    },
    {
        name: 'on-death',
        namespace: 'qg',
        description: 'What happens when this prefab\'s health reaches 0, before it goes. In a scene, with of=, when any thing of that tag dies there.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'of', description: 'scene: the tag', type: 'string' },
        ]
    },
    {
        name: 'label',
        namespace: 'qg',
        description: 'Text in the world, read every tick: over a character or a prefab, following it (a name over a player, what an enemy has left), or at a place of the scene (a sign). Only seen.',
        category: 'Game',
        attributes: [
            { name: 'value', description: 'an expression; on a character or a prefab, `me` is it', required: true, type: 'expression' },
            { name: 'x', description: 'in a scene: where its middle is', type: 'number' },
            { name: 'y', description: '', type: 'number' },
            { name: 'dx', description: 'on a character or a prefab: how far from its middle', type: 'number', default: '0' },
            { name: 'dy', description: '', type: 'number', default: '-12' },
            { name: 'size', description: '', type: 'number', default: '8' },
            { name: 'color', description: '', type: 'string', default: '#ffffff' },
            { name: 'if', description: 'placed only when this is true as the scene is built', type: 'expression' },
        ]
    },
    {
        name: 'light',
        namespace: 'qg',
        description: 'A light: a torch on a wall, a lantern a character carries, the glow of a gem. In a scene with ambient= it is what can be seen; elsewhere it brightens what it reaches. Only seen: the game\'s state never reads it.',
        category: 'Game',
        attributes: [
            { name: 'x', description: 'in a scene: where it is', type: 'number' },
            { name: 'y', description: '', type: 'number' },
            { name: 'dx', description: 'on a character or a prefab: how far from its middle', type: 'number', default: '0' },
            { name: 'dy', description: '', type: 'number', default: '0' },
            { name: 'radius', description: 'how far it reaches, pixels', type: 'number', default: '64' },
            { name: 'color', description: '', type: 'string', default: '#ffffff' },
            { name: 'energy', description: 'how bright: 1 as drawn, 2 twice', type: 'number', default: '1' },
            { name: 'flicker', description: '0 to 1: how much it flickers, as a flame does (the same in every replay)', type: 'number', default: '0' },
            { name: 'shadows', description: 'the solid tiles of a scene with ambient= stop it, and cast shadows', type: 'boolean', default: 'false' },
        ]
    },
    {
        name: 'when',
        namespace: 'qg',
        description: 'Runs its handler when a condition turns true: a wave beaten (`count(\'enemy\') == 0`), a room solved, a score reached. The condition is read at the start of every tick, from the scene\'s first, after the qg:afters due then (not while the scene is paused); the handler runs on the tick it is first true, and again only after it has been false. Holds actions and statements.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'condition', description: 'an expression of the scene\'s state', required: true, type: 'expression' },
        ]
    },
    {
        name: 'timer',
        namespace: 'qg',
        description: 'Runs its handler after so many ticks, or every so many ticks, in this scene.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'after', description: 'ticks from entering the scene, once', type: 'number' },
            { name: 'every', description: 'ticks between runs, from entering the scene (or from=)', type: 'number' },
            { name: 'from', description: 'every: the tick the count starts at', type: 'number', default: '0' },
            { name: 'count', description: 'every: stop after this many runs (0: never)', type: 'number', default: '0' },
        ]
    },
    {
        name: 'spawner',
        namespace: 'qg',
        description: 'Places count instances of a prefab, one every so many ticks, from a tick on.',
        category: 'Game',
        attributes: [
            { name: 'prefab', description: 'a prefab name, or several comma-separated: one is drawn from the seed for each instance', required: true, type: 'string' },
            { name: 'from', description: 'the tick of the first one', type: 'number', default: '0' },
            { name: 'every', description: '', type: 'number', default: '60' },
            { name: 'count', description: '0: no end', type: 'number', default: '1' },
            { name: 'x', description: 'a number, or random across the scene width (from the seed)', type: 'string', default: 'random' },
            { name: 'y', description: '', type: 'number', default: '-12' },
            { name: 'along', description: 'edges: instead of x,y, a random point on the scene\'s border', type: 'enum', values: ['edges'] },
            { name: 'heading', description: 'along: a flying prefab heads into the scene...', type: 'enum', values: ['inward'] },
            { name: 'spread', description: '...turned by up to this many degrees either way, from the seed', type: 'number', default: '0' },
        ]
    },
    {
        name: 'map-node',
        namespace: 'qg',
        description: 'A place on a world map. With scene=, pressing jump there enters that scene.',
        category: 'Game',
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'x', description: '', required: true, type: 'number' },
            { name: 'y', description: '', required: true, type: 'number' },
            { name: 'sheet', description: '', required: true, type: 'string' },
            { name: 'frame', description: '', type: 'number', default: '0' },
            { name: 'scene', description: '', type: 'string' },
        ]
    },
    {
        name: 'map-path',
        namespace: 'qg',
        description: 'A way between two map nodes, both directions.',
        category: 'Game',
        attributes: [
            { name: 'from', description: '', required: true, type: 'string' },
            { name: 'to', description: '', required: true, type: 'string' },
            { name: 'requires', description: 'a scene name that must be in the game state `cleared`', type: 'string' },
        ]
    },
    {
        name: 'on-input',
        namespace: 'qg',
        description: 'What happens when the player presses an action in this scene, or lets it go (on="release"); or, with sequence=, when a player presses several in order in a short time — a special move: "down, forward, punch" holds on the tick punch is pressed, if down and then forward were pressed before it within within= ticks (other presses between them do not matter, and the presses it uses are used up). "forward" and "back" are right and left as that player\'s character faces. Holds actions and statements.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'action', description: 'a default action, or one a qg:input declares; or sequence=', type: 'string' },
            { name: 'on', description: 'press: as it goes down; release: as it is let go', type: 'enum', values: ['press', 'release'], default: 'press' },
            { name: 'sequence', description: 'actions in the order pressed, separated by commas; forward and back follow the way the player\'s character faces', type: 'string' },
            { name: 'within', description: 'sequence: how many ticks from its first press to its last (60 a second)', type: 'number', default: '30' },
            { name: 'player', description: 'sequence: whose presses', type: 'number', default: '1' },
        ]
    },
    {
        name: 'on-hit',
        namespace: 'qg',
        description: 'What happens when this character\'s swing (attack-action) reaches something. Holds actions and statements.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'with', description: 'the tag of what it hits', required: true, type: 'string' },
        ]
    },
    {
        name: 'on-fall',
        namespace: 'qg',
        description: 'What happens when this character falls below the tilemap. Holds actions and statements.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
        ]
    },
    {
        name: 'move',
        namespace: 'qg',
        description: 'A fighter\'s attack, on an action: an animation with one active frame, in which a box of reach= at at= (in front, in the facing direction) is tested against the opponent once. A hit takes damage=, stuns for stun= ticks and pushes push= pixels; blocked (the opponent holding away), it takes no damage and half the rest.',
        category: 'Game',
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'action', description: 'a default action or one a qg:input declares', required: true, type: 'string' },
            { name: 'frames', description: 'comma-separated frame numbers', required: true, type: 'string' },
            { name: 'fps', description: '', type: 'number', default: '12' },
            { name: 'active', description: 'which frame (0-based) hits', type: 'number', default: '1' },
            { name: 'reach', description: 'the hit box, WxH', required: true, type: 'string' },
            { name: 'at', description: 'the hit box\'s centre from the body\'s, dx,dy; dx is forward', type: 'string', default: '0,0' },
            { name: 'damage', description: '', type: 'number', default: '5' },
            { name: 'stun', description: '', type: 'number', default: '12' },
            { name: 'push', description: '', type: 'number', default: '40' },
        ]
    },
    {
        name: 'behavior',
        namespace: 'qg',
        description: 'What a character controller="behavior" is made of: parts, each a small rule. A platformer is qg:gravity, qg:walk and qg:jump; a top-down walker is qg:walk axis="both"; a flapping bird is qg:gravity and a qg:jump with air=; a ship that comes back round the screen is qg:walk axis="both" and qg:wrap. Each tick, whatever their order: walk and jump read the keys, gravity pulls, the body moves, then keep-inside, wrap and face. `me.vx`, `me.vy` and `me.on_floor` read it; qg:velocity sets its speed from the game\'s rules (a dash, a knock-back), so what no part covers is written in the game. In a qg:prefab ai="behavior", an enemy\'s parts instead: what it moves by is the first of qg:seek, qg:flee, qg:keep-distance, qg:patrol, qg:wander and qg:stand, in their order, whose when= holds and that has something to do (a seek with nothing in sight has not); it stands when none has. Its qg:shoot parts fire besides. `me.doing` reads the part that moved it ("" for none). With qg:gravity the enemy walks on floors: the parts move it left and right only, a seek goes straight, the prefab\'s turns-at="edge" keeps it from walking off a ledge, and qg:leap jumps; `me.on_floor` reads whether it stands.',
        category: 'Game',
        allowedChildren: ['qg:gravity', 'qg:walk', 'qg:jump', 'qg:steer', 'qg:keep-inside', 'qg:wrap', 'qg:face', 'qg:seek', 'qg:flee', 'qg:keep-distance', 'qg:patrol', 'qg:wander', 'qg:leap', 'qg:stand', 'qg:shoot'],
        attributes: [
        ]
    },
    {
        name: 'gravity',
        namespace: 'qg',
        description: 'A part: it falls, and stands on floors (without it, the body floats: top-down). A character\'s or an enemy\'s.',
        category: 'Game',
        attributes: [
            { name: 'strength', description: 'pixels per second squared', type: 'number', default: '900' },
            { name: 'max-fall', description: 'the speed it falls at most, pixels per second', type: 'number', default: '300' },
        ]
    },
    {
        name: 'walk',
        namespace: 'qg',
        description: 'A part: left and right (and up and down, with axis="both") set its speed.',
        category: 'Game',
        attributes: [
            { name: 'speed', description: 'pixels per second', type: 'number', default: '90' },
            { name: 'accel', description: 'pixels per second squared towards the speed (0: at once)', type: 'number', default: '0' },
            { name: 'axis', description: 'x: across only (with gravity); both: in eight directions', type: 'enum', values: ['x', 'both'], default: 'x' },
        ]
    },
    {
        name: 'jump',
        namespace: 'qg',
        description: 'A part: a press on the floor leaps; with air=, also in the air. It needs qg:gravity.',
        category: 'Game',
        attributes: [
            { name: 'action', description: 'a default action, or one a qg:input declares', type: 'string', default: 'jump' },
            { name: 'height', description: 'pixels, with the button held', type: 'number', default: '64' },
            { name: 'speed', description: 'the take-off speed, pixels per second, instead of height=', type: 'number' },
            { name: 'coyote', description: 'ticks after leaving a ledge in which a jump still works', type: 'number', default: '6' },
            { name: 'buffer', description: 'a press up to this many ticks before landing jumps as it lands (0: only a press on the floor)', type: 'number', default: '0' },
            { name: 'air', description: 'jumps it may take in the air before landing again', type: 'number', default: '0' },
            { name: 'variable', description: 'letting go while rising cuts the leap', type: 'boolean', default: 'true' },
            { name: 'cut', description: 'letting go multiplies the rise by this, once (0: three times the gravity while it rises instead)', type: 'number', default: '0' },
            { name: 'sound', description: 'a qg:sound, played on take-off', type: 'string' },
        ]
    },
    {
        name: 'steer',
        namespace: 'qg',
        description: 'A part: left and right turn the body, up pushes it the way it points and down holds it back; it drifts, and slows by drag= on its own. Its picture turns with it. An Asteroids ship, a car seen from above, a horse. It needs no qg:walk.',
        category: 'Game',
        attributes: [
            { name: 'turn', description: 'degrees a second', type: 'number', default: '180' },
            { name: 'thrust', description: 'pixels per second, added every second up is held', type: 'number', default: '200' },
            { name: 'drag', description: 'the part of its speed it loses every second on its own (0: none, it drifts for ever)', type: 'number', default: '1' },
            { name: 'max', description: 'its top speed, pixels per second', type: 'number', default: '160' },
            { name: 'heading', description: 'where it points at first, degrees: 0 right, 90 down', type: 'number', default: '0' },
        ]
    },
    {
        name: 'keep-inside',
        namespace: 'qg',
        description: 'A part: the scene\'s edges stop it.',
        category: 'Game',
        attributes: [
        ]
    },
    {
        name: 'wrap',
        namespace: 'qg',
        description: 'A part: past an edge of the scene, it comes back on the other side.',
        category: 'Game',
        attributes: [
        ]
    },
    {
        name: 'face',
        namespace: 'qg',
        description: 'A part: its picture turns left or right the way it goes.',
        category: 'Game',
        attributes: [
            { name: 'by', description: 'velocity: the way it moves; input: the way it is pushed (it faces while it walks into a wall)', type: 'enum', values: ['velocity', 'input'], default: 'velocity' },
        ]
    },
    {
        name: 'seek',
        namespace: 'qg',
        description: 'An enemy\'s part: it goes for the nearest target it notices, around the walls by the shortest way over the tilemap\'s free cells (way="straight": straight at it).',
        category: 'Game',
        attributes: [
            { name: 'target', description: 'a character\'s id or a thing\'s tag; none: any character', type: 'string' },
            { name: 'sight', description: 'pixels it notices a target within (else the prefab\'s sight=)', type: 'number' },
            { name: 'through-walls', description: 'it notices a target behind a solid tile (else only one it sees)', type: 'boolean', default: 'false' },
            { name: 'way', description: '', type: 'enum', values: ['around', 'straight'], default: 'around' },
            { name: 'speed', description: 'pixels per second (else the prefab\'s speed=)', type: 'number' },
            { name: 'when', description: 'only while this is true (`me` is the enemy)', type: 'expression' },
        ]
    },
    {
        name: 'flee',
        namespace: 'qg',
        description: 'An enemy\'s part: it runs from the nearest one it notices, straight away from it.',
        category: 'Game',
        attributes: [
            { name: 'from', description: 'a character\'s id or a thing\'s tag; none: any character', type: 'string' },
            { name: 'sight', description: 'pixels (else the prefab\'s sight=)', type: 'number' },
            { name: 'through-walls', description: '', type: 'boolean', default: 'false' },
            { name: 'speed', description: '', type: 'number' },
            { name: 'when', description: '', type: 'expression' },
        ]
    },
    {
        name: 'keep-distance',
        namespace: 'qg',
        description: 'An enemy\'s part: it keeps between min= and max= pixels from the nearest one it notices: away when closer, towards it when farther, and still in between.',
        category: 'Game',
        attributes: [
            { name: 'from', description: 'a character\'s id or a thing\'s tag; none: any character', type: 'string' },
            { name: 'min', description: '', required: true, type: 'number' },
            { name: 'max', description: '', required: true, type: 'number' },
            { name: 'sight', description: 'pixels (else the prefab\'s sight=)', type: 'number' },
            { name: 'through-walls', description: '', type: 'boolean', default: 'false' },
            { name: 'speed', description: '', type: 'number' },
            { name: 'when', description: '', type: 'expression' },
        ]
    },
    {
        name: 'patrol',
        namespace: 'qg',
        description: 'An enemy\'s part: to and fro along a line, turning at walls (and after distance= pixels).',
        category: 'Game',
        attributes: [
            { name: 'heading', description: 'where it goes first (else the prefab\'s direction=)', type: 'enum', values: ['left', 'right', 'up', 'down'] },
            { name: 'distance', description: 'pixels before it turns (0: only at walls)', type: 'number', default: '0' },
            { name: 'speed', description: '', type: 'number' },
            { name: 'when', description: '', type: 'expression' },
        ]
    },
    {
        name: 'wander',
        namespace: 'qg',
        description: 'An enemy\'s part: a new heading every 30 to 90 ticks (from the scene seed), and at once on bumping a wall.',
        category: 'Game',
        attributes: [
            { name: 'speed', description: '', type: 'number' },
            { name: 'when', description: '', type: 'expression' },
        ]
    },
    {
        name: 'leap',
        namespace: 'qg',
        description: 'An enemy\'s part, with qg:gravity: it jumps, from the floor, when it bumps a wall as it walks (a step to climb) or while its when= holds; at most once every every= ticks.',
        category: 'Game',
        attributes: [
            { name: 'height', description: 'pixels', type: 'number', default: '40' },
            { name: 'at-wall', description: 'it jumps on bumping a wall as it walks', type: 'boolean', default: 'true' },
            { name: 'every', description: 'ticks between two leaps at least', type: 'number', default: '30' },
            { name: 'sound', description: '', type: 'string' },
            { name: 'when', description: 'it jumps while this is true too (`me` is the enemy)', type: 'expression' },
        ]
    },
    {
        name: 'stand',
        namespace: 'qg',
        description: 'An enemy\'s part: it stands still; the parts after it wait.',
        category: 'Game',
        attributes: [
            { name: 'when', description: '', type: 'expression' },
        ]
    },
    {
        name: 'shoot',
        namespace: 'qg',
        description: 'An enemy\'s part: it fires prefab= at the nearest target within range=, headed at it, at most once every every= ticks. It shoots whatever part moves it.',
        category: 'Game',
        attributes: [
            { name: 'prefab', description: 'what it fires: a prefab with ai="fly"', required: true, type: 'string' },
            { name: 'at', description: 'a character\'s id or a thing\'s tag; none: any character', type: 'string' },
            { name: 'every', description: 'ticks between shots', type: 'number', default: '60' },
            { name: 'range', description: 'pixels', type: 'number', default: '100' },
            { name: 'through-walls', description: 'it fires at a target behind a solid tile (else only one it sees)', type: 'boolean', default: 'false' },
            { name: 'sound', description: '', type: 'string' },
            { name: 'when', description: '', type: 'expression' },
        ]
    },
    {
        name: 'on-tile',
        namespace: 'qg',
        description: 'What happens while this character touches a tile of a kind (qg:tile kind=): stands on it, is in it, or bumps it. Holds actions and statements; `me` is the character. Without a cooldown, once as it comes to touch one; with one, again each time the cooldown runs out while it still does.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'kind', description: '', required: true, type: 'enum', values: ['ladder', 'water', 'ice', 'hurt'] },
            { name: 'cooldown', description: 'ticks before it may run again while still touching', type: 'number', default: '0' },
        ]
    },
    {
        name: 'on-animation-end',
        namespace: 'qg',
        description: 'What happens when an animation of this character or prefab with loop="false" has played to its last frame. Holds actions and statements; `me` is whose animation it is.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'name', description: 'the animation', required: true, type: 'string' },
        ]
    },
    {
        name: 'on-ko',
        namespace: 'qg',
        description: 'What happens when this fighter\'s health reaches 0. Holds actions and statements; `me` is the loser, `other` the winner.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
        ]
    },
    {
        name: 'inventory',
        namespace: 'qg',
        description: 'In the HUD: the items held, each its picture (the qg:item\'s sheet= and frame=) and how many, in a row; an item held 0 times is not shown.',
        category: 'Game',
        attributes: [
            { name: 'size', description: 'the font size of the numbers', type: 'number' },
        ]
    },
    {
        name: 'bar',
        namespace: 'qg',
        description: 'A bar in the HUD: a number against its maximum — a q:set, or a fighter\'s health as `id.health`.',
        category: 'Game',
        attributes: [
            { name: 'bind', description: 'a q:set of the scene or the game, or a fighter\'s id and .health (p1.health)', required: true, type: 'string' },
            { name: 'max', description: '', type: 'number', default: '100' },
            { name: 'width', description: '', type: 'number', default: '100' },
            { name: 'height', description: '', type: 'number', default: '10' },
            { name: 'color', description: '', type: 'string', default: '#e04040' },
        ]
    },
    {
        name: 'on-locked',
        namespace: 'qg',
        description: 'What happens when a character bumps this prefab (opens-with=) without the item. Holds actions and statements; `me` is the locked thing, `other` the character.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
        ]
    },
    {
        name: 'give',
        namespace: 'qg',
        description: 'The players get some of an item (up to its max=).',
        category: 'Game',
        attributes: [
            { name: 'item', description: 'a qg:item', required: true, type: 'string' },
            { name: 'amount', description: '', type: 'number', default: '1' },
        ]
    },
    {
        name: 'take',
        namespace: 'qg',
        description: 'The players spend some of an item (not below 0): a potion drunk, a key used.',
        category: 'Game',
        attributes: [
            { name: 'item', description: 'a qg:item', required: true, type: 'string' },
            { name: 'amount', description: '', type: 'number', default: '1' },
        ]
    },
    {
        name: 'for-each',
        namespace: 'qg',
        description: 'Runs what it holds once for every thing of a tag in the scene, in the scene\'s order, with var= naming the thing: freeze every enemy, break the bricks near a bomb. The things are those there as it starts; one destroyed meanwhile is skipped.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'tag', description: 'the things\' tag', required: true, type: 'string' },
            { name: 'var', description: 'the name of each thing in turn (a target=, an expression)', type: 'string', default: 'it' },
        ]
    },
    {
        name: 'camera-to',
        namespace: 'qg',
        description: 'The camera goes to a thing or a point, stays a while, and comes back to what it follows: a cutscene, a boss\'s entrance, the gate a lever opened. The scene waits meanwhile (unless pause="false"). The scene needs a qg:camera (in a q:function of the game, a scene without one is not shown anything).',
        category: 'Game',
        attributes: [
            { name: 'target', description: 'me, other, a character or cursor id, or a parameter, loop variable or q:set holding a thing (or x= and y=)', type: 'string' },
            { name: 'x', description: '', type: 'expression' },
            { name: 'y', description: 'a point of the scene instead', type: 'expression' },
            { name: 'zoom', description: 'how close it goes (the camera\'s own when not given)', type: 'number' },
            { name: 'seconds', description: 'to go there, and as long to come back', type: 'number', default: '0.6' },
            { name: 'hold', description: 'seconds it stays', type: 'number', default: '1' },
            { name: 'pause', description: 'the scene waits while the camera is away', type: 'boolean', default: 'true' },
        ]
    },
    {
        name: 'attach',
        namespace: 'qg',
        description: 'A thing is carried by another: it goes where its carrier goes, dx,dy from it (a key over a head, a torch in a hand, a turret on a tank). While carried it touches nothing and nothing touches it, and it stands in no cell; `carrying(me, \'key\')` finds it.',
        category: 'Game',
        attributes: [
            { name: 'target', description: 'what is carried: other, me, a character id, or a parameter, loop variable or q:set holding a thing', type: 'string', default: 'other' },
            { name: 'to', description: 'its carrier, the same', type: 'string', default: 'me' },
            { name: 'dx', description: '', type: 'number', default: '0' },
            { name: 'dy', description: 'from the carrier\'s middle', type: 'number', default: '-12' },
        ]
    },
    {
        name: 'detach',
        namespace: 'qg',
        description: 'A carried thing is put down where it is (qg:attach): it touches again.',
        category: 'Game',
        attributes: [
            { name: 'target', description: 'what is put down (or from= and tag=)', type: 'string' },
            { name: 'from', description: 'the carrier: me, other, a character id...', type: 'string' },
            { name: 'tag', description: 'with from=: every thing of this tag it carries', type: 'string' },
        ]
    },
    {
        name: 'beam',
        namespace: 'qg',
        description: 'A line between two things for a while, following them as they move: a laser, a zap, a rope, an aiming line. Only seen.',
        category: 'Game',
        attributes: [
            { name: 'from', description: 'me, other, a character or cursor id, or a parameter, loop variable or q:set holding a thing', type: 'string', default: 'me' },
            { name: 'to', description: 'the same', required: true, type: 'string' },
            { name: 'seconds', description: 'how long it shows', type: 'number', default: '0.1' },
            { name: 'color', description: '', type: 'string', default: '#ffffff' },
            { name: 'width', description: 'pixels', type: 'number', default: '2' },
        ]
    },
    {
        name: 'after',
        namespace: 'qg',
        description: 'Runs what it holds later, so many ticks (or seconds) after the handler reached it: a power-up that runs out, a bomb\'s fuse, a pause before the next serve. It counts the game\'s ticks, so a replay and every peer see the same; it waits while the scene is paused, and goes with the scene. The names it reads (me, other, a loop variable, a parameter) are what they were as it started; a thing gone by then is null, and an action on it does nothing.',
        category: 'Game',
        allowedChildren: ['qg:give', 'qg:take', 'qg:for-each', 'qg:camera-to', 'qg:attach', 'qg:detach', 'qg:beam', 'qg:after', 'qg:time-scale', 'qg:open-url', 'qg:quit', 'qg:watch', 'qg:start-now', 'qg:reset-items', 'qg:destroy', 'qg:bounce', 'qg:play-animation', 'qg:play', 'qg:music', 'qg:stop', 'qg:respawn', 'qg:deflect', 'qg:become', 'qg:spawn', 'qg:swap', 'qg:checkpoint', 'qg:damage', 'qg:burst', 'qg:rumble', 'qg:shake', 'qg:tween', 'qg:travel', 'qg:velocity', 'qg:set-tile', 'qg:emit', 'qg:put', 'qg:host', 'qg:join', 'qg:leave', 'qg:pause', 'qg:resume', 'qg:say', 'qg:goto-scene', 'qg:save', 'qg:next-language', 'qg:continue', 'qg:volume', 'qg:fullscreen'],
        attributes: [
            { name: 'ticks', description: 'how many ticks from now (60 a second)', type: 'expression' },
            { name: 'seconds', description: 'or how many seconds, rounded to ticks', type: 'expression' },
            { name: 'name', description: 'one of this name still waiting is replaced: the count starts again (a second power-up before the first runs out)', type: 'string' },
        ]
    },
    {
        name: 'time-scale',
        namespace: 'qg',
        description: 'Slow motion, or fast: the whole game runs at this speed — its ticks come further apart (or closer), each the same tick as ever, so a replay and every peer see the same game. The music is not slowed. A new scene starts at 1.',
        category: 'Game',
        attributes: [
            { name: 'scale', description: '0.25: four times slower; 1: as usual; up to 4', required: true, type: 'number' },
            { name: 'seconds', description: 'seconds as the player sees them, then back to 1 (0: until another qg:time-scale)', type: 'number', default: '0' },
        ]
    },
    {
        name: 'open-url',
        namespace: 'qg',
        description: 'Opens a web address in the player\'s browser: a new tab when the game runs in a browser, the system\'s browser elsewhere (a changelog, the game\'s page, its credits). Only http:// and https:// addresses. When an agent plays it (the play protocol, a replay) it opens nothing: the "open-url" event says what it would have opened.',
        category: 'Game',
        attributes: [
            { name: 'href', description: 'the address, or an expression ({...}) that gives one', required: true, type: 'string' },
        ]
    },
    {
        name: 'quit',
        namespace: 'qg',
        description: 'Ends the game: the window closes. In a browser there is nothing to quit to and it does nothing; `can_quit()` says whether it would.',
        category: 'Game',
        attributes: [
        ]
    },
    {
        name: 'watch',
        namespace: 'qg',
        description: 'Joins a networked game at an address with no seat, to watch it: the players\' inputs reach this machine too, and it runs the same game, its keys doing nothing. One who comes after the game has begun catches up on it first. `net_status()` is then "watching" and `net_player()` 0. Not under rollback=.',
        category: 'Game',
        attributes: [
            { name: 'address', description: 'host:port, or a relay\'s wss:// room', required: true, type: 'expression' },
        ]
    },
    {
        name: 'start-now',
        namespace: 'qg',
        description: 'The host starts the networked game with the players who are there, once qg:multiplayer\'s min-players= are (before that, and on the other machines, it does nothing). The lobby has a Start now button that does this.',
        category: 'Game',
        attributes: [
        ]
    },
    {
        name: 'reset-items',
        namespace: 'qg',
        description: 'A new game: every qg:item back to its start=, and the named things picked up or opened come back.',
        category: 'Game',
        attributes: [
        ]
    },
    {
        name: 'destroy',
        namespace: 'qg',
        description: 'Removes a thing from the scene.',
        category: 'Game',
        attributes: [
            { name: 'target', description: 'other, me, or a q:set holding a thing (thing_at)', type: 'string', default: 'other' },
        ]
    },
    {
        name: 'bounce',
        namespace: 'qg',
        description: 'Throws the character up, as after a stomp.',
        category: 'Game',
        attributes: [
            { name: 'target', description: '', type: 'enum', values: ['me'], default: 'me' },
            { name: 'height', description: 'pixels', type: 'number', default: '32' },
        ]
    },
    {
        name: 'play-animation',
        namespace: 'qg',
        description: 'Plays an animation of a thing or a character from its first frame. Its own animations (idle, walk...) wait until it ends; a looping one holds until the next qg:play-animation, and name="" gives it its own animations back.',
        category: 'Game',
        attributes: [
            { name: 'target', description: 'me, other, a character id, or a q:set holding a thing', type: 'string', default: 'me' },
            { name: 'name', description: 'an animation of the target (empty: back to its own)', required: true, type: 'string' },
        ]
    },
    {
        name: 'play',
        namespace: 'qg',
        description: 'Plays a qg:sound. Directly in a scene: as the scene is entered. With volume=, pitch= or vary=, it plays in a voice of its own, so the same sound can overlap itself. With sounds=, one of several, drawn each time (footsteps, hits that do not all sound alike). Only heard: the game\'s state records the sound\'s name (sounds= as written), never how it was played nor which one.',
        category: 'Game',
        attributes: [
            { name: 'sound', description: 'a qg:sound; or sounds=', type: 'string' },
            { name: 'sounds', description: 'several qg:sounds, separated by commas: one of them each time', type: 'string' },
            { name: 'volume', description: 'decibels added (-6: about half as loud)', type: 'number', default: '0' },
            { name: 'pitch', description: '2: an octave up, 0.5: an octave down', type: 'number', default: '1' },
            { name: 'vary', description: 'a random pitch between pitch - vary and pitch + vary, each time: twenty hits that do not sound the same', type: 'number', default: '0' },
            { name: 'at', description: 'heard from where a thing is (me, other, a character id, or a parameter holding one): softer and to one side the farther it is from the middle of the screen, silent two screens away. A thing\'s own sounds (its fire-sound, a leap\'s or a shot\'s sound=) are heard where it is', type: 'string' },
        ]
    },
    {
        name: 'music',
        namespace: 'qg',
        description: 'The music of a scene: a looping qg:sound that plays while the scene is on. Going to a scene with other music crossfades from one to the other; a scene with the same music lets it play on; a scene with none fades it out. In a handler, it changes the music there and then, crossfading over fade= (a boss\'s theme as the fight starts, the scene\'s own back as it ends). Only heard, like a sound.',
        category: 'Game',
        attributes: [
            { name: 'sound', description: 'a qg:sound with loop="true"', required: true, type: 'string' },
            { name: 'fade', description: 'seconds the crossfade takes', type: 'number', default: '1' },
            { name: 'volume', description: 'decibels (0: as recorded; -6: half as loud)', type: 'number', default: '0' },
        ]
    },
    {
        name: 'stop',
        namespace: 'qg',
        description: 'Stops a qg:sound (a looping one, mostly). Directly in a scene: as the scene is entered.',
        category: 'Game',
        attributes: [
            { name: 'sound', description: '', required: true, type: 'string' },
        ]
    },
    {
        name: 'respawn',
        namespace: 'qg',
        description: 'Puts a character back at its start or its last checkpoint, still; a thing back where it was placed, with its first heading and speed.',
        category: 'Game',
        attributes: [
            { name: 'target', description: 'me, other, or a character of the scene by id', type: 'string', default: 'me' },
        ]
    },
    {
        name: 'deflect',
        namespace: 'qg',
        description: 'Changes where a flying thing (ai="fly") goes: flips one axis of its heading, or sets the heading to dx,dy (expressions; the length does not matter).',
        category: 'Game',
        attributes: [
            { name: 'target', description: 'other, me, or a parameter, loop variable or q:set holding a thing', type: 'string', default: 'other' },
            { name: 'axis', description: 'the axis to flip', type: 'enum', values: ['x', 'y'] },
            { name: 'dx', description: '', type: 'expression' },
            { name: 'dy', description: '', type: 'expression' },
        ]
    },
    {
        name: 'become',
        namespace: 'qg',
        description: 'Changes a character or a thing to one of its qg:states.',
        category: 'Game',
        attributes: [
            { name: 'target', description: 'other, me, or a parameter, loop variable or q:set holding a thing', type: 'string', default: 'me' },
            { name: 'state', description: '', required: true, type: 'string' },
        ]
    },
    {
        name: 'spawn',
        namespace: 'qg',
        description: 'Places a new prefab instance in the scene.',
        category: 'Game',
        attributes: [
            { name: 'prefab', description: '', required: true, type: 'string' },
            { name: 'at', description: 'whose position: other, me, a character id, or a parameter, loop variable or q:set holding a thing; cursor: where the qg:on-select cursor is; path: the start of path=', type: 'string', default: 'other' },
            { name: 'path', description: 'at="path": a qg:path of the scene, which an ai="path" prefab follows', type: 'string' },
            { name: 'x', description: 'a point of the scene instead of at= (with y=): an expression, in pixels', type: 'expression' },
            { name: 'y', description: '', type: 'expression' },
            { name: 'dx', description: '', type: 'number', default: '0' },
            { name: 'dy', description: 'offset in pixels', type: 'number', default: '0' },
            { name: 'heading', description: 'an ai="fly" prefab: the way it goes, as x,y, each an expression (`{aim.x - me.x},{aim.y - me.y}`: at the pointer), instead of its own', type: 'string' },
        ]
    },
    {
        name: 'swap',
        namespace: 'qg',
        description: 'Replaces a thing with an instance of another prefab, in its place.',
        category: 'Game',
        attributes: [
            { name: 'target', description: 'other, or a q:set holding a thing', type: 'string', default: 'other' },
            { name: 'prefab', description: '', required: true, type: 'string' },
        ]
    },
    {
        name: 'checkpoint',
        namespace: 'qg',
        description: 'Makes the other thing\'s position where the character respawns.',
        category: 'Game',
        attributes: [
            { name: 'target', description: '', type: 'enum', values: ['me'], default: 'me' },
            { name: 'at', description: '', type: 'enum', values: ['other'], default: 'other' },
        ]
    },
    {
        name: 'damage',
        namespace: 'qg',
        description: 'Takes health from a thing; at 0 its qg:on-death runs and it goes.',
        category: 'Game',
        attributes: [
            { name: 'target', description: 'other, me, or a parameter, loop variable or q:set holding a thing', type: 'string', default: 'other' },
            { name: 'amount', description: '', type: 'expression', default: '1' },
        ]
    },
    {
        name: 'burst',
        namespace: 'qg',
        description: 'A puff of particles where a thing is. Cosmetic.',
        category: 'Game',
        attributes: [
            { name: 'at', description: 'other, me, or a parameter, loop variable or q:set holding a thing', type: 'string', default: 'me' },
            { name: 'color', description: '', type: 'string', default: '#ffffff' },
            { name: 'count', description: '', type: 'number', default: '12' },
        ]
    },
    {
        name: 'rumble',
        namespace: 'qg',
        description: 'A player\'s joypad shakes (and a phone, in the hand): a hit felt. Felt only, like a shake: nothing in the game depends on it. Over the network only the machine of that player\'s seat feels it; on one machine, player N\'s is the Nth joypad connected.',
        category: 'Game',
        attributes: [
            { name: 'player', description: 'whose joypad', type: 'expression', default: '1' },
            { name: 'strength', description: '0 to 1', type: 'number', default: '0.5' },
            { name: 'seconds', description: '', type: 'number', default: '0.2' },
        ]
    },
    {
        name: 'shake',
        namespace: 'qg',
        description: 'Shakes the scene a thing is in. Cosmetic.',
        category: 'Game',
        attributes: [
            { name: 'at', description: 'other, me, or a parameter, loop variable or q:set holding a thing', type: 'string', default: 'me' },
            { name: 'frames', description: '', type: 'number', default: '10' },
            { name: 'strength', description: 'pixels', type: 'number', default: '3' },
        ]
    },
    {
        name: 'tween',
        namespace: 'qg',
        description: 'Eases a property of a thing from what it is to a value, over some seconds: a coin that rises, a door that slides, a pulse. It runs in the game\'s ticks, so a replay and every peer see the same; it stops while the scene is paused, and a new tween of the same property replaces it.',
        category: 'Game',
        allowedChildren: ['qg:on-end'],
        attributes: [
            { name: 'target', description: 'me, other, a character id, or a q:set holding a thing', type: 'string', default: 'me' },
            { name: 'property', description: 'x, y: where it is (collisions see it); rotation (degrees), scale, scale-x and scale-y (across and up: a squash, a stretch), alpha, tint (a colour its picture is multiplied by: #ffffff is as drawn): its picture', required: true, type: 'enum', values: ['x', 'y', 'rotation', 'scale', 'scale-x', 'scale-y', 'alpha', 'tint'] },
            { name: 'to', description: 'a number, or for tint a colour (#rrggbb)', required: true, type: 'expression' },
            { name: 'from', description: 'where it starts (what it is now when not given)', type: 'expression' },
            { name: 'seconds', description: '', type: 'number', default: '0.5' },
            { name: 'trans', description: 'the curve', type: 'enum', values: ['linear', 'sine', 'quad', 'cubic', 'back', 'bounce', 'elastic'], default: 'sine' },
            { name: 'ease', description: 'which end of the curve is slow', type: 'enum', values: ['in', 'out', 'in-out'], default: 'out' },
            { name: 'repeat', description: 'times it plays again (-1: for ever)', type: 'number', default: '0' },
            { name: 'yoyo', description: 'each repeat goes back the other way', type: 'boolean', default: 'false' },
        ]
    },
    {
        name: 'travel',
        namespace: 'qg',
        description: 'A thing travels to a place by the cheapest way over the scene\'s qg:tilemap (qg:tile cost=), round the things and characters on it and where other travels end, a cell at a time: a unit of a tactics game. Its qg:on-end runs as it arrives (`me` the traveller); with no way, at once, where it is. In the game\'s ticks, so a replay and every peer see the same; a new travel of the same thing replaces it.',
        category: 'Game',
        allowedChildren: ['qg:on-end'],
        attributes: [
            { name: 'target', description: 'me, other, a parameter, a loop variable or a q:set holding a thing', type: 'string', default: 'me' },
            { name: 'to', description: 'a cursor (its cell), or a thing or character (up to it, beside it)', required: true, type: 'expression' },
            { name: 'budget', description: 'how much of the way\'s cost it may spend: it stops where the next step would cost more (all the way when not given)', type: 'expression' },
            { name: 'step', description: 'ticks a cell', type: 'number', default: '10' },
        ]
    },
    {
        name: 'velocity',
        namespace: 'qg',
        description: 'Sets the speed of a character controller="behavior", in pixels per second: a dash, a knock-back, a wind, a spring. An axis not given keeps its speed. Its parts go on from there (gravity pulls it back down; walk sets the speed across again on the next tick, unless it has accel=).',
        category: 'Game',
        attributes: [
            { name: 'target', description: 'me, other, or a character id', type: 'string', default: 'me' },
            { name: 'x', description: '', type: 'expression' },
            { name: 'y', description: '', type: 'expression' },
        ]
    },
    {
        name: 'set-tile',
        namespace: 'qg',
        description: 'Puts a tile in a cell of the scene\'s tilemap, or empties it: a block that breaks, a door drawn as tiles. Its collision changes from the next tick, monsters that pathfind find their way again, and the cells changed are part of the game\'s state (a replay, every peer). `tile_at(col, row)` reads a cell.',
        category: 'Game',
        attributes: [
            { name: 'col', description: 'the column, from 0 at the left', required: true, type: 'expression' },
            { name: 'row', description: 'the row, from 0 at the top', required: true, type: 'expression' },
            { name: 'tile', description: 'as in the rows of qg:tilemap: 0 nothing, n tile n-1 of the tileset, -n the same flipped', type: 'expression', default: '0' },
            { name: 'layer', description: 'a layer\'s name (a Tiled map\'s); the first with collision, else the first, when not given', type: 'string' },
        ]
    },
    {
        name: 'emit',
        namespace: 'qg',
        description: 'Plays a qg:particles effect once where a thing is, or a text that floats up from it and fades (a damage number, +10). Only seen: the game\'s state never depends on it.',
        category: 'Game',
        attributes: [
            { name: 'particles', description: 'the effect (or text=)', type: 'string' },
            { name: 'text', description: 'a text instead: "+10", or an expression (`{str(amount)}`)', type: 'expression' },
            { name: 'color', description: 'the text\'s colour', type: 'string', default: '#ffffff' },
            { name: 'size', description: 'the text\'s size', type: 'number', default: '8' },
            { name: 'at', description: 'me, other, a character id, or a q:set holding a thing', type: 'string', default: 'me' },
            { name: 'dx', description: '', type: 'number', default: '0' },
            { name: 'dy', description: 'offset in pixels', type: 'number', default: '0' },
        ]
    },
    {
        name: 'put',
        namespace: 'qg',
        description: 'Moves a thing or a character to a point, at once.',
        category: 'Game',
        attributes: [
            { name: 'target', description: 'me, other, a character id, or a q:set holding a thing (thing_at)', type: 'string', default: 'other' },
            { name: 'x', description: '', required: true, type: 'expression' },
            { name: 'y', description: '', required: true, type: 'expression' },
        ]
    },
    {
        name: 'lobby',
        namespace: 'qg',
        description: 'The usual networked-game menu, ready made: play here (local=), host, an address field, join, cancel, and a line that says where things are. It is a qg:menu and a qg:hud the compiler writes; the address is the scene\'s `lobby_address`.',
        category: 'Game',
        attributes: [
            { name: 'local', description: 'a scene to play on this machine alone (a button for it when given)', type: 'string' },
            { name: 'local-label', description: '', type: 'string', default: 'Play here' },
            { name: 'port', description: '', type: 'number', default: '7777' },
            { name: 'address', description: 'what the address field starts with, unless the web page\'s address has ?join=...', type: 'string', default: '127.0.0.1:7777' },
            { name: 'font', description: '', type: 'string' },
            { name: 'size', description: '', type: 'number', default: '16' },
            { name: 'options', description: 'a scene of the game\'s options (how loud, the full screen, the keys): an Options button goes there', type: 'string' },
        ]
    },
    {
        name: 'host',
        namespace: 'qg',
        description: 'Hosts the networked game (qg:multiplayer): this machine is player 1 and waits for the others; the game starts in the start= scene when they are all there. `net_status()` says where things are.',
        category: 'Game',
        attributes: [
            { name: 'port', description: '', type: 'number', default: '7777' },
        ]
    },
    {
        name: 'join',
        namespace: 'qg',
        description: 'Joins a networked game at an address: host:port, or a quantum relay\'s room (wss://relay.example/pong/ROOM, where two browsers meet); this machine is the next player.',
        category: 'Game',
        attributes: [
            { name: 'address', description: 'an expression: a q:set a qg:field fills, or text', required: true, type: 'expression' },
        ]
    },
    {
        name: 'leave',
        namespace: 'qg',
        description: 'Leaves the networked game, or stops hosting or joining.',
        category: 'Game',
        attributes: [
        ]
    },
    {
        name: 'pause',
        namespace: 'qg',
        description: 'Pauses the scene: its characters, things, timers and spawners stop where they are. Menus, the HUD, the camera and qg:on-input go on, so a key or a button can resume it. `paused()` says whether it is.',
        category: 'Game',
        attributes: [
        ]
    },
    {
        name: 'resume',
        namespace: 'qg',
        description: 'Goes on with a paused scene.',
        category: 'Game',
        attributes: [
        ]
    },
    {
        name: 'say',
        namespace: 'qg',
        description: 'Opens a qg:dialogue of the scene: its lines one at a time, select for the next. The scene is paused while it is open (`talking()` says so); after the last line, its qg:on-end runs.',
        category: 'Game',
        attributes: [
            { name: 'dialogue', description: '', required: true, type: 'string' },
        ]
    },
    {
        name: 'goto-scene',
        namespace: 'qg',
        description: 'Leaves this scene for another, at the end of the tick. Scene state is lost; game state stays.',
        category: 'Game',
        attributes: [
            { name: 'name', description: '', required: true, type: 'string' },
            { name: 'fade', description: 'seconds the new scene takes to come out of black (0: a cut); only the picture fades, the game runs from its first tick as without it', type: 'number', default: '0' },
        ]
    },
    {
        name: 'save',
        namespace: 'qg',
        description: 'Saves the game to continue it later: the game state (every q:set of q:application) and a scene to come back to. Kept between runs (in a browser, by the browser); a new qg:save replaces it. `has_save()` says whether there is one. A networked game is not saved.',
        category: 'Game',
        attributes: [
            { name: 'scene', description: 'the scene to continue in (none: this one); it starts over, what was in it is not saved', type: 'string' },
            { name: 'slot', description: 'which of several saves (1, 2, 3...: a game each); the scenes with save="true" save into it from then on. None: the one save', type: 'expression' },
        ]
    },
    {
        name: 'next-language',
        namespace: 'qg',
        description: 'Shows the game in its next language (qg:language), after its own: a button for it is `<qg:button label="{tr(\'Language\') + \': \' + language()}">`. The choice is kept for the next run. Only what is shown changes.',
        category: 'Game',
        attributes: [
        ]
    },
    {
        name: 'continue',
        namespace: 'qg',
        description: 'Continues the saved game (qg:save): its game state back, and on to its scene. Nothing when there is no save.',
        category: 'Game',
        attributes: [
            { name: 'slot', description: 'which save (qg:save slot=); the scenes with save="true" save into it from then on. None: the one save', type: 'expression' },
        ]
    },
    {
        name: 'volume',
        namespace: 'qg',
        description: 'How loud a bus of the game\'s sounds is, from 0 (silent) to 100; kept between runs. `volume(\'music\')` reads it. Only heard.',
        category: 'Game',
        attributes: [
            { name: 'bus', description: 'a bus of the game\'s sounds (qg:sound bus=)', required: true, type: 'string' },
            { name: 'value', description: '0 to 100', required: true, type: 'expression' },
        ]
    },
    {
        name: 'fullscreen',
        namespace: 'qg',
        description: 'The game fills the screen, or goes back to a window; kept between runs. `fullscreen()` reads it. In a browser, the page goes full screen.',
        category: 'Game',
        attributes: [
            { name: 'on', description: 'true or false; none: the other of what it is', type: 'expression' },
        ]
    },
    {
        name: 'touch-button',
        namespace: 'qg',
        description: 'A button on a touch screen that presses one of the game\'s actions while it is touched, as a key would (a replay and the lockstep see the action). In the application, every scene has it.',
        category: 'Game',
        attributes: [
            { name: 'action', description: 'an action of the game', required: true, type: 'string' },
            { name: 'x', description: '', required: true, type: 'number' },
            { name: 'y', description: 'its middle, on the screen', required: true, type: 'number' },
            { name: 'size', description: 'its width across, in pixels', type: 'number', default: '32' },
            { name: 'label', description: 'a letter or a word on it', type: 'string', default: '' },
            { name: 'player', description: 'whose action', type: 'number', default: '1' },
            { name: 'show', description: 'touch: only on a device with a touch screen', type: 'enum', values: ['touch', 'always'], default: 'touch' },
        ]
    },
    {
        name: 'touch-stick',
        namespace: 'qg',
        description: 'A stick on a touch screen: dragged from its middle, it presses left, right, up and down as far as it is pushed (strength()). In the application, every scene has it.',
        category: 'Game',
        attributes: [
            { name: 'x', description: '', required: true, type: 'number' },
            { name: 'y', description: 'its middle, on the screen', required: true, type: 'number' },
            { name: 'size', description: 'its width across, in pixels', type: 'number', default: '56' },
            { name: 'player', description: 'whose directions', type: 'number', default: '1' },
            { name: 'show', description: 'touch: only on a device with a touch screen', type: 'enum', values: ['touch', 'always'], default: 'touch' },
        ]
    },
    // END GENERATED
];

// Combine all tags for lookup
export const allTags: TagSchema[] = [...quantumTags, ...uiTags, ...gameTags];

// Create lookup maps for quick access
export const tagsByName: Map<string, TagSchema> = new Map(
    allTags.map(tag => [`${tag.namespace}:${tag.name}`, tag])
);

export const tagsByNamespace: Map<string, TagSchema[]> = new Map([
    ['q', quantumTags],
    ['ui', uiTags],
    ['qg', gameTags],
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
export function getTagsInNamespace(namespace: 'q' | 'ui' | 'qg' | 'qt'): TagSchema[] {
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
