import pytest
from app import app
from database import db
from models import Transaction, ContainerRegistered
from datetime import datetime


@pytest.fixture(autouse=True)
def client():
    """Create a Flask test client with test data — all in one app context."""
    app.config["TESTING"] = True
    with app.app_context():
        db.session.remove()

        # Ensure test containers exist
        for cid, w in [("TEST-C1", 300), ("TEST-C2", 200)]:
            if not ContainerRegistered.query.filter_by(container_id=cid).first():
                db.session.add(ContainerRegistered(container_id=cid, weight=w, unit="kg"))
        db.session.commit()

        max_id = db.session.query(db.func.max(Transaction.id)).scalar() or 0
        existing_containers = {c.container_id for c in ContainerRegistered.query.all()}

        

        # --- Containers ---
        containers_to_add = [
            ("TEST-C1", 300, "kg"), ("TEST-C2", 200, "kg"),
            ("C-101", 500, "kg"), ("C-102", 1000, "lbs"),
            ("C-103", None, None), ("C-777", 300, "kg"),
            ("C-999", 200, "kg")
        ]

        for cid, w, u in containers_to_add:
            if not ContainerRegistered.query.filter_by(container_id=cid).first():
                db.session.add(ContainerRegistered(container_id=cid, weight=w, unit=u))

        db.session.commit()

        # --- Dates ---
        now = datetime.now()
        current_month = now.replace(day=5) 
        # Safely calculate last month and last year
        last_month = now.replace(month=now.month-1 if now.month > 1 else 12, day=20, year=now.year if now.month > 1 else now.year - 1)
        last_year = now.replace(year=now.year-1, month=6, day=15)
        
        # --- Transactions ---
        
        transactions_to_add = [
            # Session 1: T-123 (Current Month) - Complete
            {"datetime": current_month, "direction": "in", "truck": "T-123", "containers": "C-101,C-102", "bruto": 15000, "session_id": 1},
            {"datetime": current_month, "direction": "out", "truck": "T-123", "containers": "C-101,C-102", "bruto": 15000, "truckTara": 5000, "session_id": 1},
            
            # Session 2: T-123 (Last Month) - Complete
            {"datetime": last_month, "direction": "in", "truck": "T-123", "containers": "C-103", "bruto": 12000, "session_id": 2},
            {"datetime": last_month, "direction": "out", "truck": "T-123", "containers": "C-103", "bruto": 12000, "truckTara": 5200, "session_id": 2},
            
            # NEW Session 3: Standalone container C-777 (Current Month)
            {"datetime": current_month, "direction": "none", "truck": "na", "containers": "C-777", "bruto": 800, "session_id": 3},
            
            # NEW Session 4: T-456 Open Session (In only) - (Current Month)
            {"datetime": current_month, "direction": "in", "truck": "T-456", "containers": "C-101", "bruto": 14000, "session_id": 4},
            
            # NEW Session 5: T-888 (Last Year) - Complete
            {"datetime": last_year, "direction": "in", "truck": "T-888", "containers": "C-101", "bruto": 16000, "session_id": 5},
            {"datetime": last_year, "direction": "out", "truck": "T-888", "containers": "C-101", "bruto": 16000, "truckTara": 6000, "session_id": 5},

            
            # NEW Session 6: Historical data for T-123 (Last Year)
            {"datetime": last_year, "direction": "in", "truck": "T-789", "containers": "C-101", "bruto": 20000, "session_id": 6},
            {"datetime": last_year, "direction": "out", "truck": "T-789", "containers": "C-101", "bruto": 20000, "truckTara": 5100, "session_id": 6}
        ]

        # Iterate, check for existence, and add to the session
        for t_data in transactions_to_add:
            # Check if a transaction with this session_id and direction already exists
            exists = Transaction.query.filter_by(
                session_id=t_data["session_id"], 
                direction=t_data["direction"]
            ).first()
            
            if not exists:
                db.session.add(Transaction(**t_data))
            
        # Commit all containers and transactions at once
        db.session.commit()

        yield app.test_client()

        
        db.session.remove()
        Transaction.query.filter(Transaction.id > max_id).delete()
        ContainerRegistered.query.filter(
            ContainerRegistered.container_id.notin_(existing_containers)
        ).delete()
        db.session.commit()