"""
The Core and AI tags (SUPPORT_TIERS.md), as the parser accepts them and SPEC.md specifies them.

tests/conformance/test_editor_schemas.py compares the attribute names here with
the attributes the parser reads (measured by parsing a corpus, refusals
excluded): an attribute added to or refused by a parser fails that test until
this file follows. vscode-quantum's q: schema is generated from this file
(scripts/generate-editor-schemas.py).
"""

from typing import Dict, List, Optional

from .types import AttributeInfo, AttributeType, TagInfo

S, I, N, B, E, X, R, U = (AttributeType.STRING, AttributeType.INTEGER, AttributeType.DECIMAL,
                          AttributeType.BOOLEAN, AttributeType.ENUM, AttributeType.EXPRESSION,
                          AttributeType.REGEX, AttributeType.URL)


def a(name: str, description: str, type: AttributeType = S, required: bool = False,
      default: Optional[str] = None, values: List[str] = None) -> AttributeInfo:
    return AttributeInfo(name=name, type=type, required=required, default=default,
                         description=description, enum_values=values or [])


def tag(name: str, description: str, attributes: List[AttributeInfo], children: List[str] = None,
        examples: List[str] = None, see_also: List[str] = None, self_closing: bool = False) -> TagInfo:
    return TagInfo(name=name, namespace="q", description=description,
                   attributes={x.name: x for x in attributes}, children=children or [],
                   examples=examples or [], see_also=see_also or [], self_closing=self_closing)


ONERROR = a("onerror", "`fail` stops the page with the error; `continue` hands it to `<name>_result` (INV-2, IA-5)",
            E, default="fail", values=["fail", "continue"])
# ERR-1 converts the first eight; the aliases after them are accepted as they are.
SET_TYPES = ["string", "number", "integer", "decimal", "boolean", "array", "object", "json",
             "text", "int", "long", "numeric", "float", "double"]
# PARSE-5: a q:param's type (param_validation.PARAM_TYPES), plus the two only a
# q:query's params take (QUERY_PARAM_TYPES): datetime and time.
PARAM_TYPES = ["string", "text", "number", "integer", "int", "long", "numeric", "decimal", "float", "double",
               "boolean", "email", "url", "date", "array", "object", "json", "any",
               "file", "binary", "upload", "datetime", "time"]
VALIDATORS = ["email", "url", "phone", "cep", "cpf", "cnpj", "uuid", "creditcard", "ipv4", "ipv6"]
RULES = [
    a("required", "The value must be given and not empty", B, default="false"),
    a("min", "Smallest number accepted", N), a("max", "Largest number accepted", N),
    a("minlength", "Shortest text accepted", I), a("maxlength", "Longest text accepted", I),
    a("pattern", "Regular expression the text must match", R),
    a("enum", "Comma-separated list of the values accepted"),
    a("range", "Inclusive range, e.g. `1..10`"),
]

