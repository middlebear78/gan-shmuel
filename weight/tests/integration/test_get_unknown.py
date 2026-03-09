# --- Basic tests ---

def test_get_unknown_empty(client):
    """Should return an empty list when no unknown containers were recorded."""
    res = client.get("/unknown")
    assert res.status_code == 200
    assert res.get_json() == []


# --- Unknown container detection tests ---

def test_get_unknown_returns_only_unknown_containers(client):
    """Should return only containers that were recorded but have no known tara."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-UNK-01",
        "weight": 15000,
        "containers": "UNKNOWN-C1,TEST-C1",
        "produce": "orange"
    })

    res = client.get("/unknown")
    data = res.get_json()

    assert res.status_code == 200
    assert "UNKNOWN-C1" in data
    assert "TEST-C1" not in data


def test_get_unknown_no_duplicates(client):
    """Unknown containers should appear only once even if used multiple times."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-UNK-02",
        "weight": 15000,
        "containers": "UNKNOWN-C2,TEST-C1",
        "produce": "orange"
    })

    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-UNK-03",
        "weight": 16000,
        "containers": "UNKNOWN-C2,UNKNOWN-C3",
        "produce": "orange"
    })

    res = client.get("/unknown")
    data = res.get_json()

    assert res.status_code == 200
    assert data.count("UNKNOWN-C2") == 1
    assert "UNKNOWN-C3" in data


def test_get_unknown_ignores_known_containers(client):
    """Known containers from fixtures should not be returned."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-UNK-04",
        "weight": 17000,
        "containers": "TEST-C1,TEST-C2",
        "produce": "orange"
    })

    res = client.get("/unknown")
    data = res.get_json()

    assert res.status_code == 200
    assert "TEST-C1" not in data
    assert "TEST-C2" not in data


# --- Null tara tests ---

def test_get_unknown_container_with_null_weight(client):
    """Registered container without weight should still be considered unknown."""
    from models import ContainerRegistered
    from database import db

    with client.application.app_context():
        existing = ContainerRegistered.query.filter_by(container_id="TEST-NOWEIGHT").first()
        if not existing:
            db.session.add(ContainerRegistered(container_id="TEST-NOWEIGHT", weight=None, unit="kg"))
            db.session.commit()

    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-UNK-05",
        "weight": 18000,
        "containers": "TEST-NOWEIGHT",
        "produce": "orange"
    })

    res = client.get("/unknown")
    data = res.get_json()

    assert res.status_code == 200
    assert "TEST-NOWEIGHT" in data