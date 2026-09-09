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

    def to_dict(self):
        """Convert to dictionary for template access"""
        result = asdict(self)
        # Rename column_list to columnList for JavaScript compatibility
        result['columnList'] = result.pop('column_list')
        result['recordCount'] = result.pop('record_count')
        result['executionTime'] = result.pop('execution_time')
        result['totalPages'] = result.pop('total_pages')
        result['hasMore'] = result.pop('has_more')
        return result


class DatabaseConnectionError(Exception):
    """Raised when database connection fails"""
    pass


class QueryExecutionError(Exception):
    """Raised when query execution fails"""
    pass


class DatabaseService:
    """Manages database connections and query execution"""

    def __init__(self, admin_api_url: str = "http://localhost:8000"):
        self.admin_api_url = admin_api_url
        self.connection_pool: Dict[str, Any] = {}  # Cache connections by datasource name

    def get_datasource_config(self, datasource_name: str) -> Dict[str, Any]:
        """
        Fetch datasource configuration from Quantum Admin API

        Args:
            datasource_name: Name of the datasource

        Returns:
            Dict with datasource configuration

        Raises:
            DatabaseConnectionError: If datasource not found or not ready
        """
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
                else:
                    column_names = []
                    data = []

                record_count = len(data)
            else:
                # Non-SELECT query (INSERT, UPDATE, DELETE)
                conn.commit()
                data = []
                column_names = []
                record_count = cursor.rowcount

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
                record_count=record_count
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
