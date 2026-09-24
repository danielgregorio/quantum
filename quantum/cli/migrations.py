"""
Database migrations: applies migrations/*.sql to a datasource declared in
quantum.config.yaml (DB-6). `quantum migrate` (cli/runner.py) drives it.
"""
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


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
            self._content = self.path.read_text(encoding="utf-8")  # DB-8: never the system encoding
        return self._content

    @property
    def checksum(self) -> str:
        return hashlib.md5(self.content.encode()).hexdigest()

    def __repr__(self):
        return f"<Migration {self.version}: {self.name}>"


class DatabaseConnection:
    """Connection to the datasource the migrations are for (DB-6).

    It used to read a separate `database:` section that nothing else uses and,
    without one, try a PostgreSQL at localhost/quantum with user postgres before
    falling back to ./data/quantum.db. A project whose pages query
    datasources.db (./data/app.db) had its migrations applied to a different
    file — or to whatever local PostgreSQL answered.
    """

    def __init__(self, project_path: Path = None, datasource: str = None):
        self.project_path = project_path or Path.cwd()
        self.datasource = datasource
        self._conn = None
        self._db_type = None

    def connect(self) -> Any:
        name, config = self._datasource_config()
        driver = str(config.get('driver', '')).lower()
        if driver == 'sqlite':
            import sqlite3
            path = Path(config.get('database') or '')
            if not config.get('database'):
                raise MigrationError(f"datasource '{name}' (sqlite) has no database: path")
            if not path.is_absolute():
                path = self.project_path / path
            path.parent.mkdir(parents=True, exist_ok=True)
            # isolation_level=None: execute_script opens the transaction
            # itself, so a CREATE TABLE is inside it too (DB-8).
            self._conn = sqlite3.connect(str(path), isolation_level=None)
            self._db_type = 'sqlite'
            logger.info("Migrating datasource %s (SQLite at %s)", name, path)
            return self._conn
        if driver in ('postgres', 'postgresql'):
            try:
                import psycopg2
            except ImportError as exc:
                raise MigrationError("datasource '%s' is PostgreSQL: pip install psycopg2-binary" % name) from exc
            self._conn = psycopg2.connect(
                host=config.get('host', 'localhost'), port=int(config.get('port', 5432)),
                dbname=config.get('database'), user=config.get('username') or config.get('user'),
                password=config.get('password', ''), connect_timeout=5)
            self._db_type = 'postgres'
            logger.info("Migrating datasource %s (PostgreSQL %s)", name, config.get('database'))
            return self._conn
        raise MigrationError(f"datasource '{name}': driver {driver!r} is not supported by quantum migrate "
                             f"(use sqlite or postgres)")

    def _datasource_config(self):
        config_path = self.project_path / "quantum.config.yaml"
        datasources = {}
        if config_path.exists():
            import yaml
            from quantum.core.config_env import expand_env
            with open(config_path, encoding='utf-8') as f:
                datasources = (expand_env(yaml.safe_load(f) or {}).get('datasources') or {})
        if not datasources:
            raise MigrationError(
                "quantum.config.yaml declares no datasources. Add one, for example:\n"
                "  datasources:\n    db:\n      driver: sqlite\n      database: ./data/app.db")
        if self.datasource:
            if self.datasource not in datasources:
                raise MigrationError(f"no datasource '{self.datasource}'; declared: {', '.join(datasources)}")
            return self.datasource, datasources[self.datasource]
        if len(datasources) > 1:
            raise MigrationError(f"several datasources are declared ({', '.join(datasources)}); "
                                 f"choose one with --datasource")
        name = next(iter(datasources))
        return name, datasources[name]

    def _ensure_connected(self):
        if self._conn is None:
            self.connect()

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

    def execute_script(self, sql: str):
        """Run a whole migration file, in one transaction (DB-8).

        sqlite3's execute() takes ONE statement, so every migration with more
        than one — a table and its index — failed with "You can only execute
        one statement at a time". The statements are split here and run
        inside an explicit BEGIN, which commit()/rollback() close: a failure
        halfway leaves no table behind.
        """
        if self._db_type != 'sqlite':
            return self.execute(sql)
        import sqlite3
        cursor = self._conn.cursor()
        if not self._conn.in_transaction:
            cursor.execute('BEGIN')
        chunk = ''
        for line in sql.splitlines(keepends=True):
            chunk += line
            if sqlite3.complete_statement(chunk):
                if chunk.strip():
                    cursor.execute(chunk)
                chunk = ''
        if chunk.strip() and not all(l.strip().startswith('--') or not l.strip() for l in chunk.splitlines()):
            raise MigrationError(f"incomplete SQL statement at the end: {chunk.strip()[:80]!r}")
        return cursor

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._conn:
            self._conn.close()


