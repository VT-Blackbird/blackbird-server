from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_perform_search_success():
    """
    Test that a valid search request returns a 200 and the expected schema.
    """
    # 1. Define a valid request payload
    payload = {
        "query": "Virginia Tech",
        "limit": 5,
        "platforms": ["Reddit"]
    }

    # 2. Hit the endpoint (make sure the URL matches your main.py prefix)
    response = client.post("/search/", json=payload)

    # 3. Assertions
    assert response.status_code == 200

    data = response.json()
    assert "results" in data
    assert "total_count" in data
    assert isinstance(data["results"], list)

    # If using your mock service, check for specific fields
    if len(data["results"]) > 0:
        assert "source" in data["results"][0]
        assert "sentiment" in data["results"][0]

def test_search_validation_error():
    """
    Test that an invalid request (empty query) returns a 422 Unprocessable Entity.
    """
    invalid_payload = {
        "query": "",  # This violates min_length=1
        "limit": 5
    }

    response = client.post("/search/", json=invalid_payload)

    # Validation happens at the Schema level, so FastAPI returns 422
    assert response.status_code == 422
    assert "detail" in response.json()