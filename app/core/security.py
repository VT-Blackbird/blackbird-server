import os
from datetime import datetime, timedelta, timezone
from typing import Any, Union

import bcrypt
import jwt
from dotenv import load_dotenv

# Load the .env file explicitly
load_dotenv()

# Configuration - pulls from .env or uses a fallback for safety
SECRET_KEY = os.getenv("SECRET_KEY", "temporary-dev-key-very-insecure")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

def get_password_hash(password: str) -> str:
    # Hash a password using bcrypt
    # 1. Convert password to bytes
    # 2. Generate a salt and hash
    # 3. Decode back to string for database storage
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Verify a plain password against the hashed version
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def create_access_token(subject: Union[str, Any]) -> str:
    """Generates a signed JWT for the user."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt