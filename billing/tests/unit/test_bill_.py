# test_bill.py

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from routes.bill_route import parse_timestamp, resolve_time_range, generate_bill
from tests.unit.mock_data import (
    mock_providers, mock_trucks, mock_rates,
    mock_weights, mock_sessions,
    mock_bill_provider1
)


# ── parse_timestamp ───────────────────────────────────────────────────────────

def test_parse_timestamp_valid():
    result = parse_timestamp("20240101000000")
    assert result == datetime(2024, 1, 1, 0, 0, 0)

def test_parse_timestamp_invalid():
    assert parse_timestamp("not-a-date") is None


# ── resolve_time_range ────────────────────────────────────────────────────────

def test_resolve_time_range_explicit():
    start, end = resolve_time_range("20240101000000", "20240131235959")
    assert start == datetime(2024, 1, 1, 0, 0, 0)
    assert end == datetime(2024, 1, 31, 23, 59, 59)

def test_resolve_time_range_defaults_to_now():
    before = datetime.now()
    start, end = resolve_time_range(None, None)
    after = datetime.now()
    assert start.day == 1
    assert before <= end <= after


# ── generate_bill ─────────────────────────────────────────────────────────────

def make_provider():
    mprovider = MagicMock()
    mprovider.id   = mock_providers[0]["id"]
    mprovider.name = mock_providers[0]["name"]
    return mprovider

def mock_fetch_session(session_id):
    return mock_sessions.get(session_id)

@patch("routes.bill_route.Rate")                                                 # Arg 1
@patch("routes.bill_route.get_provider_trucks", return_value=["TR001", "TR002"]) # Arg 2
@patch("routes.bill_route.fetch_weights")                                        # Arg 3
def test_generate_bill(mock_weights_fn, mock_trucks_fn, mock_rate_model):
    # 1. Update mock_weights to include the 'truck' key your code expects
    processed_weights = []
    for w in mock_weights:
        # Look up the truck from your mock_sessions dict and add it to the weight record
        w_with_truck = w.copy()
        w_with_truck["truck"] = mock_sessions.get(w["id"], {}).get("truck")
        processed_weights.append(w_with_truck)
    
    mock_weights_fn.return_value = processed_weights

    # 2. Setup Rate mock
    mock_rate_model.query.filter_by.return_value.all.return_value = [
        MagicMock(product_id=r["product_id"], rate=r["rate"])
        for r in mock_rates if r["scope"] == 1
    ]

    provider = make_provider()
    start = datetime(2024, 1, 1)
    end   = datetime(2024, 1, 31, 23, 59, 59)

    # 3. Run
    bill = generate_bill(provider, start, end)

    # 4. Assertions (Using pytest.approx for the total/pay just in case)
    assert bill["total"] == mock_bill_provider1["total"]
    assert bill["sessionCount"] == 3 
    
    # Check products breakdown
    result_products = {p["product"]: p for p in bill["products"]}
    for expected in mock_bill_provider1["products"]:
        actual = result_products[expected["product"]]
        assert actual["amount"] == expected["amount"]
        assert int(actual["count"]) == int(expected["count"])