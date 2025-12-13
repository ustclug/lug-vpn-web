#!/usr/bin/env python3
# encoding: utf-8

"""
Smoke-test helper: create an admin and a normal user, and ensure the normal user
has a RADIUS (radcheck) account with a known password.

Run inside the `web` container, e.g.:
  docker compose exec web python3 scripts/smoke_seed_user.py
"""

import os
import sys
import datetime

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app, db
from app.models import User, VPNAccount


def _truthy(v: str) -> bool:
    return str(v).lower() in {"1", "true", "yes", "y", "on"}

def wait_for_mysql() -> None:
    import socket
    import time

    host = os.getenv("MYSQL_HOST", "mysql")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    retries = int(os.getenv("MYSQL_WAIT_RETRIES", "60"))
    sleep_s = float(os.getenv("MYSQL_WAIT_SLEEP", "1"))

    for _ in range(retries):
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(sleep_s)

    raise RuntimeError(f"Timed out waiting for MySQL at {host}:{port}")


def upsert_user(email: str, web_password: str, *, admin: bool) -> User:
    u = User.get_user_by_email(email)
    if not u:
        u = User(email, web_password)
        db.session.add(u)
    else:
        u.set_password(web_password)

    # Bypass email-confirm flow for smoke tests.
    u.active = True
    u.admin = admin
    if not u.expiration:
        u.expiration = datetime.date.today() + datetime.timedelta(days=365)
    if u.status in (None, "none", "reject", "applying"):
        u.status = "pass"
    db.session.commit()
    return u


def ensure_radius_account(u: User, radius_password: str) -> None:
    if not u.expiration:
        u.expiration = datetime.date.today() + datetime.timedelta(days=365)

    # Use the requested password so smoke tests can authenticate to the proxy.
    u.vpnpassword = radius_password
    db.session.commit()

    existing = VPNAccount.get_account_by_email(u.email)
    if not existing:
        u.enable_vpn()
        db.session.commit()
        return

    # Update password + expiration if the account already exists.
    VPNAccount.changepass(u.email, radius_password)
    VPNAccount.update_expiration(u.email, u.expiration)
    db.session.commit()


def main() -> int:
    admin_email = os.getenv("SMOKE_ADMIN_EMAIL", "admin@ustclug.org")
    admin_pass = os.getenv("SMOKE_ADMIN_PASSWORD", "admin12345")
    user_email = os.getenv("SMOKE_USER_EMAIL", "user@ustclug.org")
    user_web_pass = os.getenv("SMOKE_USER_PASSWORD", "user12345")
    user_radius_pass = os.getenv("SMOKE_USER_RADIUS_PASSWORD", user_web_pass)

    print("==> Seeding smoke users...", file=sys.stderr)
    print(f"    Admin email: {admin_email}", file=sys.stderr)
    print(f"    User email : {user_email}", file=sys.stderr)

    with app.app_context():
        wait_for_mysql()
        db.create_all()

        admin_u = upsert_user(admin_email, admin_pass, admin=True)
        user_u = upsert_user(user_email, user_web_pass, admin=False)

        ensure_radius_account(user_u, user_radius_pass)

        # Show final values useful for testing
        print("", file=sys.stderr)
        print("==> Smoke credentials", file=sys.stderr)
        print(f"    ADMIN_LOGIN: {admin_u.email} / {admin_pass}", file=sys.stderr)
        print(f"    USER_LOGIN : {user_u.email} / {user_web_pass}", file=sys.stderr)
        print(f"    RADIUS_AUTH: {user_u.email} / {user_radius_pass}", file=sys.stderr)
        print(f"    USER_STATUS: active={user_u.active} status={user_u.status} expiration={user_u.expiration}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


