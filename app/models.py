from app import db
from flask_login import UserMixin
from app.utils import *
import hashlib
import datetime
import ipaddress
from app.config import Config
from app.wireguard import generate_key, generate_preshared_key, generate_client_config

class WireGuardPeer(db.Model):
    __tablename__ = 'wireguard_peer'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    peer_number = db.Column(db.Integer, nullable=False) # 1 or 2
    private_key = db.Column(db.String(44), nullable=False)
    public_key = db.Column(db.String(44), nullable=False)
    preshared_key = db.Column(db.String(44), nullable=False)
    ip_address = db.Column(db.String(40), nullable=False) # IPv4 or IPv6
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    user = db.relationship('User', backref=db.backref('peers', lazy=True, cascade="all, delete-orphan"))

    @classmethod
    def get_by_user(cls, user_id):
        return cls.query.filter_by(user_id=user_id).order_by(cls.peer_number).all()

    @classmethod
    def generate_ip(cls, user_id, peer_number):
        # Simple deterministic IP allocation based on user_id
        # Assuming WG_ADDRESS_POOL = 10.100.0.0/16
        # Start from .2
        # Offset = (user_id - 1) * 2 + (peer_number - 1) + 2
        try:
            network = ipaddress.ip_network(Config.WG_ADDRESS_POOL)
            offset = (user_id - 1) * 2 + (peer_number - 1) + 2
            if offset >= network.num_addresses:
                 raise ValueError("Address pool exhausted")
            return str(network[offset])
        except Exception:
            # Fallback or error
            return "10.100.0.0"

    def regenerate_keys(self):
        priv, pub = generate_key()
        self.private_key = priv
        self.public_key = pub
        self.preshared_key = generate_preshared_key()
        self.updated_at = datetime.datetime.now()
        db.session.add(self)
        db.session.commit()

    def get_config(self):
        return generate_client_config(self.private_key, self.ip_address, preshared_key=self.preshared_key)

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(63), unique=True)
    passwordhash = db.Column(db.String(127), nullable=False)
    salt = db.Column(db.String(127), nullable=False)
    active = db.Column(db.Boolean(), default=False)
    admin = db.Column(db.Boolean(), default=False)
    status = db.Column(db.Enum('none', 'applying', 'pass',
                               'reject', 'banned'), default='none')
    name = db.Column(db.String(127))
    studentno = db.Column(db.String(127))
    phone = db.Column(db.String(127))
    reason = db.Column(db.Text)
    applytime = db.Column(db.DateTime)
    vpnpassword = db.Column(db.String(127)) # Legacy field kept for schema compatibility, unused
    rejectreason = db.Column(db.Text)
    banreason = db.Column(db.Text)
    location = db.Column(db.String(127))

    def __init__(self, email, password):
        self.email = email
        self.set_password(password)

    def set_active(self):
        # Refactored: Just activate, no RADIUS check
        self.active = True
        self.save()

    def set_password(self, password):
        self.salt = random_string(10)
        s = hashlib.sha256()
        s.update(password.encode('utf-8'))
        s.update(self.salt.encode('utf-8'))
        self.passwordhash = s.hexdigest()

    def check_password(self, password):
        s = hashlib.sha256()
        s.update(password.encode('utf-8'))
        s.update(self.salt.encode('utf-8'))
        return self.passwordhash == s.hexdigest()

    def enable_vpn(self):
        # Generate 2 peers if they don't exist
        existing_peers = WireGuardPeer.query.filter_by(user_id=self.id).all()
        if not existing_peers:
            for i in range(1, 3):
                priv, pub = generate_key()
                psk = generate_preshared_key()
                ip = WireGuardPeer.generate_ip(self.id, i)
                peer = WireGuardPeer(
                    user_id=self.id,
                    peer_number=i,
                    private_key=priv,
                    public_key=pub,
                    preshared_key=psk,
                    ip_address=ip
                )
                db.session.add(peer)
            db.session.commit()
            # Trigger SSE update? Handled by views invoking this, or signal?
            # For now, just DB update.

    def disable_vpn(self):
        # Remove all peers
        WireGuardPeer.query.filter_by(user_id=self.id).delete()
        db.session.commit()

    def regenerate_vpn_config(self):
        # Regenerate keys for all peers
        for peer in self.peers:
            peer.regenerate_keys()
        # If no peers (shouldn't happen if enabled), create them
        if not self.peers:
            self.enable_vpn()

    # Legacy method compatibility or just removal
    def change_vpn_password(self, password=None):
        # Replaced by regenerate logic, but keeping method sig if calls exist might be safe?
        # Plan said: "User.change_vpn_password() -> regenerate WireGuard keys"
        self.regenerate_vpn_config()

    @classmethod
    def get_applying(cls):
        return cls.query.filter_by(status='applying').order_by(cls.applytime).all()

    @classmethod
    def get_rejected(cls):
        return cls.query.filter_by(status='reject').order_by(cls.applytime.desc()).all()

    @classmethod
    def get_users(cls):
        return cls.query.filter(db.or_(cls.status == 'pass', cls.status == 'banned')).order_by(cls.id).all()

    @classmethod
    def get_inactive(cls):
        return cls.query.filter_by(active=False).order_by(cls.applytime.desc()).all()

    def pass_apply(self):
        self.status = 'pass'
        self.enable_vpn()
        self.save()

    def reject_apply(self, reason=''):
        self.status = 'reject'
        self.rejectreason = reason
        self.save()

    def ban(self, reason=''):
        self.status = 'banned'
        self.banreason = reason
        self.disable_vpn()
        self.save()

    def unban(self):
        self.status = 'pass'
        self.enable_vpn()
        self.save()

    def save(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_user_by_email(cls, email):
        return cls.query.filter_by(email=email).first()

    @classmethod
    def get_user_by_id(cls, id):
        return cls.query.get(id)
