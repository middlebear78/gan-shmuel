import pytest
from app import app
from database import db
from models import Transaction, ContainerRegistered


@pytest.fixture
def client():
    """Create a Flask test client."""
    app.config["TESTING"] = True
    yield app.test_client()

@pytest.fixture(autouse=True)
def setup_and_cleanup():
    """Set up test data and clean up after each test."""
    with app.app_context():
        Transaction.query.filter(Transaction.truck.like("TEST-%")).delete()
        existing = ContainerRegistered.query.filter_by(container_id="TEST-C1").first()
        if not existing:
            db.session.add(ContainerRegistered(container_id="TEST-C1", weight=300, unit="kg"))
        existing2 = ContainerRegistered.query.filter_by(container_id="TEST-C2").first()
        if not existing2:
            db.session.add(ContainerRegistered(container_id="TEST-C2", weight=200, unit="kg"))
        db.session.commit()
    yield
    with app.app_context():
        Transaction.query.filter(Transaction.truck.like("TEST-%")).delete()
        db.session.commit()
