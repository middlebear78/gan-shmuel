# pytest is the test framework
import pytest
# patch lets us replace real HTTP calls with fake ones,
# MagicMock lets us build fake response objects
from unittest.mock import patch, MagicMock

# create_app builds a fresh Flask app with the config we choose
from app import create_app
# import the db instance and models so we can seed test data
from models import db, Provider, Truck, Rate


# this fixture creates a fresh Flask app using the TestConfig (SQLite in-memory DB),
# sets up all tables before each test, and tears them down after
@pytest.fixture
def app():
    # create the app with TestConfig — uses an in-memory SQLite database
    app = create_app("TestConfig")

    # push the app context so SQLAlchemy knows which app/db to use
    with app.app_context():
        # drop any leftover tables from a previous test (safety net)
        db.drop_all()
        # create all tables fresh based on the model definitions
        db.create_all()
        # yield pauses here — the test runs — then cleanup happens after
        yield app
        # remove the current db session to release connections
        db.session.remove()
        # drop all tables so the next test starts clean
        db.drop_all()


# this fixture gives each test a Flask test client, which lets us
# make fake HTTP requests (client.get, client.post, etc.) without a real server
@pytest.fixture
def client(app):
    # test_client() returns a client bound to our test app
    return app.test_client()


# helper that inserts a provider with two trucks and a rate into the test db
# returns the provider's auto-generated ID so tests can use it in URLs
def seed_provider_with_trucks(app):
    # need app context to interact with the database
    with app.app_context():
        # create a provider named "Test Provider"
        provider = Provider(name="Test Provider")
        # add it to the session so SQLAlchemy tracks it
        db.session.add(provider)
        # flush writes it to the DB so we get the auto-incremented ID back
        db.session.flush()

        # create two trucks and link them to our provider via provider_id
        db.session.add(Truck(id="T-001", provider_id=provider.id))
        db.session.add(Truck(id="T-002", provider_id=provider.id))

        # create a rate: oranges cost 5 per kg for this provider
        # scope is the provider ID as a string (that's how the Rate model works)
        rate = Rate(product_id="oranges", scope=str(provider.id), rate=5)
        db.session.add(rate)
        # commit everything to the database in one transaction
        db.session.commit()

        # return the provider ID so the test can build the URL like /bill/<id>
        return provider.id


# helper that builds a fake requests.Response object
# simulates a successful response from the weight service
def make_weight_response(items):
    # MagicMock creates a fake object that accepts any attribute access
    mock_resp = MagicMock()
    # set status_code to 200 so our code thinks the request succeeded
    mock_resp.status_code = 200
    # when our code calls response.json(), return the items list we passed in
    mock_resp.json.return_value = items
    # return the fake response object
    return mock_resp


# ---- TEST: happy path ----
# provider exists, has trucks, weight data matches those trucks,
# rate is configured — should return a correct bill with totals

# @patch replaces the real requests.get inside bill_route with a mock
# so we never actually call the weight service during tests
@patch("routes.bill_route.requests.get")
def test_happy_path_returns_correct_bill(mock_get, client, app):
    # insert provider + trucks + rate into the test DB, get the provider ID back
    pid = seed_provider_with_trucks(app)

    # build fake weight data — two completed weighings for our two trucks
    weight_data = [
        # first truck (T-001) weighed out with 1000 kg neto of oranges
        {"id": 1, "direction": "out", "truck": "T-001", "bruto": 5000,
         "neto": 1000, "produce": "oranges", "containers": ["C1"]},
        # second truck (T-002) weighed out with 2000 kg neto of oranges
        {"id": 2, "direction": "out", "truck": "T-002", "bruto": 6000,
         "neto": 2000, "produce": "oranges", "containers": ["C2"]},
    ]
    # tell the mock to return our fake weight data when requests.get is called
    mock_get.return_value = make_weight_response(weight_data)

    # hit the GET /bill endpoint with a full-year time range
    resp = client.get(
        f"/bill/{pid}?from=20250101000000&to=20251231235959"
    )
    # parse the JSON response body
    data = resp.get_json()

    # should succeed with 200
    assert resp.status_code == 200
    # provider name should match what we seeded
    assert data["name"] == "Test Provider"
    # both trucks appeared in the weight data
    assert data["truckCount"] == 2
    # two sessions (one per weight record)
    assert data["sessionCount"] == 2
    # only one product (oranges)
    assert len(data["products"]) == 1
    # the product name should be "oranges"
    assert data["products"][0]["product"] == "oranges"
    # total kg should be 1000 + 2000 = 3000
    assert data["products"][0]["amount"] == 3000
    # rate should be 5 per kg (what we seeded)
    assert data["products"][0]["rate"] == 5
    # pay should be 3000 * 5 = 15000
    assert data["products"][0]["pay"] == 15000
    # grand total should match the single product's pay
    assert data["total"] == 15000


# ---- TEST: provider not found ----
# requesting a bill for a provider ID that doesn't exist should return 404

def test_provider_not_found_returns_404(client, app):
    # provider ID 9999 was never created, so it doesn't exist in the DB
    resp = client.get("/bill/9999?from=20250101000000&to=20251231235959")

    # should get a 404 Not Found
    assert resp.status_code == 404
    # error message should say "provider not found"
    assert "provider not found" in resp.get_json()["error"]


