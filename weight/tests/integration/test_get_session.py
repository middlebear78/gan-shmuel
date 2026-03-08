# --- Validation tests ---

def test_get_session_not_found(client):
    """Should return 404 when session does not exist."""
    res = client.get("/session/99999")
    assert res.status_code == 404
    assert res.get_json()["error"] == "session not found"


def test_get_session_invalid_id(client):
    """Should return 400 when session id is not a valid integer."""
    res = client.get("/session/abc")
    assert res.status_code == 400
    assert res.get_json()["error"] == "invalid session id"


# --- Open session tests ---

def test_get_open_session(client):
    """Open session should return id, truck, bruto without truckTara/neto."""
    post_res = client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-SESSION-OPEN",
        "weight": 32000,
        "containers": "TEST-C1,TEST-C2",
        "produce": "orange"
    })

    assert post_res.status_code == 200
    session_id = post_res.get_json()["id"]

    res = client.get(f"/session/{session_id}")
    assert res.status_code == 200

    data = res.get_json()
    assert data["id"] == str(session_id)
    assert data["truck"] == "TEST-SESSION-OPEN"
    assert data["bruto"] == 32000
    assert "truckTara" not in data
    assert "neto" not in data


# --- Closed session tests ---

def test_get_closed_session(client):
    """Closed session should return id, truck, bruto, truckTara and neto."""
    post_in = client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-SESSION-CLOSED",
        "weight": 32000,
        "containers": "TEST-C1,TEST-C2",
        "produce": "orange"
    })

    assert post_in.status_code == 200
    session_id = post_in.get_json()["id"]

    post_out = client.post("/weight", json={
        "direction": "out",
        "truck": "TEST-SESSION-CLOSED",
        "weight": 18000
    })

    assert post_out.status_code == 200

    res = client.get(f"/session/{session_id}")
    assert res.status_code == 200

    data = res.get_json()
    assert data["id"] == str(session_id)
    assert data["truck"] == "TEST-SESSION-CLOSED"
    assert data["bruto"] == 32000
    assert data["truckTara"] == 18000
    assert data["neto"] == 13500