# --- Validation tests ---

def test_missing_file_param(client):
    """Should return 400 when file parameter is missing."""
    res = client.post("/batch-weight", data={})
    assert res.status_code == 400
    assert "missing required field" in res.get_json()["error"]


def test_file_not_found(client):
    """Should return 404 when file doesn't exist in /in."""
    res = client.post("/batch-weight", data={"file": "nofile.csv"})
    assert res.status_code == 404
    assert "file not found" in res.get_json()["error"]


def test_unsupported_format(client):
    """Should return 400 for non-csv non-json files."""
    res = client.post("/batch-weight", data={"file": ".gitkeep"})
    assert res.status_code == 400
    assert "unsupported file format" in res.get_json()["error"]


# --- CSV happy path ---

def test_csv_kg_inserts_records(client):
    """containers1.csv should insert records with kg weights."""
    res = client.post("/batch-weight", data={"file": "containers1.csv"})
    assert res.status_code == 200
    assert res.get_json()["message"] == "processed 36 records"


def test_csv_lbs_converts_to_kg(client):
    """containers2.csv should convert lbs to kg and insert."""
    res = client.post("/batch-weight", data={"file": "containers2.csv"})
    assert res.status_code == 200
    assert res.get_json()["message"] == "processed 21 records"


# --- Data verification ---

def test_csv_kg_correct_weight_in_db(client):
    """Verify actual weight values are stored correctly."""
    client.post("/batch-weight", data={"file": "containers1.csv"})
    from models import ContainerRegistered
    container = ContainerRegistered.query.filter_by(container_id="C-35434").first()
    assert container is not None
    assert container.weight == 296
    assert container.unit == "kg"


def test_csv_lbs_converted_in_db(client):
    """Verify lbs values are converted to kg in the database."""
    client.post("/batch-weight", data={"file": "containers2.csv"})
    from models import ContainerRegistered
    container = ContainerRegistered.query.filter_by(container_id="K-8263").first()
    assert container is not None
    assert container.weight == int(666 * 0.453592)
    assert container.unit == "kg"


# --- JSON happy path ---

def test_json_inserts_records(client):
    """trucks.json should parse and insert records."""
    res = client.post("/batch-weight", data={"file": "trucks.json"})
    assert res.status_code == 200
    assert res.get_json()["message"] == "processed 31 records"


# --- Upsert behavior ---

def test_csv_upsert_updates_existing(client):
    """Running the same file twice should update, not duplicate."""
    client.post("/batch-weight", data={"file": "containers1.csv"})

    from models import ContainerRegistered
    count_after_first = ContainerRegistered.query.filter(
        ContainerRegistered.container_id.like("C-%")
    ).count()

    res = client.post("/batch-weight", data={"file": "containers1.csv"})
    assert res.status_code == 200

    count_after_second = ContainerRegistered.query.filter(
        ContainerRegistered.container_id.like("C-%")
    ).count()
    assert count_after_first == count_after_second


# --- JSON via JSON body ---

def test_json_body_request(client):
    """Should also accept file parameter via JSON body."""
    res = client.post("/batch-weight", json={"file": "containers1.csv"})
    assert res.status_code == 200
    assert res.get_json()["message"] == "processed 36 records"