def _paths_migrations(project_path: Path) -> str:
    """CFG-3: paths.migrations in quantum.config.yaml (default ./migrations)."""
    try:
        import yaml
        from quantum.core.config_env import expand_env
        with open(project_path / "quantum.config.yaml", encoding="utf-8") as f:
            config = expand_env(yaml.safe_load(f) or {})
        return (config.get("paths") or {}).get("migrations") or "migrations"
    except (OSError, ValueError, AttributeError):
        return "migrations"


class MigrationRunner:
    """Runs database migrations"""

    MIGRATIONS_TABLE = "_migrations"

    def __init__(self, project_path: Path = None, datasource: str = None):
        self.project_path = project_path or Path.cwd()
        self.migrations_dir = self.project_path / _paths_migrations(self.project_path)
        self.db = DatabaseConnection(self.project_path, datasource)

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
            # `create` writes a PAIR: V001_name.sql and V001_name.down.sql.
            # This glob used to pick up both, and the rollback file sorted
            # FIRST ('.down.sql' < '.sql'), so `migrate up` executed the
            # rollback — DROP TABLE and all — before the migration it belongs
            # to, and then recorded the version as applied. On an already
            # migrated database that is data destruction from a command whose
            # entire job is to move forward. Reproduced before fixing.
            if f.name.endswith('.down.sql'):
                continue

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
                print(f"Applying {migration.version}: {migration.name}...")

                # Execute migration SQL
                self.db.execute_script(migration.content)

                # Record migration
                self._record_migration(migration)
                self.db.commit()

                results.append({
                    'version': migration.version,
                    'name': migration.name,
                    'status': 'applied',
                    'checksum': migration.checksum
                })

                print(f"  [OK] Applied {migration.version}")

            except Exception as e:
                self.db.rollback()
                results.append({
                    'version': migration.version,
                    'name': migration.name,
                    'status': 'failed',
                    'error': str(e)
                })
                print(f"  [FAILED] {e}")
                break  # Stop on first failure

        self.db.close()
        return results

    def down(self, count: int = 1) -> List[Dict]:
        """Rollback migrations"""
        self.db.connect()
        self._ensure_migrations_table()

        applied = self._get_applied_migrations()
        if not applied:
            print("No migrations to rollback")
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
                print(f"Warning: No down migration for {version}")
                results.append({
                    'version': version,
                    'status': 'skipped',
                    'reason': 'No down migration file'
                })
                continue

            try:
                print(f"Rolling back {version}: {migration_info['name']}...")

                # Execute rollback SQL
                self.db.execute_script(down_file.read_text(encoding="utf-8"))

                # Remove migration record
                self._remove_migration_record(version)
                self.db.commit()

                results.append({
                    'version': version,
                    'name': migration_info['name'],
                    'status': 'rolled_back'
                })

                print(f"  [OK] Rolled back {version}")

            except Exception as e:
                self.db.rollback()
                results.append({
                    'version': version,
                    'status': 'failed',
                    'error': str(e)
                })
                print(f"  [FAILED] {e}")
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
