"""
Tests for app.views module (integration tests).
"""

import pytest
from app.models import User

class TestViews:
    
    def test_index_redirects(self, client):
        response = client.get("/", follow_redirects=True)
        assert response.status_code == 200
        assert b"login" in response.data.lower()

    def test_auth_flow(self, app, client, db):
        with app.app_context():
            # Create user
            user = User(email="user@test.com", password="password")
            user.set_active()
            user.status = "pass" # Approved
            db.session.add(user)
            db.session.commit()
            
            # Login
            client.post("/login/", data={"email": "user@test.com", "password": "password"}, follow_redirects=True)
            
            # Access index
            resp = client.get("/")
            assert resp.status_code == 200
            # Should show WireGuard UI
            assert b"WireGuard Configuration" in resp.data

    def test_wireguard_api(self, app, client, db):
        with app.app_context():
            user = User(email="wg@test.com", password="password")
            user.set_active()
            user.status = "pass"
            db.session.add(user)
            db.session.commit()
            
            client.post("/login/", data={"email": "wg@test.com", "password": "password"}, follow_redirects=True)
            
            # Trigger enable_vpn by visiting index (it auto-provisions)
            client.get("/")
            
            # Check config download
            resp = client.get("/api/wireguard/config/1")
            assert resp.status_code == 200
            assert b"[Interface]" in resp.data
            
            # Check regenerate
            resp = client.post("/api/wireguard/regenerate", follow_redirects=True)
            assert resp.status_code == 200
            assert b"configurations regenerated" in resp.data.lower()

    def test_sse_endpoint_auth(self, app, client):
        # Without token
        resp = client.get("/api/sse/server-config")
        assert resp.status_code == 403
        
        # With token
        token = app.config['SSE_TOKEN']
        resp = client.get(f"/api/sse/server-config?token={token}")
        assert resp.status_code == 200
        assert resp.mimetype == "text/event-stream"
