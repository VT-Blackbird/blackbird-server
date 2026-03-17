import os

from sqlmodel import Session, create_engine

# hostname is 'db' because that is the service name in docker-compose
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@db:5432/blackbird")

engine = create_engine(DATABASE_URL, echo=False)

def get_session():
    with Session(engine) as session:
        yield session