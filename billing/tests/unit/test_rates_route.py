import os
import tempfile
import pytest
from openpyxl import Workbook

from app import create_app
from models import db, Provider, Rate, RatesFile
from routes import rates_route


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


@pytest.fixture
def temp_in_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        monkeypatch.setattr(rates_route, "IN_DIR", temp_dir)
        yield temp_dir


def create_rates_excel(file_path, rows):
    wb = Workbook()
    ws = wb.active

    ws.append(["Product", "Rate", "Scope"])

    for row in rows:
        ws.append(row)

    wb.save(file_path)


def test_post_rates_success_with_all_scope(client, app, temp_in_dir):
    file_path = os.path.join(temp_in_dir, "rates.xlsx")

    create_rates_excel(file_path, [
        ("Navel", 93, "ALL"),
        ("Blood", 112, "ALL"),
        ("Mandarin", 104, "ALL"),
    ])

    response = client.post("/rates", json={"file": "rates.xlsx"})
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "OK"
    assert data["file"] == "rates.xlsx"
    assert data["rows"] == 3
    assert data["inserted"] == 3
    assert data["updated"] == 0

    with app.app_context():
        rates = db.session.query(Rate).all()
        latest_file = db.session.query(RatesFile).first()

        assert len(rates) == 3
        assert latest_file is not None
        assert latest_file.filename == "rates.xlsx"


def test_post_rates_success_with_provider_scope(client, app, temp_in_dir):
    with app.app_context():
        provider = Provider(name="Test Provider")
        db.session.add(provider)
        db.session.commit()
        provider_id = provider.id

    file_path = os.path.join(temp_in_dir, "rates.xlsx")

    create_rates_excel(file_path, [
        ("Mandarin", 120, provider_id),
    ])

    response = client.post("/rates", json={"file": "rates.xlsx"})
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "OK"
    assert data["rows"] == 1
    assert data["inserted"] == 1
    assert data["updated"] == 0

    with app.app_context():
        rate = db.session.query(Rate).filter_by(product_id="Mandarin", scope=str(provider_id)).first()
        assert rate is not None
        assert rate.rate == 120


def test_post_rates_missing_file_field(client):
    response = client.post("/rates", json={})
    data = response.get_json()

    assert response.status_code == 400
    assert "error" in data
    assert "file is required" in data["error"]


def test_post_rates_file_not_found(client, temp_in_dir):
    response = client.post("/rates", json={"file": "not_exists.xlsx"})
    data = response.get_json()

    assert response.status_code == 404
    assert data["error"] == "file not found"


def test_post_rates_provider_scope_not_found(client, temp_in_dir):
    file_path = os.path.join(temp_in_dir, "rates.xlsx")

    create_rates_excel(file_path, [
        ("Mandarin", 120, 43),
    ])

    response = client.post("/rates", json={"file": "rates.xlsx"})
    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "bad input"
    assert "Provider id in Scope does not exist" in data["details"]


def test_post_rates_updates_existing_rate(client, app, temp_in_dir):
    file_path = os.path.join(temp_in_dir, "rates.xlsx")

    create_rates_excel(file_path, [
        ("Navel", 93, "ALL"),
    ])

    first_response = client.post("/rates", json={"file": "rates.xlsx"})
    first_data = first_response.get_json()

    assert first_response.status_code == 200
    assert first_data["inserted"] == 1
    assert first_data["updated"] == 0

    create_rates_excel(file_path, [
        ("Navel", 99, "ALL"),
    ])

    second_response = client.post("/rates", json={"file": "rates.xlsx"})
    second_data = second_response.get_json()

    assert second_response.status_code == 200
    assert second_data["inserted"] == 0
    assert second_data["updated"] == 1

    with app.app_context():
        rate = db.session.query(Rate).filter_by(product_id="Navel", scope="ALL").first()
        assert rate is not None
        assert rate.rate == 99


def test_get_rates_success(client, app, temp_in_dir):
    file_path = os.path.join(temp_in_dir, "rates.xlsx")

    create_rates_excel(file_path, [
        ("Navel", 93, "ALL"),
    ])

    with app.app_context():
        db.session.add(RatesFile(filename="rates.xlsx"))
        db.session.commit()

    response = client.get("/rates")

    assert response.status_code == 200
    assert "attachment; filename=rates.xlsx" in response.headers["Content-Disposition"]
    assert response.headers["Content-Type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_get_rates_no_uploaded_file_record(client):
    response = client.get("/rates")
    data = response.get_json()

    assert response.status_code == 404
    assert data["error"] == "no rates file uploaded yet"


def test_get_rates_file_record_exists_but_file_missing(client, app, temp_in_dir):
    with app.app_context():
        db.session.add(RatesFile(filename="rates.xlsx"))
        db.session.commit()

    response = client.get("/rates")
    data = response.get_json()

    assert response.status_code == 404
    assert data["error"] == "rates file record exists but file is missing"
    assert data["file"] == "rates.xlsx"