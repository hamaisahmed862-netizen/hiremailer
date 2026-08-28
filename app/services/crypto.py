from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import TypeDecorator, String
from app.config import TOKEN_ENCRYPTION_KEY

if not TOKEN_ENCRYPTION_KEY:
    raise RuntimeError(
        "TOKEN_ENCRYPTION_KEY is not set in .env. "
        "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )

_fernet = Fernet(TOKEN_ENCRYPTION_KEY.encode())


class EncryptedString(TypeDecorator):
    """
    A string column that's automatically encrypted before writing to the
    database, and automatically decrypted when read back — application
    code just reads/writes it like a normal string, e.g. company.refresh_token.
    """
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return _fernet.encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return _fernet.decrypt(value.encode()).decode()
        except InvalidToken:
            # Value was stored before encryption was added, or key changed.
            return None