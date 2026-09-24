# q:query Implementation Plan

## Phase 1 (MVP) - Current Focus

### Goal
Implement basic database query functionality that allows Quantum components to execute SQL queries against configured datasources with automatic parameter binding and SQL injection protection.

### Components to Create/Modify

#### 1. AST Nodes (`src/core/ast_nodes.py`)

**New Classes:**

```python
class QueryNode(ASTNode):
    """Represents <q:query> component"""
    def __init__(self, name: str, datasource: str, sql: str, params: List['ParamNode'],
                 attributes: Dict[str, Any]):
        self.name = name
        self.datasource = datasource
        self.sql = sql  # Raw SQL content
        self.params = params
        self.attributes = attributes  # cache, ttl, timeout, maxrows, etc.

class ParamNode(ASTNode):
    """Represents <q:param> within q:query"""
    def __init__(self, name: str, value: Any, type: str, attributes: Dict[str, Any]):
        self.name = name
        self.value = value
        self.type = type  # string, integer, decimal, boolean, datetime, array, json
        self.attributes = attributes  # null, maxLength, scale
```

#### 2. Parser (`src/core/parser.py`)

**New Methods:**

```python
def parse_query(self) -> QueryNode:
    """Parse <q:query> component"""
    # 1. Parse opening tag attributes
    # 2. Extract SQL content (everything between tags except <q:param>)
    # 3. Parse <q:param> children
    # 4. Validate required attributes (name, datasource)
    # 5. Return QueryNode

def parse_param(self) -> ParamNode:
    """Parse <q:param> component"""
    # 1. Parse attributes
    # 2. Validate required attributes (name, value, type)
    # 3. Return ParamNode
```

#### 3. Database Service (`src/runtime/database_service.py`) - NEW FILE

```python
class DatabaseService:
    """Manages database connections and query execution"""

    def __init__(self, admin_api_url: str):
        self.admin_api_url = admin_api_url
        self.connection_pool = {}  # Cache connections

    def get_datasource_config(self, datasource_name: str) -> Dict:
        """Fetch datasource configuration from Quantum Admin API"""
        # GET http://localhost:8000/api/datasources/by-name/{name}
        pass

    def get_connection(self, datasource_config: Dict):
        """Get or create database connection"""
        # Support: PostgreSQL, MySQL, MariaDB, MongoDB
        # Use connection pooling
        pass

    def execute_query(self, connection, sql: str, params: Dict) -> QueryResult:
        """Execute SQL with parameter binding"""
        # 1. Validate parameters
        # 2. Bind parameters (convert :name to %s or $1 based on DB)
        # 3. Execute query
        # 4. Return results with metadata
        pass

    def close_connection(self, connection):
        """Close database connection"""
        pass
```

**QueryResult Class:**

```python
class QueryResult:
    """Container for query results and metadata"""
    def __init__(self, data: List[Dict], column_list: List[str],
                 execution_time: float, record_count: int):
        self.data = data
        self.column_list = column_list
        self.execution_time = execution_time
        self.record_count = record_count
        self.sql = None  # Set in debug mode

    def to_dict(self):
        """Convert to dictionary for template access"""
        return {
            'data': self.data,
            'columnList': self.column_list,
            'executionTime': self.execution_time,
            'recordCount': self.record_count
        }
```

#### 4. Component Runtime (`src/runtime/component.py`)

**New Method:**

```python
def execute_query(self, node: QueryNode, context: ExecutionContext) -> QueryResult:
    """Execute database query"""
    # 1. Get datasource configuration
    # 2. Resolve parameter values from context
    # 3. Validate parameters
    # 4. Execute query via DatabaseService
    # 5. Store result in context with node.name
    # 6. Return result
    pass
```

#### 5. Parameter Validation (`src/runtime/query_validators.py`) - NEW FILE

