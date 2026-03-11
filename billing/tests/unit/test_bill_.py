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

@patch("routes.bill_route.fetch_weights", return_value=mock_weights)
@patch("routes.bill_route.fetch_session", side_effect=mock_fetch_session)
@patch("routes.bill_route.get_provider_trucks", return_value=["TR001", "TR002"])
@patch("routes.bill_route.Rate")
def test_generate_bill(mock_rate_model, mock_trucks_fn, mock_session_fn, mock_weights_fn):
    mock_rate_model.query.filter_by.return_value.all.return_value = [
        MagicMock(product_id=r["product_id"], rate=r["rate"])
        for r in mock_rates if r["scope"] == 1
    ]

    provider = make_provider()
    start = datetime(2024, 1, 1)
    end   = datetime(2024, 1, 31, 23, 59, 59)

    bill = generate_bill(provider, start, end)

    assert bill["id"]           == mock_bill_provider1["id"]
    assert bill["name"]         == mock_bill_provider1["name"]
    assert bill["truckCount"]   == mock_bill_provider1["truckCount"]
    assert bill["sessionCount"] == mock_bill_provider1["sessionCount"]
    assert bill["total"]        == mock_bill_provider1["total"]

    result_products = {mprovider["product"]: mprovider for mprovider in bill["products"]}
    for expected in mock_bill_provider1["products"]:
        actual = result_products[expected["product"]]
        assert actual["amount"] == expected["amount"]
        assert actual["pay"]    == expected["pay"]


@patch("routes.bill_route.fetch_weights", return_value=mock_weights)
@patch("routes.bill_route.fetch_session", side_effect=mock_fetch_session)
@patch("routes.bill_route.get_provider_trucks", return_value=["TR001", "TR002"])
@patch("routes.bill_route.Rate")
def test_generate_bill_missing_rate_raises(mock_rate_model, *_):
    mock_rate_model.query.filter_by.return_value.all.return_value = []  # no rates

    with pytest.raises(ValueError, match="No rate configured"):
        generate_bill(make_provider(), datetime(2024, 1, 1), datetime(2024, 1, 31))