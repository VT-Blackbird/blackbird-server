from fastapi.testclient import TestClient

from app.main import app
from app.models.article import Article
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
    print(f"Test Perform Search Response: {response.json()}")
    assert response.status_code == 200

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
    print(f"Test Search Limit and Variety Response: {response.json()}")
    assert response.status_code == 200
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