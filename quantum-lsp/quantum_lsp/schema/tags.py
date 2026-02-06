"""
Quantum Tag Definitions

Complete schema for all Quantum framework tags organized by namespace.
"""

from typing import Dict, List, Optional
from .types import TagInfo, AttributeInfo, AttributeType


def _attr(
    name: str,
    type: AttributeType = AttributeType.STRING,
    required: bool = False,
    default: Optional[str] = None,
    description: str = "",
    enum_values: List[str] = None
) -> AttributeInfo:
    """Helper to create AttributeInfo."""
    return AttributeInfo(
        name=name,
        type=type,
        required=required,
        default=default,
        description=description,
        enum_values=enum_values or []
    )


# =============================================================================
# QUANTUM CORE TAGS (q: namespace)
# =============================================================================

Q_COMPONENT = TagInfo(
    name="component",
    namespace="q",
    description="Defines a reusable Quantum component. Components are the building blocks of Quantum applications.",
    attributes={
        "name": _attr("name", required=True, description="Component name (PascalCase recommended)"),
        "type": _attr("type", type=AttributeType.ENUM, default="pure",
                     enum_values=["pure", "microservice", "event-driven", "worker", "websocket", "graphql", "grpc", "serverless"],
                     description="Component type defining its runtime behavior"),
        "port": _attr("port", type=AttributeType.INTEGER, description="Port number for microservice components"),
        "basePath": _attr("basePath", description="Base URL path for REST endpoints"),
        "health": _attr("health", description="Health check endpoint path"),
        "metrics": _attr("metrics", description="Metrics provider (prometheus, datadog)"),
        "trace": _attr("trace", description="Tracing provider (jaeger, zipkin)"),
        "require_auth": _attr("require_auth", type=AttributeType.BOOLEAN, default="false",
                             description="Require authentication to access this component"),
        "require_role": _attr("require_role", description="Required role(s) for access (comma-separated)"),
        "require_permission": _attr("require_permission", description="Required permission(s) for access"),
        "interactive": _attr("interactive", type=AttributeType.BOOLEAN, default="false",
                            description="Enable client-side hydration for interactivity"),
    },
    children=["q:param", "q:return", "q:function", "q:onEvent", "q:script", "q:set", "q:if", "q:loop", "q:query", "q:import"],
    examples=[
        '<q:component name="UserProfile" type="pure">\n  <q:param name="userId" type="integer" required="true" />\n</q:component>',
        '<q:component name="UserService" type="microservice" port="8080">\n  <q:function name="getUsers" endpoint="/users" method="GET">\n  </q:function>\n</q:component>',
    ],
    see_also=["q:application", "q:function", "q:param"]
)

Q_APPLICATION = TagInfo(
    name="application",
    namespace="q",
    description="Defines a Quantum application. Applications can be HTML, game, terminal, testing, or UI type.",
    attributes={
        "id": _attr("id", required=True, description="Unique application identifier"),
        "type": _attr("type", type=AttributeType.ENUM, default="html",
                     enum_values=["html", "game", "terminal", "testing", "ui"],
                     description="Application type"),
        "engine": _attr("engine", description="Engine variant (e.g., '2d' for game type)"),
        "theme": _attr("theme", description="Theme preset for UI applications"),
    },
    children=["q:route", "q:component"],
    examples=[
        '<q:application id="myApp" type="html">\n  <q:route path="/" method="GET" />\n</q:application>',
        '<q:application id="myGame" type="game" engine="2d">\n</q:application>',
    ],
    see_also=["q:component", "q:route"]
)

Q_SET = TagInfo(
    name="set",
    namespace="q",
    description="Declares or modifies a variable. Supports multiple data types, validation, and operations.",
    attributes={
        "name": _attr("name", required=True, description="Variable name"),
        "value": _attr("value", type=AttributeType.EXPRESSION, description="Value to assign (supports databinding)"),
        "type": _attr("type", type=AttributeType.ENUM, default="string",
                     enum_values=["string", "integer", "decimal", "boolean", "array", "struct", "date", "datetime"],
                     description="Data type of the variable"),
        "default": _attr("default", description="Default value if not set"),
        "scope": _attr("scope", type=AttributeType.ENUM, default="local",
                      enum_values=["local", "component", "session", "application", "request"],
                      description="Variable scope"),
        "operation": _attr("operation", type=AttributeType.ENUM, default="assign",
                          enum_values=["assign", "increment", "decrement", "add", "remove", "append", "prepend", "toggle", "clear"],
                          description="Operation to perform"),
        "required": _attr("required", type=AttributeType.BOOLEAN, default="false",
                         description="Whether the variable is required"),
        "validate": _attr("validate", description="Validation rule (email, url, etc.)"),
        "pattern": _attr("pattern", type=AttributeType.REGEX, description="Regex pattern for validation"),
        "min": _attr("min", description="Minimum value"),
        "max": _attr("max", description="Maximum value"),
        "minlength": _attr("minlength", type=AttributeType.INTEGER, description="Minimum string length"),
        "maxlength": _attr("maxlength", type=AttributeType.INTEGER, description="Maximum string length"),
        "enum": _attr("enum", description="Allowed values (comma-separated)"),
        "persist": _attr("persist", type=AttributeType.ENUM,
                        enum_values=["local", "session", "sync"],
                        description="Persistence mode for state"),
        "persistKey": _attr("persistKey", description="Custom key for persistent storage"),
        "persistEncrypt": _attr("persistEncrypt", type=AttributeType.BOOLEAN, default="false",
                               description="Encrypt persisted value"),
    },
    examples=[
        '<q:set name="counter" type="integer" value="0" />',
        '<q:set name="items" type="array" value="[]" />',
        '<q:set name="counter" operation="increment" />',
        '<q:set name="email" type="string" validate="email" required="true" />',
    ],
    see_also=["q:param", "q:loop", "q:if"]
)

Q_IF = TagInfo(
    name="if",
    namespace="q",
    description="Conditional execution. Supports elseif and else blocks.",
    attributes={
        "condition": _attr("condition", type=AttributeType.EXPRESSION, required=True,
                          description="Boolean expression to evaluate"),
    },
    children=["q:elseif", "q:else", "q:set", "q:loop", "q:query", "q:return"],
    examples=[
        '<q:if condition="{user.isAdmin}">\n  <p>Admin content</p>\n</q:if>',
        '<q:if condition="{age >= 18}">\n  <p>Adult</p>\n  <q:else>\n    <p>Minor</p>\n  </q:else>\n</q:if>',
    ],
    see_also=["q:elseif", "q:else", "q:loop"]
)

Q_ELSEIF = TagInfo(
    name="elseif",
    namespace="q",
    description="Else-if branch within a q:if block.",
    attributes={
        "condition": _attr("condition", type=AttributeType.EXPRESSION, required=True,
                          description="Boolean expression to evaluate"),
    },
    parent_tags=["q:if"],
    examples=['<q:elseif condition="{age >= 13}">\n  <p>Teen</p>\n</q:elseif>'],
    see_also=["q:if", "q:else"]
)

Q_ELSE = TagInfo(
    name="else",
    namespace="q",
    description="Else branch within a q:if block. Executed when all conditions are false.",
    parent_tags=["q:if"],
    examples=['<q:else>\n  <p>Default content</p>\n</q:else>'],
    see_also=["q:if", "q:elseif"]
)

Q_LOOP = TagInfo(
    name="loop",
    namespace="q",
    description="Iterates over ranges, arrays, lists, or query results.",
    attributes={
        "var": _attr("var", required=True, description="Loop variable name"),
        "type": _attr("type", type=AttributeType.ENUM, default="range",
                     enum_values=["range", "array", "list", "query", "object"],
                     description="Type of iteration"),
        "from": _attr("from", type=AttributeType.INTEGER, description="Start value for range loops"),
        "to": _attr("to", type=AttributeType.INTEGER, description="End value for range loops"),
        "step": _attr("step", type=AttributeType.INTEGER, default="1", description="Step value for range loops"),
        "items": _attr("items", type=AttributeType.EXPRESSION, description="Array or list to iterate"),
        "query": _attr("query", description="Query result to iterate (shorthand for type='query')"),
        "index": _attr("index", description="Variable name for current index"),
        "delimiter": _attr("delimiter", default=",", description="Delimiter for list loops"),
    },
    examples=[
        '<q:loop var="i" type="range" from="1" to="10">\n  <p>Item {i}</p>\n</q:loop>',
        '<q:loop var="user" type="array" items="{users}">\n  <p>{user.name}</p>\n</q:loop>',
        '<q:loop query="users">\n  <tr><td>{users.name}</td></tr>\n</q:loop>',
    ],
    see_also=["q:if", "q:set", "q:query"]
)

