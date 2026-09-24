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
        description: 'A source of a q:knowledge, read whole (IA-8)',
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
