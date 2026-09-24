"""
Database Setup Service
Handles initial configuration of database containers
"""
import logging
import time
import psycopg2
import pymysql
from pymongo import MongoClient

logger = logging.getLogger(__name__)


class DatabaseSetupService:
    """Service for setting up databases in containers"""

    @staticmethod
    def setup_database(datasource) -> tuple[bool, str]:
        """
        Setup database based on type

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            db_type = datasource.type.lower()

            if db_type == 'postgres':
                return DatabaseSetupService._setup_postgres(datasource)
            elif db_type in ['mysql', 'mariadb']:
                return DatabaseSetupService._setup_mysql(datasource)
            elif db_type == 'mongodb':
                return DatabaseSetupService._setup_mongodb(datasource)
            elif db_type == 'redis':
                # Redis doesn't need setup
                return True, "Redis is ready to use"
            else:
                return False, f"Unsupported database type: {db_type}"

        except Exception as e:
            logger.error(f"Database setup failed: {e}")
            return False, str(e)

    @staticmethod
    def _setup_postgres(datasource) -> tuple[bool, str]:
        """Setup PostgreSQL database"""
        max_retries = 30
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                # Connect to default postgres database
                conn = psycopg2.connect(
                    host=datasource.host,
                    port=datasource.port,
                    database='postgres',
                    user=datasource.username,
                    password=datasource.password_encrypted,
                    connect_timeout=5
                )
                conn.autocommit = True
                cursor = conn.cursor()

                # Check if database exists
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (datasource.database_name,)
                )

                if not cursor.fetchone():
                    # Create database
                    cursor.execute(
                        f'CREATE DATABASE "{datasource.database_name}" '
                        f'OWNER "{datasource.username}"'
                    )
                    logger.info(f"Created database: {datasource.database_name}")

                cursor.close()
                conn.close()

                # Test connection to new database
                test_conn = psycopg2.connect(
                    host=datasource.host,
                    port=datasource.port,
                    database=datasource.database_name,
                    user=datasource.username,
                    password=datasource.password_encrypted,
                    connect_timeout=5
                )
                test_conn.close()

                return True, f"PostgreSQL database '{datasource.database_name}' is ready"

            except psycopg2.OperationalError as e:
                if attempt < max_retries - 1:
                    logger.info(f"Waiting for PostgreSQL to be ready... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    return False, f"PostgreSQL failed to start: {str(e)}"
            except Exception as e:
                return False, f"PostgreSQL setup error: {str(e)}"

    @staticmethod
    def _setup_mysql(datasource) -> tuple[bool, str]:
        """Setup MySQL/MariaDB database"""
        max_retries = 30
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                # Connect to MySQL server
                conn = pymysql.connect(
                    host=datasource.host,
                    port=datasource.port,
                    user=datasource.username,
                    password=datasource.password_encrypted,
                    connect_timeout=5
                )
                cursor = conn.cursor()

                # Create database if not exists
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{datasource.database_name}`")

                # Grant privileges
                cursor.execute(
                    f"GRANT ALL PRIVILEGES ON `{datasource.database_name}`.* "
                    f"TO '{datasource.username}'@'%'"
                )
                cursor.execute("FLUSH PRIVILEGES")

                cursor.close()
                conn.close()

                # Test connection to new database
                test_conn = pymysql.connect(
                    host=datasource.host,
                    port=datasource.port,
                    database=datasource.database_name,
                    user=datasource.username,
                    password=datasource.password_encrypted,
                    connect_timeout=5
                )
                test_conn.close()

                db_type = 'MariaDB' if datasource.type == 'mariadb' else 'MySQL'
                return True, f"{db_type} database '{datasource.database_name}' is ready"

            except pymysql.OperationalError as e:
                if attempt < max_retries - 1:
                    logger.info(f"Waiting for MySQL/MariaDB to be ready... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    return False, f"MySQL/MariaDB failed to start: {str(e)}"
            except Exception as e:
                return False, f"MySQL/MariaDB setup error: {str(e)}"

    @staticmethod
    def _setup_mongodb(datasource) -> tuple[bool, str]:
        """Setup MongoDB database"""
        max_retries = 30
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                # Connect to MongoDB
                client = MongoClient(
                    host=datasource.host,
                    port=datasource.port,
                    username=datasource.username,
                    password=datasource.password_encrypted,
                    serverSelectionTimeoutMS=5000
                )

                # Test connection
                client.server_info()

                # Create database (MongoDB creates it on first write)
                db = client[datasource.database_name]

                # Create a test collection to initialize the database
                db.create_collection('_quantum_init')
                db['_quantum_init'].insert_one({'initialized': True})

                client.close()

                return True, f"MongoDB database '{datasource.database_name}' is ready"

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.info(f"Waiting for MongoDB to be ready... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    return False, f"MongoDB failed to start: {str(e)}"
