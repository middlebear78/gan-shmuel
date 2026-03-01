import pytest
from database import db
from models import Transaction, ContainerRegistered


@pytest.fixture(autouse=True)
def setup_and_cleanup():
    """Set up test data and clean up after each test."""
    from app import app
    with app.app_context():
        Transaction.query.filter(Transaction.truck.like("TEST-%")).delete()
        existing = ContainerRegistered.query.filter_by(container_id="TEST-C1").first()
        if not existing:
            db.session.add(ContainerRegistered(container_id="TEST-C1", weight=300, unit="kg"))
        existing2 = ContainerRegistered.query.filter_by(container_id="TEST-C2").first()
        if not existing2:
            db.session.add(ContainerRegistered(container_id="TEST-C2", weight=200, unit="kg"))
        db.session.commit()
    yield
    with app.app_context():
        Transaction.query.filter(Transaction.truck.like("TEST-%")).delete()
        db.session.commit()


# --- Validation tests ---

def test_missing_direction(client):
    """Should return 400 when direction is missing."""
    res = client.post("/weight", json={"weight": 15000})
    assert res.status_code == 400
    assert "missing required fields" in res.get_json()["error"]


def test_missing_weight(client):
    """Should return 400 when weight is missing."""
    res = client.post("/weight", json={"direction": "in"})
    assert res.status_code == 400
    assert "missing required fields" in res.get_json()["error"]


def test_invalid_direction(client):
    """Should return 400 for an invalid direction value."""
    res = client.post("/weight", json={"direction": "sideways", "weight": 15000})
    assert res.status_code == 400
    assert "invalid direction" in res.get_json()["error"]


# --- Direction "in" tests ---

def test_in_creates_session(client):
    """Weigh-in should create a transaction and return id, truck, bruto."""
    res = client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-001",
        "weight": 15000,
        "containers": "TEST-C1,TEST-C2",
        "produce": "orange"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "id" in data
    assert data["truck"] == "TEST-001"
    assert data["bruto"] == 15000


def test_in_lbs_conversion(client):
    """Weigh-in with lbs should convert to kg."""
    res = client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-002",
        "weight": 33000,
        "unit": "lbs"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["bruto"] == int(33000 * 0.453592)


def test_in_default_values(client):
    """Weigh-in with minimal fields should use correct defaults."""
    res = client.post("/weight", json={
        "direction": "in",
        "weight": 15000
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["truck"] == "na"


# --- Direction "in" force tests ---

def test_in_after_in_no_force_error(client):
    """Duplicate weigh-in without force should return error."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-003",
        "weight": 15000
    })
    res = client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-003",
        "weight": 14000
    })
    assert res.status_code == 400
    assert "force=true" in res.get_json()["error"]


def test_in_after_in_with_force_overwrites(client):
    """Duplicate weigh-in with force should overwrite and return new data."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-004",
        "weight": 15000
    })
    res = client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-004",
        "weight": 14000,
        "force": "true"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["bruto"] == 14000


# --- Direction "none" tests ---

def test_none_standalone_container(client):
    """Standalone container weigh should create session with truck=na."""
    res = client.post("/weight", json={
        "direction": "none",
        "truck": "na",
        "weight": 285,
        "containers": "TEST-C1"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["truck"] == "na"
    assert data["bruto"] == 285


def test_none_after_in_error(client):
    """'none' for a truck with open session should return error."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-005",
        "weight": 15000
    })
    res = client.post("/weight", json={
        "direction": "none",
        "truck": "TEST-005",
        "weight": 300
    })
    assert res.status_code == 400
    assert "open" in res.get_json()["error"]


# --- Direction "out" tests ---

def test_out_without_in_error(client):
    """Weigh-out without a prior weigh-in should return error."""
    res = client.post("/weight", json={
        "direction": "out",
        "truck": "TEST-006",
        "weight": 4500
    })
    assert res.status_code == 400
    assert "no open" in res.get_json()["error"]


def test_out_closes_session(client):
    """Weigh-out should return session id, bruto, truckTara, and neto."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-007",
        "weight": 15000,
        "containers": "TEST-C1,TEST-C2",
        "produce": "orange"
    })
    res = client.post("/weight", json={
        "direction": "out",
        "truck": "TEST-007",
        "weight": 4500
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["truckTara"] == 4500
    assert data["bruto"] == 15000
    assert data["neto"] == 10000


def test_out_neto_na_unknown_container(client):
    """Neto should be 'na' when a container tara is unknown."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-008",
        "weight": 15000,
        "containers": "TEST-C1,UNKNOWN-CONTAINER"
    })
    res = client.post("/weight", json={
        "direction": "out",
        "truck": "TEST-008",
        "weight": 4500
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["neto"] == "na"


# --- Direction "out" force tests ---

def test_out_after_out_no_force_error(client):
    """Duplicate weigh-out without force should return error."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-009",
        "weight": 15000
    })
    client.post("/weight", json={
        "direction": "out",
        "truck": "TEST-009",
        "weight": 4500
    })
    res = client.post("/weight", json={
        "direction": "out",
        "truck": "TEST-009",
        "weight": 4600
    })
    assert res.status_code == 400
    assert "force=true" in res.get_json()["error"]


def test_out_after_out_with_force_overwrites(client):
    """Duplicate weigh-out with force should overwrite."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-010",
        "weight": 15000,
        "containers": "TEST-C1"
    })
    client.post("/weight", json={
        "direction": "out",
        "truck": "TEST-010",
        "weight": 4500
    })
    res = client.post("/weight", json={
        "direction": "out",
        "truck": "TEST-010",
        "weight": 4600,
        "force": "true"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["truckTara"] == 4600
    assert data["neto"] == 10100


# --- Form data fallback tests ---

def test_in_via_form_data(client):
    """Weigh-in via HTML form data should work the same as JSON."""
    res = client.post("/weight", data={
        "direction": "in",
        "truck": "TEST-FORM-01",
        "weight": "15000",
        "containers": "TEST-C1,TEST-C2",
        "produce": "orange"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["truck"] == "TEST-FORM-01"
    assert data["bruto"] == 15000


def test_in_out_flow_via_form_data(client):
    """Full in→out flow via form data, including neto calculation."""
    client.post("/weight", data={
        "direction": "in",
        "truck": "TEST-FORM-02",
        "weight": "15000",
        "containers": "TEST-C1,TEST-C2",
        "produce": "orange"
    })
    res = client.post("/weight", data={
        "direction": "out",
        "truck": "TEST-FORM-02",
        "weight": "4500"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["truckTara"] == 4500
    assert data["neto"] == 10000