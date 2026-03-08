import requests

BASE_URL = "http://localhost"

def test_get_session_not_found():
    response = requests.get(f"{BASE_URL}/session/99999")

    assert response.status_code == 404
    assert response.json()["error"] == "session not found"