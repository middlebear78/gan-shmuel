import pytest
from app import create_app
from models import db

@pytest.fixture
def client():
    app = create_app("TestConfig")
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()