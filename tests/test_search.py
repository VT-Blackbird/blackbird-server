import os
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.api import deps  # <--- Ensure this points to your get_current_user definition
from app.main import app
from app.models.article import Article
from app.models.user import User
from app.schemas.search_request import KeywordFilters, SearchRequest
from app.services.search_service import search_service
from app.utils.boolean_utils import apply_boolean_filters


# 1. Setup the Mock User
async def override_get_current_user() -> User:
    return User(
        username=os.getenv("ADMIN_USERNAME", "admin"),
        is_active=True
    )

# 2. Apply the override to the app
# This tells FastAPI: "Ignore the real auth, use my mock user instead"
app.dependency_overrides[deps.get_current_user] = override_get_current_user

client = TestClient(app)

def test_perform_search_success()->None:
    payload = {"query": "Virginia Tech", "limit": 5, "platforms": ["Reddit"]}
    # No headers needed! The dependency override handles the "lock" automatically.
    response = client.post("/api/v1/search/", json=payload)

    assert response.status_code == 200, f"\nresponse is not 200:\n {response.text}"
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)

def test_search_validation_error()->None:
    invalid_payload = {"query": "", "limit": 5}
    response = client.post("/api/v1/search/", json=invalid_payload)
    assert response.status_code == 422
    assert "detail" in response.json()

def test_search_with_invalid_platform() -> None:
    payload = {
        "query": "Artificial Intelligence",
        "limit": 10,
        "platforms": ["Gov", "FakePlatform123"]
    }
    response = client.post("/api/v1/search/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["results"], list)

def test_search_limit_and_variety() -> None:
    limit = 3
    payload = {"query": "tech", "limit": limit, "platforms": ["Google News",
                                            "USA.gov", "Reddit", "Bluesky"]}
    response = client.post("/api/v1/search/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) <= limit

def test_map_to_schema_edge_cases() -> None:
    data_bad = Article(
        content="",
        published_at="not-a-date-string",
        source_id=999,
        title="Edge Case",
    )
    result = search_service._map_article_to_search_result_item(data_bad)
    assert result.content == "Edge Case"
    assert result.source == "Web"
    assert result.published_at is not None

def test_no_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.search_service.load_proxies",
                        lambda source="db": [])
    payload = {"query": "Virginia Tech", "limit": 5, "platforms": ["Reddit"]}
    response = client.post("/api/v1/search/", json=payload)
    assert response.status_code == 200
    assert "results" in response.json()

@pytest.mark.asyncio
async def test_execute_search_full_path(monkeypatch: pytest.MonkeyPatch)\
        -> None:
    mock_data = [{"title": "Test", "content": "Test content",
                  "url": "http://test.com", "source_id": 1}]
    async def mock_safe_scrape(*args: Any,
                               **kwargs: Any) -> Optional[List[Dict[str, Any]]]:
        return mock_data

    monkeypatch.setattr("app.services.search_service.SearchService._safe_scrape",
                        mock_safe_scrape)
    payload = SearchRequest(query="test", limit=5, platforms=["News"])
    response = await search_service.execute_search(payload)
    assert len(response.results) > 0

def test_apply_boolean_filters_all_of() -> None:
    """Tests the AND logic (all_of)."""
    statement = select(Article)
    filters = KeywordFilters(all_of=["Virginia", "Tech"], any_of=[], none_of=[])

    filtered_stmt = apply_boolean_filters(statement, filters)

    # Converting to string to verify SQL generation
    sql_str = str(filtered_stmt)
    assert "lower(article.title) LIKE lower(:title_1)" in sql_str
    assert "lower(article.content) LIKE lower(:content_1)" in sql_str
    # SQLModel/SQLAlchemy uses incremental parameters for multiple 'where' clauses
    assert "LIKE lower(:title_2)" in sql_str

def test_apply_boolean_filters_any_of() -> None:
    """Tests the OR logic (any_of)."""
    statement = select(Article)
    filters = KeywordFilters(all_of=[], any_of=["Hokies", "Blacksburg"], none_of=[])

    filtered_stmt = apply_boolean_filters(statement, filters)
    sql_str = str(filtered_stmt)

    # OR logic puts clauses together
    assert "OR" in sql_str
    assert "lower(article.title) LIKE lower(:title_1)" in sql_str

def test_apply_boolean_filters_none_of() -> None:
    """Tests the NOT logic (none_of)."""
    statement = select(Article)
    filters = KeywordFilters(all_of=[], any_of=[], none_of=["Spam", "Ad"])

    filtered_stmt = apply_boolean_filters(statement, filters)
    sql_str = str(filtered_stmt)

    assert "NOT" in sql_str
    assert "lower(article.title) LIKE lower(:title_1)" in sql_str

def test_apply_boolean_filters_empty_inputs() -> None:
    """Tests that empty strings or whitespace don't break the query."""
    statement = select(Article)
    filters = KeywordFilters(all_of=[" "], any_of=["  "], none_of=["\n"])

    filtered_stmt = apply_boolean_filters(statement, filters)
    sql_str = str(filtered_stmt)

    # The statement should remain unchanged (no WHERE clauses added)
    assert "WHERE" not in sql_str