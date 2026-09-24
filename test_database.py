"""
Quantum Test Database - Self-contained SQLite database for regression tests

Creates and manages a SQLite database with test data for query tests.
No external dependencies, runs entirely in-memory or as a file.
"""

import sqlite3
from pathlib import Path
from typing import Optional


class TestDatabase:
    """Manages test database for regression tests"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize test database

        Args:
            db_path: Path to SQLite database file. If None, uses in-memory database.
        """
        if db_path is None:
            db_path = str(Path(__file__).parent / "test_data" / "quantum_test.db")

        self.db_path = db_path
        self.conn = None

    def setup(self):
        """Create database and populate with test data"""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Remove old database if exists
        if Path(self.db_path).exists():
            Path(self.db_path).unlink()

        # Create new database
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()

        # Create users table
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create activity_log table
        cursor.execute("""
            CREATE TABLE activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Insert test users
        test_users = [
            ("Alice Johnson", "alice@example.com", "hash1", "active"),
            ("Bob Smith", "bob@example.com", "hash2", "active"),
            ("Charlie Brown", "charlie@example.com", "hash3", "active"),
            ("Diana Prince", "diana@example.com", "hash4", "pending"),
            ("Eve Anderson", "eve@example.com", "hash5", "active"),
            ("Frank Castle", "frank@example.com", "hash6", "inactive"),
            ("Grace Hopper", "grace@example.com", "hash7", "active"),
            ("Henry Ford", "henry@example.com", "hash8", "active"),
            ("Iris West", "iris@example.com", "hash9", "active"),
            ("Jack Ryan", "jack@example.com", "hash10", "pending"),
        ]

        cursor.executemany(
            "INSERT INTO users (name, email, password_hash, status) VALUES (?, ?, ?, ?)",
            test_users
        )

        # Insert activity log entries
        activities = [
            (1, "login"),
            (1, "view_profile"),
            (2, "login"),
            (2, "update_settings"),
            (3, "login"),
            (3, "create_post"),
            (4, "login"),
            (5, "login"),
            (5, "logout"),
        ]

        cursor.executemany(
            "INSERT INTO activity_log (user_id, action) VALUES (?, ?)",
            activities
        )

        self.conn.commit()
        cursor.close()

        print(f"[OK] Test database created: {self.db_path}")
        print(f"   - {len(test_users)} test users")
        print(f"   - {len(activities)} activity log entries")

    def get_config(self) -> dict:
        """Get datasource configuration for this test database"""
        return {
            "name": "test-sqlite",
            "type": "sqlite",
            "database": self.db_path,
            "status": "ready"
        }

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None


if __name__ == '__main__':
    """Run this script to create/recreate the test database"""
    db = TestDatabase()
    db.setup()
    db.close()
    print("\n[OK] Test database ready for regression tests!")
