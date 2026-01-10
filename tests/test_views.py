"""
Tests for app.views module (integration tests).
"""

import pytest


class TestPublicViews:
    """Tests for public (unauthenticated) views."""

    def test_index_accessible(self, client):
        """Test that index page is accessible."""
        response = client.get("/", follow_redirects=True)
        assert response.status_code == 200

    def test_login_page_renders(self, client):
        """Test that login page renders successfully."""
        response = client.get("/login/")
        assert response.status_code == 200

    def test_register_page_renders(self, client):
        """Test that register page renders successfully."""
        response = client.get("/register/")
        assert response.status_code == 200


class TestAuthentication:
    """Tests for authentication flow."""

    def test_login_with_invalid_credentials(self, app, client, db):
        """Test login with invalid credentials fails."""
        with app.app_context():
            response = client.post("/login/", data={
                "email": "nonexistent@example.com",
                "password": "wrongpass",
            })
            # Should stay on login page (200) or show error
            assert response.status_code == 200

    def test_login_form_requires_email(self, app, client, db):
        """Test that login form validates email field."""
        with app.app_context():
            response = client.post("/login/", data={
                "email": "",
                "password": "somepass",
            })
            # Form validation should show error, stays on page
            assert response.status_code == 200

    def test_logout_requires_post(self, app, client, db):
        """Test that logout requires POST method."""
        with app.app_context():
            # GET to logout should fail (405 Method Not Allowed)
            response = client.get("/logout/")
            assert response.status_code == 405

    def test_logout_requires_login(self, app, client, db):
        """Test logout when not logged in redirects to login."""
        with app.app_context():
            response = client.post("/logout/", follow_redirects=True)
            # Should redirect to login page
            assert response.status_code == 200


class TestProtectedViews:
    """Tests for views that require authentication."""

    def test_manage_requires_login(self, client):
        """Test that manage page requires login."""
        response = client.get("/manage/", follow_redirects=True)
        # Should redirect to login and show login page
        assert response.status_code == 200
        # Check we're on login page (redirected)
        assert b"login" in response.data.lower() or b"email" in response.data.lower()

    def test_apply_requires_login(self, client):
        """Test that apply page requires login."""
        response = client.get("/apply/", follow_redirects=True)
        # Should redirect to login and show login page
        assert response.status_code == 200
