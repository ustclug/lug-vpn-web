"""
Tests for app.models module.
"""

import pytest
from app.models import User, WireGuardPeer

class TestUser:
    """Tests for User model."""

    def test_user_creation(self, app, db):
        """Test creating a new user."""
        with app.app_context():
            user = User(email="newuser@example.com", password="mypassword")
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.email == "newuser@example.com"
            assert user.active is False

    def test_user_password_hashing(self, app, db):
        """Test that passwords are hashed correctly."""
        with app.app_context():
            user = User(email="hash@example.com", password="secret123")
            assert user.passwordhash != "secret123"
            assert user.check_password("secret123") is True
            assert user.check_password("wrongpassword") is False

    def test_user_enable_vpn(self, app, db):
        """Test enabling VPN for a user (should create peers)."""
        with app.app_context():
            user = User(email="vpn@example.com", password="test")
            db.session.add(user)
            db.session.commit()
            
            assert len(WireGuardPeer.get_by_user(user.id)) == 0
            
            user.enable_vpn()
            
            peers = WireGuardPeer.get_by_user(user.id)
            assert len(peers) == 2
            assert peers[0].peer_number == 1
            assert peers[1].peer_number == 2
            assert peers[0].private_key is not None
            assert peers[0].ip_address is not None

    def test_user_regenerate_config(self, app, db):
        """Test regenerating VPN config."""
        with app.app_context():
            user = User(email="regen@example.com", password="test")
            db.session.add(user)
            db.session.commit()
            user.enable_vpn()
            
            peer = WireGuardPeer.get_by_user(user.id)[0]
            old_priv = peer.private_key
            
            user.regenerate_vpn_config()
            
            peer = WireGuardPeer.get_by_user(user.id)[0]
            assert peer.private_key != old_priv


class TestWireGuardPeer:
    """Tests for WireGuardPeer model."""

    def test_peer_generation(self, app, db):
        """Test basic peer properties."""
        with app.app_context():
            user = User(email="p@example.com", password="p")
            db.session.add(user)
            db.session.commit()
            
            # Manually create peer
            from app.wireguard import generate_key, generate_preshared_key
            priv, pub = generate_key()
            psk = generate_preshared_key()
            
            peer = WireGuardPeer(
                user_id=user.id,
                peer_number=1,
                private_key=priv,
                public_key=pub,
                preshared_key=psk,
                ip_address="10.100.0.10"
            )
            db.session.add(peer)
            db.session.commit()
            
            assert peer.id is not None
            assert peer.user_id == user.id
            config = peer.get_config()
            assert "[Interface]" in config
            assert f"PrivateKey = {priv}" in config
            assert "Address = 10.100.0.10" in config