Q_FUNCTION = TagInfo(
    name="function",
    namespace="q",
    description="Defines a function within a component. Can be exposed as REST endpoint.",
    attributes={
        "name": _attr("name", required=True, description="Function name"),
        "returnType": _attr("returnType", type=AttributeType.ENUM, default="any",
                           enum_values=["any", "void", "string", "integer", "decimal", "boolean", "array", "struct", "query"],
                           description="Return type"),
        "scope": _attr("scope", type=AttributeType.ENUM, default="component",
                      enum_values=["component", "public", "private"],
                      description="Function visibility scope"),
        "access": _attr("access", type=AttributeType.ENUM, default="public",
                       enum_values=["public", "private", "protected"],
                       description="Access modifier"),
        "description": _attr("description", description="Function documentation"),
        "hint": _attr("hint", description="Short hint for IDE"),
        "cache": _attr("cache", type=AttributeType.BOOLEAN, description="Cache function results"),
        "memoize": _attr("memoize", type=AttributeType.BOOLEAN, default="false",
                        description="Memoize function calls"),
        "pure": _attr("pure", type=AttributeType.BOOLEAN, default="false",
                     description="Mark as pure function (no side effects)"),
        "async": _attr("async", type=AttributeType.BOOLEAN, default="false",
                      description="Async function execution"),
        "timeout": _attr("timeout", description="Execution timeout (e.g., '30s')"),
        "retry": _attr("retry", type=AttributeType.INTEGER, description="Number of retries on failure"),
        "endpoint": _attr("endpoint", description="REST endpoint path"),
        "method": _attr("method", type=AttributeType.ENUM,
                       enum_values=["GET", "POST", "PUT", "DELETE", "PATCH"],
                       description="HTTP method for REST endpoint"),
        "produces": _attr("produces", default="application/json",
                         description="Response content type"),
        "consumes": _attr("consumes", default="application/json",
                         description="Request content type"),
        "auth": _attr("auth", description="Authentication requirement"),
        "roles": _attr("roles", description="Required roles (comma-separated)"),
        "rateLimit": _attr("rateLimit", description="Rate limit (e.g., '100/minute')"),
        "cors": _attr("cors", type=AttributeType.BOOLEAN, description="Enable CORS"),
    },
    children=["q:param", "q:return", "q:set", "q:if", "q:loop", "q:query"],
    examples=[
        '<q:function name="greet" returnType="string">\n  <q:param name="name" type="string" />\n  <q:return value="Hello, {name}!" />\n</q:function>',
        '<q:function name="getUsers" endpoint="/users" method="GET">\n  <q:query name="users" datasource="db">SELECT * FROM users</q:query>\n  <q:return value="{users}" />\n</q:function>',
    ],
    see_also=["q:param", "q:return", "q:component"]
)

Q_PARAM = TagInfo(
    name="param",
    namespace="q",
    description="Declares a parameter for components, functions, queries, or actions.",
    attributes={
        "name": _attr("name", required=True, description="Parameter name"),
        "type": _attr("type", type=AttributeType.ENUM, default="string",
                     enum_values=["string", "integer", "decimal", "boolean", "array", "struct", "date", "datetime", "binary", "email", "url"],
                     description="Parameter data type"),
        "required": _attr("required", type=AttributeType.BOOLEAN, default="false",
                         description="Whether the parameter is required"),
        "default": _attr("default", description="Default value"),
        "value": _attr("value", type=AttributeType.EXPRESSION,
                      description="Value expression (for query params)"),
        "description": _attr("description", description="Parameter documentation"),
        "source": _attr("source", type=AttributeType.ENUM, default="auto",
                       enum_values=["auto", "path", "query", "body", "header", "cookie"],
                       description="Parameter source for REST endpoints"),
        "validate": _attr("validate", description="Validation rule"),
        "pattern": _attr("pattern", type=AttributeType.REGEX, description="Regex pattern"),
        "min": _attr("min", description="Minimum value"),
        "max": _attr("max", description="Maximum value"),
        "minlength": _attr("minlength", type=AttributeType.INTEGER, description="Minimum length"),
        "maxlength": _attr("maxlength", type=AttributeType.INTEGER, description="Maximum length"),
        "enum": _attr("enum", description="Allowed values (comma-separated)"),
        "accept": _attr("accept", description="Accepted file types for binary"),
        "maxsize": _attr("maxsize", description="Maximum file size"),
    },
    self_closing=True,
    examples=[
        '<q:param name="userId" type="integer" required="true" />',
        '<q:param name="email" type="email" required="true" validate="email" />',
        '<q:param name="status" type="string" enum="active,inactive,pending" default="active" />',
    ],
    see_also=["q:function", "q:component", "q:query"]
)

Q_RETURN = TagInfo(
    name="return",
    namespace="q",
    description="Returns a value from a function or route.",
    attributes={
        "value": _attr("value", type=AttributeType.EXPRESSION, required=True,
                      description="Value to return"),
        "type": _attr("type", type=AttributeType.ENUM, default="string",
                     enum_values=["string", "integer", "decimal", "boolean", "array", "struct", "query", "json"],
                     description="Return type"),
        "name": _attr("name", description="Named return for multiple values"),
        "description": _attr("description", description="Return value documentation"),
    },
    self_closing=True,
    examples=[
        '<q:return value="{result}" />',
        '<q:return value="Success" type="string" />',
    ],
    see_also=["q:function"]
)

Q_QUERY = TagInfo(
    name="query",
    namespace="q",
    description="Executes a database query with automatic parameter binding.",
    attributes={
        "name": _attr("name", required=True, description="Query result variable name"),
        "datasource": _attr("datasource", description="Database connection name"),
        "source": _attr("source", description="Source query for Query-of-Queries"),
        "cache": _attr("cache", type=AttributeType.BOOLEAN, default="false",
                      description="Cache query results"),
        "ttl": _attr("ttl", type=AttributeType.INTEGER, description="Cache TTL in seconds"),
        "reactive": _attr("reactive", type=AttributeType.BOOLEAN, default="false",
                         description="Enable reactive updates"),
        "interval": _attr("interval", type=AttributeType.INTEGER,
                         description="Polling interval in ms for reactive"),
        "paginate": _attr("paginate", type=AttributeType.BOOLEAN, default="false",
                         description="Enable automatic pagination"),
        "page": _attr("page", type=AttributeType.INTEGER, default="1",
                     description="Current page number"),
        "pageSize": _attr("pageSize", type=AttributeType.INTEGER, default="20",
                         description="Items per page"),
        "timeout": _attr("timeout", type=AttributeType.INTEGER, description="Query timeout in ms"),
        "maxrows": _attr("maxrows", type=AttributeType.INTEGER, description="Maximum rows to return"),
        "result": _attr("result", description="Variable for query metadata"),
        "mode": _attr("mode", type=AttributeType.ENUM, enum_values=["rag"],
                     description="Query mode (rag for RAG pipeline)"),
        "model": _attr("model", description="LLM model for RAG queries"),
    },
    children=["q:param"],
    examples=[
        '<q:query name="users" datasource="db">\n  SELECT * FROM users WHERE active = true\n</q:query>',
        '<q:query name="user" datasource="db">\n  SELECT * FROM users WHERE id = :userId\n  <q:param name="userId" value="{userId}" type="integer" />\n</q:query>',
    ],
    see_also=["q:param", "q:loop", "q:transaction"]
)

Q_INVOKE = TagInfo(
    name="invoke",
    namespace="q",
    description="Invokes a function, component method, or external HTTP endpoint.",
    attributes={
        "name": _attr("name", required=True, description="Result variable name"),
        "function": _attr("function", description="Function name to call"),
        "component": _attr("component", description="Component containing the function"),
        "url": _attr("url", type=AttributeType.URL, description="External URL to call"),
        "endpoint": _attr("endpoint", description="REST endpoint path"),
        "service": _attr("service", description="Service name for service discovery"),
        "method": _attr("method", type=AttributeType.ENUM, default="GET",
                       enum_values=["GET", "POST", "PUT", "DELETE", "PATCH"],
                       description="HTTP method"),
        "contentType": _attr("contentType", default="application/json",
                            description="Request content type"),
        "authType": _attr("authType", type=AttributeType.ENUM,
                         enum_values=["none", "basic", "bearer", "api-key"],
                         description="Authentication type"),
        "authToken": _attr("authToken", description="Auth token value"),
        "timeout": _attr("timeout", type=AttributeType.INTEGER, description="Request timeout in ms"),
        "retry": _attr("retry", type=AttributeType.INTEGER, description="Retry count"),
        "retryDelay": _attr("retryDelay", type=AttributeType.INTEGER, description="Delay between retries in ms"),
        "responseFormat": _attr("responseFormat", type=AttributeType.ENUM, default="auto",
                               enum_values=["auto", "json", "xml", "text", "binary"],
                               description="Expected response format"),
        "cache": _attr("cache", type=AttributeType.BOOLEAN, default="false",
                      description="Cache response"),
        "ttl": _attr("ttl", type=AttributeType.INTEGER, description="Cache TTL in seconds"),
    },
    children=["q:header", "q:param", "q:body"],
    examples=[
        '<q:invoke name="result" function="calculateTotal" />',
        '<q:invoke name="data" url="https://api.example.com/users" method="GET" />',
    ],
    see_also=["q:function", "q:query"]
)

Q_IMPORT = TagInfo(
    name="import",
    namespace="q",
    description="Imports a component for use within the current component.",
    attributes={
        "component": _attr("component", required=True, description="Component name to import"),
        "from": _attr("from", type=AttributeType.PATH, description="Path to component file"),
        "as": _attr("as", description="Alias name for the imported component"),
    },
    self_closing=True,
    examples=[
        '<q:import component="Header" />',
        '<q:import component="Button" from="./components/ui" />',
        '<q:import component="AdminLayout" as="Layout" />',
    ],
    see_also=["q:component", "q:slot"]
)

Q_SLOT = TagInfo(
    name="slot",
    namespace="q",
    description="Defines a content projection slot for component composition.",
    attributes={
        "name": _attr("name", default="default", description="Slot name"),
    },
    examples=[
        '<q:slot />',
        '<q:slot name="header" />',
        '<q:slot name="footer">\n  <p>Default footer content</p>\n</q:slot>',
    ],
    see_also=["q:import", "q:component"]
)

Q_ACTION = TagInfo(
    name="action",
    namespace="q",
    description="Defines a form action handler with validation and CSRF protection.",
    attributes={
        "name": _attr("name", required=True, description="Action name"),
        "method": _attr("method", type=AttributeType.ENUM, default="POST",
                       enum_values=["POST", "PUT", "DELETE", "PATCH"],
                       description="HTTP method"),
        "csrf": _attr("csrf", type=AttributeType.BOOLEAN, default="true",
                     description="Enable CSRF protection"),
        "rate_limit": _attr("rate_limit", description="Rate limit (e.g., '10/minute')"),
        "require_auth": _attr("require_auth", type=AttributeType.BOOLEAN, default="false",
                             description="Require authentication"),
    },
    children=["q:param", "q:query", "q:set", "q:redirect", "q:flash"],
    examples=[
        '<q:action name="createUser" method="POST">\n  <q:param name="email" type="email" required="true" />\n  <q:query datasource="db">\n    INSERT INTO users (email) VALUES (:email)\n    <q:param name="email" value="{email}" type="string" />\n  </q:query>\n  <q:redirect url="/users" flash="User created!" />\n</q:action>',
    ],
    see_also=["q:redirect", "q:flash", "q:query"]
)

Q_REDIRECT = TagInfo(
    name="redirect",
    namespace="q",
    description="Redirects to another URL, optionally with a flash message.",
    attributes={
        "url": _attr("url", type=AttributeType.URL, required=True, description="Target URL"),
        "flash": _attr("flash", description="Flash message to display"),
        "status": _attr("status", type=AttributeType.INTEGER, default="302",
                       description="HTTP status code (301, 302, 303, 307, 308)"),
    },
    self_closing=True,
    examples=[
        '<q:redirect url="/thank-you" />',
        '<q:redirect url="/products" flash="Product created successfully" />',
    ],
    see_also=["q:action", "q:flash"]
)

Q_FLASH = TagInfo(
    name="flash",
    namespace="q",
    description="Sets a flash message to be displayed once after redirect.",
    attributes={
        "type": _attr("type", type=AttributeType.ENUM, default="info",
                     enum_values=["info", "success", "warning", "error"],
                     description="Message type"),
        "message": _attr("message", description="Message text (or use tag content)"),
    },
    examples=[
        '<q:flash type="success" message="Operation completed!" />',
        '<q:flash type="error">An error occurred</q:flash>',
    ],
    see_also=["q:redirect", "q:action"]
)

Q_LOG = TagInfo(
    name="log",
    namespace="q",
    description="Logs a message for debugging or monitoring.",
    attributes={
        "message": _attr("message", type=AttributeType.EXPRESSION,
                        description="Log message (supports databinding)"),
        "level": _attr("level", type=AttributeType.ENUM, default="info",
                      enum_values=["debug", "info", "warn", "error"],
                      description="Log level"),
        "var": _attr("var", description="Variable to dump"),
    },
    self_closing=True,
    examples=[
        '<q:log message="Processing user {userId}" level="debug" />',
        '<q:log var="userData" level="info" />',
    ],
    see_also=["q:dump"]
)

Q_DUMP = TagInfo(
    name="dump",
    namespace="q",
    description="Dumps a variable's contents for debugging.",
    attributes={
        "var": _attr("var", required=True, description="Variable to dump"),
        "label": _attr("label", description="Label for the dump output"),
        "format": _attr("format", type=AttributeType.ENUM, default="auto",
                       enum_values=["auto", "json", "table", "tree"],
                       description="Output format"),
    },
    self_closing=True,
    examples=[
        '<q:dump var="users" />',
        '<q:dump var="config" label="Configuration" format="json" />',
    ],
    see_also=["q:log"]
)

Q_TRANSACTION = TagInfo(
    name="transaction",
    namespace="q",
    description="Wraps queries in a database transaction for atomic operations.",
    attributes={
        "isolationLevel": _attr("isolationLevel", type=AttributeType.ENUM, default="READ_COMMITTED",
                               enum_values=["READ_UNCOMMITTED", "READ_COMMITTED", "REPEATABLE_READ", "SERIALIZABLE"],
                               description="Transaction isolation level"),
    },
    children=["q:query", "q:set", "q:if"],
    examples=[
        '<q:transaction>\n  <q:query datasource="db">UPDATE accounts SET balance = balance - :amount WHERE id = :from</q:query>\n  <q:query datasource="db">UPDATE accounts SET balance = balance + :amount WHERE id = :to</q:query>\n</q:transaction>',
    ],
    see_also=["q:query"]
)

