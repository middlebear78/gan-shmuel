# mock_data.py

mock_providers = [
    {"id": 1, "name": "ProviderA"},
    {"id": 2, "name": "ProviderB"}
]

mock_trucks = [
    {"id": "TR001", "provider_id": 1},
    {"id": "TR002", "provider_id": 1},
    {"id": "TR003", "provider_id": 2}
]

mock_rates = [
    {"product_id": "P1", "scope": 1, "rate": 100},
    {"product_id": "P2", "scope": 1, "rate": 80},
    {"product_id": "P1", "scope": 2, "rate": 200},
]

mock_weights = [
    {"id": "S1", "neto": "500",  "produce": "P1"},
    {"id": "S2", "neto": "300",  "produce": "P1"},
    {"id": "S3", "neto": "na",   "produce": "P2"},  # should be skipped
    {"id": "S4", "neto": "200",  "produce": "P2"},
    {"id": "S5", "neto": "1000", "produce": "P1"},  # belongs to provider 2's truck
]

mock_sessions = {
    "S1": {"truck": "TR001"},
    "S2": {"truck": "TR002"},
    "S3": {"truck": "TR001"},  # neto=na, skipped anyway
    "S4": {"truck": "TR002"},
    "S5": {"truck": "TR003"},  # provider 2's truck
}

mock_weights_edge_cases = [
    {"id": "S10", "neto": "na",  "produce": "P1"},        # na neto
    {"id": "S11", "neto": "abc", "produce": "P1"},        # non-numeric neto
    {"id": "S12", "neto": "500", "produce": "P1"},        # session returns None
    {"id": "S13", "neto": "500", "produce": "P_UNKNOWN"}, # no rate configured
]

mock_sessions_edge_cases = {
    "S10": {"truck": "TR001"},
    "S11": {"truck": "TR001"},
    "S12": None,               # simulates fetch_session returning None
    "S13": {"truck": "TR001"},
}

# ── Expected results ──────────────────────────────────────────────────────────
# Manually derived from the mock data above.
# Valid sessions for provider 1: S1 (TR001), S2 (TR002), S4 (TR002)
# S3 skipped (neto=na), S5 skipped (TR003 belongs to provider 2)

mock_bill_provider1 = {
    "id": "1",
    "name": "ProviderA",
    "from": "20240101000000",
    "to": "20240131235959",
    "truckCount": 2,       # TR001, TR002
    "sessionCount": 3,     # S1, S2, S4
    "products": [
        {"product": "P1", "count": "2", "amount": 800,  "rate": 100, "pay": 80000},
        {"product": "P2", "count": "1", "amount": 200,  "rate": 80,  "pay": 16000},
    ],
    "total": 96000
}