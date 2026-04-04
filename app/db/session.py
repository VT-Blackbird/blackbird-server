import os
from typing import Generator

from sqlmodel import Session, create_engine

# hostname is 'db' because that is the service name in docker-compose
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@db:5432/blackbird")

engine = create_engine(DATABASE_URL, echo=False) # Set echo=True for SQL debugging

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session