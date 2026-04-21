import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.core import security
from app.db.session import engine
from app.models.user import User

# This tells FastAPI where to look for the token (the 'Authorization' header)
# It also links to the login URL so the "Authorize" button works in Swagger
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency that validates the JWT and returns the current user.
    If the token is invalid or the user doesn't exist, it raises a 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 1. Decode the token using our SECRET_KEY
        payload = jwt.decode(
            token,
            security.SECRET_KEY,
            algorithms=[security.ALGORITHM]
        )
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

    except jwt.PyJWTError:
        # Handles expired tokens, tampered tokens, or wrong keys
        raise credentials_exception

    # 2. Check if the user actually exists in the database
    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()

        if user is None:
            raise credentials_exception

        return user