CORE_AI_TAGS: Dict[str, TagInfo] = {t.full_name: t for t in [
    tag("component", "A page or a reusable component. A file of `components/` is served at its path (ROUTE-1).", [
        a("name", "Component name", required=True),
        a("require_auth", "Only an authenticated, unexpired session sees it (AUTH-1)", B, default="false"),
        a("require_role", "Comma-separated roles, one of which `session.userRole` must have (AUTH-2)"),
        a("login_url", "Where an unauthenticated visitor is sent; a local path (AUTH-4)"),
        a("require_permission", "Required permission(s)"),
        a("interactive", "Client-side hydration", B, default="false"),
        a("type", "Component type", default="pure"),
        a("port", "Port", I),
    ], examples=['<q:component name="Home">\n  <p>Hello</p>\n</q:component>']),
    tag("param", "A parameter of a component, function, action, query or tool, converted to `type` and checked "
        "against its rules (FN-1, ACT-2, DB-1)", [
        a("name", "Parameter name", required=True),
        a("type", "Type the value is converted to. `datetime` and `time` exist only for a q:query's "
          "param; in a q:query the type is one of string, integer, decimal, boolean, datetime, date, time, "
          "array, json (PARSE-5)", E, default="string", values=PARAM_TYPES),
        a("default", "Value when none is given"),
        a("value", "The value bound (in a q:query, q:invoke)", X),
        a("description", "What it is (shown to the model in a q:tool)"),
        a("validate", "A named validator, or a regular expression starting with `^`", values=VALIDATORS),
        a("accept", "Accepted uploads: `image/*`, `.pdf`, `application/pdf` (ACT-11)"),
        a("maxsize", "Largest upload: `500KB`, `5MB`, `1GB` (FILE-1)"),
        a("maxLength", "Longest text bound to a query (DB-1)", I),
        a("scale", "Decimal places a query value is rounded to (DB-1)", I),
        a("null", "Bind an empty value as NULL (q:query)", B),
        a("source", "Where the value comes from"),
    ] + RULES, self_closing=True, examples=['<q:param name="age" type="integer" required="true" min="18" />']),
    tag("return", "Ends the component or function with a value (RET-1, RET-2)", [
        a("value", "The value; exactly one expression keeps its type", X),
        a("name", "Name of the returned value"), a("type", "Type of the returned value"),
        a("description", "What it is"),
    ], self_closing=True),
    tag("set", "Stores a variable, converted to `type`, checked and changed by `operation` (ERR-1, SET-1, SET-3, SET-4)", [
        a("name", "Variable name (`session.x`, `application.x` for the scopes)", required=True),
        a("value", "The value", X),
        a("type", "Type the value is converted to (ERR-1); without it, a value that is one expression keeps its type (SET-5)", E, values=SET_TYPES),
        a("default", "Stored when value resolves to nothing (SET-1)"),
        a("operation", "What to do with the variable (SET-3)", E, default="assign", values=[
            "assign", "increment", "decrement", "add", "multiply", "append", "prepend", "remove", "removeAt",
            "clear", "sort", "reverse", "unique", "merge", "setProperty", "deleteProperty", "clone",
            "uppercase", "lowercase", "trim", "format"]),
        a("step", "Step of increment/decrement", I, default="1"),
        a("index", "Position for removeAt", I), a("key", "Key for setProperty/deleteProperty"),
        a("source", "Variable clone copies"),
        a("scope", "Where the variable lives", E, default="local",
          values=["local", "function", "component", "session", "application", "request"]),
        a("nullable", "`false`: a null value is an error", B, default="true"),
        # Not an enum: a regular expression starting with ^ is accepted too.
        a("validate", "A named validator, or a regular expression starting with `^` (SET-4)", values=VALIDATORS),
    ] + RULES, self_closing=True, examples=['<q:set name="total" value="{price * qty}" type="number" />']),
    tag("if", "Runs its body when the condition is true (IF-1..IF-4)", [
        a("condition", "An expression; a missing name makes it false (EXPR-5)", X, required=True)],
        children=["q:elseif", "q:else"]),
    tag("elseif", "Another branch of the q:if before it", [a("condition", "An expression", X, required=True)]),
    tag("else", "The branch when no condition was true", []),
    tag("loop", "Repeats its body (LOOP-1..LOOP-5)", [
        a("type", "Loop type; inferred when missing", E, values=["range", "array", "list", "query"]),
        a("var", "The loop variable"),
        a("from", "First number (range)", X), a("to", "Last number, included (range)", X),
        a("step", "Step (range)", I, default="1"),
        a("items", "The list (array) or text (list)", X),
        a("index", "Name of the position variable, from 0"),
        a("delimiter", "Separator of a list loop", default=","),
        a("query", "Name of the query to loop over (LOOP-4)"),
    ]),
    tag("function", "A function the component's expressions can call (FN-1..FN-4)", [
        a("name", "Function name", required=True),
        a("returnType", "Type the returned value is converted to (FN-4)", E, default="any",
          values=["any", "void", "string", "text", "number", "integer", "int", "long", "numeric", "decimal",
                  "float", "double", "boolean", "email", "url", "array", "object", "json"]),
        a("description", "What it does"), a("hint", "A hint for readers"),
    ], children=["q:param", "q:return"]),
    tag("query", "Runs SQL on a declared datasource, binding `:name` to q:param (DB-1..DB-5, DB-9, UI-13)", [
        a("name", "Result variable (`<name>`, `<name>_result`)"),
        a("datasource", "Datasource declared in quantum.config.yaml, or `knowledge:<name>` (IA-3)"),
        a("source", "Query of queries: an earlier query's name (DB-3)"),
        a("result", "Another name for `<name>_result`"),
        a("paginate", "Return one page (DB-2)", B, default="false"),
        a("page", "Page number, an expression (DB-9)", X),
        a("pageSize", "Rows per page", I), a("page_size", "Rows per page", I),
        a("sortable", "Sort by the URL's ?sort=/&dir= (UI-13)", B, default="false"),
        ONERROR,
    ], children=["q:param"]),
    tag("transaction", "Its queries commit together or roll back together (DB-4)", [
        a("datasource", "Datasource of the queries that declare none"),
        a("isolationLevel", "Isolation level", E, default="READ_COMMITTED",
          values=["READ_UNCOMMITTED", "READ_COMMITTED", "REPEATABLE_READ", "SERIALIZABLE"]),
        a("isolation", "Isolation level (same as isolationLevel)", E,
          values=["READ_UNCOMMITTED", "READ_COMMITTED", "REPEATABLE_READ", "SERIALIZABLE"]),
    ], children=["q:query"]),
    tag("invoke", "Calls a URL, a declared service or a function (INV-1, INV-2, SVC-3)", [
        a("name", "Result variable", required=True),
        a("url", "URL to request", U), a("service", "Name registered with @service (SVC-3)"),
        a("function", "Function to call"), a("component", "Component to call"),
        a("method", "HTTP method", E, default="GET",
          values=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]),
        a("timeout", "Seconds to wait", I, default="30"),
        a("contentType", "Type of the body", default="application/json"),
        a("authType", "Authentication", E, values=["bearer", "apikey", "basic"]),
        a("authToken", "Token for bearer/apikey"), a("authHeader", "Header for apikey"),
        a("authUsername", "User for basic"), a("authPassword", "Password for basic"),
        a("retry", "More attempts when it times out or cannot connect", I, default="0"),
        a("retryDelay", "Milliseconds between attempts", I, default="1000"),
        a("responseFormat", "How to read the response", default="auto"),
        a("cache", "Cache the response", B), a("ttl", "Cache seconds", I),
        a("result", "Another name for `<name>_result`"),
        ONERROR,
    ], children=["q:param", "q:header", "q:body"]),
    tag("header", "A header of a q:invoke or q:data request", [
        a("name", "Header name", required=True), a("value", "Header value", X)], self_closing=True),
    tag("body", "The body of a q:invoke request (with expressions)", []),
    tag("data", "Imports CSV, JSON or XML as a list of records (DATA-1..DATA-4)", [
        a("name", "Result variable", required=True), a("source", "File or URL", required=True),
        a("type", "Format", E, default="csv", values=["csv", "json", "xml"]),
        a("delimiter", "CSV separator", default=","), a("quote", "CSV quote character", default='"'),
        a("header", "The first CSV line is the header", B, default="true"),
        a("encoding", "Encoding of the file or response", default="utf-8"),
        a("skip_rows", "Lines to skip before the header", I, default="0"),
        a("xpath", "XPath of the records (xml)"), a("namespace", "XML namespace"),
        a("cache", "Cache the import", B, default="true"), a("ttl", "Cache seconds", I),
        a("result", "Another name for `<name>_result`"),
        ONERROR,
    ], children=["q:column", "q:field", "q:transform", "q:header"]),
    tag("column", "A CSV column converted to `type` (DATA-1)", [
        a("name", "Column name", required=True),
        a("type", "Type", E, default="string", values=["string", "integer", "decimal", "boolean", "json", "array"]),
    ], self_closing=True),
    tag("field", "A field of a JSON/XML record (DATA-2)", [
        a("name", "Field name", required=True), a("xpath", "Path relative to the record"),
        a("path", "Path relative to the record"), a("type", "Type"),
    ], self_closing=True),
    tag("transform", "Operations applied in order (DATA-3)", [], children=["q:filter", "q:sort", "q:limit", "q:compute"]),
    tag("filter", "Keeps the records for which the condition is true", [
        a("condition", "An expression over the record's fields", X, required=True)], self_closing=True),
    tag("sort", "Sorts the records", [a("by", "Field", required=True),
                                      a("order", "Order", E, default="asc", values=["asc", "desc"])],
        self_closing=True),
    tag("limit", "Keeps the first records", [a("value", "How many", I, required=True)], self_closing=True),
    tag("compute", "Adds a computed field", [a("field", "New field", required=True),
                                            a("expression", "Its value", X, required=True), a("type", "Type")],
        self_closing=True),
    tag("action", "Runs on a POST with the `action` field; its q:params are the validated form fields (ACT-1..ACT-11)", [
        a("name", "Action name", required=True),
        a("method", "HTTP method", E, default="POST", values=["POST", "GET"]),
        a("table", "Take the q:params from this table's schema (UI-10)"),
        a("datasource", "Datasource of `table`"),
        a("columns", "Only these columns, in this order (UI-10)"),
    ], children=["q:param", "q:set", "q:query", "q:if", "q:loop", "q:file", "q:mail", "q:flash", "q:redirect"]),
    tag("redirect", "Ends the action or page with a redirect (ACT-3, ACT-7)", [
        a("url", "Where to", X), a("to", "Where to (same as url)", X),
        a("flash", "Message for the next page", X),
        a("status", "HTTP status", I, default="302"),
    ], self_closing=True),
    tag("flash", "Inside a q:action: a flash of another kind for the next page (ACT-3)", [
        a("type", "Kind", E, default="info", values=["info", "success", "warning", "error"]),
        a("message", "The message (or the tag's text)", X),
    ]),
    tag("file", "Saves an upload, sends a stored file or deletes one (FILE-1, FILE-2)", [
        a("action", "What to do", E, required=True, values=["upload", "send", "delete"]),
        a("file", "The upload, or the stored file's name", X, required=True),
        a("destination", "Folder inside paths.uploads"),
        a("nameConflict", "On a clash", E, default="makeUnique", values=["makeUnique", "overwrite", "skip", "error"]),
        a("name", "File name the browser gets (send)"),
        a("result", "Result variable"),
    ], self_closing=True),
    tag("mail", "Sends a message through `mail:` in quantum.config.yaml (MAIL-1, MAIL-2)", [
        a("to", "Recipients", X, required=True), a("subject", "Subject", X, required=True),
        a("from", "Sender (else mail.from)"), a("cc", "Copy"), a("bcc", "Hidden copy"),
        a("replyTo", "Reply address"),
        a("type", "Body format", E, default="html", values=["html", "text"]),
        a("body", "Body, when the tag has no content", X),
        a("name", "Result name (`<name>_result`)", default="mail"),
        ONERROR,
    ], children=["q:attachment"]),
    tag("attachment", "A file attached to a q:mail", [a("file", "Path of the file", required=True)], self_closing=True),
    tag("import", "Makes a component usable as `<Name/>` (COMP-1)", [
        a("component", "Component name"), a("from", "Folder under paths.components"),
        a("as", "Local name"),
        a("behavior", "Game behavior (Laboratory)"), a("prefab", "Game prefab (Laboratory)"),
        a("tilemap", "Game tilemap (Laboratory)"),
    ], self_closing=True),
    tag("slot", "Where the content between `<Name>` and `</Name>` goes (COMP-3)", [a("name", "Slot name")]),
    tag("script", "Client-side JavaScript of the page", []),
    tag("llm", "A model call; with knowledge=, an answer that cites its sources (IA-1, IA-5..IA-9)", [
        a("name", "Result variable", required=True),
        a("model", "Model, an expression; else QUANTUM_LLM_DEFAULT_MODEL / llm.model (IA-1)", X),
        a("endpoint", "Another model server for this tag", X), a("apiKey", "API key", X),
        a("provider", "Provider", E, values=["ollama", "openai", "anthropic", "claude", "lmstudio", "auto"]),
        a("temperature", "Temperature", N), a("maxTokens", "Most tokens to generate", I),
        a("responseFormat", "`json`: the value is the parsed object", E, default="text", values=["text", "json"]),
        a("timeout", "Seconds to wait for the model", I, default="60"),
        a("knowledge", "Answer from this q:knowledge, citing it (IA-6)"),
        a("top", "Chunks to retrieve", I, default="4"),
        a("minRelevance", "Chunks below it are not retrieved, 0 to 1 (IA-9)", N, default="0"),
        a("stream", "In a web request, the answer arrives as it is written (IA-7)", B, default="false"),
        a("cache", "Cache the answer", B, default="false"), a("ttl", "Cache seconds", I),
        ONERROR,
    ], children=["q:prompt", "q:message", "q:system"],
        examples=['<q:llm name="answer" model="phi3" knowledge="docs" minRelevance="0.79">\n'
                  '  <q:message role="user">{question}</q:message>\n</q:llm>']),
    tag("prompt", "The prompt of a q:llm (with expressions)", []),
    tag("system", "The system message of a q:llm", []),
    tag("message", "A chat message of a q:llm", [
        a("role", "Who says it", E, default="user", values=["system", "user", "assistant"])]),
    tag("knowledge", "A base of text chunks that q:llm knowledge= answers from (IA-2, IA-6, IA-8)", [
        a("name", "Base name", required=True),
        a("embedModel", "Embedding model", default="nomic-embed-text"),
        a("chunkSize", "Characters per chunk", I, default="500"),
        a("chunkOverlap", "Characters shared by neighbouring chunks", I, default="50"),
        a("persist", "Keep the index on disk", B, default="true"),
        a("persistPath", "Where", default="./.quantum/knowledge"),
        a("rebuild", "Index again", B, default="false"),
        ONERROR,
    ], children=["q:source"]),
    tag("source", "A source of a q:knowledge, read whole (IA-8)", [
        a("type", "Kind", E, required=True, values=["text", "file", "directory", "query"]),
        a("path", "File or folder"), a("pattern", "Files of the folder, e.g. `*.md`"),
        a("datasource", "Datasource of a query source"),
        a("chunkSize", "Characters per chunk for this source", I),
        a("chunkOverlap", "Overlap for this source", I),
    ]),
    tag("agent", "A model that uses the declared tools to do a task (IA-4, IA-5)", [
        a("name", "Result variable", required=True),
        a("model", "Model, an expression; else QUANTUM_LLM_DEFAULT_MODEL / llm.model (IA-1)", X),
        a("endpoint", "Another model server", X), a("apiKey", "API key", X),
        a("provider", "Provider", E, default="auto", values=["ollama", "openai", "anthropic", "claude", "lmstudio", "auto"]),
        a("maxIterations", "Most reasoning steps", I, default="10"),
        a("timeout", "Milliseconds for the whole run", I, default="60000"),
        ONERROR,
    ], children=["q:instruction", "q:tool", "q:execute"]),
    tag("instruction", "The agent's instruction", []),
    tag("tool", "A tool the agent can call; its body runs with the arguments as variables", [
        a("name", "Tool name", required=True), a("description", "What it does (shown to the model)"),
        a("builtin", "A built-in tool (q:team)", B, default="false"),
    ], children=["q:param", "q:function"]),
    tag("execute", "The agent's task", [
        a("task", "The task", X, required=True), a("context", "Extra text for the model", X),
        a("entry", "First agent (q:team)"),
    ], self_closing=True),
]}
