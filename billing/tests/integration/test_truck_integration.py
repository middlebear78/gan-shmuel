import pytest
import requests_mock
import os
from models import db, Provider, Truck

# Get base URL from environment
WEIGHT_SERVER_URL = os.getenv("WEIGHT_SERVER_URL", "http://weight-app:5000")

class TestTruckIntegration:

    def test_get_truck_data_flow(self, client):
        provider = Provider(name="Integration Provider")
        db.session.add(provider)
        db.session.commit()
        truck_id = "INT-100"
        truck = Truck(id=truck_id, provider_id=provider.id)
        db.session.add(truck)
        db.session.commit()
        mock_weight_payload = {
            "id": truck_id,
            "tara": 5500,
            "sessions": ["sess-1", "sess-2"]
        }

        with requests_mock.Mocker() as m:
            m.get(f"{WEIGHT_SERVER_URL}/item/{truck_id}", json=mock_weight_payload, status_code=200)
            response = client.get(f"/truck/{truck_id}")
            assert response.status_code == 200
            data = response.get_json()
            assert data["id"] == truck_id
            assert data["tara"] == 5500
            assert data["sessions"] == ["sess-1", "sess-2"]

    def test_get_truck_external_server_down(self, client):
        
        provider = Provider(name="Failure Test Provider")
        db.session.add(provider)
        db.session.commit()
        truck = Truck(id="FAIL-500", provider_id=provider.id)
        db.session.add(truck)
        db.session.commit()

        with requests_mock.Mocker() as m:
            m.get(f"{WEIGHT_SERVER_URL}/item/FAIL-500", status_code=500)
            response = client.get("/truck/FAIL-500")   
            assert response.status_code == 200
            data = response.get_json()
            assert data["tara"] == "na"
            assert data["sessions"] == []

    def test_truck_db_lifecycle(self, client):
        p_res = client.post('/provider', json={"name": "Lifecycle Provider"})
        provider_id = p_res.get_json()["id"]
        truck_id = "LIFECYCLE-1"
        post_res = client.post('/truck', json={"id": truck_id, "provider": provider_id})
        assert post_res.status_code == 201
        db.session.expire_all()
        assert db.session.get(Truck, truck_id) is not None
        new_p_res = client.post('/provider', json={"name": "Second Provider"})
        new_p_id = new_p_res.get_json()["id"]
        put_res = client.put(f'/truck/{truck_id}', json={"provider": new_p_id})
        assert put_res.status_code == 200
        db.session.expire_all()
        updated_truck = db.session.get(Truck, truck_id)
        assert updated_truck is not None
        assert updated_truck.provider_id == int(new_p_id)