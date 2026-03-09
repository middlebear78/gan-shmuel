from datetime import datetime

def test_get_item_container_kg(client):
    response = client.get("/item/C-101")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "C-101"
    assert data["tara"] == 500
    assert 1 in data["sessions"]

def test_get_item_container_lbs(client):
    response = client.get("/item/C-102")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "C-102"
    assert data["tara"] == 453 

def test_get_item_truck_default_dates(client):
    response = client.get("/item/T-123")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "T-123"
    assert data["tara"] == 5000
    assert data["sessions"] == [1]

def test_get_item_truck_custom_dates(client):
    now = datetime.now()
    from_date = now.replace(year=now.year-1, month=1, day=1).strftime("%Y%m%d%H%M%S")
    to_date = now.replace(year=now.year+1, month=12, day=31).strftime("%Y%m%d%H%M%S")
    
    response = client.get(f"/item/T-123?from={from_date}&to={to_date}")
    assert response.status_code == 200
    data = response.get_json()
    assert 1 in data["sessions"]
    assert 2 in data["sessions"]

def test_get_item_not_found(client):
    response = client.get("/item/NON-EXISTENT-ITEM")
    assert response.status_code == 404

def test_get_item_container_default_dates_excludes_old(client):
    """Test that a container's older sessions are excluded by default dates."""
    # C-103 only has transactions from last month (session 2).
    # Default 'from' is the 1st of the current month.
    response = client.get("/item/C-103")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "C-103"
    assert data["tara"] == "na" # It was registered with NULL weight
    assert data["sessions"] == [] # Should be empty because session 2 is too old

def test_get_item_container_custom_dates_includes_old(client):
    """Test that custom dates can include a container's older sessions."""
    now = datetime.now()
    # Create a 'from' date from the start of last year to ensure we catch last month
    from_date = now.replace(year=now.year-1, month=1, day=1).strftime("%Y%m%d%H%M%S")
    
    # Now query C-103 with the expanded date range
    response = client.get(f"/item/C-103?from={from_date}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "C-103"
    assert 2 in data["sessions"] # Session 2 should now be found!

def test_get_item_container_custom_dates_strict_range(client):
    """Test strict date ranges that exclude the current month's transactions."""
    now = datetime.now()
    
    # Set 'to' date to exactly the 1st of this month at 00:00:00
    to_date = now.replace(day=1, hour=0, minute=0, second=0).strftime("%Y%m%d%H%M%S")
    from_date = now.replace(year=now.year-1, month=1, day=1).strftime("%Y%m%d%H%M%S")
    
    response = client.get(f"/item/C-101?from={from_date}&to={to_date}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "C-101"
    assert data["sessions"] == [5,6]

def test_get_item_invalid_date_format(client):
    """Test that passing incorrectly formatted dates returns a 400 error."""
    # The API expects yyyymmddhhmmss, so this standard format should fail
    response = client.get("/item/C-101?from=2026-01-01") 
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "invalid datetime format" in data["error"]

def test_get_item_unused_container(client):
    """Test a registered container that has no transaction history."""
    response = client.get("/item/C-999")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "C-999"
    assert data["tara"] == 200
    assert data["sessions"] == [] # Never used, should be empty

def test_get_item_standalone_container(client):
    """Test a container that was weighed by itself (direction='none')."""
    response = client.get("/item/C-777")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "C-777"
    assert 3 in data["sessions"] # Session 3 is the standalone weighing

def test_get_item_truck_open_session(client):
    """Test a truck that has an 'in' but no 'out' yet."""
    response = client.get("/item/T-456")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "T-456"
    assert data["tara"] == "na" # No 'out' transaction exists, so tara is unknown
    assert 4 in data["sessions"] # But the session ID should still be listed

def test_get_item_truck_very_old_session(client):
    """Test a truck whose only transactions are outside the default date range."""
    # T-789 has transactions from 'last_year', which is outside the default current-month range.
    response = client.get("/item/T-789")
    assert response.status_code == 200 
    data = response.get_json() 
    # Verify the ID matches
    assert data["id"] == "T-789" 
    # In the new dataset, T-789 (Session 6) has a truckTara of 5100.
    # The 'tara' should be returned as the last known weight regardless of the date filter.
    assert data["tara"] == 5100 
    # Since Session 6 is from 'last_year', it should not appear in the default 
    # date range (which typically starts at the beginning of the current month).
    assert data["sessions"] == []