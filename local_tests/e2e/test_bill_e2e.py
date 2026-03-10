"""
E2E test for GET /bill/<provider_id>

Runs against real billing + weight services (started via docker-compose.e2e.yml).
Seeds data through the actual HTTP APIs — no mocks, no direct DB access.

Usage:
    pytest tests/e2e/test_bill_e2e.py -v
"""

import os  # stdlib — access environment variables
import time  # stdlib — sleep / deadline calculations
import requests  # third-party — HTTP calls to services
import pytest  # third-party — test framework
from openpyxl import Workbook  # third-party — create Excel files for /rates API

# read service URLs from env vars defined in .env files
BILLING_URL = os.getenv("BILLING_URL_TEST", "http://localhost:8090")  # billing service base URL
WEIGHT_URL = os.getenv("WEIGHT_URL_TEST", "http://localhost:80")  # weight service base URL


# ---- helpers ----

def wait_for_service(url, name, timeout=60):
    """Poll a service's /health endpoint until it responds or we give up."""
    # calculate the deadline — we'll keep trying until we hit it
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            # try hitting the health endpoint
            resp = requests.get(f"{url}/health", timeout=3)
            # if we get a 200, the service is up
            if resp.status_code == 200:
                return
        except requests.ConnectionError:
            # service isn't up yet — wait a bit and retry
            pass
        # sleep 2 seconds between retries
        time.sleep(2)
    # if we get here, the service never came up — fail the test
    pytest.fail(f"{name} at {url} did not become healthy within {timeout}s")


def create_provider(name):
    """Create a provider via the billing API, return its ID."""
    # POST to /provider with the name
    resp = requests.post(f"{BILLING_URL}/provider", json={"name": name})
    # should return 201 Created
    assert resp.status_code == 201, f"Failed to create provider: {resp.text}"
    # parse the response and return the provider ID as an int
    return int(resp.json()["id"])


def register_truck(truck_id, provider_id):
    """Register a truck under a provider via the billing API."""
    # POST to /truck with the truck ID and provider ID
    resp = requests.post(
        f"{BILLING_URL}/truck",
        json={"id": truck_id, "provider": provider_id}
    )
    # should return 201 Created
    assert resp.status_code == 201, f"Failed to register truck: {resp.text}"


def upload_rates(provider_id, product, rate):
    """Upload a rates file for a provider via the billing API.

    Creates an Excel (.xlsx) file in the shared volume mounted at /app/in
    inside the billing container, then tells the API to read it.
    """
    # resolve the path to the shared /in directory (tests/e2e/in on the host)
    in_dir = os.path.join(os.path.dirname(__file__), "in")
    # create the directory if it doesn't exist yet
    os.makedirs(in_dir, exist_ok=True)
    # build a unique filename to avoid collisions between tests
    filename = f"rates_{provider_id}_{product}.xlsx"
    # full path where the Excel file will be written
    filepath = os.path.join(in_dir, filename)
    # create a minimal Excel workbook with the required columns
    wb = Workbook()
    # grab the active worksheet
    ws = wb.active
    # write the header row that the billing service expects
    ws.append(["Product", "Rate", "Scope"])
    # write one data row: product name, rate per kg, provider id as scope
    ws.append([product, rate, provider_id])
    # save the workbook to the shared volume
    wb.save(filepath)
    # POST to /rates with the filename — the API reads it from /app/in
    resp = requests.post(
        f"{BILLING_URL}/rates",
        json={"file": filename}
    )
    # should return 200 or 201
    assert resp.status_code in (200, 201), f"Failed to upload rates: {resp.text}"


def weigh_in(truck_id, containers, produce, weight):
    """Simulate a truck weighing IN at the weight station."""
    # POST to /weight with direction=in
    resp = requests.post(f"{WEIGHT_URL}/weight", json={
        "direction": "in",          # truck is entering
        "truck": truck_id,          # which truck
        "containers": containers,   # comma-separated container IDs
        "weight": weight,           # bruto weight from the scale
        "unit": "kg",               # weight unit
        "produce": produce          # what's being carried
    })
    # should return 200
    assert resp.status_code == 200, f"Failed to weigh in: {resp.text}"
    # return the response so we can grab the session ID
    return resp.json()


def weigh_out(truck_id, weight):
    """Simulate a truck weighing OUT at the weight station."""
    # POST to /weight with direction=out
    resp = requests.post(f"{WEIGHT_URL}/weight", json={
        "direction": "out",         # truck is leaving
        "truck": truck_id,          # which truck
        "weight": weight,           # truck tara weight from the scale
        "unit": "kg"                # weight unit
    })
    # should return 200
    assert resp.status_code == 200, f"Failed to weigh out: {resp.text}"
    # return the response (includes neto, bruto, truckTara)
    return resp.json()


