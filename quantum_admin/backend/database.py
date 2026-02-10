"""
Database configuration and session management
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

# SQLite database file location - use absolute path relative to quantum_admin folder
_QUANTUM_ADMIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_QUANTUM_ADMIN_DIR, "quantum_admin.db")
DATABASE_URL = f"sqlite:///{_DB_PATH}"

# Create engine with SQLite-specific settings
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=False  # Set to True for SQL query logging during development
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize database - create all tables
    Call this on application startup
    """
    Base.metadata.create_all(bind=engine)
    print("[OK] Database initialized successfully")


def seed_db():
    """
    Seed database with sample data if empty
    """
    from . import models

    db = SessionLocal()
    try:
        # Check if we already have data
        existing_projects = db.query(models.Project).first()
        if existing_projects:
            print("[OK] Database already has data, skipping seed")
            return

        print("[INFO] Seeding database with sample data...")

        # Create sample projects
        projects = [
            models.Project(
                name="Blog Application",
                description="A full-featured blog with posts, comments, and user authentication",
                status="active"
            ),
            models.Project(
                name="E-Commerce API",
                description="REST API for an e-commerce platform with products, orders, and payments",
                status="active"
            ),
            models.Project(
                name="Dashboard App",
                description="Real-time analytics dashboard with charts and data visualization",
                status="inactive"
            ),
        ]
        for p in projects:
            db.add(p)
        db.flush()

        # Create sample connectors
        connectors = [
            models.Connector(
                name="PostgreSQL Production",
                connector_type="database",
                config={"host": "db.example.com", "port": 5432, "database": "production"},
                status="connected"
            ),
            models.Connector(
                name="Redis Cache",
                connector_type="cache",
                config={"host": "redis.example.com", "port": 6379},
                status="connected"
            ),
            models.Connector(
                name="AWS S3 Storage",
                connector_type="storage",
                config={"bucket": "my-app-files", "region": "us-east-1"},
                status="disconnected"
            ),
        ]
        for c in connectors:
            db.add(c)

        # Create sample environments for first project
        environments = [
            models.Environment(
                name="Development",
                env_type="development",
                project_id=1,
                config={"debug": True, "log_level": "DEBUG"},
                status="active"
            ),
            models.Environment(
                name="Staging",
                env_type="staging",
                project_id=1,
                config={"debug": False, "log_level": "INFO"},
                status="active"
            ),
            models.Environment(
                name="Production",
                env_type="production",
                project_id=1,
                config={"debug": False, "log_level": "WARNING"},
                status="inactive"
            ),
        ]
        for e in environments:
            db.add(e)

        # Create sample jobs
        jobs = [
            models.Job(
                name="Daily Backup",
                job_type="backup",
                schedule="0 2 * * *",
                status="active",
                config={"target": "s3://backups/daily"}
            ),
            models.Job(
                name="Health Check",
                job_type="health",
                schedule="*/5 * * * *",
                status="active",
                config={"endpoints": ["/health", "/api/status"]}
            ),
        ]
        for j in jobs:
            db.add(j)

        db.commit()
        print("[OK] Database seeded with sample data")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to seed database: {e}")
    finally:
        db.close()


def get_db():
    """
    Dependency for FastAPI endpoints
    Provides a database session and ensures cleanup

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
