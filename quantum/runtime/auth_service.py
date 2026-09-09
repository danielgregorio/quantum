"""
Phase G: Authentication & Security Service

Provides password hashing, authentication, and RBAC functionality.
"""

import bcrypt
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


class AuthService:
    """Authentication and security service for Quantum framework"""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt

        Args:
            password: Plain text password

        Returns:
            Hashed password (bcrypt hash)
        """
        if not password:
            raise ValueError("Password cannot be empty")

        # Generate salt and hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)

        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify a password against a bcrypt hash

        Args:
            password: Plain text password to verify
            hashed: Bcrypt hash to check against

        Returns:
            True if password matches, False otherwise
        """
        if not password or not hashed:
            return False

        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False

    @staticmethod
    def is_authenticated(session_data: Dict[str, Any]) -> bool:
        """
        Check if user is authenticated based on session data

        Args:
            session_data: Session dictionary

        Returns:
            True if authenticated, False otherwise
        """
        return AuthService._is_true(session_data.get('authenticated'))

    # The set of values that count as "yes". Deliberately CLOSED: anything not
    # listed is false, so this stays fail-closed. In particular '' , None, 0,
    # 'false', 'no' and any unrecognised string are NOT authenticated.
    _TRUTHY = frozenset({'true', '1', 'yes', 'on'})

    @staticmethod
    def _is_true(value: Any) -> bool:
        """Whether a session flag means yes.

        This used to be `value is True`, requiring the Python boolean. But a
        .q attribute is a string: the framework's own components/login.q line
        19 writes

            <q:set name="session.authenticated" value="true" />

        which stores the STRING "true" unless the author remembered
        type="boolean". "true" is not True, so is_authenticated returned False
        for a user who had just logged in successfully, and require_auth
        bounced them back to /login forever.

        Same root cause as the q:set arithmetic bug: the engine stores strings
        and the consumer demanded a strict type. Accepting the written forms
        fixes the login without widening what counts as authenticated —
        the list is closed and everything else is false.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in AuthService._TRUTHY
        return value is True

    @staticmethod
    def get_user_id(session_data: Dict[str, Any]) -> Optional[int]:
        """
        Get authenticated user ID from session

        Args:
            session_data: Session dictionary

        Returns:
            User ID if authenticated, None otherwise
        """
        if not AuthService.is_authenticated(session_data):
            return None

        return session_data.get('userId')

    @staticmethod
    def get_user_role(session_data: Dict[str, Any]) -> Optional[str]:
        """
        Get authenticated user role from session

        Args:
            session_data: Session dictionary

        Returns:
            User role if authenticated, None otherwise
        """
        if not AuthService.is_authenticated(session_data):
            return None

        return session_data.get('userRole')

    @staticmethod
    def has_permission(session_data: Dict[str, Any], required_permission: str) -> bool:
        """
        Check if user has a specific permission

        Args:
            session_data: Session dictionary
            required_permission: Permission to check (e.g., "admin", "user", "editor")

        Returns:
            True if user has permission, False otherwise
        """
        if not AuthService.is_authenticated(session_data):
            return False

        user_permissions = session_data.get('permissions', [])

        # If permissions is a string, convert to list
        if isinstance(user_permissions, str):
            user_permissions = [user_permissions]

        return required_permission in user_permissions

    @staticmethod
    def has_role(session_data: Dict[str, Any], required_role: str) -> bool:
        """
        Check if user has a specific role

        Args:
            session_data: Session dictionary
            required_role: Role to check (e.g., "admin", "user", "editor")

        Returns:
            True if user has role, False otherwise
        """
        if not AuthService.is_authenticated(session_data):
            return False

        user_role = session_data.get('userRole', '')

        # Support multiple roles separated by comma
        if ',' in required_role:
            required_roles = [r.strip() for r in required_role.split(',')]
            return user_role in required_roles

        return user_role == required_role

    @staticmethod
    def login(session_data: Dict[str, Any], user_id: int, user_name: str,
              user_role: str = "user", permissions: List[str] = None,
              remember_me: bool = False) -> Dict[str, Any]:
        """
        Login user and set session data

        Args:
            session_data: Session dictionary to update
            user_id: User ID
            user_name: User name
            user_role: User role (default: "user")
            permissions: List of permissions (optional)
            remember_me: Whether to remember user (extended session)

        Returns:
            Updated session data
        """
        session_data['authenticated'] = True
        session_data['userId'] = user_id
        session_data['userName'] = user_name
        session_data['userRole'] = user_role
        session_data['loginTime'] = datetime.now().isoformat()

        if permissions:
            session_data['permissions'] = permissions

        if remember_me:
            # Set extended session expiry (30 days)
            session_data['rememberMe'] = True
            session_data['sessionExpiry'] = (datetime.now() + timedelta(days=30)).isoformat()
        else:
            # Default session expiry (24 hours)
            session_data['sessionExpiry'] = (datetime.now() + timedelta(hours=24)).isoformat()

        return session_data

    @staticmethod
    def logout(session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Logout user and clear session data

        Args:
            session_data: Session dictionary to clear

        Returns:
            Cleared session data
        """
        # Clear all authentication-related session data
        keys_to_remove = [
            'authenticated', 'userId', 'userName', 'userRole',
            'loginTime', 'permissions', 'rememberMe', 'sessionExpiry'
        ]

        for key in keys_to_remove:
            session_data.pop(key, None)

        session_data['logoutTime'] = datetime.now().isoformat()

        return session_data

    @staticmethod
    def is_session_expired(session_data: Dict[str, Any]) -> bool:
        """
        Check if session has expired

        Args:
            session_data: Session dictionary

        Returns:
            True if session expired, False otherwise
        """
        if not AuthService.is_authenticated(session_data):
            return True

        expiry_str = session_data.get('sessionExpiry')
        if not expiry_str:
            # No expiry set - consider expired for safety
            return True

        try:
            expiry_time = datetime.fromisoformat(expiry_str)
            return datetime.now() > expiry_time
        except Exception:
            return True


class AuthorizationError(Exception):
    """Raised when user is not authorized to access a resource"""
    pass