```python
class QueryValidator:
    """Validates query parameters"""

    @staticmethod
    def validate_param(value: Any, param_type: str, attributes: Dict) -> Any:
        """Validate and convert parameter value"""
        # Type conversion and validation
        # Handle: string, integer, decimal, boolean, datetime, array, json
        # Check maxLength, scale, null constraints
        pass

    @staticmethod
    def sanitize_sql(sql: str) -> str:
        """Basic SQL sanitization (prevent comment injection, etc.)"""
        pass
```

### Dependencies to Add

```
# requirements.txt additions
psycopg2-binary>=2.9.9    # PostgreSQL (already in quantum_admin)
pymysql>=1.1.0            # MySQL/MariaDB (already in quantum_admin)
pymongo>=4.6.1            # MongoDB (already in quantum_admin)
sqlparse>=0.4.4           # SQL parsing and formatting
```

### Integration with Quantum Admin

**New API Endpoint Needed:**

```python
# quantum_admin/backend/main.py

@app.get("/api/datasources/by-name/{name}", tags=["API"])
def get_datasource_by_name(name: str, db: Session = Depends(get_db)):
    """Get datasource configuration by name for runtime use"""
    datasource = db.query(models.Datasource).filter(
        models.Datasource.name == name
    ).first()

    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")

    # Only return if status is 'running' and setup is 'ready'
    if datasource.status != 'running' or datasource.setup_status != 'ready':
        raise HTTPException(
            status_code=503,
            detail=f"Datasource '{name}' is not ready (status: {datasource.status}, setup: {datasource.setup_status})"
        )

    return {
        'name': datasource.name,
        'type': datasource.type,
        'host': datasource.host,
        'port': datasource.port,
        'database_name': datasource.database_name,
        'username': datasource.username,
        'password': datasource.password_encrypted,  # TODO: Decrypt
        'connection_string': f"{datasource.type}://{datasource.username}@{datasource.host}:{datasource.port}/{datasource.database_name}"
    }
```

### Configuration

**New Environment Variable:**

```
QUANTUM_ADMIN_URL=http://localhost:8000
```

### Example Implementation Flow

```
1. Parser encounters <q:query name="users" datasource="my-db">
   ↓
2. Creates QueryNode with SQL content and ParamNodes
   ↓
3. ComponentRuntime.execute_query() is called
   ↓
4. DatabaseService.get_datasource_config() fetches from Admin API
   ↓
5. DatabaseService.get_connection() creates/reuses connection
   ↓
6. QueryValidator.validate_param() validates each parameter
   ↓
7. DatabaseService.execute_query() runs SQL with bound parameters
   ↓
8. QueryResult is stored in ExecutionContext with name "users"
   ↓
9. Template can access {users.data}, {users.recordCount}, etc.
```

### Test Cases to Create

```
examples/test-query-basic.q       # Simple SELECT
examples/test-query-params.q      # Parameter binding
examples/test-query-insert.q      # INSERT with RETURNING
examples/test-query-update.q      # UPDATE operations
examples/test-query-delete.q      # DELETE operations
examples/test-query-loop.q        # Using results in q:loop
examples/test-query-error.q       # Error handling
examples/test-query-metadata.q    # Accessing metadata
```

### Success Criteria

✅ Can execute SELECT queries against PostgreSQL
✅ Parameter binding prevents SQL injection
✅ Results accessible in q:loop and databinding
✅ Query metadata available (recordCount, columnList, executionTime)
✅ INSERT/UPDATE/DELETE operations work
✅ RETURNING clause supported for PostgreSQL
✅ Error messages are clear and helpful
✅ Connection pooling prevents connection exhaustion

### Performance Targets

- Query execution overhead: < 5ms
- Connection pool: Reuse connections across requests
- Parameter validation: < 1ms per parameter
- Memory: < 1MB per 1000 records

### Security Requirements

✅ All queries use parameterized statements (no string concatenation)
✅ Type validation prevents type confusion attacks
✅ maxLength prevents buffer overflow
✅ Datasource credentials encrypted in transit
✅ SQL parsing prevents comment injection
✅ Connection strings never exposed to templates

