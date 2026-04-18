from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.article import Article
from app.schemas.search_request import SearchRequest
from app.services.search_service import search_service

client = TestClient(app)

def test_perform_search_success()->None:
    """
    Test that a valid search request returns a 200 and the expected schema.
    """
    # 1. Define a valid request payload
    payload = {"query": "Virginia Tech", "limit": 5, "platforms": ["Reddit"]}

    # 2. Hit the endpoint (make sure the URL matches your main.py prefix)
    response = client.post("/api/v1/search/", json=payload)

    # 3. Assertions
    assert response.status_code == 200,  f"\nresponse is not 200:\n {response.text}"

    data = response.json()
    assert "results" in data
    assert "total_count" in data
    assert isinstance(data["results"], list)

    # If using your mock service, check for specific fields
    if len(data["results"]) > 0:
        assert "source" in data["results"][0]
        assert "sentiment" in data["results"][0]


def test_search_validation_error()->None:
    """
    Test that an invalid request (empty query) returns a 422 Unprocessable Entity.
    """
    invalid_payload = {"query": "", "limit": 5}  # This violates min_length=1

    response = client.post("/api/v1/search/", json=invalid_payload)

    # Validation happens at the Schema level, so FastAPI returns 422
    assert response.status_code == 422
    assert "detail" in response.json()


def test_search_with_invalid_platform() -> None:
    """
    Test that including a non-existent platform doesn't crash the service.
    """
    payload = {
        "query": "Artificial Intelligence",
        "limit": 10,
        "platforms": ["Gov", "FakePlatform123"]  #Fake platform does not exist
    }

    response = client.post("/api/v1/search/", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Response should still return results from 'Gov'
    assert isinstance(data["results"], list)
    if data["total_count"] > 0:
        assert data["results"][0]["source"] == "USA.gov"


def test_search_limit_and_variety() -> None:
    """
    Test that the limit is strictly enforced and multiple sources can coexist.
    """
    limit = 3
    payload = {
        "query": "tech",
        "limit": limit,
        "platforms": ["News", "Reddit"]
    }

    response = client.post("/api/v1/search/", json=payload)
    assert response.status_code == 200,  f"\nresponse is not 200:\n {response.text}"
    data = response.json()

    # Assert limit is respected
    assert len(data["results"]) <= limit
    assert data["total_count"] <= limit


def test_map_to_schema_edge_cases() -> None:
    # 1. Test invalid date parsing (Hits line 134/142-145)
    data_bad = Article(
        content="",
        published_at="not-a-date-string",
        source_id=999,
        title="Edge Case",
    )
    #change type of bad_data
    result = search_service._map_article_to_search_result_item(data_bad)

    # Assertions to ensure the fallbacks worked
    assert result.content == "Edge Case"  # Fell back to title
    assert result.source == "Web"  # Fell back to default source
    assert result.published_at is not None  # Fell back to now()


def test_no_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    # IMPORTANT: Patch the function in the file where it is CONSUMED
    # Assuming search_service.py imports load_proxies from app.workers.core.utils
    monkeypatch.setattr("app.services.search_service.load_proxies",
                        lambda source="db": [])

    payload = {"query": "Virginia Tech", "limit": 5, "platforms": ["Reddit"]}
    response = client.post("/api/v1/search/", json=payload)

    assert response.status_code == 200, f"\nresponse is not 200:\n {response.json}"
    data = response.json()

    # This now officially tests the "if not proxies" error handling path
    assert "results" in data


@pytest.mark.asyncio
async def test_execute_search_full_path(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock the scraper to return a fake article
    mock_data = [{"title": "Test", "content": "Test content",
                  "url": "http://test.com", "source_id": 1}]

    async def mock_safe_scrape(*args: Any, **kwargs: Any)\
            -> Optional[List[Dict[str, Any]]]:
        return mock_data

    # Patch the service method with your async mock
    monkeypatch.setattr(
        "app.services.search_service.SearchService._safe_scrape",
        mock_safe_scrape
    )


    payload = SearchRequest(query="test", limit=5, platforms=["News"])
    response = await search_service.execute_search(payload)

    # This forces the code to run the cleaning, embedding, and DB session logic
    assert len(response.results) > 0
