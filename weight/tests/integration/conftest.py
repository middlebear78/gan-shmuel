import pytest
from app import app
from database import db
from models import Transaction, ContainerRegistered


@pytest.fixture(autouse=True)
def client():
    """Create a Flask test client with test data — all in one app context."""
    app.config["TESTING"] = True
    with app.app_context():
        Transaction.query.filter(Transaction.truck.like("TEST-%")).delete()
        existing = ContainerRegistered.query.filter_by(container_id="TEST-C1").first()
        if not existing:
            db.session.add(ContainerRegistered(container_id="TEST-C1", weight=300, unit="kg"))
        existing2 = ContainerRegistered.query.filter_by(container_id="TEST-C2").first()
        if not existing2:
            db.session.add(ContainerRegistered(container_id="TEST-C2", weight=200, unit="kg"))
        db.session.commit()

        yield app.test_client()

        Transaction.query.filter(Transaction.truck.like("TEST-%")).delete()
        db.session.commit()
