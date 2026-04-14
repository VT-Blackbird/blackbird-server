from fastapi import HTTPException, status
from sqlmodel import Session, select
from app.db.session import engine
from app.models.user import User
from app.core.security import verify_password, create_access_token


class AuthService:
    def authenticate_user(self, username: str, password: str) -> str:
        with Session(engine) as session:
            # 1. Find user in DB
            statement = select(User).where(User.username == username)
            user = session.exec(statement).first()

            # 2. Check if user exists and password is correct
            if not user or not verify_password(password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # 3. Create and return the JWT
            return create_access_token(subject=user.username)

auth_service = AuthService()