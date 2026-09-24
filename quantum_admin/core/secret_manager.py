"""
Secret Manager for Quantum Admin
Handles encryption and decryption of sensitive data using Fernet symmetric encryption
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class SecretManager:
    """
    Manages encryption and decryption of secrets using Fernet symmetric encryption

    The encryption key is derived from environment variable QUANTUM_ENCRYPTION_KEY.
    If not set, a default key is generated (NOT secure for production).
    """

    _instance = None
    _cipher = None

    def __new__(cls):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(SecretManager, cls).__new__(cls)
            cls._instance._initialize_cipher()
        return cls._instance

    def _initialize_cipher(self):
        """Initialize Fernet cipher with encryption key from environment"""
        encryption_key = os.getenv('QUANTUM_ENCRYPTION_KEY')

        # Fail closed in production. The default key below is DERIVED FROM
        # LITERALS IN THE SOURCE (fixed password + fixed salt, PBKDF2 100k):
        # anyone with the code rebuilds the key and decrypts everything
        # encrypted with it. And the admin writes those encrypted values to
        # quantum_admin/settings/*.yaml, which has already been versioned — that
        # is, the default re-arms the leak on every save. In production this
        # cannot be a warning nobody reads; the service refuses to start,
        # mirroring auth_service._load_config.
        if not encryption_key:
            strict = os.environ.get('QUANTUM_ADMIN_ENV', '').lower() in (
                'production', 'prod')
            if strict:
                raise RuntimeError(
                    "QUANTUM_ADMIN_ENV=production requires QUANTUM_ENCRYPTION_KEY. "
                    "The built-in default key is derived from source literals and "
                    "provides no confidentiality; refusing to start. Generate one "
                    "with: python -m quantum_admin.core.secret_manager"
                )

        try:
            if encryption_key:
                # Use provided key
                key = encryption_key.encode()
                logger.info("✅ Using encryption key from QUANTUM_ENCRYPTION_KEY environment variable")
            else:
                # Generate default key (NOT secure for production!)
                logger.warning("⚠️  QUANTUM_ENCRYPTION_KEY not set! Using default key (NOT SECURE FOR PRODUCTION!)")
                logger.warning("⚠️  Set QUANTUM_ENCRYPTION_KEY environment variable for production use")

                # Use a deterministic default key derived from a fixed password
                # This allows decryption after restart but is NOT secure
                password = b"quantum-admin-default-key-change-me-in-production"
                salt = b"quantum-salt"  # Fixed salt for deterministic key
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                    backend=default_backend()
                )
                key = base64.urlsafe_b64encode(kdf.derive(password))

            self._cipher = Fernet(key)
            logger.info("🔐 Secret manager initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize secret manager: {e}")
            raise RuntimeError(f"Secret manager initialization failed: {e}")

    def encrypt(self, plain_text: str) -> str:
        """
        Encrypt a plain text string

        Args:
            plain_text: The plain text to encrypt

        Returns:
            str: Base64-encoded encrypted string

        Raises:
            ValueError: If encryption fails
        """
        if not plain_text:
            raise ValueError("Cannot encrypt empty string")

        try:
            encrypted_bytes = self._cipher.encrypt(plain_text.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"❌ Encryption failed: {e}")
            raise ValueError(f"Encryption failed: {e}")

    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt an encrypted string

        Args:
            encrypted_text: The encrypted text (base64-encoded)

        Returns:
            str: Decrypted plain text

        Raises:
            ValueError: If decryption fails
        """
        if not encrypted_text:
            raise ValueError("Cannot decrypt empty string")

        try:
            decrypted_bytes = self._cipher.decrypt(encrypted_text.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"❌ Decryption failed: {e}")
            raise ValueError(f"Decryption failed: {e}")

    def mask_value(self, value: str, show_chars: int = 4) -> str:
        """
        Mask a sensitive value for display purposes

        Args:
            value: The value to mask
            show_chars: Number of characters to show at the end

        Returns:
            str: Masked value (e.g., "****xyz")

        Example:
            >>> manager = SecretManager()
            >>> manager.mask_value("my-secret-password")
            '****word'
        """
        if not value:
            return ""

        if len(value) <= show_chars:
            return "*" * len(value)

        masked_length = len(value) - show_chars
        return ("*" * min(masked_length, 8)) + value[-show_chars:]

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key

        Returns:
            str: Base64-encoded encryption key

        Example:
            >>> key = SecretManager.generate_key()
            >>> print(f"Set this as environment variable:")
            >>> print(f"export QUANTUM_ENCRYPTION_KEY={key}")
        """
        return Fernet.generate_key().decode('utf-8')


# Singleton instance
secret_manager = SecretManager()


# Convenience functions
def encrypt_value(plain_text: str) -> str:
    """Encrypt a value using the global secret manager"""
    return secret_manager.encrypt(plain_text)


def decrypt_value(encrypted_text: str) -> str:
    """Decrypt a value using the global secret manager"""
    return secret_manager.decrypt(encrypted_text)


def mask_value(value: str, show_chars: int = 4) -> str:
    """Mask a value for display using the global secret manager"""
    return secret_manager.mask_value(value, show_chars)


def _looks_like_fernet_token(stored: str) -> bool:
    """Is this a Fernet token — regardless of whether OUR key opens it?

    A Fernet token is urlsafe-base64 over `0x80 | 8-byte timestamp | 16-byte
    IV | ciphertext | 32-byte HMAC`, so the shortest possible one is 57
    bytes and every one of them starts with the version byte 0x80. Plain
    text that happens to be valid base64 (`user:pass`, a JSON blob) does
    not.
    """
    try:
        raw = base64.urlsafe_b64decode(stored.encode('ascii'))
    except Exception:
        return False
    return len(raw) >= 57 and raw[0] == 0x80


class DecryptionKeyMismatch(ValueError):
    """The stored value IS encrypted and the current key does not open it."""


def decrypt_or_legacy(stored: str) -> str:
    """Decrypt a value, tolerating one written before it was encrypted.

    Cloud integration credentials were saved as plain JSON into a column
    named credentials_encrypted, with a `# TODO: encrypt properly` beside it.
    Rows written back then are still plain text, and refusing to read them
    would lose configuration people already have.

    So: decrypt when it decrypts, and when it does not, hand back what is
    stored and say why. The next write encrypts it.

    BUT only when what is stored is not an encrypted token.

    The `except Exception: return stored` applied to both failure reasons,
    and the second one is disastrous. If QUANTUM_ENCRYPTION_KEY changes —
    replaced, lost, or simply absent in a new deploy, when the module falls
    back to the default key — decryption fails with InvalidToken and the
    ENCRYPTED text was returned as if it were the password. Hence:

      * the database connection tried to authenticate with the base64 token
        as the password, and the error that showed up was "invalid password",
        pointing to the wrong place;
      * worse, the next save re-encrypted that token with the NEW key. The
        real password, which only the old key opened, was gone for good — and
        nothing on the way said anything had been lost.

    A secret that does not open is an error, not a value. Only text that was
    never encrypted goes through the legacy path.
    """
    if not stored:
        return stored
    try:
        return secret_manager.decrypt(stored)
    except Exception as exc:
        if _looks_like_fernet_token(stored):
            logger.error(
                "a stored secret is encrypted but the current "
                "QUANTUM_ENCRYPTION_KEY does not decrypt it — the key has "
                "changed or is missing. Restore the original key; saving "
                "over this value would destroy the secret permanently."
            )
            raise DecryptionKeyMismatch(
                "cannot decrypt a stored secret with the current "
                "QUANTUM_ENCRYPTION_KEY (the key changed or is not set). "
                "Restore the key that encrypted it — re-saving this record "
                "would overwrite the secret irrecoverably."
            ) from exc
        logger.warning(
            "reading a credential that was stored unencrypted (written "
            "before encryption was wired up); it will be encrypted on the "
            "next save"
        )
        return stored


if __name__ == "__main__":
    # Generate a new encryption key
    print("="*70)
    print("QUANTUM ADMIN - ENCRYPTION KEY GENERATOR")
    print("="*70)
    print("\nGenerate a new encryption key for production use:\n")
    key = SecretManager.generate_key()
    print(f"export QUANTUM_ENCRYPTION_KEY='{key}'")
    print("\nAdd this to your environment variables or .env file")
    print("="*70)