Q_LLM = TagInfo(
    name="llm",
    namespace="q",
    description="Invokes an LLM (Large Language Model) via Ollama or compatible API.",
    attributes={
        "name": _attr("name", required=True, description="Result variable name"),
        "model": _attr("model", description="Model name (e.g., phi3, mistral, llama3)"),
        "endpoint": _attr("endpoint", type=AttributeType.URL, description="Custom API endpoint"),
        "system": _attr("system", description="System prompt"),
        "responseFormat": _attr("responseFormat", type=AttributeType.ENUM,
                               enum_values=["text", "json"],
                               description="Expected response format"),
        "temperature": _attr("temperature", type=AttributeType.DECIMAL, description="Temperature (0.0-2.0)"),
        "maxTokens": _attr("maxTokens", type=AttributeType.INTEGER, description="Max tokens in response"),
        "timeout": _attr("timeout", type=AttributeType.INTEGER, default="30",
                        description="Request timeout in seconds"),
        "cache": _attr("cache", type=AttributeType.BOOLEAN, default="false",
                      description="Cache LLM responses"),
    },
    children=["q:prompt", "q:message"],
    examples=[
        '<q:llm name="response" model="phi3">\n  <q:prompt>Summarize this text: {text}</q:prompt>\n</q:llm>',
        '<q:llm name="chat" model="mistral">\n  <q:message role="system">You are a helpful assistant</q:message>\n  <q:message role="user">{question}</q:message>\n</q:llm>',
    ],
    see_also=["q:knowledge"]
)

Q_PROMPT = TagInfo(
    name="prompt",
    namespace="q",
    description="Defines the prompt text for an LLM invocation.",
    parent_tags=["q:llm"],
    examples=['<q:prompt>Translate to French: {text}</q:prompt>'],
    see_also=["q:llm", "q:message"]
)

Q_MESSAGE = TagInfo(
    name="message",
    namespace="q",
    description="Defines a chat message for LLM conversation mode.",
    attributes={
        "role": _attr("role", type=AttributeType.ENUM, default="user",
                     enum_values=["system", "user", "assistant"],
                     description="Message role"),
    },
    parent_tags=["q:llm"],
    examples=[
        '<q:message role="system">You are a helpful assistant</q:message>',
        '<q:message role="user">{userQuestion}</q:message>',
    ],
    see_also=["q:llm", "q:prompt"]
)

Q_MAIL = TagInfo(
    name="mail",
    namespace="q",
    description="Sends an email. ColdFusion cfmail-inspired.",
    attributes={
        "to": _attr("to", required=True, description="Recipient email address(es)"),
        "subject": _attr("subject", required=True, description="Email subject"),
        "from": _attr("from", description="Sender email address"),
        "cc": _attr("cc", description="CC recipients"),
        "bcc": _attr("bcc", description="BCC recipients"),
        "replyTo": _attr("replyTo", description="Reply-To address"),
        "type": _attr("type", type=AttributeType.ENUM, default="html",
                     enum_values=["html", "text"],
                     description="Email content type"),
        "charset": _attr("charset", default="UTF-8", description="Character encoding"),
    },
    examples=[
        '<q:mail to="{user.email}" from="noreply@app.com" subject="Welcome!">\n  <h1>Welcome, {user.name}!</h1>\n</q:mail>',
    ],
    see_also=["q:action"]
)

Q_FILE = TagInfo(
    name="file",
    namespace="q",
    description="Handles file operations like upload, delete, move, copy.",
    attributes={
        "action": _attr("action", type=AttributeType.ENUM, default="upload",
                       enum_values=["upload", "delete", "move", "copy"],
                       description="File operation to perform"),
        "file": _attr("file", required=True, description="File variable or path"),
        "destination": _attr("destination", type=AttributeType.PATH, default="./uploads/",
                            description="Destination path for uploads"),
        "nameConflict": _attr("nameConflict", type=AttributeType.ENUM, default="error",
                             enum_values=["error", "overwrite", "skip", "makeUnique"],
                             description="How to handle name conflicts"),
        "result": _attr("result", description="Variable to store operation result"),
    },
    self_closing=True,
    examples=[
        '<q:file action="upload" file="{avatar}" destination="./uploads/avatars/" />',
        '<q:file action="delete" file="{filePath}" />',
    ],
    see_also=["q:action", "q:param"]
)

Q_ROUTE = TagInfo(
    name="route",
    namespace="q",
    description="Defines a route in an application.",
    attributes={
        "path": _attr("path", required=True, description="URL path pattern"),
        "method": _attr("method", type=AttributeType.ENUM, default="GET",
                       enum_values=["GET", "POST", "PUT", "DELETE", "PATCH"],
                       description="HTTP method"),
    },
    children=["q:return"],
    parent_tags=["q:application"],
    self_closing=True,
    examples=[
        '<q:route path="/" method="GET" />',
        '<q:route path="/users/:id" method="GET" />',
    ],
    see_also=["q:application"]
)

Q_ONEVENT = TagInfo(
    name="onEvent",
    namespace="q",
    description="Subscribes to and handles events.",
    attributes={
        "event": _attr("event", required=True, description="Event pattern (supports wildcards)"),
        "queue": _attr("queue", description="Queue name for message broker"),
        "maxRetries": _attr("maxRetries", type=AttributeType.INTEGER, default="0",
                           description="Maximum retry attempts"),
        "retryDelay": _attr("retryDelay", description="Delay between retries (e.g., '30s')"),
        "deadLetter": _attr("deadLetter", description="Dead letter queue name"),
        "filter": _attr("filter", type=AttributeType.EXPRESSION, description="Filter expression"),
        "concurrent": _attr("concurrent", type=AttributeType.INTEGER, default="1",
                           description="Concurrent handler count"),
        "timeout": _attr("timeout", description="Handler timeout"),
    },
    children=["q:set", "q:if", "q:query", "q:invoke"],
    examples=[
        '<q:onEvent event="user.created">\n  <q:log message="User created: {event.data.userId}" />\n</q:onEvent>',
    ],
    see_also=["q:dispatchEvent"]
)

Q_DISPATCHEVENT = TagInfo(
    name="dispatchEvent",
    namespace="q",
    description="Publishes an event to the event bus.",
    attributes={
        "event": _attr("event", required=True, description="Event name"),
        "data": _attr("data", type=AttributeType.EXPRESSION, description="Event payload"),
        "queue": _attr("queue", description="Target queue"),
        "exchange": _attr("exchange", description="Exchange name"),
        "routingKey": _attr("routingKey", description="Routing key"),
        "priority": _attr("priority", type=AttributeType.ENUM, default="normal",
                         enum_values=["low", "normal", "high"],
                         description="Event priority"),
        "delay": _attr("delay", description="Delay before delivery (e.g., '5s')"),
        "ttl": _attr("ttl", description="Time-to-live (e.g., '60s')"),
    },
    self_closing=True,
    examples=[
        '<q:dispatchEvent event="user.created" data="{userData}" />',
    ],
    see_also=["q:onEvent"]
)

Q_SCRIPT = TagInfo(
    name="script",
    namespace="q",
    description="Embeds custom script code within a component.",
    examples=['<q:script>\n  // Custom JavaScript or Python code\n</q:script>'],
    see_also=["q:component"]
)

Q_DATA = TagInfo(
    name="data",
    namespace="q",
    description="Imports and transforms data from external sources (CSV, XML, JSON).",
    attributes={
        "name": _attr("name", required=True, description="Result variable name"),
        "source": _attr("source", type=AttributeType.URL, required=True,
                       description="Data source URL or path"),
        "type": _attr("type", type=AttributeType.ENUM, default="csv",
                     enum_values=["csv", "xml", "json", "excel"],
                     description="Data format"),
        "cache": _attr("cache", type=AttributeType.BOOLEAN, default="true",
                      description="Cache imported data"),
        "ttl": _attr("ttl", type=AttributeType.INTEGER, description="Cache TTL in seconds"),
        "delimiter": _attr("delimiter", default=",", description="CSV delimiter"),
        "header": _attr("header", type=AttributeType.BOOLEAN, default="true",
                       description="CSV has header row"),
        "encoding": _attr("encoding", default="utf-8", description="File encoding"),
        "xpath": _attr("xpath", description="XPath for XML extraction"),
    },
    children=["q:column", "q:field", "q:transform"],
    examples=[
        '<q:data name="products" source="./data/products.csv" type="csv" />',
    ],
    see_also=["q:query", "q:invoke"]
)