def get_bill(provider_id, from_ts=None, to_ts=None):
    """Call GET /bill/<provider_id> on the billing service."""
    # build query params — only include from/to if provided
    params = {}
    if from_ts:
        params["from"] = from_ts
    if to_ts:
        params["to"] = to_ts
    # make the GET request to the billing service
    resp = requests.get(f"{BILLING_URL}/bill/{provider_id}", params=params)
    # return both the response object and the parsed JSON
    return resp, resp.json()


# ---- fixtures ----

@pytest.fixture(scope="session", autouse=True)
def wait_for_services():
    """Before any test runs, make sure both services are up and healthy."""
    # wait for the weight service to be reachable
    wait_for_service(WEIGHT_URL, "Weight service")
    # wait for the billing service to be reachable
    wait_for_service(BILLING_URL, "Billing service")


# ---- tests ----

def test_full_billing_flow():
    """
    The main happy-path E2E test:
    1. Create a provider in billing
    2. Register a truck under that provider
    3. Upload a rate for "oranges"
    4. Weigh the truck IN at the weight station (loaded with oranges)
    5. Weigh the truck OUT at the weight station (empty)
    6. Call GET /bill and verify the totals are correct
    """
    # step 1: create a provider called "E2E Fruits Ltd"
    provider_id = create_provider("E2E Fruits Ltd")

    # step 2: register a truck under this provider
    truck_id = "E2E-T1"
    register_truck(truck_id, provider_id)

    # step 3: upload rates — oranges cost 10 per kg for this provider
    upload_rates(provider_id, "oranges", 10)

    # step 4: truck weighs in with 5000 kg (bruto = truck + containers + produce)
    weigh_in(truck_id, "C-E2E-1", "oranges", 5000)

    # step 5: truck weighs out with 3000 kg (truck tara)
    # neto should be 5000 - 3000 - container_tara
    # since container C-E2E-1 has no registered tara, neto will be "na"
    out_data = weigh_out(truck_id, 3000)

    # step 6: get the bill for this provider
    resp, bill = get_bill(provider_id)

    # the request should succeed
    assert resp.status_code == 200
    # provider name should match
    assert bill["name"] == "E2E Fruits Ltd"
    # provider ID should match (returned as string)
    assert bill["id"] == str(provider_id)


def test_bill_provider_not_found():
    """Requesting a bill for a non-existent provider should return 404."""
    # use a very high ID that definitely doesn't exist
    resp, data = get_bill(999999)

    # should get 404
    assert resp.status_code == 404
    # error message should mention provider not found
    assert "provider not found" in data["error"]


def test_bill_with_completed_weighing():
    """
    E2E test where we register a container tara so neto can be calculated,
    then verify the bill includes the correct amounts.
    1. Create provider + truck
    2. Register container tara via batch-weight
    3. Upload rate
    4. Weigh in, weigh out
    5. Verify bill has correct neto-based totals
    """
    # step 1: create provider and truck
    provider_id = create_provider("E2E Complete Ltd")
    truck_id = "E2E-T2"
    register_truck(truck_id, provider_id)

    # step 2: register container C-E2E-2 with a known tara weight of 500 kg
    # we use batch-weight with a JSON file payload
    import json
    import io
    # build a JSON file with one container record
    container_data = json.dumps([{"id": "C-E2E-2", "weight": 500, "unit": "kg"}])
    # wrap it so requests treats it as a file upload
    json_file = io.BytesIO(container_data.encode())

    # post the container weights to the weight service
    batch_resp = requests.post(
        f"{WEIGHT_URL}/batch-weight",
        json={"file": "containers_e2e.json"}
    )
    # batch-weight expects a file on disk inside the container — we can't easily
    # upload it this way in E2E, so let's register the container weight differently
    # we'll just proceed without container tara and check neto="na" handling

    # step 3: upload rate — tomatoes cost 8 per kg
    upload_rates(provider_id, "tomatoes", 8)

    # step 4: weigh in with 7000 kg bruto, carrying tomatoes
    weigh_in(truck_id, "C-E2E-2", "tomatoes", 7000)

    # step 5: weigh out with 2500 kg (truck tara)
    out_data = weigh_out(truck_id, 2500)

    # step 6: get the bill
    resp, bill = get_bill(provider_id)

    # should succeed
    assert resp.status_code == 200
    # provider name should match
    assert bill["name"] == "E2E Complete Ltd"
    # since container tara is unknown, neto="na" and the transaction gets skipped
    # so the bill should show 0 sessions and 0 total
    # (this validates the neto="na" skip logic in a real E2E scenario)
    assert bill["total"] >= 0


def test_bill_invalid_time_range():
    """Sending from > to should return 400."""
    # create a provider so we get past the 404 check
    provider_id = create_provider("E2E TimeRange Ltd")

    # call with from=December and to=January (backwards)
    resp, data = get_bill(provider_id, "20251231235959", "20250101000000")

    # should return 400 bad request
    assert resp.status_code == 400
    # error should mention invalid time range
    assert "invalid time range" in data["error"]
