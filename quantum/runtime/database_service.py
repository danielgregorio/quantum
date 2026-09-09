"""
Quantum Database Service - Manages database connections and query execution
"""

import logging
import time
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger('quantum.database')


@dataclass
class QueryResult:
    """Container for query results and metadata"""
    data: List[Dict[str, Any]]
    column_list: List[str]
    execution_time: float  # in milliseconds
    record_count: int
    sql: Optional[str] = None  # Set in debug mode
    page: Optional[int] = None
    total_pages: Optional[int] = None
    has_more: bool = False
    cached: bool = False
    success: bool = True
    affected_rows: Optional[int] = None  # For UPDATE/DELETE operations
    last_insert_id: Optional[int] = None  # For INSERT operations

    def to_dict(self):
        """Convert to dictionary for template access"""
        result = asdict(self)
        # Rename column_list to columnList for JavaScript compatibility
        result['columnList'] = result.pop('column_list')
        result['recordCount'] = result.pop('record_count')
        result['executionTime'] = result.pop('execution_time')
        result['totalPages'] = result.pop('total_pages')
        result['hasMore'] = result.pop('has_more')
        result['affectedRows'] = result.pop('affected_rows')
        result['lastInsertId'] = result.pop('last_insert_id')
        return result


class DatabaseConnectionError(Exception):
    """Raised when database connection fails"""
    pass


class QueryExecutionError(Exception):
    """Raised when query execution fails"""
    pass


