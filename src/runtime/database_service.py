"""
Quantum Database Service - Manages database connections and query execution
"""

import time
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


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
            raise DatabaseConnectionError(
                f"Cannot connect to Quantum Admin API at {self.admin_api_url}. "
                "Please ensure Quantum Admin is running."
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
        except:
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

        # Get connection
        conn = self.get_connection(config)

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
                # Non-SELECT query (INSERT, UPDATE, DELETE)
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
            # Rollback on error
            conn.rollback()
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
        Begin a database transaction
        
        Phase D: Database Backend
        
        Args:
            datasource_name: Name of datasource
            
        Returns:
            Transaction context dict
        """
        # For now, return a transaction context
        # Real implementation would use database-specific transaction APIs
        return {
            'datasource': datasource_name,
            'active': True,
            'queries': [],
            'start_time': time.time()
        }
    
    def commit_transaction(self, transaction_context: Dict[str, Any]) -> bool:
        """
        Commit a transaction
        
        Args:
            transaction_context: Transaction context from begin_transaction
            
        Returns:
            True if successful
        """
        # Mark transaction as committed
        transaction_context['active'] = False
        transaction_context['committed'] = True
        return True
    
    def rollback_transaction(self, transaction_context: Dict[str, Any]) -> bool:
        """
        Rollback a transaction
        
        Args:
            transaction_context: Transaction context from begin_transaction
            
        Returns:
            True if successful
        """
        # Mark transaction as rolled back
        transaction_context['active'] = False
        transaction_context['rolled_back'] = True
        return True
    
    # Phase D: Query Caching

    def __init__(self, admin_api_url: str = "http://localhost:8000", local_datasources: Dict[str, Any] = None):
        self.admin_api_url = admin_api_url
        self.local_datasources = local_datasources or {}
        self.connection_pool: Dict[str, Any] = {}
        # Phase D: Query cache with TTL
        self.query_cache: Dict[str, Dict[str, Any]] = {}  # cache_key -> {result, expires_at}
    
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
