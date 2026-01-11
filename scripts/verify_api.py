import requests
import sys

BASE_URL = "http://localhost:5000"
EMAIL = "ustcaf@yfgao.com"
PASSWORD = "tNz-bTL-cgp-K4T"

session = requests.Session()

def log(msg):
    print(f"[TEST] {msg}")

def check(response, expected_code=200, check_text=None):
    if response.status_code != expected_code:
        log(f"FAIL: {response.url} returned {response.status_code}, expected {expected_code}")
        print(response.text[:500])
        sys.exit(1)
    if check_text and check_text not in response.text:
        log(f"FAIL: {response.url} did not contain '{check_text}'")
        sys.exit(1)
    log(f"PASS: {response.url}")

def test_login():
    log("Testing Login...")
    # First get CSRF token if needed? Flask-WTF usually needs it.
    # We can try GET login first.
    r = session.get(f"{BASE_URL}/login/")
    check(r, 200, "Login")
    
    # Simple login without CSRF for now (if WTF_CSRF_ENABLED is True, might fail)
    # But usually app config has SECRET_KEY.
    # Let's try to parse csrf_token if present.
    csrf_token = None
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        token_input = soup.find('input', {'name': 'csrf_token'})
        log(f"Token input found: {token_input}")
        if token_input:
            csrf_token = token_input.get('value')
            log(f"Found CSRF token: {csrf_token}")
        else:
            log("CSRF token not found in HTML")
    except ImportError:
        log("BeautifulSoup not installed")
        sys.exit(1)
    except Exception as e:
        log(f"Error parsing HTML: {e}")
    
    data = {"email": EMAIL, "password": PASSWORD}
    if csrf_token:
        data["csrf_token"] = csrf_token
        
    log(f"Posting login: {data}")
    r = session.post(f"{BASE_URL}/login/", data=data)
    
    if r.history:
        log("Login redirected.")
        check(r, 200, "WireGuard Configuration")
    else:
        log("Login failed (no redirect). checking for errors...")
        soup = BeautifulSoup(r.text, 'html.parser')
        alerts = soup.find_all(class_='alert')
        for a in alerts:
            log(f"Alert: {a.get_text().strip()}")
            
        if "Please log in" in r.text or "Login" in r.text:
            log("FAIL: Still on login page.")
            sys.exit(1)
        check(r, 200, "WireGuard Configuration")

def test_regenerate():
    log("Testing Key Regeneration...")
    # Get index to find csrf token again if needed
    r = session.get(f"{BASE_URL}/")
    csrf_token = None
    if 'name="csrf_token"' in r.text:
        import re
        match = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
        if match:
            csrf_token = match.group(1)
    
    headers = {}
    data = {}
    if csrf_token:
        data['csrf_token'] = csrf_token
        
    r = session.post(f"{BASE_URL}/api/wireguard/regenerate", data=data)
    check(r, 200, "WireGuard keys regenerated successfully")

def test_download_config():
    log("Testing Config Download...")
    # Peer 1
    r = session.get(f"{BASE_URL}/api/wireguard/config/1")
    check(r, 200, "[Interface]")
    check(r, 200, "PrivateKey = ")

def test_server_config():
    log("Testing Server Config Endpoint (Token Auth)...")
    token = "change-me-token" # From .env default
    r = session.get(f"{BASE_URL}/api/wireguard/server-config?token={token}")
    check(r, 200, "allowed_ips")
    log(f"Server config response json: {r.json()}")

if __name__ == "__main__":
    try:
        test_login()
        test_regenerate()
        test_download_config()
        test_server_config()
        log("ALL API TESTS PASSED")
    except Exception as e:
        log(f"Exception: {e}")
        sys.exit(1)
