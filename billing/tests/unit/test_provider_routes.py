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


def test_post_provider_success(client, app):
    response = client.post("/provider", json={"name": "Test Provider"})
    data = response.get_json()

    assert response.status_code == 201
    assert "id" in data

    with app.app_context():
        provider = db.session.query(Provider).filter_by(name="Test Provider").first()
        assert provider is not None
        assert str(provider.id) == data["id"]


def test_post_provider_missing_name(client):
    response = client.post("/provider", json={})
    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "Provider name is required"


def test_post_provider_empty_name(client):
    response = client.post("/provider", json={"name": "   "})
    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "Provider name is required"


def test_post_provider_duplicate_name(client, app):
    with app.app_context():
        db.session.add(Provider(name="Test Provider"))
        db.session.commit()

    response = client.post("/provider", json={"name": "Test Provider"})
    data = response.get_json()

    assert response.status_code == 409
    assert data["error"] == "Provider 'Test Provider' already exists"


def test_post_provider_duplicate_name_case_insensitive(client, app):
    with app.app_context():
        db.session.add(Provider(name="Test Provider"))
        db.session.commit()

    response = client.post("/provider", json={"name": "test provider"})
    data = response.get_json()

    assert response.status_code == 409
    assert data["error"] == "Provider 'test provider' already exists"


def test_put_provider_success(client, app):
    with app.app_context():
        provider = Provider(name="Old Name")
        db.session.add(provider)
        db.session.commit()
        provider_id = provider.id

    response = client.put(f"/provider/{provider_id}", json={"name": "New Name"})
    data = response.get_json()

    assert response.status_code == 200
    assert data["id"] == provider_id
    assert data["name"] == "New Name"

    with app.app_context():
        updated_provider = db.session.get(Provider, provider_id)
        assert updated_provider is not None
        assert updated_provider.name == "New Name"


def test_put_provider_missing_name(client, app):
    with app.app_context():
        provider = Provider(name="Old Name")
        db.session.add(provider)
        db.session.commit()
        provider_id = provider.id

    response = client.put(f"/provider/{provider_id}", json={})
    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "Provider name is required"


def test_put_provider_empty_name(client, app):
    with app.app_context():
        provider = Provider(name="Old Name")
        db.session.add(provider)
        db.session.commit()
        provider_id = provider.id

    response = client.put(f"/provider/{provider_id}", json={"name": "   "})
    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "Provider name is required"


def test_put_provider_not_found(client):
    response = client.put("/provider/99999", json={"name": "New Name"})
    data = response.get_json()

    assert response.status_code == 404
    assert data["error"] == "Provider not found"


def test_put_provider_duplicate_name_of_other_provider(client, app):
    with app.app_context():
        provider1 = Provider(name="Provider One")
        provider2 = Provider(name="Provider Two")
        db.session.add(provider1)
        db.session.add(provider2)
        db.session.commit()
        provider2_id = provider2.id

    response = client.put(f"/provider/{provider2_id}", json={"name": "Provider One"})
    data = response.get_json()

    assert response.status_code == 409
    assert data["error"] == "Provider 'Provider One' already exists"


def test_put_provider_same_name_same_provider_allowed(client, app):
    with app.app_context():
        provider = Provider(name="Same Name")
        db.session.add(provider)
        db.session.commit()
        provider_id = provider.id

    response = client.put(f"/provider/{provider_id}", json={"name": "Same Name"})
    data = response.get_json()

    assert response.status_code == 200
    assert data["id"] == provider_id
    assert data["name"] == "Same Name"