# ---- TEST: no matching trucks ----
# the weight data contains a truck that doesn't belong to our provider
# so the bill should come back empty (zero everything)

@patch("routes.bill_route.requests.get")
def test_no_matching_trucks_returns_empty_bill(mock_get, client, app):
    # seed our provider (owns T-001 and T-002)
    pid = seed_provider_with_trucks(app)

    # weight data has a truck "T-OTHER" which is NOT one of our provider's trucks
    weight_data = [
        {"id": 1, "direction": "out", "truck": "T-OTHER", "bruto": 5000,
         "neto": 1000, "produce": "oranges", "containers": ["C1"]},
    ]
    # set up the mock to return this data
    mock_get.return_value = make_weight_response(weight_data)

    # call the endpoint
    resp = client.get(
        f"/bill/{pid}?from=20250101000000&to=20251231235959"
    )
    # parse response
    data = resp.get_json()

    # should still return 200 — it's not an error, just nothing to bill
    assert resp.status_code == 200
    # no trucks matched, so truck count is 0
    assert data["truckCount"] == 0
    # no sessions counted
    assert data["sessionCount"] == 0
    # no products in the bill
    assert data["products"] == []
    # total is 0 since there's nothing to charge
    assert data["total"] == 0


# ---- TEST: missing rate ----
# the weight data has a product ("tomatoes") that has no rate configured
# the endpoint should return 422 Unprocessable Entity

@patch("routes.bill_route.requests.get")
def test_missing_rate_returns_422(mock_get, client, app):
    # seed provider — only has a rate for "oranges", not "tomatoes"
    pid = seed_provider_with_trucks(app)

    # weight data contains "tomatoes" which has no rate in the database
    weight_data = [
        {"id": 1, "direction": "out", "truck": "T-001", "bruto": 5000,
         "neto": 1000, "produce": "tomatoes", "containers": ["C1"]},
    ]
    # mock the weight service response
    mock_get.return_value = make_weight_response(weight_data)

    # call the endpoint
    resp = client.get(
        f"/bill/{pid}?from=20250101000000&to=20251231235959"
    )

    # should return 422 because we can't calculate pay without a rate
    assert resp.status_code == 422
    # error message should mention the missing rate
    assert "No rate configured" in resp.get_json()["error"]


# ---- TEST: weight service error ----
# if the weight microservice is down or returns an error,
# our endpoint should return 500

@patch("routes.bill_route.requests.get")
def test_weight_service_error_returns_500(mock_get, client, app):
    # seed a valid provider so the 404 check passes
    pid = seed_provider_with_trucks(app)

    # simulate the weight service returning a 503 Service Unavailable
    error_resp = MagicMock()
    # set status_code to 503 so our code sees a non-200 and raises an exception
    error_resp.status_code = 503
    # tell the mock to return this error response
    mock_get.return_value = error_resp

    # call the endpoint
    resp = client.get(
        f"/bill/{pid}?from=20250101000000&to=20251231235959"
    )

    # the route should catch the exception and return 500
    assert resp.status_code == 500
    # error message should say "billing failed"
    assert "billing failed" in resp.get_json()["error"]


# ---- TEST: invalid time range ----
# if "from" is after "to", the endpoint should reject it with 400

def test_invalid_time_range_returns_400(client, app):
    # seed a provider so the 404 check passes (we need to reach the time range check)
    pid = seed_provider_with_trucks(app)

    # "from" is Dec 31 and "to" is Jan 1 — backwards
    resp = client.get(
        f"/bill/{pid}?from=20251231235959&to=20250101000000"
    )

    # should return 400 Bad Request
    assert resp.status_code == 400
    # error message should mention the invalid time range
    assert "invalid time range" in resp.get_json()["error"]


# ---- TEST: neto="na" transactions are skipped ----
# transactions where neto is "na" (container tara unknown) should be
# excluded from the bill — only the ones with a real neto count

@patch("routes.bill_route.requests.get")
def test_neto_na_transactions_are_skipped(mock_get, client, app):
    # seed provider with trucks and oranges rate
    pid = seed_provider_with_trucks(app)

    weight_data = [
        # this record has neto="na" — container tara unknown, should be SKIPPED
        {"id": 1, "direction": "out", "truck": "T-001", "bruto": 5000,
         "neto": "na", "produce": "oranges", "containers": ["C1"]},
        # this record has a real neto — should be COUNTED
        {"id": 2, "direction": "out", "truck": "T-002", "bruto": 6000,
         "neto": 2000, "produce": "oranges", "containers": ["C2"]},
    ]
    # mock the weight service to return both records
    mock_get.return_value = make_weight_response(weight_data)

    # call the endpoint
    resp = client.get(
        f"/bill/{pid}?from=20250101000000&to=20251231235959"
    )
    # parse the response
    data = resp.get_json()

    # should succeed
    assert resp.status_code == 200
    # only T-002 was counted (T-001 was skipped because neto="na")
    assert data["truckCount"] == 1
    # only session 2 was counted
    assert data["sessionCount"] == 1
    # only the 2000 kg from session 2
    assert data["products"][0]["amount"] == 2000
    # total pay = 2000 kg * 5 per kg = 10000
    assert data["total"] == 10000
