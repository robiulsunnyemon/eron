from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Argon2 Password Hasher Instance
ph = PasswordHasher()

def hash_password(password: str) -> str | None:
    """
    Hashes a plain-text password using Argon2.
    It automatically handles salts and has no 72-byte limit.
    """
    if not password:
        return None
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored Argon2 hash.
    """
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False