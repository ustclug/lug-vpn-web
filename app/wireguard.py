import subprocess
import qrcode
import io
import base64
from app.config import Config

def generate_key():
    """Generate a WireGuard private key."""
    # wireguard-tools might be a wrapper, but standard way is often just calling wg
    # or using a library. If wireguard-tools is pure python, we can use it.
    # For now, let's assume we can shell out or use a simple python implementation.
    # Actually, let's use the `wireguard_tools` library if available, otherwise fallback.
    # But since I added it to pyproject.toml, let's try to import it.
    # However, to be safe and robust without knowing the exact library API in detail blindly,
    # utilizing standard `subprocess` to `wg` is risky if wg isn't installed.
    # Re-reading search result: "wireguard-tools (Pure Python reimplementation)... WireguardKey.generate()"
    try:
        from wireguard_tools import WireguardKey
        private_key = WireguardKey.generate()
        public_key = private_key.public_key()
        return str(private_key), str(public_key)
    except ImportError:
        # Fallback if library issue (though we added it)
        # Simplified curve25519 key generation could be here, but let's stick to the library expectation
        raise RuntimeError("wireguard-tools library not found")

def generate_preshared_key():
    """Generate a Wireshared preshared key."""
    from wireguard_tools import WireguardKey
    return str(WireguardKey.generate())

def get_public_key(private_key_str):
    """Derive public key from private key string."""
    from wireguard_tools import WireguardKey
    return str(WireguardKey(private_key_str).public_key())

def generate_client_config(private_key, address, dns=None):
    """Generate WireGuard client configuration."""
    if dns is None:
        dns = Config.WG_DNS
    
    server_pub = get_public_key(Config.WG_SERVER_PRIVATE_KEY)

    config = f"""[Interface]
PrivateKey = {private_key}
Address = {address}
DNS = {dns}

[Peer]
PublicKey = {server_pub}
AllowedIPs = {Config.WG_ALLOWED_IPS}
Endpoint = {Config.WG_SERVER_ENDPOINT}
PersistentKeepalive = 25
"""
    return config

def generate_server_config(peers):
    """Generate WireGuard server configuration."""
    lines = [
        "[Interface]",
        f"PrivateKey = {Config.WG_SERVER_PRIVATE_KEY}",
        f"Address = {Config.WG_SERVER_INTERFACE_IP}",
        f"ListenPort = {Config.WG_LISTEN_PORT}",
        f"MTU = {Config.WG_MTU}",
        ""
    ]
    
    for peer in peers:
        lines.append("[Peer]")
        lines.append(f"PublicKey = {peer.public_key}")
        if peer.preshared_key:
            lines.append(f"PresharedKey = {peer.preshared_key}")
        lines.append(f"AllowedIPs = {peer.ip_address}/32")
        lines.append("")
        
    return "\n".join(lines)

def generate_qr_code(config_data):
    """Generate a QR code and return it as a base64 encoded string."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(config_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
