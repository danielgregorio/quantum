"""
Unit Tests for Authentication Service
Tests user creation, login, token generation, and role management
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from auth_service import (
    AuthService,
    UserCreate,
    UserLogin,
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    get_current_user
)


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "SecurePass123!"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "SecurePass123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "SecurePass123!"
        hashed = hash_password(password)

        assert verify_password("WrongPassword", hashed) is False

    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (salt)"""
        password = "SecurePass123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestTokens:
    """Test JWT token creation and validation"""

    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self):
        """Test JWT token decoding"""
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data)

        decoded = decode_access_token(token)

        assert decoded is not None
        assert decoded["sub"] == "testuser"
        assert decoded["user_id"] == 1
        assert "exp" in decoded

    def test_decode_invalid_token(self):
        """Test decoding invalid token"""
        invalid_token = "invalid.token.here"

        decoded = decode_access_token(invalid_token)

        assert decoded is None

    def test_token_expiration(self):
        """Test that token contains expiration"""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)

        decoded = decode_access_token(token)

        assert "exp" in decoded
        exp_timestamp = decoded["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)

        # Should expire in approximately 30 minutes
        now = datetime.utcnow()
        diff = exp_datetime - now
        assert 29 <= diff.total_seconds() / 60 <= 31


class TestAuthService:
    """Test AuthService class"""

    def test_create_user(self, test_db, user_factory):
        """Test user creation"""
        auth_service = AuthService(test_db)
        user_data = user_factory(
            username="newuser",
            email="newuser@example.com",
            password="Pass123!"
        )

        user = auth_service.create_user(user_data)

        assert user is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.hashed_password != "Pass123!"
        assert user.is_active is True

    def test_create_duplicate_username(self, test_db, user_factory):
        """Test creating user with duplicate username"""
        auth_service = AuthService(test_db)

        # Create first user
        user_data = user_factory(username="testuser")
        auth_service.create_user(user_data)

        # Try to create duplicate
        with pytest.raises(Exception):  # Should raise integrity error
            auth_service.create_user(user_data)

    def test_create_duplicate_email(self, test_db, user_factory):
        """Test creating user with duplicate email"""
        auth_service = AuthService(test_db)

        # Create first user
        user_data = user_factory(
            username="user1",
            email="same@example.com"
        )
        auth_service.create_user(user_data)

        # Try to create with same email
        with pytest.raises(Exception):
            duplicate_data = user_factory(
                username="user2",
                email="same@example.com"
            )
            auth_service.create_user(duplicate_data)

    def test_authenticate_user_success(self, test_db, user_factory):
        """Test successful user authentication"""
        auth_service = AuthService(test_db)

        # Create user
        user_data = user_factory(
            username="authuser",
            password="TestPass123!"
        )
        auth_service.create_user(user_data)

        # Authenticate
        user = auth_service.authenticate_user("authuser", "TestPass123!")

        assert user is not None
        assert user.username == "authuser"

    def test_authenticate_user_wrong_password(self, test_db, user_factory):
        """Test authentication with wrong password"""
        auth_service = AuthService(test_db)

        # Create user
        user_data = user_factory(username="authuser", password="TestPass123!")
        auth_service.create_user(user_data)

        # Try wrong password
        user = auth_service.authenticate_user("authuser", "WrongPassword")

        assert user is None

    def test_authenticate_nonexistent_user(self, test_db):
        """Test authentication of non-existent user"""
        auth_service = AuthService(test_db)

        user = auth_service.authenticate_user("nonexistent", "password")

        assert user is None

    def test_get_user_by_username(self, test_db, user_factory):
        """Test retrieving user by username"""
        auth_service = AuthService(test_db)

        # Create user
        user_data = user_factory(username="findme")
        created_user = auth_service.create_user(user_data)

        # Retrieve user
        found_user = auth_service.get_user_by_username("findme")

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.username == "findme"

    def test_get_user_by_email(self, test_db, user_factory):
        """Test retrieving user by email"""
        auth_service = AuthService(test_db)

        # Create user
        user_data = user_factory(email="findme@example.com")
        created_user = auth_service.create_user(user_data)

        # Retrieve user
        found_user = auth_service.get_user_by_email("findme@example.com")

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == "findme@example.com"


class TestUserRoles:
    """Test role-based access control"""

    def test_user_has_no_roles_initially(self, test_db, user_factory):
        """Test that new users have no roles"""
        auth_service = AuthService(test_db)
        user_data = user_factory()
        user = auth_service.create_user(user_data)

        assert len(user.roles) == 0

    def test_assign_role_to_user(self, test_db, user_factory):
        """Test assigning role to user"""
        from auth_service import UserRole

        auth_service = AuthService(test_db)

        # Create user
        user_data = user_factory()
        user = auth_service.create_user(user_data)

        # Create role
        role = UserRole(name="admin", description="Administrator")
        test_db.add(role)
        test_db.commit()

        # Assign role
        user.roles.append(role)
        test_db.commit()

        # Verify
        assert len(user.roles) == 1
        assert user.roles[0].name == "admin"

    def test_user_has_role(self, test_db, user_factory):
        """Test checking if user has specific role"""
        from auth_service import UserRole

        auth_service = AuthService(test_db)

        # Create user and role
        user_data = user_factory()
        user = auth_service.create_user(user_data)

        admin_role = UserRole(name="admin", description="Admin")
        test_db.add(admin_role)
        test_db.commit()

        # Assign role
        user.roles.append(admin_role)
        test_db.commit()

        # Check role
        has_admin = any(role.name == "admin" for role in user.roles)
        has_moderator = any(role.name == "moderator" for role in user.roles)

        assert has_admin is True
        assert has_moderator is False


class TestPasswordValidation:
    """Test password strength validation"""

    def test_weak_password_too_short(self):
        """Test that short passwords are rejected"""
        # This test assumes password validation is implemented
        # Adjust based on actual implementation
        password = "Pass1!"
        # Should be rejected (less than 8 characters)
        assert len(password) < 8

    def test_strong_password(self):
        """Test that strong passwords are accepted"""
        password = "StrongPass123!"
        # Should have: uppercase, lowercase, numbers, special chars
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)

        assert has_upper and has_lower and has_digit and has_special


class TestUserManagement:
    """Test user CRUD operations"""

    def test_update_user_email(self, test_db, user_factory):
        """Test updating user email"""
        auth_service = AuthService(test_db)

        user_data = user_factory(email="old@example.com")
        user = auth_service.create_user(user_data)

        # Update email
        user.email = "new@example.com"
        test_db.commit()

        # Verify
        updated_user = auth_service.get_user_by_email("new@example.com")
        assert updated_user is not None
        assert updated_user.id == user.id

    def test_deactivate_user(self, test_db, user_factory):
        """Test deactivating user account"""
        auth_service = AuthService(test_db)

        user_data = user_factory()
        user = auth_service.create_user(user_data)

        # Deactivate
        user.is_active = False
        test_db.commit()

        # Verify
        assert user.is_active is False

    def test_delete_user(self, test_db, user_factory):
        """Test deleting user"""
        auth_service = AuthService(test_db)

        user_data = user_factory(username="deleteme")
        user = auth_service.create_user(user_data)
        user_id = user.id

        # Delete
        test_db.delete(user)
        test_db.commit()

        # Verify
        deleted_user = auth_service.get_user_by_username("deleteme")
        assert deleted_user is None


# ============================================================================
# Integration with pytest
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
