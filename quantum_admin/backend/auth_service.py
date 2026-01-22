"""
Quantum Admin - Authentication & Authorization Service
JWT-based authentication with RBAC (Role-Based Access Control)
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

import jwt
import bcrypt
from pydantic import BaseModel, EmailStr, validator
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship, Session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# ============================================================================
# Configuration
# ============================================================================

SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ============================================================================
# Role Definitions
# ============================================================================

class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"

ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        "read:*", "write:*", "delete:*", "admin:*",
        "deploy:*", "manage:users", "manage:roles",
        "manage:environments", "manage:containers"
    ],
    UserRole.DEVELOPER: [
        "read:*", "write:datasources", "write:containers",
        "write:components", "deploy:staging", "deploy:development",
        "read:logs", "write:queries"
    ],
    UserRole.VIEWER: [
        "read:datasources", "read:containers", "read:components",
        "read:logs", "read:monitoring"
    ]
}

# ============================================================================
# Database Models
# ============================================================================

# Many-to-many relationship table
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('role_id', Integer, ForeignKey('roles.id'))
)

class User(Base):
    """User model"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role"""
        return any(r.name == role.value for r in self.roles)

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission"""
        if self.is_superuser:
            return True

        for role in self.roles:
            role_perms = ROLE_PERMISSIONS.get(UserRole(role.name), [])
            if permission in role_perms or "read:*" in role_perms or "write:*" in role_perms:
                return True
        return False


class Role(Base):
    """Role model"""
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")


class UserSession(Base):
    """User session model for tracking active sessions"""
    __tablename__ = 'user_sessions'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token_jti = Column(String, unique=True, index=True, nullable=False)
    refresh_token_jti = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    is_revoked = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="sessions")


# ============================================================================
# Pydantic Models
# ============================================================================

class UserCreate(BaseModel):
    """Schema for creating a new user"""
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    password: str
    roles: List[UserRole] = [UserRole.VIEWER]

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    roles: List[str]
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        orm_mode = True


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenPayload(BaseModel):
    """Schema for JWT token payload"""
    sub: str  # subject (user_id)
    jti: str  # JWT ID (unique token identifier)
    exp: int  # expiration time
    iat: int  # issued at
    type: str  # token type (access or refresh)
    roles: List[str]


# ============================================================================
# Authentication Service
# ============================================================================

class AuthService:
    """Authentication and authorization service"""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------------
    # Password Hashing
    # ------------------------------------------------------------------------

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    # ------------------------------------------------------------------------
    # User Management
    # ------------------------------------------------------------------------

    def create_user(self, user_create: UserCreate) -> User:
        """Create a new user"""
        # Check if user already exists
        existing_user = self.db.query(User).filter(
            (User.email == user_create.email) | (User.username == user_create.username)
        ).first()

        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")

        # Create user
        hashed_password = self.hash_password(user_create.password)
        user = User(
            email=user_create.email,
            username=user_create.username,
            full_name=user_create.full_name,
            hashed_password=hashed_password
        )

        # Assign roles
        for role_name in user_create.roles:
            role = self.db.query(Role).filter(Role.name == role_name.value).first()
            if not role:
                role = Role(name=role_name.value, description=f"{role_name.value.capitalize()} role")
                self.db.add(role)
            user.roles.append(role)

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user by username and password"""
        user = self.db.query(User).filter(User.username == username).first()

        if not user:
            return None

        if not self.verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            raise HTTPException(status_code=403, detail="User is inactive")

        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()

        return user

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()

    # ------------------------------------------------------------------------
    # Token Management
    # ------------------------------------------------------------------------

    def create_access_token(self, user: User, jti: Optional[str] = None) -> str:
        """Create JWT access token"""
        if jti is None:
            jti = secrets.token_urlsafe(32)

        now = datetime.utcnow()
        expires = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "sub": str(user.id),
            "jti": jti,
            "exp": int(expires.timestamp()),
            "iat": int(now.timestamp()),
            "type": "access",
            "roles": [role.name for role in user.roles]
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token

    def create_refresh_token(self, user: User, jti: Optional[str] = None) -> str:
        """Create JWT refresh token"""
        if jti is None:
            jti = secrets.token_urlsafe(32)

        now = datetime.utcnow()
        expires = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        payload = {
            "sub": str(user.id),
            "jti": jti,
            "exp": int(expires.timestamp()),
            "iat": int(now.timestamp()),
            "type": "refresh",
            "roles": [role.name for role in user.roles]
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token

    def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            token_data = TokenPayload(**payload)
            return token_data
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    def create_session(
        self,
        user: User,
        token_jti: str,
        refresh_token_jti: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserSession:
        """Create a new user session"""
        expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        session = UserSession(
            user_id=user.id,
            token_jti=token_jti,
            refresh_token_jti=refresh_token_jti,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def revoke_session(self, token_jti: str):
        """Revoke a user session"""
        session = self.db.query(UserSession).filter(
            UserSession.token_jti == token_jti
        ).first()

        if session:
            session.is_revoked = True
            self.db.commit()

    def is_session_valid(self, token_jti: str) -> bool:
        """Check if a session is valid"""
        session = self.db.query(UserSession).filter(
            UserSession.token_jti == token_jti
        ).first()

        if not session:
            return False

        if session.is_revoked:
            return False

        if datetime.utcnow() > session.expires_at:
            return False

        return True

    # ------------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------------

    def check_permission(self, user: User, permission: str) -> bool:
        """Check if user has a specific permission"""
        return user.has_permission(permission)

    def require_role(self, user: User, required_role: UserRole):
        """Require user to have a specific role"""
        if not user.has_role(required_role) and not user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail=f"User does not have required role: {required_role.value}"
            )


# ============================================================================
# FastAPI Dependencies
# ============================================================================

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = None  # Will be injected
) -> User:
    """Get current authenticated user"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database session not available")

    token = credentials.credentials
    auth_service = AuthService(db)

    # Verify token
    token_payload = auth_service.verify_token(token)

    # Check if session is valid
    if not auth_service.is_session_valid(token_payload.jti):
        raise HTTPException(status_code=401, detail="Session has been revoked")

    # Get user
    user = auth_service.get_user(int(token_payload.sub))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    return user


def require_role(role: UserRole):
    """Dependency to require a specific role"""
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if not user.has_role(role) and not user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {role.value}"
            )
        return user
    return role_checker


def require_permission(permission: str):
    """Dependency to require a specific permission"""
    def permission_checker(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {permission}"
            )
        return user
    return permission_checker


# ============================================================================
# Utility Functions
# ============================================================================

def init_default_roles(db: Session):
    """Initialize default roles if they don't exist"""
    for role in UserRole:
        existing_role = db.query(Role).filter(Role.name == role.value).first()
        if not existing_role:
            new_role = Role(
                name=role.value,
                description=f"{role.value.capitalize()} role with predefined permissions"
            )
            db.add(new_role)
    db.commit()


def create_default_admin(db: Session, username: str = "admin", password: str = "admin123"):
    """Create default admin user if no users exist"""
    user_count = db.query(User).count()
    if user_count == 0:
        auth_service = AuthService(db)
        admin_user = UserCreate(
            email="admin@quantum.local",
            username=username,
            full_name="System Administrator",
            password=password,
            roles=[UserRole.ADMIN]
        )
        user = auth_service.create_user(admin_user)
        user.is_superuser = True
        db.commit()
        return user
    return None
