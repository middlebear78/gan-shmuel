import pytest
from datetime import datetime
from app import app
from database import db
from models import ContainerRegistered, Transaction

# 1. Configure the application exactly ONCE for the entire test session
@pytest.fixture(scope="session", autouse=True)
def configure_test_app():
    # Override config for testing
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    # Safely reset the SQLAlchemy extension before ANY tests run
    # This prevents the "teardown_appcontext" AssertionError
    if 'sqlalchemy' in app.extensions:
        del app.extensions['sqlalchemy']
    db.init_app(app)

# 2. Provide a clean database and test client for EACH test
@pytest.fixture
def client():
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            
            # --- Containers ---
            c1 = ContainerRegistered(container_id="C-101", weight=500, unit="kg")
            c2 = ContainerRegistered(container_id="C-102", weight=1000, unit="lbs")
            c3 = ContainerRegistered(container_id="C-103", weight=None, unit=None)
            
            # NEW: A container for standalone weighing
            c4 = ContainerRegistered(container_id="C-777", weight=300, unit="kg") 
            # NEW: A container that is registered but has no transactions
            c5 = ContainerRegistered(container_id="C-999", weight=200, unit="kg") 
            
            db.session.add_all([c1, c2, c3, c4, c5])
            
            # --- Dates ---
            now = datetime.now()
            current_month = now.replace(day=5) 
            # Safely calculate last month and last year
            last_month = now.replace(month=now.month-1 if now.month > 1 else 12, day=20, year=now.year if now.month > 1 else now.year - 1)
            last_year = now.replace(year=now.year-1, month=6, day=15)
            
            # --- Transactions ---
            
            # Session 1: T-123 (Current Month) - Complete
            t1 = Transaction(datetime=current_month, direction="in", truck="T-123", containers="C-101,C-102", bruto=15000, session_id=1)
            t2 = Transaction(datetime=current_month, direction="out", truck="T-123", containers="C-101,C-102", bruto=15000, truckTara=5000, session_id=1)
            
            # Session 2: T-123 (Last Month) - Complete
            t3 = Transaction(datetime=last_month, direction="in", truck="T-123", containers="C-103", bruto=12000, session_id=2)
            t4 = Transaction(datetime=last_month, direction="out", truck="T-123", containers="C-103", bruto=12000, truckTara=5200, session_id=2)
            
            # NEW Session 3: Standalone container C-777 (Current Month)
            t5 = Transaction(datetime=current_month, direction="none", truck="na", containers="C-777", bruto=800, session_id=3)
            
            # NEW Session 4: T-456 Open Session (In only) - (Current Month)
            t6 = Transaction(datetime=current_month, direction="in", truck="T-456", containers="C-101", bruto=14000, session_id=4)
            
            # NEW Session 5: T-888 (Last Year) - Complete
            t7 = Transaction(datetime=last_year, direction="in", truck="T-888", containers="C-101", bruto=16000, session_id=5)
            t8 = Transaction(datetime=last_year, direction="out", truck="T-888", containers="C-101", bruto=16000, truckTara=6000, session_id=5)
            
            db.session.add_all([t1, t2, t3, t4, t5, t6, t7, t8])
            db.session.commit()
            
            yield client
            
            db.session.remove()
            db.drop_all()

# --- Tests ---

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.data.decode("utf-8") == "OK"

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
    
    # C-101 has transactions THIS month (Session 1 & 4) and LAST YEAR (Session 5). 
    # By restricting the search to end right before this month started, 
    # it should ONLY return Session 5.
    response = client.get(f"/item/C-101?from={from_date}&to={to_date}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "C-101"
    assert data["sessions"] == [5] # Updated to expect Session 5!

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
    response = client.get("/item/T-888")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "T-888"
    assert data["tara"] == 6000 # Last known tara is still valid regardless of date
    assert data["sessions"] == [] # But the session list should be empty by default