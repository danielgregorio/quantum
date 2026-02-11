"""
Database configuration and session management
"""
import os
from datetime import datetime
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
    import uuid

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

        # Create sample connectors (id is String, required)
        connectors = [
            models.Connector(
                id="postgres-prod",
                name="PostgreSQL Production",
                type="database",
                provider="postgres",
                host="db.example.com",
                port=5432,
                database="production",
                status="connected"
            ),
            models.Connector(
                id="redis-cache",
                name="Redis Cache",
                type="cache",
                provider="redis",
                host="redis.example.com",
                port=6379,
                status="connected"
            ),
            models.Connector(
                id="s3-storage",
                name="AWS S3 Storage",
                type="storage",
                provider="s3",
                database="my-app-files",
                status="disconnected"
            ),
        ]
        for c in connectors:
            db.add(c)

        # Create sample environments for first project
        environments = [
            models.Environment(
                name="dev",
                display_name="Development",
                project_id=1,
                order=1,
                branch="develop",
                is_active=True
            ),
            models.Environment(
                name="staging",
                display_name="Staging",
                project_id=1,
                order=2,
                branch="staging",
                is_active=True
            ),
            models.Environment(
                name="production",
                display_name="Production",
                project_id=1,
                order=3,
                branch="main",
                requires_approval=True,
                is_active=True
            ),
        ]
        for e in environments:
            db.add(e)

        # Create sample application logs
        from datetime import timedelta
        sample_logs = [
            models.ApplicationLog(
                project_id=1,
                timestamp=datetime.utcnow() - timedelta(minutes=5),
                level="INFO",
                source="app",
                message="Application started successfully",
                component_name="main"
            ),
            models.ApplicationLog(
                project_id=1,
                timestamp=datetime.utcnow() - timedelta(minutes=4),
                level="INFO",
                source="database",
                message="Database connection established",
                response_time_ms=45
            ),
            models.ApplicationLog(
                project_id=1,
                timestamp=datetime.utcnow() - timedelta(minutes=3),
                level="INFO",
                source="access",
                message="GET /api/posts 200",
                request_method="GET",
                request_path="/api/posts",
                response_status=200,
                response_time_ms=120
            ),
            models.ApplicationLog(
                project_id=1,
                timestamp=datetime.utcnow() - timedelta(minutes=2),
                level="WARNING",
                source="api",
                message="External API rate limit approaching",
                component_name="oauth_service"
            ),
            models.ApplicationLog(
                project_id=1,
                timestamp=datetime.utcnow() - timedelta(minutes=1),
                level="INFO",
                source="security",
                message="User login successful: admin@example.com",
                component_name="auth"
            ),
            models.ApplicationLog(
                project_id=1,
                timestamp=datetime.utcnow(),
                level="INFO",
                source="deploy",
                message="Deployment completed: v1.2.3",
                component_name="deployer"
            ),
        ]
        for log in sample_logs:
            db.add(log)

        db.commit()
        print("[OK] Database seeded with sample data")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to seed database: {e}")
        import traceback
        traceback.print_exc()
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
