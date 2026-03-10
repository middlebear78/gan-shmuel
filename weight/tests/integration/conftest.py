import pytest
from app import app
from database import db
from models import Transaction, ContainerRegistered
from datetime import datetime, timedelta


@pytest.fixture(autouse=True)
def client():
    """Create a Flask test client with test data — all in one app context."""
    app.config["TESTING"] = True
    with app.app_context():
        db.session.remove()

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

        max_id = db.session.query(db.func.max(Transaction.id)).scalar() or 0
        existing_containers = {c.container_id for c in ContainerRegistered.query.all()}

        yield app.test_client()

        db.session.remove()
        Transaction.query.filter(Transaction.id > max_id).delete()
        ContainerRegistered.query.filter(
            ContainerRegistered.container_id.notin_(existing_containers)
        ).delete()
        db.session.commit()