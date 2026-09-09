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

        # Fail-closed em producao. A chave padrao abaixo e DERIVADA DE LITERAIS
        # NO FONTE (senha fixa + salt fixo, PBKDF2 100k): qualquer um com o
        # codigo reconstroi a chave e decifra tudo que foi cifrado com ela. E
        # o admin grava esses valores cifrados em quantum_admin/settings/*.yaml,
        # que ja foi versionado — ou seja, o default re-arma o vazamento a
        # cada save. Em producao isso nao pode ser um aviso que ninguem le;
        # o servico se recusa a subir, espelhando auth_service._load_config.
        if not encryption_key:
            estrito = os.environ.get('QUANTUM_ADMIN_ENV', '').lower() in (
                'production', 'prod')
            if estrito:
                raise RuntimeError(
                    "QUANTUM_ADMIN_ENV=production requires QUANTUM_ENCRYPTION_KEY. "
                    "The built-in default key is derived from source literals and "
                    "provides no confidentiality; refusing to start. Generate one "
                    "with: python -m quantum_admin.backend.secret_manager"
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

    MAS so quando o guardado nao e um token cifrado.

    O `except Exception: return stored` valia para os dois motivos de falha,
    e o segundo e desastroso. Se QUANTUM_ENCRYPTION_KEY mudar — trocada,
    perdida, ou simplesmente ausente num deploy novo, quando o modulo cai na
    chave padrao — a decifragem falha com InvalidToken e o texto CIFRADO era
    devolvido como se fosse a senha. Dai:

      * a conexao com o banco tentava autenticar com o token base64 como
        senha, e o erro que aparecia era "senha invalida", apontando para o
        lugar errado;
      * pior, o proximo save re-cifrava esse token com a chave NOVA. A senha
        de verdade, que so a chave antiga abria, ia embora de vez — e nada
        no caminho dizia que algo tinha se perdido.

    Um segredo que nao abre e um erro, nao um valor. So texto que nunca foi
    cifrado passa pelo caminho legado.
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