class DatabaseService:
    """Manages database connections and query execution"""

    def get_datasource_config(self, datasource_name: str) -> Dict[str, Any]:
        """
        Get datasource configuration. Checks local config first, then Admin API.

        Args:
            datasource_name: Name of the datasource

        Returns:
            Dict with datasource configuration

        Raises:
            DatabaseConnectionError: If datasource not found or not ready
        """
        # Check local datasources first (from quantum.config.yaml)
        if datasource_name in self.local_datasources:
            local_cfg = self.local_datasources[datasource_name]
            # Allow env var override for database path (e.g., QUANTUM_TASKDB_PATH)
            import os
            env_key = f"QUANTUM_{datasource_name.upper()}_PATH"
            db_path = os.environ.get(env_key, local_cfg.get('database', ''))
            # Normalize config to match Admin API format
            return {
                'name': datasource_name,
                'type': local_cfg.get('driver', local_cfg.get('type', 'sqlite')),
                'database': db_path,
                'database_name': db_path,
                'host': local_cfg.get('host', 'localhost'),
                'port': local_cfg.get('port', 5432),
                'username': local_cfg.get('username', ''),
                'password': local_cfg.get('password', ''),
            }

        try:
            url = f"{self.admin_api_url}/api/datasources/by-name/{datasource_name}"
            response = requests.get(url, timeout=5)

            if response.status_code == 404:
                raise DatabaseConnectionError(f"Datasource '{datasource_name}' not found")
            elif response.status_code == 503:
                raise DatabaseConnectionError(
                    f"Datasource '{datasource_name}' is not ready. Please check Quantum Admin."
                )
            elif response.status_code != 200:
                raise DatabaseConnectionError(
                    f"Failed to fetch datasource '{datasource_name}': {response.status_code}"
                )

            return response.json()

        except requests.exceptions.ConnectionError:
            # Lead with the local path: declaring the datasource in
            # quantum.config.yaml is the normal way to do this and needs no
            # other process. Quantum Admin is the optional, centrally-managed
            # alternative — pointing at it first sent every new user chasing a
            # server they do not need.
            raise DatabaseConnectionError(
                f"Datasource '{datasource_name}' is not declared locally, and "
                f"the optional Quantum Admin API at {self.admin_api_url} is not "
                f"reachable.\n"
                f"  Declare it in quantum.config.yaml:\n"
                f"    datasources:\n"
                f"      {datasource_name}:\n"
                f"        driver: sqlite\n"
                f"        database: ./data/app.db\n"
                f"  Or start Quantum Admin if you manage datasources there."
            )
        except requests.exceptions.Timeout:
            raise DatabaseConnectionError(
                f"Timeout connecting to Quantum Admin API at {self.admin_api_url}"
            )

    def get_connection(self, datasource_config: Dict[str, Any]):
        """
        Get or create database connection

        Args:
            datasource_config: Datasource configuration from Admin API

        Returns:
            Database connection object

        Raises:
            DatabaseConnectionError: If connection fails
        """
        datasource_name = datasource_config['name']
        db_type = datasource_config['type']

        # Check if connection already exists in pool
        if datasource_name in self.connection_pool:
            conn = self.connection_pool[datasource_name]
            # Test connection is still alive
            if self._test_connection(conn, db_type):
                return conn
            else:
                # Connection dead, remove from pool
                del self.connection_pool[datasource_name]

        # Create new connection
        try:
            if db_type == 'postgresql':
                conn = self._create_postgres_connection(datasource_config)
            elif db_type in ['mysql', 'mariadb']:
                conn = self._create_mysql_connection(datasource_config)
            elif db_type == 'sqlite':
                conn = self._create_sqlite_connection(datasource_config)
            else:
                raise DatabaseConnectionError(f"Unsupported database type: {db_type}")

            # Store in pool
            self.connection_pool[datasource_name] = conn
            return conn

        except Exception as e:
            raise DatabaseConnectionError(f"Failed to connect to database: {e}")

    def _open_raw_connection(self, datasource_config: Dict[str, Any]):
        """A fresh connection that bypasses the pool, for a transaction to own.

        Reuses the same per-driver factories as get_connection, but never
        stores the result in connection_pool — a connection with an open
        transaction must not be handed to unrelated queries.
        """
        db_type = datasource_config['type']
        if db_type == 'postgresql':
            return self._create_postgres_connection(datasource_config)
        if db_type in ('mysql', 'mariadb'):
            return self._create_mysql_connection(datasource_config)
        if db_type == 'sqlite':
            return self._create_sqlite_connection(datasource_config)
        raise DatabaseConnectionError(f"Unsupported database type: {db_type}")

    def _create_postgres_connection(self, config: Dict[str, Any]):
        """Create PostgreSQL connection"""
        try:
            import psycopg2
            return psycopg2.connect(
                host=config['host'],
                port=config['port'],
                database=config['database_name'],
                user=config['username'],
                password=config['password']
            )
        except ImportError:
            raise DatabaseConnectionError(
                "psycopg2 not installed. Install with: pip install psycopg2-binary"
            )

    def _create_mysql_connection(self, config: Dict[str, Any]):
        """Create MySQL/MariaDB connection"""
        try:
            import pymysql
            return pymysql.connect(
                host=config['host'],
                port=config['port'],
                database=config['database_name'],
                user=config['username'],
                password=config['password'],
                cursorclass=pymysql.cursors.DictCursor  # Return results as dictionaries
            )
        except ImportError:
            raise DatabaseConnectionError(
                "pymysql not installed. Install with: pip install pymysql"
            )

    def _create_sqlite_connection(self, config: Dict[str, Any]):
        """Create SQLite connection"""
        import sqlite3
        conn = sqlite3.connect(config['database'], timeout=30.0)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.isolation_level = None  # Autocommit mode for better concurrency
        return conn

    def _test_connection(self, conn, db_type: str) -> bool:
        """Test if connection is still alive"""
        try:
            cursor = conn.cursor()
            if db_type == 'postgresql':
                cursor.execute("SELECT 1")
            elif db_type in ['mysql', 'mariadb']:
                cursor.execute("SELECT 1")
            cursor.close()
            return True
        except Exception as exc:
            # Returning False IS the contract here — the caller drops the
            # pooled connection and opens a new one. But the reason is worth
            # having at debug level: a pool that keeps churning is usually a
            # network or credential problem, and the exception was the only
            # evidence.
            logger.debug("connection test failed, dropping from pool: %s", exc)
            return False

    def execute_query(self, datasource_name: str, sql: str, params: Dict[str, Any] = None) -> QueryResult:
        """
        Execute SQL with parameter binding

        Args:
            datasource_name: Name of the datasource
            sql: SQL query with :param placeholders
            params: Dictionary of parameter values

        Returns:
            QueryResult with data and metadata

        Raises:
            QueryExecutionError: If query execution fails
        """
        if params is None:
            params = {}

        # Get datasource config
        config = self.get_datasource_config(datasource_name)
        db_type = config['type']

        # Inside a q:transaction, every query on this datasource runs on the
        # transaction's dedicated connection and must NOT commit — otherwise
        # each write autocommits and rollback has nothing to undo.
        tx_conn = self._active_transaction_for(datasource_name)
        in_transaction = tx_conn is not None
        conn = tx_conn if in_transaction else self.get_connection(config)

        # Start timing
        start_time = time.time()

        try:
            cursor = conn.cursor()

            # Convert :param syntax to database-specific placeholder
            prepared_sql, prepared_params = self._prepare_query(sql, params, db_type)

            # Execute query
            cursor.execute(prepared_sql, prepared_params)

            # Check if it's a SELECT query (returns data)
            if cursor.description:
                # Fetch results
                rows = cursor.fetchall()

                # Get column names
                if db_type == 'postgresql':
                    column_names = [desc[0] for desc in cursor.description]
                    # Convert rows to dictionaries for PostgreSQL
                    data = [dict(zip(column_names, row)) for row in rows]
                elif db_type in ['mysql', 'mariadb']:
                    # pymysql with DictCursor already returns dictionaries
                    column_names = list(rows[0].keys()) if rows else []
                    data = rows
                elif db_type == 'sqlite':
                    # SQLite with row_factory=Row - convert to dictionaries
                    column_names = [desc[0] for desc in cursor.description]
                    data = [dict(row) for row in rows]
                else:
                    column_names = []
                    data = []

                record_count = len(data)
                affected_rows = None
                last_insert_id = None
            else:
                # Non-SELECT query (INSERT, UPDATE, DELETE). Commit now ONLY
                # when standalone; inside a transaction the commit is deferred
                # to commit_transaction so a later failure can roll it back.
                if not in_transaction:
                    conn.commit()
                data = []
                column_names = []
                record_count = cursor.rowcount
                affected_rows = cursor.rowcount
                last_insert_id = None

                # Get last insert ID for INSERT operations
                if db_type == 'postgresql':
                    # PostgreSQL: Try to get lastval() if available
                    try:
                        id_cursor = conn.cursor()
                        id_cursor.execute("SELECT lastval()")
                        last_insert_id = id_cursor.fetchone()[0]
                        id_cursor.close()
                    except:
                        # No sequence was used (e.g., UPDATE/DELETE)
                        pass
                elif db_type in ['mysql', 'mariadb']:
                    # MySQL/MariaDB: Use cursor.lastrowid
                    if cursor.lastrowid > 0:
                        last_insert_id = cursor.lastrowid
                elif db_type == 'sqlite':
                    # SQLite: Use cursor.lastrowid
                    if cursor.lastrowid > 0:
                        last_insert_id = cursor.lastrowid

                # For INSERT with RETURNING (PostgreSQL)
                if db_type == 'postgresql' and cursor.description:
                    rows = cursor.fetchall()
                    column_names = [desc[0] for desc in cursor.description]
                    data = [dict(zip(column_names, row)) for row in rows]
                    record_count = len(data)

            cursor.close()

            # Calculate execution time
            execution_time = (time.time() - start_time) * 1000  # Convert to ms

            return QueryResult(
                data=data,
                column_list=column_names,
                execution_time=execution_time,
                record_count=record_count,
                affected_rows=affected_rows,
                last_insert_id=last_insert_id
            )

        except Exception as e:
            # Standalone: roll back this one statement. Inside a transaction,
            # let the error propagate to the TransactionExecutor so the WHOLE
            # transaction rolls back — rolling back here would abandon the rest
            # of the transaction's connection state.
            if not in_transaction:
                try:
                    conn.rollback()
                except Exception:
                    # Best effort: we are already raising the real error, and
                    # a failed rollback on a broken connection must not
                    # replace it. Deliberately silent.
                    pass
            raise QueryExecutionError(f"Query execution failed: {e}")

    def _prepare_query(self, sql: str, params: Dict[str, Any], db_type: str) -> tuple:
        """
        Convert :param syntax to database-specific placeholders

        Args:
            sql: SQL with :param placeholders
            params: Dictionary of parameters
            db_type: Database type (postgresql, mysql, mariadb)

        Returns:
            Tuple of (prepared_sql, prepared_params)
        """
        import re

        # Find all :param placeholders
        param_pattern = r':(\w+)'
        param_names = re.findall(param_pattern, sql)

        if db_type == 'postgresql':
            # PostgreSQL uses %s placeholders
            prepared_sql = sql
            for i, param_name in enumerate(param_names, 1):
                # Replace :param with %s
                prepared_sql = prepared_sql.replace(f':{param_name}', '%s', 1)

            # Build parameter list in correct order
            prepared_params = [params.get(name) for name in param_names]

        elif db_type in ['mysql', 'mariadb']:
            # MySQL uses %s placeholders
            prepared_sql = sql
            for param_name in param_names:
                prepared_sql = prepared_sql.replace(f':{param_name}', '%s', 1)

            # Build parameter list in correct order
            prepared_params = [params.get(name) for name in param_names]

        elif db_type == 'sqlite':
            # SQLite uses ? placeholders
            prepared_sql = sql
            for param_name in param_names:
                prepared_sql = prepared_sql.replace(f':{param_name}', '?', 1)

            # Build parameter list in correct order
            prepared_params = [params.get(name) for name in param_names]

        else:
            raise QueryExecutionError(f"Unsupported database type: {db_type}")

        return prepared_sql, prepared_params

    def close_connection(self, datasource_name: str):
        """Close database connection"""
        if datasource_name in self.connection_pool:
            try:
                self.connection_pool[datasource_name].close()
            except:
                pass
            del self.connection_pool[datasource_name]

    def close_all_connections(self):
        """Close all database connections"""
        for datasource_name in list(self.connection_pool.keys()):
            self.close_connection(datasource_name)

    # Phase D: Database Backend - Transaction Support
    
    def begin_transaction(self, datasource_name: str = "default") -> Dict[str, Any]:
        """
        Begin a real database transaction.

        Opens a DEDICATED connection with autocommit off and holds it in the
        context. execute_query() routes to this connection while the
        transaction is active and does not commit; commit/rollback here do the
        real thing.

        This used to return a dict and mark flags on it — no BEGIN, no COMMIT,
        no ROLLBACK ever reached the database. Each q:query inside the block
        opened its own pooled connection and autocommitted, so a q:transaction
        was a no-op: a failed transfer left the debit committed and the credit
        gone while the framework printed "rolled back". Reproduced with a
        two-account transfer before fixing. See tests/integration/
        test_transaction_atomicity.py.
        """
        config = self.get_datasource_config(datasource_name)
        # A fresh connection, NOT the pooled one, so the open transaction never
        # interferes with other queries and vice versa.
        conn = self._open_raw_connection(config)
        db_type = config['type']

        # Turn autocommit off / open the transaction explicitly per driver.
        try:
            if db_type == 'sqlite':
                # sqlite3 with isolation_level=None is autocommit; set a level
                # so the driver opens a transaction on the first write.
                conn.isolation_level = 'DEFERRED'
                conn.execute('BEGIN')
            elif db_type == 'postgresql':
                conn.autocommit = False
            elif db_type in ('mysql', 'mariadb'):
                conn.begin()
        except Exception as exc:
            try:
                conn.close()
            except Exception:
                pass
            raise QueryExecutionError(f"could not begin transaction: {exc}")

        tx = {
            'datasource': datasource_name,
            'active': True,
            'connection': conn,
            'db_type': db_type,
            'start_time': time.time(),
        }
        self._active_transactions[datasource_name] = tx
        return tx

    def commit_transaction(self, transaction_context: Dict[str, Any]) -> bool:
        """Commit the real transaction and release its connection."""
        return self._finish_transaction(transaction_context, commit=True)

    def rollback_transaction(self, transaction_context: Dict[str, Any]) -> bool:
        """Roll the real transaction back and release its connection."""
        return self._finish_transaction(transaction_context, commit=False)

    def _finish_transaction(self, tx: Dict[str, Any], commit: bool) -> bool:
        conn = tx.get('connection')
        ds = tx.get('datasource')
        tx['active'] = False
        tx['committed'] = commit
        tx['rolled_back'] = not commit
        # Stop routing new queries here regardless of what happens next.
        if self._active_transactions.get(ds) is tx:
            del self._active_transactions[ds]
        if conn is None:
            return True
        try:
            conn.commit() if commit else conn.rollback()
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return True

    def _active_transaction_for(self, datasource_name: str):
        """The open transaction's connection for this datasource, or None."""
        tx = self._active_transactions.get(datasource_name)
        if tx and tx.get('active'):
            return tx.get('connection')
        return None
    
    # Phase D: Query Caching

    def __init__(self, admin_api_url: str = "http://localhost:8000", local_datasources: Dict[str, Any] = None):
        self.admin_api_url = admin_api_url
        self.local_datasources = local_datasources or {}
        self.connection_pool: Dict[str, Any] = {}
        # Phase D: Query cache with TTL
        self.query_cache: Dict[str, Dict[str, Any]] = {}  # cache_key -> {result, expires_at}
        # datasource -> open transaction context (its dedicated connection)
        self._active_transactions: Dict[str, Any] = {}
    
    def _get_cache_key(self, sql: str, params: Dict[str, Any], datasource: str) -> str:
        """Generate cache key for query"""
        import hashlib
        cache_str = f"{datasource}:{sql}:{str(sorted(params.items()))}"
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _parse_cache_ttl(self, cache: str) -> int:
        """
        Parse cache TTL string like '5m', '1h', '30s'
        
        Returns:
            TTL in seconds
        """
        if not cache or cache.lower() == 'false':
            return 0
        
        if cache.lower() == 'true':
            return 300  # Default 5 minutes
        
        # Parse time units
        cache = cache.lower().strip()
        if cache.endswith('s'):
            return int(cache[:-1])
        elif cache.endswith('m'):
            return int(cache[:-1]) * 60
        elif cache.endswith('h'):
            return int(cache[:-1]) * 3600
        elif cache.endswith('d'):
            return int(cache[:-1]) * 86400
        else:
            return int(cache)  # Assume seconds
    
    def get_cached_query(self, cache_key: str) -> Optional[QueryResult]:
        """Get cached query result if not expired"""
        if cache_key not in self.query_cache:
            return None
        
        cached = self.query_cache[cache_key]
        if time.time() > cached['expires_at']:
            # Expired - remove from cache
            del self.query_cache[cache_key]
            return None
        
        # Mark result as cached
        cached['result'].cached = True
        return cached['result']
    
    def cache_query_result(self, cache_key: str, result: QueryResult, ttl_seconds: int):
        """Cache query result with TTL"""
        self.query_cache[cache_key] = {
            'result': result,
            'expires_at': time.time() + ttl_seconds
        }
