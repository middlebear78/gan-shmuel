import pytest
import requests_mock
from models import db, Provider, Truck

class TestTruckIntegration:

    def test_get_truck_data_flow(self, client):
        # 1. הכנת נתונים ב-DB
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
            # שימוש ב-ANY מבטיח שנתפוס את הקריאה בלי קשר לאיך שה-URL בנוי
            m.get(requests_mock.ANY, json=mock_weight_payload, status_code=200)
            
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
        
        truck_id = "FAIL-500"
        truck = Truck(id=truck_id, provider_id=provider.id)
        db.session.add(truck)
        db.session.commit()

        with requests_mock.Mocker() as m:
            # מדמים מצב שבו שרת המשקלים מחזיר שגיאה (השרת נפל)
            m.get(requests_mock.ANY, status_code=500)
            
            response = client.get(f"/truck/{truck_id}")   
            
            # האפליקציה שלנו אמורה לשרוד ולהחזיר na
            assert response.status_code == 200
            data = response.get_json()
            assert data["tara"] == "na"
            assert data["sessions"] == []

    def test_truck_db_lifecycle(self, client):
        # בדיקת אינטגרציה מלאה ל-DB: יצירה ועדכון מול MariaDB
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