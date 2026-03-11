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


def test_rates_full_flow_all_scope_post_then_get(client, app, temp_in_dir):
    file_path = os.path.join(temp_in_dir, "rates.xlsx")
    create_rates_excel(file_path, [
        ("Navel", 93, "ALL"),
        ("Blood", 112, "ALL"),
        ("Mandarin", 104, "ALL"),
    ])

    post_response = client.post("/rates", json={"file": "rates.xlsx"})
    post_data = post_response.get_json()

    assert post_response.status_code == 200
    assert post_data["status"] == "OK"
    assert post_data["rows"] == 3
    assert post_data["inserted"] == 3
    assert post_data["updated"] == 0

    with app.app_context():
        assert db.session.query(Rate).count() == 3
        latest_file = db.session.query(RatesFile).first()
        assert latest_file is not None
        assert latest_file.filename == "rates.xlsx"

    get_response = client.get("/rates")

    assert get_response.status_code == 200
    assert "attachment; filename=rates.xlsx" in get_response.headers["Content-Disposition"]
    assert get_response.headers["Content-Type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(get_response.data) > 0


def test_rates_full_flow_with_provider_scope(client, app, temp_in_dir):
    create_provider_response = client.post("/provider", json={"name": "Rates Provider"})
    create_provider_data = create_provider_response.get_json()

    assert create_provider_response.status_code == 201
    provider_id = int(create_provider_data["id"])

    file_path = os.path.join(temp_in_dir, "rates_provider.xlsx")
    create_rates_excel(file_path, [
        ("Valencia", 90, provider_id),
        ("Tangerine", 85, provider_id),
    ])

    post_response = client.post("/rates", json={"file": "rates_provider.xlsx"})
    post_data = post_response.get_json()

    assert post_response.status_code == 200
    assert post_data["status"] == "OK"
    assert post_data["rows"] == 2
    assert post_data["inserted"] == 2

    with app.app_context():
        rate1 = db.session.query(Rate).filter_by(product_id="Valencia", scope=str(provider_id)).first()
        rate2 = db.session.query(Rate).filter_by(product_id="Tangerine", scope=str(provider_id)).first()

        assert rate1 is not None
        assert rate1.rate == 90
        assert rate2 is not None
        assert rate2.rate == 85


def test_rates_reupload_updates_existing_rows_and_latest_file(client, app, temp_in_dir):
    first_file = os.path.join(temp_in_dir, "rates_v1.xlsx")
    second_file = os.path.join(temp_in_dir, "rates_v2.xlsx")

    create_rates_excel(first_file, [
        ("Navel", 93, "ALL"),
        ("Blood", 112, "ALL"),
    ])

    first_response = client.post("/rates", json={"file": "rates_v1.xlsx"})
    first_data = first_response.get_json()

    assert first_response.status_code == 200
    assert first_data["inserted"] == 2
    assert first_data["updated"] == 0

    create_rates_excel(second_file, [
        ("Navel", 99, "ALL"),
        ("Blood", 112, "ALL"),
        ("Clementine", 113, "ALL"),
    ])

    second_response = client.post("/rates", json={"file": "rates_v2.xlsx"})
    second_data = second_response.get_json()

    assert second_response.status_code == 200
    assert second_data["inserted"] == 1
    assert second_data["updated"] == 1

    with app.app_context():
        navel = db.session.query(Rate).filter_by(product_id="Navel", scope="ALL").first()
        blood = db.session.query(Rate).filter_by(product_id="Blood", scope="ALL").first()
        clementine = db.session.query(Rate).filter_by(product_id="Clementine", scope="ALL").first()
        latest_file = db.session.query(RatesFile).first()

        assert navel is not None
        assert navel.rate == 99
        assert blood is not None
        assert blood.rate == 112
        assert clementine is not None
        assert clementine.rate == 113
        assert latest_file is not None
        assert latest_file.filename == "rates_v2.xlsx"

    get_response = client.get("/rates")

    assert get_response.status_code == 200
    assert "attachment; filename=rates_v2.xlsx" in get_response.headers["Content-Disposition"]


def test_rates_invalid_provider_scope_flow_fails_and_does_not_save(client, app, temp_in_dir):
    file_path = os.path.join(temp_in_dir, "bad_rates.xlsx")
    create_rates_excel(file_path, [
        ("Mandarin", 120, 43),
    ])

    response = client.post("/rates", json={"file": "bad_rates.xlsx"})
    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "bad input"
    assert "Provider id in Scope does not exist" in data["details"]

    with app.app_context():
        assert db.session.query(Rate).count() == 0
        assert db.session.query(RatesFile).count() == 0


def test_rates_get_without_uploaded_file_record(client, app):
    response = client.get("/rates")
    data = response.get_json()

    assert response.status_code == 404
    assert data["error"] == "no rates file uploaded yet"