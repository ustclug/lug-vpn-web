"""
Configuration module for lug-vpn-web.

All configuration is read from environment variables at import time.
"""

import os
from typing import Any


def _get_bool(key: str, default: bool = False) -> bool:
    """Parse a boolean from an environment variable."""
    val = os.environ.get(key, "").lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


def _get_int(key: str, default: int) -> int:
    """Parse an integer from an environment variable."""
    val = os.environ.get(key, "")
    if val.isdigit():
        return int(val)
    return default


class Config:
    """Flask configuration class, loaded from environment variables."""

    # Database
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "SQLALCHEMY_DATABASE_URI",
        "mysql+pymysql://{user}:{password}@{host}/{database}?charset={charset}".format(
            user=os.environ.get("MYSQL_USER", "radius"),
            password=os.environ.get("MYSQL_PASSWORD", "radius"),
            host=os.environ.get("MYSQL_HOST", "mysql"),
            database=os.environ.get("MYSQL_DATABASE", "radius"),
            charset=os.environ.get("MYSQL_CHARSET", "utf8"),
        ),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Flask core
    DEBUG: bool = _get_bool("DEBUG", default=False)
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me-to-a-random-string")
    SERVER_NAME: str | None = os.environ.get("SERVER_NAME") or None
    SEND_FILE_MAX_AGE_DEFAULT: int = _get_int("SEND_FILE_MAX_AGE_DEFAULT", 3600)

    # Mail
    MAIL_ENABLE: bool = _get_bool("MAIL_ENABLE", default=False)
    MAIL_SERVER: str = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT: int = _get_int("MAIL_PORT", 25)
    MAIL_USE_TLS: bool = _get_bool("MAIL_TLS_ENABLE", default=False)
    MAIL_USE_SSL: bool = _get_bool("MAIL_SSL_ENABLE", default=False)
    MAIL_USERNAME: str = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER: str = os.environ.get("MAIL_SENDER", "noreply@vpn.example.org")
    ADMIN_MAIL: str = os.environ.get("ADMIN_MAIL", "vpn@example.org")

    # WireGuard
    WG_SERVER_ENDPOINT: str = os.environ.get("WG_SERVER_ENDPOINT", "vpn.example.org:51820")
    WG_SERVER_PRIVATE_KEY: str = os.environ.get("WG_SERVER_PRIVATE_KEY", "")
    try:
        if not WG_SERVER_PRIVATE_KEY:
            raise ValueError("WG_SERVER_PRIVATE_KEY is not set")
        from wireguard_tools import WireguardKey
        # This will raise ValueError if the key is invalid (e.g. "change-me", "REPLACE_ME", or empty)
        WireguardKey(WG_SERVER_PRIVATE_KEY).public_key()
    except Exception as e:
        raise ValueError(f"Invalid WG_SERVER_PRIVATE_KEY: {e}. Please set a valid Base64 encoded Curve25519 private key.")
    WG_LISTEN_PORT: int = _get_int("WG_LISTEN_PORT", 51820)
    WG_SERVER_INTERFACE_IP: str = os.environ.get("WG_SERVER_INTERFACE_IP", "10.100.0.1/16")
    WG_MTU: int = _get_int("WG_MTU", 1420)
    WG_ADDRESS_POOL: str = os.environ.get("WG_ADDRESS_POOL", "10.100.0.0/16")
    WG_DNS: str = os.environ.get("WG_DNS", "1.1.1.1")
    WG_ALLOWED_IPS: str = os.environ.get("WG_ALLOWED_IPS", "0.0.0.0/0, ::/0")
    
    # SSE
    SSE_TOKEN: str = os.environ.get("SSE_TOKEN", "change-me-token")

    # Bootstrap
    BOOTSTRAP_SERVE_LOCAL: bool = True
