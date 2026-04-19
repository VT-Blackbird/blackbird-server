import os
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api import deps  # <--- Import your dependencies
from app.db.session import engine, get_session
from app.main import app
from app.models import Article, ExtractionMethod, Search, Source, SourceType


# 1. Auth Override: This handles the protected route gate
async def override_get_current_user() -> Any:
    return {
        "username": os.getenv("ADMIN_USERNAME", "admin"),
        "is_active": True
    }

# 2. THE CLEANER: This fixture handles the "Undo" button
@pytest.fixture(name="session")
def session_fixture() -> Session:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# 3. THE BRIDGE: Tell FastAPI to use our "Rollback-able" session AND our Mock User
@pytest.fixture(name="client")
def client_fixture(session: Session) -> TestClient:
    def override_get_session() -> Session:
        yield session

    # Apply both overrides here
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[deps.get_current_user] = override_get_current_user

    with patch("app.services.summary_service.engine", session.bind):
        yield TestClient(app)

    # Clean up overrides after the test is done
    del app.dependency_overrides[get_session]
    del app.dependency_overrides[deps.get_current_user]


class TestSummary:
    BASE_URL = "/api/v1/summary"

    def test_perform_summary_success(self, client: TestClient,
                                     session: Session) -> None:
        # 1. Setup Source
        source = session.exec(select(Source).where(Source.name == "Reddit")).first()

        if not source:
            source = Source(
                name="Reddit",
                source_type=SourceType.SOCIAL,
                extraction_method=ExtractionMethod.RSS,
                base_url="https://reddit.com"
            )
            session.add(source)
            session.flush()

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

        assert response.status_code == 200
        assert response.json()["total_count"] >= 1

    def test_perform_summary_invalid_source(self, client: TestClient) -> None:
        response = client.post(
            f"{self.BASE_URL}/",
            json={
                "query": "machine learning",
                "start_date": "2026-01-01T00:00:00Z",
                "end_date": "2026-12-31T23:59:59Z",
                "sources": ["NonExistentSource"]
            }
        )
        assert response.status_code == 200
        assert response.json()["total_count"] == 0

    def test_perform_summary_invalid_date_format(self,
                                                 client: TestClient) -> None:
        response = client.post(
            f"{self.BASE_URL}/",
            json={
                "query": "machine learning",
                "start_date": "not-a-date",
                "end_date": "2026-12-31T23:59:59Z",
                "sources": ["Reddit"]
            }
        )
        assert response.status_code == 422