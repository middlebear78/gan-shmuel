import pytest
from models import Provider, Truck, db

######## Test Post/truck#########
def test_create_truck_success(client):
    new_provider = Provider(name="Osem Test")
    db.session.add(new_provider)
    db.session.commit()
    provider_id = new_provider.id 
    
    response = client.post('/truck', json={
        "id": "111-22-333",
        "provider": provider_id
    })
    
    assert response.status_code == 201
    data = response.get_json()
    assert data["id"] == "111-22-333"
    
    saved_truck = Truck.query.get("111-22-333")
    assert saved_truck is not None
    assert saved_truck.provider_id == provider_id

@pytest.mark.parametrize("payload, expected_status", [
    ({"provider": 1}, 400), 
    ({"id": "111-22-333"}, 400), 
    ({"id": "111-22-333", "provider": 9999}, 404),
])
def test_create_truck_failures(client, payload, expected_status):
    response = client.post('/truck', json=payload)
    assert response.status_code == expected_status
    
##########################