Q_KNOWLEDGE = TagInfo(
    name="knowledge",
    namespace="q",
    description="Defines a knowledge base for RAG (Retrieval Augmented Generation).",
    attributes={
        "name": _attr("name", required=True, description="Knowledge base name"),
        "model": _attr("model", description="Embedding model"),
        "chunkSize": _attr("chunkSize", type=AttributeType.INTEGER, default="500",
                          description="Text chunk size"),
        "chunkOverlap": _attr("chunkOverlap", type=AttributeType.INTEGER, default="50",
                             description="Overlap between chunks"),
    },
    children=["q:source"],
    examples=[
        '<q:knowledge name="docs">\n  <q:source type="file" path="./docs/" />\n  <q:source type="url" url="https://docs.example.com" />\n</q:knowledge>',
    ],
    see_also=["q:llm", "q:query"]
)

Q_PERSIST = TagInfo(
    name="persist",
    namespace="q",
    description="Configures state persistence for variables.",
    attributes={
        "scope": _attr("scope", type=AttributeType.ENUM, default="local",
                      enum_values=["local", "session", "sync"],
                      description="Storage scope"),
        "prefix": _attr("prefix", description="Key prefix in storage"),
        "key": _attr("key", description="Custom storage key"),
        "encrypt": _attr("encrypt", type=AttributeType.BOOLEAN, default="false",
                        description="Encrypt stored values"),
        "ttl": _attr("ttl", type=AttributeType.INTEGER, description="TTL in seconds"),
    },
    children=["q:var"],
    examples=[
        '<q:persist scope="local" prefix="myapp_">\n  <q:var name="theme" />\n  <q:var name="locale" />\n</q:persist>',
    ],
    see_also=["q:set"]
)


# =============================================================================
# UI ENGINE TAGS (ui: namespace)
# =============================================================================

# Layout attributes shared by most UI containers
_LAYOUT_ATTRS = {
    "gap": _attr("gap", type=AttributeType.CSS_SIZE, description="Gap between children"),
    "padding": _attr("padding", type=AttributeType.CSS_SIZE, description="Inner padding"),
    "margin": _attr("margin", type=AttributeType.CSS_SIZE, description="Outer margin"),
    "align": _attr("align", type=AttributeType.ENUM,
                  enum_values=["start", "center", "end", "stretch"],
                  description="Cross-axis alignment"),
    "justify": _attr("justify", type=AttributeType.ENUM,
                    enum_values=["start", "center", "end", "between", "around"],
                    description="Main-axis alignment"),
    "width": _attr("width", type=AttributeType.CSS_SIZE, description="Width"),
    "height": _attr("height", type=AttributeType.CSS_SIZE, description="Height"),
    "background": _attr("background", type=AttributeType.CSS_COLOR, description="Background color"),
    "color": _attr("color", type=AttributeType.CSS_COLOR, description="Text color"),
    "border": _attr("border", description="Border style"),
    "id": _attr("id", description="Element ID"),
    "class": _attr("class", description="CSS class(es)"),
    "visible": _attr("visible", type=AttributeType.EXPRESSION, description="Visibility binding"),
}

