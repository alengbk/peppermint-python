from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
import hashlib
import secrets
from app.core.config import settings

# Use PBKDF2 with SHA256 for password hashing (more stable than bcrypt)
HASH_ITERATIONS = 100000
HASH_ALGORITHM = "sha256"
SALT_LENGTH = 16


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        algorithm, iterations, salt, hash_value = hashed_password.split("$")
        if algorithm != "pbkdf2_sha256" or int(iterations) != HASH_ITERATIONS:
            return False
        computed_hash = hashlib.pbkdf2_hmac(
            HASH_ALGORITHM,
            plain_password.encode(),
            bytes.fromhex(salt),
            HASH_ITERATIONS
        ).hex()
        return secrets.compare_digest(computed_hash, hash_value)
    except (ValueError, AttributeError):
        return False


def get_password_hash(password: str) -> str:
    """Generate a secure password hash"""
    salt = secrets.token_bytes(SALT_LENGTH)
    hash_value = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode(),
        salt,
        HASH_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${HASH_ITERATIONS}${salt.hex()}${hash_value}"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None