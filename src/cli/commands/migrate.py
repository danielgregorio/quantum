"""
Quantum CLI - Database Migration Commands
Handles database migrations with automatic PostgreSQL/SQLite failover
"""
import os
import sys
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

import click

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Migration operation failed"""
    pass


class Migration:
    """Represents a single migration file"""

    def __init__(self, version: str, name: str, path: Path):
        self.version = version
        self.name = name
        self.path = path
        self._content = None

    @property
    def content(self) -> str:
        if self._content is None:
            self._content = self.path.read_text()
        return self._content

    @property
    def checksum(self) -> str:
        return hashlib.md5(self.content.encode()).hexdigest()

    def __repr__(self):
        return f"<Migration {self.version}: {self.name}>"


class DatabaseConnection:
    """Database connection with automatic failover"""

    def __init__(self, project_path: Path = None):
        self.project_path = project_path or Path.cwd()
        self._conn = None
        self._db_type = None

    def connect(self) -> Any:
        """
        Connect to database with automatic failover.
        Tries PostgreSQL first, falls back to SQLite.
        """
        # Try to load database config from quantum.config.yaml
        config = self._load_config()

        # Try PostgreSQL
        if self._try_postgres(config):
            return self._conn

        # Fallback to SQLite
        logger.warning("PostgreSQL unavailable, falling back to SQLite")
        if self._try_sqlite(config):
            return self._conn

        raise MigrationError("Could not connect to any database")

    def _load_config(self) -> Dict:
        """Load database configuration from quantum.config.yaml"""
        config_path = self.project_path / "quantum.config.yaml"
        if not config_path.exists():
            return {}

        try:
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
            return config.get('database', {})
        except Exception as e:
            logger.warning(f"Could not load config: {e}")
            return {}

    def _try_postgres(self, config: Dict) -> bool:
        """Try to connect to PostgreSQL"""
        try:
            import psycopg2

            # Get connection params from config or environment
            host = config.get('host') or os.environ.get('QUANTUM_DB_HOST', 'localhost')
            port = config.get('port') or os.environ.get('QUANTUM_DB_PORT', '5432')
            database = config.get('database') or os.environ.get('QUANTUM_DB_NAME', 'quantum')
            user = config.get('user') or os.environ.get('QUANTUM_DB_USER', 'postgres')
            password = config.get('password') or os.environ.get('QUANTUM_DB_PASSWORD', '')

            self._conn = psycopg2.connect(
                host=host,
                port=int(port),
                database=database,
                user=user,
                password=password,
                connect_timeout=5
            )
            self._db_type = 'postgres'
            logger.info(f"Connected to PostgreSQL at {host}:{port}/{database}")
            return True

        except ImportError:
            logger.debug("psycopg2 not installed")
            return False
        except Exception as e:
            logger.debug(f"PostgreSQL connection failed: {e}")
            return False

    def _try_sqlite(self, config: Dict) -> bool:
        """Try to connect to SQLite"""
        try:
            import sqlite3

            db_path = config.get('sqlite_path') or self.project_path / "data" / "quantum.db"
            db_path = Path(db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            self._conn = sqlite3.connect(str(db_path))
            self._db_type = 'sqlite'
            logger.info(f"Connected to SQLite at {db_path}")
            return True

        except Exception as e:
            logger.error(f"SQLite connection failed: {e}")
            return False

    @property
    def db_type(self) -> str:
        return self._db_type

    def execute(self, sql: str, params: tuple = None):
        """Execute SQL statement"""
        cursor = self._conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._conn:
            self._conn.close()


class MigrationRunner:
    """Runs database migrations"""

    MIGRATIONS_TABLE = "_migrations"

    def __init__(self, project_path: Path = None):
        self.project_path = project_path or Path.cwd()
        self.migrations_dir = self.project_path / "migrations"
        self.db = DatabaseConnection(self.project_path)

    def _ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        if self.db.db_type == 'postgres':
            sql = f"""
                CREATE TABLE IF NOT EXISTS {self.MIGRATIONS_TABLE} (
                    version VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    checksum VARCHAR(32) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        else:  # SQLite
            sql = f"""
                CREATE TABLE IF NOT EXISTS {self.MIGRATIONS_TABLE} (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
        self.db.execute(sql)
        self.db.commit()

    def _get_applied_migrations(self) -> Dict[str, Dict]:
        """Get list of already applied migrations"""
        cursor = self.db.execute(
            f"SELECT version, name, checksum, applied_at FROM {self.MIGRATIONS_TABLE} ORDER BY version"
        )
        rows = cursor.fetchall()
        return {
            row[0]: {
                'version': row[0],
                'name': row[1],
                'checksum': row[2],
                'applied_at': row[3]
            }
            for row in rows
        }

    def _get_pending_migrations(self) -> List[Migration]:
        """Get list of migrations that need to be applied"""
        if not self.migrations_dir.exists():
            return []

        applied = self._get_applied_migrations()
        pending = []

        for f in sorted(self.migrations_dir.glob("*.sql")):
            # Expected format: V001_create_users.sql
            parts = f.stem.split('_', 1)
            if len(parts) < 2:
                continue

            version = parts[0]
            name = parts[1]

            if version not in applied:
                pending.append(Migration(version, name, f))

        return pending

    def _record_migration(self, migration: Migration):
        """Record that a migration was applied"""
        if self.db.db_type == 'postgres':
            sql = f"""
                INSERT INTO {self.MIGRATIONS_TABLE} (version, name, checksum)
                VALUES (%s, %s, %s)
            """
        else:  # SQLite
            sql = f"""
                INSERT INTO {self.MIGRATIONS_TABLE} (version, name, checksum)
                VALUES (?, ?, ?)
            """
        self.db.execute(sql, (migration.version, migration.name, migration.checksum))

    def _remove_migration_record(self, version: str):
        """Remove migration record for rollback"""
        if self.db.db_type == 'postgres':
            self.db.execute(f"DELETE FROM {self.MIGRATIONS_TABLE} WHERE version = %s", (version,))
        else:
            self.db.execute(f"DELETE FROM {self.MIGRATIONS_TABLE} WHERE version = ?", (version,))

    def status(self) -> Dict:
        """Get migration status"""
        self.db.connect()
        self._ensure_migrations_table()

        applied = self._get_applied_migrations()
        pending = self._get_pending_migrations()

        self.db.close()

        return {
            'database_type': self.db.db_type,
            'applied': list(applied.values()),
            'pending': [{'version': m.version, 'name': m.name} for m in pending],
            'total_applied': len(applied),
            'total_pending': len(pending)
        }

    def up(self, count: int = None) -> List[Dict]:
        """Apply pending migrations"""
        self.db.connect()
        self._ensure_migrations_table()

        pending = self._get_pending_migrations()
        if count:
            pending = pending[:count]

        results = []

        for migration in pending:
            try:
                click.echo(f"Applying {migration.version}: {migration.name}...")

                # Execute migration SQL
                self.db.execute(migration.content)

                # Record migration
                self._record_migration(migration)
                self.db.commit()

                results.append({
                    'version': migration.version,
                    'name': migration.name,
                    'status': 'applied',
                    'checksum': migration.checksum
                })

                click.echo(f"  [OK] Applied {migration.version}")

            except Exception as e:
                self.db.rollback()
                results.append({
                    'version': migration.version,
                    'name': migration.name,
                    'status': 'failed',
                    'error': str(e)
                })
                click.echo(f"  [FAILED] {e}")
                break  # Stop on first failure

        self.db.close()
        return results

    def down(self, count: int = 1) -> List[Dict]:
        """Rollback migrations"""
        self.db.connect()
        self._ensure_migrations_table()

        applied = self._get_applied_migrations()
        if not applied:
            click.echo("No migrations to rollback")
            self.db.close()
            return []

        # Get migrations in reverse order
        versions = sorted(applied.keys(), reverse=True)[:count]
        results = []

        for version in versions:
            migration_info = applied[version]

            # Look for down migration file
            down_file = self.migrations_dir / f"{version}_{migration_info['name']}.down.sql"

            if not down_file.exists():
                click.echo(f"Warning: No down migration for {version}")
                results.append({
                    'version': version,
                    'status': 'skipped',
                    'reason': 'No down migration file'
                })
                continue

            try:
                click.echo(f"Rolling back {version}: {migration_info['name']}...")

                # Execute rollback SQL
                self.db.execute(down_file.read_text())

                # Remove migration record
                self._remove_migration_record(version)
                self.db.commit()

                results.append({
                    'version': version,
                    'name': migration_info['name'],
                    'status': 'rolled_back'
                })

                click.echo(f"  [OK] Rolled back {version}")

            except Exception as e:
                self.db.rollback()
                results.append({
                    'version': version,
                    'status': 'failed',
                    'error': str(e)
                })
                click.echo(f"  [FAILED] {e}")
                break

        self.db.close()
        return results

    def create(self, name: str) -> Path:
        """Create a new migration file"""
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

        # Get next version number
        existing = sorted(self.migrations_dir.glob("V*.sql"))
        if existing:
            last_version = existing[-1].stem.split('_')[0]
            next_num = int(last_version[1:]) + 1
        else:
            next_num = 1

        version = f"V{next_num:03d}"
        filename = f"{version}_{name}.sql"
        filepath = self.migrations_dir / filename

        # Create template
        template = f"""-- Migration: {name}
-- Version: {version}
-- Created: {datetime.now().isoformat()}

-- Write your SQL here

"""
        filepath.write_text(template)

        # Also create down file
        down_filepath = self.migrations_dir / f"{version}_{name}.down.sql"
        down_template = f"""-- Rollback Migration: {name}
-- Version: {version}

-- Write your rollback SQL here

"""
        down_filepath.write_text(down_template)

        return filepath


# CLI Commands

@click.group()
def migrate():
    """Database migration commands"""
    pass


@migrate.command()
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def status(as_json: bool):
    """Show migration status"""
    runner = MigrationRunner()

    try:
        result = runner.status()

        if as_json:
            import json
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            click.echo(f"\nDatabase: {result['database_type']}")
            click.echo(f"Applied migrations: {result['total_applied']}")
            click.echo(f"Pending migrations: {result['total_pending']}")

            if result['applied']:
                click.echo("\nApplied:")
                for m in result['applied']:
                    click.echo(f"  {m['version']}: {m['name']} (applied: {m['applied_at']})")

            if result['pending']:
                click.echo("\nPending:")
                for m in result['pending']:
                    click.echo(f"  {m['version']}: {m['name']}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@migrate.command()
@click.option('--count', '-n', type=int, help='Number of migrations to apply')
def up(count: Optional[int]):
    """Apply pending migrations"""
    runner = MigrationRunner()

    try:
        results = runner.up(count=count)

        applied = sum(1 for r in results if r.get('status') == 'applied')
        failed = sum(1 for r in results if r.get('status') == 'failed')

        click.echo(f"\nApplied: {applied}, Failed: {failed}")

        if failed:
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@migrate.command()
@click.option('--count', '-n', type=int, default=1, help='Number of migrations to rollback')
def down(count: int):
    """Rollback migrations"""
    runner = MigrationRunner()

    try:
        results = runner.down(count=count)

        rolled_back = sum(1 for r in results if r.get('status') == 'rolled_back')
        failed = sum(1 for r in results if r.get('status') == 'failed')

        click.echo(f"\nRolled back: {rolled_back}, Failed: {failed}")

        if failed:
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@migrate.command()
@click.argument('name')
def create(name: str):
    """Create a new migration"""
    runner = MigrationRunner()

    try:
        filepath = runner.create(name)
        click.echo(f"Created migration: {filepath}")
        click.echo(f"Also created rollback: {filepath.with_suffix('.down.sql')}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    migrate()
