"""
Pytest fixtures for lug-vpn-web tests.
"""

import os
import pytest

# Configure test environment before importing app
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
os.environ["DEBUG"] = "False"
os.environ["MAIL_ENABLE"] = "False"


@pytest.fixture(scope="session")
def app():
    """Create application for testing."""
    from app import app as flask_app
    
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    
    yield flask_app


@pytest.fixture(scope="function")
def db(app):
    """Create database tables for each test."""
    from app import db as _db
    
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app, db):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def test_user(app, db):
    """Create a test user."""
    from app.models import User
    
    with app.app_context():
        user = User(email="test@example.com", password="testpassword")
        user.active = True
        user.status = "pass"
        db.session.add(user)
        db.session.commit()
        
        # Return the user ID so we can fetch it in tests
        user_id = user.id
    
    return {"id": user_id, "email": "test@example.com", "password": "testpassword"}
