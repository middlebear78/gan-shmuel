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
    """Set up test data and clean up after each test.

    Uses max-id approach: captures the highest transaction id before the test,
    then deletes everything above it after. This catches ALL test-created records
    regardless of truck name (including truck='na').
    """
    with app.app_context():
        db.session.remove()

        # Ensure test containers exist
        for cid, w in [("TEST-C1", 300), ("TEST-C2", 200)]:
            if not ContainerRegistered.query.filter_by(container_id=cid).first():
                db.session.add(ContainerRegistered(container_id=cid, weight=w, unit="kg"))
        db.session.commit()

        # Capture the current max id — everything above this was created by the test
        max_id = db.session.query(db.func.max(Transaction.id)).scalar() or 0

    yield

    with app.app_context():
        db.session.remove()
        Transaction.query.filter(Transaction.id > max_id).delete()
        db.session.commit()