## Phase 2 (Next)

- Multiple queries per component
- Pagination with automatic COUNT(*) queries
- Query of Queries (in-memory processing)
- Enhanced metadata (affected rows, last insert ID)

## Phase 3 (Future)

- Transaction support (<q:transaction>)
- Query caching with TTL
- Stored procedure support
- Batch operations

## Phase 4 (Advanced)

- Reactive queries (auto-refresh)
- Query monitoring and profiling
- Slow query logging
- Query optimization hints

## Migration Path from ColdFusion

### CF:query → q:query Mapping

| ColdFusion | Quantum | Notes |
|------------|---------|-------|
| `<cfquery name="q" datasource="ds">` | `<q:query name="q" datasource="ds">` | Same syntax |
| `<cfqueryparam name="id" value="#id#" cfsqltype="cf_sql_integer">` | `<q:param name="id" value="{id}" type="integer" />` | Cleaner syntax |
| `#q.recordcount#` | `{q.recordCount}` | camelCase |
| `#q.columnlist#` | `{q.columnList}` | camelCase |
| `<cfloop query="q">` | `<q:loop items="{q}" var="row">` | More explicit |
| `cachedwithin` | `cache="true" ttl="3600"` | Separate attributes |
| `result="meta"` | `result="meta"` | Same |
| `blockfactor` | *(not needed)* | Modern drivers handle this |

### Example Migration

**ColdFusion:**
```cfml
<cfquery name="getUsers" datasource="mydb">
    SELECT id, name, email
    FROM users
    WHERE status = <cfqueryparam value="#status#" cfsqltype="cf_sql_varchar">
    ORDER BY created_at DESC
</cfquery>

<cfloop query="getUsers">
    <p>#getUsers.name# - #getUsers.email#</p>
</cfloop>
```

**Quantum:**
```quantum
<q:query name="getUsers" datasource="mydb">
    SELECT id, name, email
    FROM users
    WHERE status = :status
    ORDER BY created_at DESC
    <q:param name="status" value="{status}" type="string" />
</q:query>

<q:loop items="{getUsers}" var="user">
    <p>{user.name} - {user.email}</p>
</q:loop>
```

## Technical Decisions

### Why Named Parameters (:name) instead of Positional (?)?

✅ **Readability** - Clear what each parameter represents
✅ **Maintainability** - Adding/removing parameters doesn't break order
✅ **Validation** - Can validate by name in error messages
✅ **Familiar** - ColdFusion, Oracle, and modern ORMs use this

### Why Separate <q:param> instead of Inline?

✅ **Security** - Forces explicit parameter declaration
✅ **Type Safety** - Required type annotation
✅ **Clarity** - Parameters are visually distinct from SQL
✅ **Validation** - Can validate before query execution

### Why Connection Pooling?

✅ **Performance** - Creating connections is expensive (50-100ms)
✅ **Scalability** - Limited connection slots on DB server
✅ **Reliability** - Graceful handling of connection issues

### Database Driver Selection

| Database | Driver | Reason |
|----------|--------|--------|
| PostgreSQL | psycopg2 | Industry standard, C-optimized |
| MySQL | pymysql | Pure Python, reliable |
| MariaDB | pymysql | Same as MySQL |
| MongoDB | pymongo | Official driver |

## Open Questions

1. **Connection Pool Size**: Default 10? Configurable per datasource?
2. **Query Timeout**: Default 30s? User configurable?
3. **Memory Limit**: Max recordset size before warning?
4. **Error Handling**: Return empty result or throw exception?
5. **Admin API Auth**: How does runtime authenticate to Admin API?

## Resources

- [psycopg2 Documentation](https://www.psycopg.org/docs/)
- [PyMySQL Documentation](https://pymysql.readthedocs.io/)
- [SQLAlchemy Engine](https://docs.sqlalchemy.org/en/14/core/engines.html)
- [SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
