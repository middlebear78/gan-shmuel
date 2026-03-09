import pytest
from models import Provider, Truck, db
from datetime import datetime
######## Test Post/truck#########
@pytest.mark.parametrize("truck_id", [
    "123-45-678", 
    "99988877",   
    "ABC-123", 
])
def test_create_truck_success(client,truck_id):
    new_provider = Provider(name="Osem Test")
    db.session.add(new_provider)
    db.session.commit()
    provider_id = new_provider.id 
    
    response = client.post('/truck', json={
        "id": truck_id,
        "provider": provider_id
    })
    
    assert response.status_code == 201
    data = response.get_json()
    assert data["id"] == truck_id
    
    saved_truck = db.session.get(Truck, truck_id)
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

@pytest.mark.parametrize("truck_id, from_date, to_date", [
    ("123-45-678", None, None), 
    ("99988877", "20260101000000", "20260102000000"),   
    ("ABC-123", "20251212083000", None), 
])
def test_get_truck_data_success(client, truck_id, from_date, to_date):
    url = f"/truck/{truck_id}"
    new_provider = Provider(name=f"Provider for {truck_id}") 
    db.session.add(new_provider)
    db.session.commit()
    
    truck = Truck(id=truck_id, provider_id=new_provider.id)
    db.session.add(truck)
    db.session.commit() 

    params = {}
    if from_date: params['from'] = from_date
    if to_date: params['to'] = to_date

    response = client.get(url, query_string=params) #
    assert response.status_code == 200 
    
    data = response.get_json()
    assert data["id"] == truck_id
    assert "tara" in data 
    assert "sessions" in data 

def test_get_truck_not_found(client):
    response = client.get('/truck/999-99-999')
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert "999-99-999" in data["error"]



@pytest.mark.parametrize("from_val, to_val, expected_status", [
    # Default case: No dates provided (Should default to 1st of current month)
    (None, None, 200),
    
    # Only start date provided
    ("20260101000000", None, 200),
    
    # Only end date provided
    (None, "20260131235959", 200),
    
    # Full valid date range
    ("20260101000000", "20260102000000", 200),
    
    # Invalid format: Date string too short (Validation test)
    ("202601", None, 400),
    
    # Invalid format: Contains non-numeric characters
    ("20260101abcde", None, 400),
    
    # Invalid date: Non-existent calendar date (May 32nd)
    ("20260532000000", None, 400),
])
def test_get_truck_date_logic(client, from_val, to_val, expected_status):
    unique_suffix = datetime.now().microsecond
    test_truck_id = f"T-{unique_suffix}"
    p = Provider(name=f"Date Logic Test Provider {unique_suffix}")
    db.session.add(p)
    db.session.commit()
    t = Truck(id=test_truck_id, provider_id=p.id)
    db.session.add(t)
    db.session.commit()
    params = {}
    if from_val: params['from'] = from_val
    if to_val: params['to'] = to_val
    response = client.get(f"/truck/{test_truck_id}", query_string=params)
    assert response.status_code == expected_status
    if expected_status == 200:
        data = response.get_json()
        if from_val is None:
            first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            expected_default = first_of_month.strftime('%Y%m%d%H%M%S')
            assert data.get("from") == expected_default

#############################
######## Test PUT /truck/<id> #########

def test_update_truck_success(client):
    old_provider = Provider(name="Old Provider")
    new_provider = Provider(name="New Provider")
    db.session.add_all([old_provider, new_provider])
    db.session.commit()
    
    truck_id = "PUT-123"
    truck = Truck(id=truck_id, provider_id=old_provider.id)
    db.session.add(truck)
    db.session.commit()

    response = client.put(f'/truck/{truck_id}', json={"provider": new_provider.id})

    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == truck_id
    assert data["provider"] == new_provider.id
    
    updated_truck = db.session.get(Truck, truck_id)
    assert updated_truck is not None
    assert updated_truck.provider_id == new_provider.id


@pytest.mark.parametrize("target_truck_id, payload, expected_status", [
    # Missing 'provider' key in JSON payload. 
    ("VALID-TRUCK", {}, 400),

    # Provider ID does not exist in the database. 
    ("VALID-TRUCK", {"provider": 9999}, 404),

    # Truck ID does not exist in the database. 
    ("INVALID-TRUCK", {"provider": "VALID_PROVIDER_ID"}, 404)
])
def test_update_truck_failures(client, target_truck_id, payload, expected_status):
    unique_num = datetime.now().microsecond
    p = Provider(name=f"PUT Fail Provider {unique_num}")
    db.session.add(p)
    db.session.commit()
    
    t = Truck(id="VALID-TRUCK", provider_id=p.id)
    db.session.add(t)
    db.session.commit()

    if payload.get("provider") == "VALID_PROVIDER_ID":
        payload["provider"] = p.id

    response = client.put(f'/truck/{target_truck_id}', json=payload)

    assert response.status_code == expected_status