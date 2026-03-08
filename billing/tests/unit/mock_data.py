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
    {"product_id": "P1", "scope": "local", "rate": 100},
    {"product_id": "P1", "scope": "global", "rate": 200},
    {"product_id": "P2", "scope": "local", "rate": 80}
]