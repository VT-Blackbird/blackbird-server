from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.session import engine, get_session
from app.main import app
from app.models import Article, ExtractionMethod, Search, Source, SourceType


# 1. THE CLEANER: This fixture handles the "Undo" button
# Remove 'session: Session' from the arguments
@pytest.fixture(name="session")
def session_fixture() -> Session:
    # Connect to the real Postgres engine
    connection = engine.connect()
    # Begin a transaction
    transaction = connection.begin()

    # Create the session here
    session = Session(bind=connection)

    yield session

    # ROLLBACK: This deletes everything created during the test
    session.close()
    transaction.rollback()
    connection.close()


# 2. THE BRIDGE: Tell FastAPI to use our "Rollback-able" session
@pytest.fixture(name="client")
def client_fixture(session: Session) -> TestClient:
    def override_get_session() -> Session:
        yield session

    app.dependency_overrides[get_session] = override_get_session

    # 1. We MUST patch the engine inside the service
    # to use the session's existing connection.
    # Replace 'app.services.summary_service' with your actual service path.
    with patch("app.services.summary_service.engine", session.bind):
        yield TestClient(app)

    del app.dependency_overrides[get_session]


class TestSummary:
    BASE_URL = "/api/v1/summary"

    def test_perform_summary_success(self, client: TestClient,
                                     session: Session) -> None:
        # 1. Setup Source: Check if 'Reddit' exists first to avoid IntegrityError
        source = session.exec(select(Source).where(Source.name == "Reddit")).first()

        if not source:
            source = Source(
                name="Reddit",
                source_type=SourceType.SOCIAL,
                extraction_method=ExtractionMethod.RSS,
                base_url="https://reddit.com"
            )
            session.add(source)
            session.flush()  # This lets Postgres assign an ID automatically

        # 2. Setup Search
        search = Search(query_text="machine learning", request_limit=5)
        session.add(search)
        session.flush()

        # 3. Setup Article
        article = Article(
            search_id=search.id,
            source_id=source.id,
            title="Real DB Test",
            url="https://vt.edu/research",
            published_at=datetime.now(timezone.utc),
            relevance_score=0.95
        )
        session.add(article)
        session.flush()

        # 4. Action
        response = client.post(
            f"{self.BASE_URL}/",
            json={
                "query": "machine learning",
                "start_date": "2026-01-01T00:00:00Z",
                "end_date": "2026-12-31T23:59:59Z",
                "sources": ["Reddit"]
            }
        )

        # 5. Assertions
        assert response.status_code == 200
        assert response.json()["total_count"] >= 1

    def test_perform_summary_invalid_source(self, client: TestClient) -> None:
        """Test that requesting a source that doesn't
        exist returns 0 results gracefully."""
        response = client.post(
            f"{self.BASE_URL}/",
            json={
                "query": "machine learning",
                "start_date": "2026-01-01T00:00:00Z",
                "end_date": "2026-12-31T23:59:59Z",
                "sources": ["NonExistentSource"]
            }
        )

        # We now expect a success, but with no data found
        assert response.status_code == 200
        assert response.json()["total_count"] == 0

    def test_perform_summary_invalid_date_format(self,
                                                 client: TestClient) -> None:
        """Test that bad date strings
        trigger a 422 Unprocessable Entity (FastAPI default)."""
        response = client.post(
            f"{self.BASE_URL}/",
            json={
                "query": "machine learning",
                "start_date": "not-a-date",
                "end_date": "2026-12-31T23:59:59Z",
                "sources": ["Reddit"]
            }
        )

        # FastAPI/Pydantic automatically catches bad datetime strings
        assert response.status_code == 422