UI_WINDOW = TagInfo(
    name="window",
    namespace="ui",
    description="Top-level window container for UI applications.",
    attributes={
        "title": _attr("title", description="Window title"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:window title="My App">\n  <ui:vbox>\n    <ui:text>Hello World</ui:text>\n  </ui:vbox>\n</ui:window>'],
    see_also=["ui:vbox", "ui:hbox", "ui:panel"]
)

UI_VBOX = TagInfo(
    name="vbox",
    namespace="ui",
    description="Vertical flex container. Children are stacked vertically.",
    attributes=_LAYOUT_ATTRS,
    examples=['<ui:vbox gap="10">\n  <ui:text>Item 1</ui:text>\n  <ui:text>Item 2</ui:text>\n</ui:vbox>'],
    see_also=["ui:hbox", "ui:grid"]
)

UI_HBOX = TagInfo(
    name="hbox",
    namespace="ui",
    description="Horizontal flex container. Children are arranged horizontally.",
    attributes=_LAYOUT_ATTRS,
    examples=['<ui:hbox gap="10" justify="between">\n  <ui:button>Left</ui:button>\n  <ui:button>Right</ui:button>\n</ui:hbox>'],
    see_also=["ui:vbox", "ui:grid"]
)

UI_PANEL = TagInfo(
    name="panel",
    namespace="ui",
    description="Bordered container with optional title.",
    attributes={
        "title": _attr("title", description="Panel title"),
        "collapsible": _attr("collapsible", type=AttributeType.BOOLEAN, default="false",
                            description="Allow collapsing"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:panel title="Settings" collapsible="true">\n  <ui:input bind="name" />\n</ui:panel>'],
    see_also=["ui:card", "ui:accordion"]
)

UI_GRID = TagInfo(
    name="grid",
    namespace="ui",
    description="CSS grid container.",
    attributes={
        "columns": _attr("columns", description="Column definition (e.g., '3' or '1fr 2fr 1fr')"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:grid columns="3" gap="10">\n  <ui:panel>1</ui:panel>\n  <ui:panel>2</ui:panel>\n  <ui:panel>3</ui:panel>\n</ui:grid>'],
    see_also=["ui:vbox", "ui:hbox"]
)

UI_BUTTON = TagInfo(
    name="button",
    namespace="ui",
    description="Clickable button widget.",
    attributes={
        "onClick": _attr("onClick", type=AttributeType.EXPRESSION, description="Click handler"),
        "variant": _attr("variant", type=AttributeType.ENUM,
                        enum_values=["primary", "secondary", "danger", "success"],
                        description="Button style variant"),
        "disabled": _attr("disabled", type=AttributeType.BOOLEAN, default="false",
                         description="Disable the button"),
        **_LAYOUT_ATTRS,
    },
    examples=[
        '<ui:button onClick="handleSave" variant="primary">Save</ui:button>',
        '<ui:button disabled="{!isValid}">Submit</ui:button>',
    ],
    see_also=["ui:link"]
)

UI_INPUT = TagInfo(
    name="input",
    namespace="ui",
    description="Text input widget with validation support.",
    attributes={
        "bind": _attr("bind", type=AttributeType.EXPRESSION, description="Two-way binding variable"),
        "placeholder": _attr("placeholder", description="Placeholder text"),
        "type": _attr("type", type=AttributeType.ENUM, default="text",
                     enum_values=["text", "password", "email", "number", "tel", "url", "search", "date", "time", "datetime-local"],
                     description="Input type"),
        "onChange": _attr("onChange", type=AttributeType.EXPRESSION, description="Change handler"),
        "onSubmit": _attr("onSubmit", type=AttributeType.EXPRESSION, description="Submit handler"),
        "required": _attr("required", type=AttributeType.BOOLEAN, default="false",
                         description="Field is required"),
        "min": _attr("min", description="Minimum value"),
        "max": _attr("max", description="Maximum value"),
        "minlength": _attr("minlength", type=AttributeType.INTEGER, description="Minimum length"),
        "maxlength": _attr("maxlength", type=AttributeType.INTEGER, description="Maximum length"),
        "pattern": _attr("pattern", type=AttributeType.REGEX, description="Validation pattern"),
        "errorMessage": _attr("errorMessage", description="Custom error message"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=[
        '<ui:input bind="email" type="email" placeholder="Enter email" required="true" />',
        '<ui:input bind="age" type="number" min="0" max="120" />',
    ],
    see_also=["ui:form", "ui:select", "ui:checkbox"]
)

UI_TEXT = TagInfo(
    name="text",
    namespace="ui",
    description="Text display widget.",
    attributes={
        "size": _attr("size", type=AttributeType.ENUM,
                     enum_values=["xs", "sm", "md", "lg", "xl", "2xl"],
                     description="Text size"),
        "weight": _attr("weight", type=AttributeType.ENUM,
                       enum_values=["normal", "bold", "light"],
                       description="Font weight"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:text size="xl" weight="bold">Title</ui:text>'],
    see_also=["ui:markdown", "ui:header"]
)

UI_SELECT = TagInfo(
    name="select",
    namespace="ui",
    description="Dropdown select widget.",
    attributes={
        "bind": _attr("bind", type=AttributeType.EXPRESSION, description="Binding variable"),
        "options": _attr("options", description="Comma-separated options or binding"),
        "source": _attr("source", type=AttributeType.EXPRESSION, description="Data source for options"),
        **_LAYOUT_ATTRS,
    },
    children=["ui:option"],
    examples=[
        '<ui:select bind="country" options="US,CA,UK,AU" />',
        '<ui:select bind="user" source="{users}">\n  <ui:option value="{item.id}" label="{item.name}" />\n</ui:select>',
    ],
    see_also=["ui:input", "ui:radio"]
)

UI_OPTION = TagInfo(
    name="option",
    namespace="ui",
    description="Option for select, menu, or dropdown.",
    attributes={
        "value": _attr("value", description="Option value"),
        "label": _attr("label", description="Display label"),
        "onClick": _attr("onClick", type=AttributeType.EXPRESSION, description="Click handler"),
    },
    parent_tags=["ui:select", "ui:menu", "ui:dropdown"],
    examples=['<ui:option value="1" label="Option 1" />'],
    see_also=["ui:select", "ui:dropdown"]
)

UI_CHECKBOX = TagInfo(
    name="checkbox",
    namespace="ui",
    description="Checkbox widget.",
    attributes={
        "bind": _attr("bind", type=AttributeType.EXPRESSION, description="Binding variable"),
        "label": _attr("label", description="Checkbox label"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:checkbox bind="agreed" label="I agree to terms" />'],
    see_also=["ui:switch", "ui:radio"]
)

UI_SWITCH = TagInfo(
    name="switch",
    namespace="ui",
    description="Toggle switch widget.",
    attributes={
        "bind": _attr("bind", type=AttributeType.EXPRESSION, description="Binding variable"),
        "label": _attr("label", description="Switch label"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:switch bind="darkMode" label="Dark Mode" />'],
    see_also=["ui:checkbox"]
)

UI_RADIO = TagInfo(
    name="radio",
    namespace="ui",
    description="Radio button group.",
    attributes={
        "bind": _attr("bind", type=AttributeType.EXPRESSION, description="Binding variable"),
        "options": _attr("options", description="Comma-separated options"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:radio bind="size" options="S,M,L,XL" />'],
    see_also=["ui:checkbox", "ui:select"]
)

UI_TABLE = TagInfo(
    name="table",
    namespace="ui",
    description="Data table widget.",
    attributes={
        "source": _attr("source", type=AttributeType.EXPRESSION, required=True,
                       description="Data source binding"),
        **_LAYOUT_ATTRS,
    },
    children=["ui:column"],
    examples=['<ui:table source="{users}">\n  <ui:column key="name" label="Name" />\n  <ui:column key="email" label="Email" />\n</ui:table>'],
    see_also=["ui:list", "ui:column"]
)

UI_COLUMN = TagInfo(
    name="column",
    namespace="ui",
    description="Table column definition.",
    attributes={
        "key": _attr("key", required=True, description="Data field key"),
        "label": _attr("label", description="Column header label"),
        "width": _attr("width", type=AttributeType.CSS_SIZE, description="Column width"),
        "align": _attr("align", type=AttributeType.ENUM,
                      enum_values=["left", "center", "right"],
                      description="Text alignment"),
    },
    parent_tags=["ui:table"],
    self_closing=True,
    examples=['<ui:column key="name" label="Name" width="200" />'],
    see_also=["ui:table"]
)

UI_LIST = TagInfo(
    name="list",
    namespace="ui",
    description="Repeating list widget.",
    attributes={
        "source": _attr("source", type=AttributeType.EXPRESSION, description="Data source binding"),
        "as": _attr("as", description="Loop variable name"),
        **_LAYOUT_ATTRS,
    },
    children=["ui:item"],
    examples=['<ui:list source="{items}" as="item">\n  <ui:item>\n    <ui:text>{item.name}</ui:text>\n  </ui:item>\n</ui:list>'],
    see_also=["ui:table", "ui:item"]
)

UI_ITEM = TagInfo(
    name="item",
    namespace="ui",
    description="List item container.",
    attributes=_LAYOUT_ATTRS,
    parent_tags=["ui:list"],
    examples=['<ui:item>\n  <ui:text>{item.name}</ui:text>\n</ui:item>'],
    see_also=["ui:list"]
)

UI_FORM = TagInfo(
    name="form",
    namespace="ui",
    description="Form container with validation support.",
    attributes={
        "onSubmit": _attr("onSubmit", type=AttributeType.EXPRESSION, description="Submit handler"),
        "validationMode": _attr("validationMode", type=AttributeType.ENUM, default="both",
                               enum_values=["client", "server", "both"],
                               description="Validation mode"),
        "errorDisplay": _attr("errorDisplay", type=AttributeType.ENUM, default="inline",
                             enum_values=["inline", "summary", "both"],
                             description="Error display mode"),
        "novalidate": _attr("novalidate", type=AttributeType.BOOLEAN, default="false",
                           description="Disable HTML5 validation"),
        **_LAYOUT_ATTRS,
    },
    children=["ui:formitem", "ui:input", "ui:select", "ui:button", "ui:validator"],
    examples=['<ui:form onSubmit="handleSubmit">\n  <ui:formitem label="Email">\n    <ui:input bind="email" type="email" required="true" />\n  </ui:formitem>\n  <ui:button type="submit">Submit</ui:button>\n</ui:form>'],
    see_also=["ui:formitem", "ui:input", "ui:validator"]
)

UI_FORMITEM = TagInfo(
    name="formitem",
    namespace="ui",
    description="Form item wrapper with label.",
    attributes={
        "label": _attr("label", description="Field label"),
        **_LAYOUT_ATTRS,
    },
    parent_tags=["ui:form"],
    examples=['<ui:formitem label="Name">\n  <ui:input bind="name" />\n</ui:formitem>'],
    see_also=["ui:form", "ui:input"]
)

UI_IMAGE = TagInfo(
    name="image",
    namespace="ui",
    description="Image display widget.",
    attributes={
        "src": _attr("src", type=AttributeType.URL, required=True, description="Image source URL"),
        "alt": _attr("alt", description="Alternative text"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:image src="/images/logo.png" alt="Logo" width="200" />'],
    see_also=["ui:avatar"]
)

UI_LINK = TagInfo(
    name="link",
    namespace="ui",
    description="Hyperlink widget.",
    attributes={
        "to": _attr("to", type=AttributeType.URL, required=True, description="Target URL"),
        "external": _attr("external", type=AttributeType.BOOLEAN, default="false",
                         description="Open in new tab"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:link to="/about">About Us</ui:link>'],
    see_also=["ui:button"]
)

UI_MODAL = TagInfo(
    name="modal",
    namespace="ui",
    description="Modal/dialog container.",
    attributes={
        "title": _attr("title", description="Modal title"),
        "id": _attr("id", description="Modal ID for targeting"),
        "open": _attr("open", type=AttributeType.BOOLEAN, default="false",
                     description="Initial open state"),
        "closable": _attr("closable", type=AttributeType.BOOLEAN, default="true",
                         description="Show close button"),
        "size": _attr("size", type=AttributeType.ENUM,
                     enum_values=["sm", "md", "lg", "xl", "full"],
                     description="Modal size"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:modal title="Confirm" id="confirmModal">\n  <ui:text>Are you sure?</ui:text>\n  <ui:hbox>\n    <ui:button onClick="closeModal">Cancel</ui:button>\n    <ui:button onClick="confirm" variant="danger">Delete</ui:button>\n  </ui:hbox>\n</ui:modal>'],
    see_also=["ui:panel", "ui:alert"]
)

UI_CARD = TagInfo(
    name="card",
    namespace="ui",
    description="Card container with header, body, and footer sections.",
    attributes={
        "title": _attr("title", description="Card title"),
        "subtitle": _attr("subtitle", description="Card subtitle"),
        "image": _attr("image", type=AttributeType.URL, description="Header image"),
        "variant": _attr("variant", type=AttributeType.ENUM,
                        enum_values=["default", "elevated", "outlined"],
                        description="Card style"),
        **_LAYOUT_ATTRS,
    },
    children=["ui:card-header", "ui:card-body", "ui:card-footer"],
    examples=['<ui:card title="Product" image="/product.jpg">\n  <ui:card-body>\n    <ui:text>Description</ui:text>\n  </ui:card-body>\n  <ui:card-footer>\n    <ui:button>Buy</ui:button>\n  </ui:card-footer>\n</ui:card>'],
    see_also=["ui:panel"]
)

UI_ALERT = TagInfo(
    name="alert",
    namespace="ui",
    description="Alert/notification box.",
    attributes={
        "title": _attr("title", description="Alert title"),
        "variant": _attr("variant", type=AttributeType.ENUM, default="info",
                        enum_values=["info", "success", "warning", "danger"],
                        description="Alert style"),
        "dismissible": _attr("dismissible", type=AttributeType.BOOLEAN, default="false",
                            description="Allow dismissing"),
        "icon": _attr("icon", description="Icon name"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:alert variant="success" dismissible="true">\n  Operation completed successfully!\n</ui:alert>'],
    see_also=["ui:modal"]
)

UI_PROGRESS = TagInfo(
    name="progress",
    namespace="ui",
    description="Progress bar widget.",
    attributes={
        "value": _attr("value", type=AttributeType.EXPRESSION, description="Current value binding"),
        "max": _attr("max", default="100", description="Maximum value"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:progress value="{progress}" max="100" />'],
    see_also=["ui:loading", "ui:skeleton"]
)

UI_LOADING = TagInfo(
    name="loading",
    namespace="ui",
    description="Loading indicator widget.",
    attributes={
        "text": _attr("text", description="Loading text"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:loading text="Loading data..." />'],
    see_also=["ui:progress", "ui:skeleton"]
)

UI_BADGE = TagInfo(
    name="badge",
    namespace="ui",
    description="Small status badge.",
    attributes={
        "variant": _attr("variant", type=AttributeType.ENUM,
                        enum_values=["primary", "secondary", "danger", "success", "warning"],
                        description="Badge style"),
        "color": _attr("color", type=AttributeType.CSS_COLOR, description="Custom color"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:badge variant="success">Active</ui:badge>'],
    see_also=["ui:text"]
)

UI_TOOLTIP = TagInfo(
    name="tooltip",
    namespace="ui",
    description="Tooltip on hover.",
    attributes={
        "content": _attr("content", required=True, description="Tooltip text"),
        "position": _attr("position", type=AttributeType.ENUM, default="top",
                         enum_values=["top", "bottom", "left", "right"],
                         description="Tooltip position"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:tooltip content="Click to save" position="bottom">\n  <ui:button>Save</ui:button>\n</ui:tooltip>'],
    see_also=["ui:dropdown"]
)

UI_DROPDOWN = TagInfo(
    name="dropdown",
    namespace="ui",
    description="Dropdown menu.",
    attributes={
        "label": _attr("label", description="Trigger button label"),
        "trigger": _attr("trigger", type=AttributeType.ENUM, default="click",
                        enum_values=["click", "hover"],
                        description="Trigger mode"),
        "align": _attr("align", type=AttributeType.ENUM, default="left",
                      enum_values=["left", "right"],
                      description="Menu alignment"),
        **_LAYOUT_ATTRS,
    },
    children=["ui:option"],
    examples=['<ui:dropdown label="Actions">\n  <ui:option label="Edit" onClick="handleEdit" />\n  <ui:option label="Delete" onClick="handleDelete" />\n</ui:dropdown>'],
    see_also=["ui:menu", "ui:select"]
)

UI_TABPANEL = TagInfo(
    name="tabpanel",
    namespace="ui",
    description="Tabbed content container.",
    attributes=_LAYOUT_ATTRS,
    children=["ui:tab"],
    examples=['<ui:tabpanel>\n  <ui:tab title="Tab 1">\n    <ui:text>Content 1</ui:text>\n  </ui:tab>\n  <ui:tab title="Tab 2">\n    <ui:text>Content 2</ui:text>\n  </ui:tab>\n</ui:tabpanel>'],
    see_also=["ui:tab", "ui:accordion"]
)

UI_TAB = TagInfo(
    name="tab",
    namespace="ui",
    description="Individual tab inside a tabpanel.",
    attributes={
        "title": _attr("title", required=True, description="Tab title"),
        **_LAYOUT_ATTRS,
    },
    parent_tags=["ui:tabpanel"],
    examples=['<ui:tab title="Settings">\n  <ui:text>Settings content</ui:text>\n</ui:tab>'],
    see_also=["ui:tabpanel"]
)

UI_ACCORDION = TagInfo(
    name="accordion",
    namespace="ui",
    description="Collapsible sections container.",
    attributes=_LAYOUT_ATTRS,
    children=["ui:section"],
    examples=['<ui:accordion>\n  <ui:section title="Section 1" expanded="true">\n    Content 1\n  </ui:section>\n  <ui:section title="Section 2">\n    Content 2\n  </ui:section>\n</ui:accordion>'],
    see_also=["ui:section", "ui:tabpanel"]
)

UI_SECTION = TagInfo(
    name="section",
    namespace="ui",
    description="Collapsible section inside an accordion.",
    attributes={
        "title": _attr("title", required=True, description="Section title"),
        "expanded": _attr("expanded", type=AttributeType.BOOLEAN, default="false",
                         description="Initial expanded state"),
        **_LAYOUT_ATTRS,
    },
    parent_tags=["ui:accordion"],
    examples=['<ui:section title="Details" expanded="true">\n  Section content\n</ui:section>'],
    see_also=["ui:accordion", "ui:panel"]
)

UI_SPACER = TagInfo(
    name="spacer",
    namespace="ui",
    description="Flexible space filler.",
    attributes={
        "size": _attr("size", type=AttributeType.CSS_SIZE, description="Fixed size"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:hbox>\n  <ui:text>Left</ui:text>\n  <ui:spacer />\n  <ui:text>Right</ui:text>\n</ui:hbox>'],
    see_also=["ui:rule"]
)

UI_RULE = TagInfo(
    name="rule",
    namespace="ui",
    description="Horizontal rule/separator.",
    self_closing=True,
    examples=['<ui:rule />'],
    see_also=["ui:spacer"]
)

UI_MARKDOWN = TagInfo(
    name="markdown",
    namespace="ui",
    description="Markdown rendered content.",
    attributes=_LAYOUT_ATTRS,
    examples=['<ui:markdown>\n# Heading\n\nThis is **bold** text.\n</ui:markdown>'],
    see_also=["ui:text"]
)

UI_HEADER = TagInfo(
    name="header",
    namespace="ui",
    description="Page/window header.",
    attributes={
        "title": _attr("title", description="Header title"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:header title="Dashboard" />'],
    see_also=["ui:footer"]
)

UI_FOOTER = TagInfo(
    name="footer",
    namespace="ui",
    description="Page/window footer.",
    attributes=_LAYOUT_ATTRS,
    examples=['<ui:footer>\n  <ui:text>Copyright 2024</ui:text>\n</ui:footer>'],
    see_also=["ui:header"]
)

UI_AVATAR = TagInfo(
    name="avatar",
    namespace="ui",
    description="User avatar with image or initials.",
    attributes={
        "src": _attr("src", type=AttributeType.URL, description="Image URL"),
        "name": _attr("name", description="Name for initials fallback"),
        "size": _attr("size", type=AttributeType.ENUM,
                     enum_values=["xs", "sm", "md", "lg", "xl"],
                     description="Avatar size"),
        "shape": _attr("shape", type=AttributeType.ENUM, default="circle",
                      enum_values=["circle", "square"],
                      description="Avatar shape"),
        "status": _attr("status", type=AttributeType.ENUM,
                       enum_values=["online", "offline", "away", "busy"],
                       description="Status indicator"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:avatar src="/user.jpg" name="John Doe" size="lg" status="online" />'],
    see_also=["ui:image"]
)

UI_CHART = TagInfo(
    name="chart",
    namespace="ui",
    description="Simple charts (bar, line, pie).",
    attributes={
        "type": _attr("type", type=AttributeType.ENUM, default="bar",
                     enum_values=["bar", "line", "pie", "doughnut"],
                     description="Chart type"),
        "source": _attr("source", type=AttributeType.EXPRESSION, description="Data source"),
        "labels": _attr("labels", description="Comma-separated labels"),
        "values": _attr("values", description="Comma-separated values"),
        "title": _attr("title", description="Chart title"),
        "colors": _attr("colors", description="Comma-separated colors"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:chart type="bar" labels="Jan,Feb,Mar" values="10,20,30" title="Sales" />'],
    see_also=["ui:table"]
)

UI_BREADCRUMB = TagInfo(
    name="breadcrumb",
    namespace="ui",
    description="Navigation breadcrumbs.",
    attributes={
        "separator": _attr("separator", default="/", description="Separator character"),
        **_LAYOUT_ATTRS,
    },
    children=["ui:breadcrumb-item"],
    examples=['<ui:breadcrumb>\n  <ui:breadcrumb-item label="Home" to="/" />\n  <ui:breadcrumb-item label="Products" to="/products" />\n  <ui:breadcrumb-item label="Details" />\n</ui:breadcrumb>'],
    see_also=["ui:link"]
)

UI_PAGINATION = TagInfo(
    name="pagination",
    namespace="ui",
    description="Pagination controls.",
    attributes={
        "total": _attr("total", type=AttributeType.EXPRESSION, description="Total items"),
        "pageSize": _attr("pageSize", default="10", description="Items per page"),
        "current": _attr("current", default="1", description="Current page"),
        "bind": _attr("bind", type=AttributeType.EXPRESSION, description="Binding for current page"),
        "onChange": _attr("onChange", type=AttributeType.EXPRESSION, description="Page change handler"),
        "showTotal": _attr("showTotal", type=AttributeType.BOOLEAN, default="false",
                          description="Show total count"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:pagination total="{totalItems}" pageSize="20" bind="currentPage" />'],
    see_also=["ui:table"]
)

UI_SKELETON = TagInfo(
    name="skeleton",
    namespace="ui",
    description="Loading skeleton placeholder.",
    attributes={
        "variant": _attr("variant", type=AttributeType.ENUM, default="text",
                        enum_values=["text", "circle", "rect", "card"],
                        description="Skeleton shape"),
        "lines": _attr("lines", type=AttributeType.INTEGER, default="1",
                      description="Number of lines for text variant"),
        "animated": _attr("animated", type=AttributeType.BOOLEAN, default="true",
                         description="Animate the skeleton"),
        **_LAYOUT_ATTRS,
    },
    self_closing=True,
    examples=['<ui:skeleton variant="text" lines="3" />'],
    see_also=["ui:loading"]
)

UI_ANIMATE = TagInfo(
    name="animate",
    namespace="ui",
    description="Animation wrapper container.",
    attributes={
        "type": _attr("type", type=AttributeType.ENUM,
                     enum_values=["fade", "slide", "scale", "rotate", "slide-left", "slide-right",
                                 "slide-up", "slide-down", "fade-in", "fade-out", "bounce", "pulse", "shake"],
                     description="Animation type"),
        "duration": _attr("duration", description="Duration in ms"),
        "delay": _attr("delay", description="Delay before animation"),
        "easing": _attr("easing", type=AttributeType.ENUM,
                       enum_values=["ease", "ease-in", "ease-out", "ease-in-out", "linear", "spring", "bounce"],
                       description="Easing function"),
        "repeat": _attr("repeat", description="Repeat count (or 'infinite')"),
        "trigger": _attr("trigger", type=AttributeType.ENUM, default="on-load",
                        enum_values=["on-load", "on-hover", "on-click", "on-visible", "none"],
                        description="Animation trigger"),
        **_LAYOUT_ATTRS,
    },
    examples=['<ui:animate type="fade-in" duration="300" trigger="on-load">\n  <ui:panel>Animated content</ui:panel>\n</ui:animate>'],
    see_also=["ui:panel"]
)


# =============================================================================
# TAG REGISTRY
# =============================================================================

QUANTUM_TAGS: Dict[str, TagInfo] = {
    # Quantum core tags (q:)
    "q:component": Q_COMPONENT,
    "q:application": Q_APPLICATION,
    "q:set": Q_SET,
    "q:if": Q_IF,
    "q:elseif": Q_ELSEIF,
    "q:else": Q_ELSE,
    "q:loop": Q_LOOP,
    "q:function": Q_FUNCTION,
    "q:param": Q_PARAM,
    "q:return": Q_RETURN,
    "q:query": Q_QUERY,
    "q:invoke": Q_INVOKE,
    "q:import": Q_IMPORT,
    "q:slot": Q_SLOT,
    "q:action": Q_ACTION,
    "q:redirect": Q_REDIRECT,
    "q:flash": Q_FLASH,
    "q:log": Q_LOG,
    "q:dump": Q_DUMP,
    "q:transaction": Q_TRANSACTION,
    "q:llm": Q_LLM,
    "q:prompt": Q_PROMPT,
    "q:message": Q_MESSAGE,
    "q:mail": Q_MAIL,
    "q:file": Q_FILE,
    "q:route": Q_ROUTE,
    "q:onEvent": Q_ONEVENT,
    "q:dispatchEvent": Q_DISPATCHEVENT,
    "q:script": Q_SCRIPT,
    "q:data": Q_DATA,
    "q:knowledge": Q_KNOWLEDGE,
    "q:persist": Q_PERSIST,

    # UI engine tags (ui:)
    "ui:window": UI_WINDOW,
    "ui:vbox": UI_VBOX,
    "ui:hbox": UI_HBOX,
    "ui:panel": UI_PANEL,
    "ui:grid": UI_GRID,
    "ui:button": UI_BUTTON,
    "ui:input": UI_INPUT,
    "ui:text": UI_TEXT,
    "ui:select": UI_SELECT,
    "ui:option": UI_OPTION,
    "ui:checkbox": UI_CHECKBOX,
    "ui:switch": UI_SWITCH,
    "ui:radio": UI_RADIO,
    "ui:table": UI_TABLE,
    "ui:column": UI_COLUMN,
    "ui:list": UI_LIST,
    "ui:item": UI_ITEM,
    "ui:form": UI_FORM,
    "ui:formitem": UI_FORMITEM,
    "ui:image": UI_IMAGE,
    "ui:link": UI_LINK,
    "ui:modal": UI_MODAL,
    "ui:card": UI_CARD,
    "ui:alert": UI_ALERT,
    "ui:progress": UI_PROGRESS,
    "ui:loading": UI_LOADING,
    "ui:badge": UI_BADGE,
    "ui:tooltip": UI_TOOLTIP,
    "ui:dropdown": UI_DROPDOWN,
    "ui:tabpanel": UI_TABPANEL,
    "ui:tab": UI_TAB,
    "ui:accordion": UI_ACCORDION,
    "ui:section": UI_SECTION,
    "ui:spacer": UI_SPACER,
    "ui:rule": UI_RULE,
    "ui:markdown": UI_MARKDOWN,
    "ui:header": UI_HEADER,
    "ui:footer": UI_FOOTER,
    "ui:avatar": UI_AVATAR,
    "ui:chart": UI_CHART,
    "ui:breadcrumb": UI_BREADCRUMB,
    "ui:pagination": UI_PAGINATION,
    "ui:skeleton": UI_SKELETON,
    "ui:animate": UI_ANIMATE,
}


def get_tag_info(tag_name: str) -> Optional[TagInfo]:
    """Get tag information by full tag name (e.g., 'q:set')."""
    return QUANTUM_TAGS.get(tag_name)


def get_all_tags() -> List[str]:
    """Get all registered tag names."""
    return list(QUANTUM_TAGS.keys())


def get_tags_by_namespace(namespace: str) -> List[TagInfo]:
    """Get all tags for a given namespace (e.g., 'q', 'ui')."""
    return [tag for name, tag in QUANTUM_TAGS.items() if tag.namespace == namespace]
