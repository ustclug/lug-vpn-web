"""
Tests for app.models module.
"""

import pytest


class TestUser:
    """Tests for User model."""

    def test_user_creation(self, app, db):
        """Test creating a new user."""
        from app.models import User
        
        with app.app_context():
            user = User(email="newuser@example.com", password="mypassword")
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.email == "newuser@example.com"
            assert user.active is False
            assert user.admin is False
            assert user.status == "none"

    def test_user_password_hashing(self, app, db):
        """Test that passwords are hashed correctly."""
        from app.models import User
        
        with app.app_context():
            user = User(email="hash@example.com", password="secret123")
            
            # Password should not be stored in plain text
            assert user.passwordhash != "secret123"
            assert user.salt is not None
            assert len(user.salt) > 0
            
            # Password check should work
            assert user.check_password("secret123") is True
            assert user.check_password("wrongpassword") is False

    def test_user_set_password(self, app, db):
        """Test changing user password."""
        from app.models import User
        
        with app.app_context():
            user = User(email="setpass@example.com", password="oldpass")
            old_hash = user.passwordhash
            old_salt = user.salt
            
            user.set_password("newpass")
            
            # Hash and salt should change
            assert user.passwordhash != old_hash
            # Salt may or may not change depending on implementation
            
            # New password should work
            assert user.check_password("newpass") is True
            assert user.check_password("oldpass") is False

    def test_user_get_by_email(self, app, db):
        """Test finding a user by email."""
        from app.models import User
        
        with app.app_context():
            user = User(email="findme@example.com", password="test")
            db.session.add(user)
            db.session.commit()
            
            found = User.get_user_by_email("findme@example.com")
            assert found is not None
            assert found.email == "findme@example.com"
            
            not_found = User.get_user_by_email("notexist@example.com")
            assert not_found is None

    def test_user_set_active(self, app, db):
        """Test activating a user."""
        from app.models import User
        
        with app.app_context():
            user = User(email="activate@example.com", password="test")
            db.session.add(user)
            db.session.commit()
            
            assert user.active is False
            user.set_active()
            assert user.active is True


class TestVPNAccount:
    """Tests for VPNAccount model."""

    def test_vpn_account_creation(self, app, db):
        """Test creating a VPN account."""
        from app.models import VPNAccount
        
        with app.app_context():
            account = VPNAccount(username="vpnuser@example.com", password="vpnpass")
            db.session.add(account)
            db.session.commit()
            
            assert account.id is not None
            assert account.username == "vpnuser@example.com"
            assert account.value == "vpnpass"
            assert account.attribute == "Cleartext-Password"
            assert account.op == ":="

    def test_vpn_account_get_by_email(self, app, db):
        """Test finding a VPN account by email."""
        from app.models import VPNAccount
        
        with app.app_context():
            account = VPNAccount(username="find@vpn.com", password="pass")
            db.session.add(account)
            db.session.commit()
            
            found = VPNAccount.get_account_by_email("find@vpn.com")
            assert found is not None
            assert found.username == "find@vpn.com"
            
            not_found = VPNAccount.get_account_by_email("noexist@vpn.com")
            assert not_found is None

    def test_vpn_account_add(self, app, db):
        """Test adding a VPN account via class method."""
        from app.models import VPNAccount
        
        with app.app_context():
            VPNAccount.add("add@vpn.com", "mypassword")
            
            account = VPNAccount.get_account_by_email("add@vpn.com")
            assert account is not None
            assert account.value == "mypassword"

    def test_vpn_account_add_duplicate_raises(self, app, db):
        """Test that adding duplicate account raises exception."""
        from app.models import VPNAccount
        
        with app.app_context():
            VPNAccount.add("dup@vpn.com", "pass1")
            
            with pytest.raises(Exception, match="account already exist"):
                VPNAccount.add("dup@vpn.com", "pass2")

    def test_vpn_account_delete(self, app, db):
        """Test deleting a VPN account."""
        from app.models import VPNAccount
        
        with app.app_context():
            VPNAccount.add("delete@vpn.com", "pass")
            assert VPNAccount.get_account_by_email("delete@vpn.com") is not None
            
            VPNAccount.delete("delete@vpn.com")
            assert VPNAccount.get_account_by_email("delete@vpn.com") is None

    def test_vpn_account_delete_nonexistent_raises(self, app, db):
        """Test that deleting non-existent account raises exception."""
        from app.models import VPNAccount
        
        with app.app_context():
            with pytest.raises(Exception, match="account not found"):
                VPNAccount.delete("nonexistent@vpn.com")

    def test_vpn_account_changepass(self, app, db):
        """Test changing VPN account password."""
        from app.models import VPNAccount
        
        with app.app_context():
            VPNAccount.add("change@vpn.com", "oldpass")
            VPNAccount.changepass("change@vpn.com", "newpass")
            
            account = VPNAccount.get_account_by_email("change@vpn.com")
            assert account.value == "newpass"
