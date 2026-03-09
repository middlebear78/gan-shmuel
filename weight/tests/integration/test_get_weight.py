
# --- Default behavior ---

def test_get_weight_returns_list(client):
    """Should return a JSON array."""
    res = client.get("/weight")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


def test_get_weight_includes_today(client):
    """Transactions created now should appear in default query."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-GW-01",
        "weight": 15000,
        "containers": "TEST-C1",
        "produce": "orange"
    })
    res = client.get("/weight")
    data = res.get_json()
    # Find our transaction by checking produce and direction
    ours = [t for t in data if t.get("produce") == "orange" and t["direction"] == "in"]
    assert len(ours) >= 1


# --- Filter tests ---

def test_filter_out_only(client):
    """filter=out should exclude 'in' and 'none' transactions."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-GW-02",
        "weight": 15000,
        "containers": "TEST-C1"
    })
    client.post("/weight", json={
        "direction": "out",
        "truck": "TEST-GW-02",
        "weight": 4500
    })
    res = client.get("/weight?filter=out")
    data = res.get_json()
    directions = [t["direction"] for t in data]
    assert "in" not in directions
    assert "none" not in directions


def test_filter_multiple(client):
    """filter=in,none should exclude 'out' transactions."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-GW-03",
        "weight": 15000
    })
    res = client.get("/weight?filter=in,none")
    data = res.get_json()
    directions = [t["direction"] for t in data]
    assert "out" not in directions


# --- Response format ---

def test_response_has_required_fields(client):
    """Each transaction should have all spec-required fields."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-GW-04",
        "weight": 15000,
        "containers": "TEST-C1,TEST-C2",
        "produce": "orange"
    })
    res = client.get("/weight")
    data = res.get_json()
    ours = [t for t in data if t["direction"] == "in"]
    assert len(ours) >= 1
    t = ours[0]
    assert "id" in t
    assert "direction" in t
    assert "bruto" in t
    assert "neto" in t
    assert "produce" in t
    assert "containers" in t


def test_containers_is_array(client):
    """Containers should be a JSON array, not a comma-delimited string."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-GW-05",
        "weight": 15000,
        "containers": "TEST-C1,TEST-C2"
    })
    res = client.get("/weight")
    data = res.get_json()
    ours = [t for t in data if len(t["containers"]) == 2]
    assert len(ours) >= 1
    assert isinstance(ours[0]["containers"], list)


def test_neto_na_for_in_direction(client):
    """'in' transactions should have neto='na'."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-GW-06",
        "weight": 15000
    })
    res = client.get("/weight?filter=in")
    data = res.get_json()
    for t in data:
        assert t["neto"] == "na"


def test_neto_calculated_for_out(client):
    """'out' with known containers should have numeric neto."""
    client.post("/weight", json={
        "direction": "in",
        "truck": "TEST-GW-07",
        "weight": 16500,
        "containers": "TEST-C1,TEST-C2",
        "produce": "orange"
    })
    client.post("/weight", json={
        "direction": "out",
        "truck": "TEST-GW-07",
        "weight": 4500
    })
    res = client.get("/weight?filter=out")
    data = res.get_json()
    ours = [t for t in data if t["bruto"] == 16500]
    assert len(ours) >= 1
    # neto = 16500 - 4500 - 300 - 200 = 11500
    assert ours[0]["neto"] == 11500

# --- Datetime validation ---

def test_bad_from_format(client):
    """Invalid 'from' format should return 400."""
    res = client.get("/weight?from=2026-03-01")
    assert res.status_code == 400
    assert "invalid datetime" in res.get_json()["error"]


def test_bad_to_format(client):
    """Invalid 'to' format should return 400."""
    res = client.get("/weight?to=abc")
    assert res.status_code == 400
    assert "invalid datetime" in res.get_json()["error"]