"""
Auth Service for Quantum Admin
JWT-based authentication with bcrypt password hashing
"""
import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import JWT library
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("PyJWT not installed. Run: pip install PyJWT")

# Try to import bcrypt
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logger.warning("bcrypt not installed. Run: pip install bcrypt")


@dataclass
class User:
    id: int
    username: str
    role: str = "user"  # user, admin


@dataclass
class TokenPayload:
    user_id: int
    username: str
    role: str
    exp: datetime
    iat: datetime


class AuthService:
    """JWT authentication service with bcrypt password hashing"""

    # Default admin credentials (should be changed in production)
    DEFAULT_USERS = {
        "admin": {
            "id": 1,
            "password_hash": None,  # Will be set on first run
            "role": "admin"
        }
    }

    def __init__(self, secret_key: str = None, expiry_hours: int = 24):
        """
        Initialize auth service

        Args:
            secret_key: JWT secret key (uses env var or generates one)
            expiry_hours: Token expiry in hours
        """
        self.secret_key = secret_key or os.environ.get(
            "JWT_SECRET_KEY",
            "quantum-admin-secret-change-in-production"
        )
        self.expiry_hours = expiry_hours
        self.algorithm = "HS256"

        # In-memory user store (in production, use database)
        self._users = self.DEFAULT_USERS.copy()

        # Set default admin password if not set
        if self._users["admin"]["password_hash"] is None:
            default_password = os.environ.get("ADMIN_PASSWORD", "admin")
            self._users["admin"]["password_hash"] = self._hash_password(default_password)
            logger.warning(
                "Using default admin password. Set ADMIN_PASSWORD env var in production!"
            )

    def _hash_password(self, password: str) -> str:
        """Hash a password with bcrypt (secure, with salt)"""
        if not BCRYPT_AVAILABLE:
            # Fallback to less secure method if bcrypt not installed
            import hashlib
            logger.warning("Using SHA-256 fallback - install bcrypt for production!")
            return "sha256:" + hashlib.sha256(password.encode()).hexdigest()

        # bcrypt automatically generates a salt and includes it in the hash
        salt = bcrypt.gensalt(rounds=12)  # Cost factor of 12 is secure and fast enough
        password_bytes = password.encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, salt)
        return "bcrypt:" + hashed.decode('utf-8')

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        if password_hash.startswith("bcrypt:"):
            if not BCRYPT_AVAILABLE:
                logger.error("bcrypt required to verify password but not installed")
                return False
            stored_hash = password_hash[7:].encode('utf-8')  # Remove "bcrypt:" prefix
            password_bytes = password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, stored_hash)
        elif password_hash.startswith("sha256:"):
            # Legacy SHA-256 support (for migration)
            import hashlib
            stored_hash = password_hash[7:]  # Remove "sha256:" prefix
            return hashlib.sha256(password.encode()).hexdigest() == stored_hash
        else:
            # Very old format without prefix (assume SHA-256)
            import hashlib
            return hashlib.sha256(password.encode()).hexdigest() == password_hash

    # =========================================================================
    # Authentication
    # =========================================================================

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user and return tokens

        Args:
            username: Username
            password: Plain text password

        Returns:
            Dict with access_token and user info, or None if invalid
        """
        if not JWT_AVAILABLE:
            logger.error("PyJWT not available")
            return None

        user_data = self._users.get(username)
        if not user_data:
            logger.warning(f"Authentication failed: user '{username}' not found")
            return None

        if not self._verify_password(password, user_data["password_hash"]):
            logger.warning(f"Authentication failed: invalid password for '{username}'")
            return None

        # Migrate old SHA-256 passwords to bcrypt on successful login
        if BCRYPT_AVAILABLE and not user_data["password_hash"].startswith("bcrypt:"):
            logger.info(f"Migrating password hash to bcrypt for user '{username}'")
            user_data["password_hash"] = self._hash_password(password)

        # Generate token
        user = User(
            id=user_data["id"],
            username=username,
            role=user_data["role"]
        )

        token = self._create_token(user)

        logger.info(f"User '{username}' authenticated successfully")
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": self.expiry_hours * 3600,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role
            }
        }

    def _create_token(self, user: User) -> str:
        """Create JWT token for user"""
        now = datetime.utcnow()
        payload = {
            "sub": str(user.id),  # JWT sub claim must be a string
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "iat": now,
            "exp": now + timedelta(hours=self.expiry_hours)
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """
        Verify JWT token and return payload

        Args:
            token: JWT token string

        Returns:
            TokenPayload or None if invalid
        """
        if not JWT_AVAILABLE:
            return None

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return TokenPayload(
                user_id=payload.get("user_id", int(payload["sub"])),
                username=payload["username"],
                role=payload["role"],
                exp=datetime.fromtimestamp(payload["exp"]),
                iat=datetime.fromtimestamp(payload["iat"])
            )
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def get_current_user(self, token: str) -> Optional[User]:
        """Get current user from token"""
        payload = self.verify_token(token)
        if not payload:
            return None

        return User(
            id=payload.user_id,
            username=payload.username,
            role=payload.role
        )

    # =========================================================================
    # User Management
    # =========================================================================

    def create_user(
        self,
        username: str,
        password: str,
        role: str = "user"
    ) -> Optional[User]:
        """Create a new user"""
        if username in self._users:
            logger.error(f"User '{username}' already exists")
            return None

        user_id = max(u["id"] for u in self._users.values()) + 1

        self._users[username] = {
            "id": user_id,
            "password_hash": self._hash_password(password),
            "role": role
        }

        logger.info(f"User '{username}' created with role '{role}'")
        return User(id=user_id, username=username, role=role)

    def change_password(self, username: str, new_password: str) -> bool:
        """Change user password"""
        if username not in self._users:
            return False

        self._users[username]["password_hash"] = self._hash_password(new_password)
        logger.info(f"Password changed for user '{username}'")
        return True

    def delete_user(self, username: str) -> bool:
        """Delete a user"""
        if username not in self._users:
            return False

        if username == "admin":
            logger.error("Cannot delete admin user")
            return False

        del self._users[username]
        logger.info(f"User '{username}' deleted")
        return True

    def list_users(self) -> list:
        """List all users (without passwords)"""
        return [
            {"id": data["id"], "username": username, "role": data["role"]}
            for username, data in self._users.items()
        ]

    # =========================================================================
    # Role Checking
    # =========================================================================

    def require_role(self, token: str, required_role: str) -> bool:
        """Check if token has required role"""
        payload = self.verify_token(token)
        if not payload:
            return False

        # Admin has access to everything
        if payload.role == "admin":
            return True

        return payload.role == required_role

    def is_admin(self, token: str) -> bool:
        """Check if token belongs to admin"""
        return self.require_role(token, "admin")


# Singleton instance
_auth_service = None


def get_auth_service() -> AuthService:
    """Get singleton instance of AuthService"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
