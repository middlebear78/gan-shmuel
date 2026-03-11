import pytest

from app import create_app
from models import db, Provider


@pytest.fixture
def app():
    app = create_app("TestConfig")

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_provider_create_then_update_flow(client, app):
    create_response = client.post("/provider", json={"name": "Gan Provider"})
    create_data = create_response.get_json()

    assert create_response.status_code == 201
    assert "id" in create_data

    provider_id = int(create_data["id"])

    with app.app_context():
        provider = db.session.get(Provider, provider_id)
        assert provider is not None
        assert provider.name == "Gan Provider"

    update_response = client.put(
        f"/provider/{provider_id}",
        json={"name": "Gan Provider Updated"}
    )
    update_data = update_response.get_json()

    assert update_response.status_code == 200
    assert update_data["id"] == provider_id
    assert update_data["name"] == "Gan Provider Updated"

    with app.app_context():
        provider = db.session.get(Provider, provider_id)
        assert provider is not None
        assert provider.name == "Gan Provider Updated"


def test_provider_duplicate_flow_case_insensitive(client, app):
    first_response = client.post("/provider", json={"name": "Fresh Fruits"})
    first_data = first_response.get_json()

    assert first_response.status_code == 201
    assert "id" in first_data

    second_response = client.post("/provider", json={"name": "fresh fruits"})
    second_data = second_response.get_json()

    assert second_response.status_code == 409
    assert second_data["error"] == "Provider 'fresh fruits' already exists"

    with app.app_context():
        providers = db.session.query(Provider).all()
        assert len(providers) == 1
        assert providers[0].name == "Fresh Fruits"


def test_provider_update_to_existing_other_provider_name_fails(client, app):
    first_response = client.post("/provider", json={"name": "Provider A"})
    second_response = client.post("/provider", json={"name": "Provider B"})

    first_id = int(first_response.get_json()["id"])
    second_id = int(second_response.get_json()["id"])

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    update_response = client.put(
        f"/provider/{second_id}",
        json={"name": "Provider A"}
    )
    update_data = update_response.get_json()

    assert update_response.status_code == 409
    assert update_data["error"] == "Provider 'Provider A' already exists"

    with app.app_context():
        provider_a = db.session.get(Provider, first_id)
        provider_b = db.session.get(Provider, second_id)

        assert provider_a.name == "Provider A"
        assert provider_b.name == "Provider B"


def test_provider_validation_flow_missing_name(client, app):
    response = client.post("/provider", json={})
    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "Provider name is required"

    with app.app_context():
        assert db.session.query(Provider).count() == 0