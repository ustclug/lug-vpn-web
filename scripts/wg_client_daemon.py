#!/usr/bin/env python3
import os
import sys
import json
import time
import requests
import argparse
import sseclient # pip install sseclient-py
import datetime
import subprocess

# Configuration defaults
DEFAULT_SERVER_URL = "http://localhost:5000"
DEFAULT_TOKEN = "change-me-token"
DEFAULT_WG_DEV = "wg0"
DEFAULT_WG_CONFIG = "/etc/wireguard/wg0.conf"

def log(msg):
    print(f"[{datetime.datetime.now()}] {msg}")

def fetch_config(server_url, token):
    url = f"{server_url}/api/wireguard/server-config?token={token}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.text

def update_configs(server_url, token, wg_config, wg_dev, dry_run=False):
    log("Fetching fresh configuration from server...")
    try:
        config_text = fetch_config(server_url, token)
        log(f"Received config ({len(config_text)} bytes)")
        
        if dry_run:
            log("Dry run: Configuration from server:")
            print("--- BEGIN CONFIG ---")
            print(config_text)
            print("--- END CONFIG ---")
        else:
            log(f"Writing configuration to {wg_config}")
            with open(wg_config, 'w') as f:
                f.write(config_text)
            
            log(f"Reloading systemd service: wg-quick@{wg_dev}.service")
            subprocess.run(["systemctl", "reload", f"wg-quick@{wg_dev}.service"], check=True)
            log("Reload complete.")
            
    except Exception as e:
        log(f"Error updating config: {e}")

def listen_sse(server_url, token, wg_config, wg_dev, dry_run=False):
    url = f"{server_url}/api/sse/server-config?token={token}"
    log(f"Connecting to SSE stream at {url}")
    
    try:
        # Use a 5-minute timeout for the stream
        response = requests.get(url, stream=True, timeout=300)
        client = sseclient.SSEClient(response)
        
        for event in client.events():
            if event.data == "config_update":
                log("Received config_update event")
                update_configs(server_url, token, wg_config, wg_dev, dry_run)
            elif event.data:
                log(f"Received other event: {event.data}")
                
    except Exception as e:
        log(f"Connection lost or error: {e}")
        time.sleep(5)

def main():
    parser = argparse.ArgumentParser(description="WireGuard Client Daemon")
    parser.add_argument("--url", default=os.environ.get("WG_API_URL", DEFAULT_SERVER_URL), help="Web API URL")
    parser.add_argument("--token", default=os.environ.get("SSE_TOKEN", DEFAULT_TOKEN), help="Authentication token")
    parser.add_argument("--wg-config", default=DEFAULT_WG_CONFIG, help="WireGuard config file path")
    parser.add_argument("--wg-dev", default=DEFAULT_WG_DEV, help="WireGuard device name (e.g. wg0)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files or run commands, just print")
    
    args = parser.parse_args()
    
    log("Starting WG Client Daemon...")
    if args.dry_run:
        log("Running in DRY-RUN mode")
        
    # Initial sync
    update_configs(args.url, args.token, args.wg_config, args.wg_dev, args.dry_run)
    
    # Listen for updates
    while True:
        try:
            listen_sse(args.url, args.token, args.wg_config, args.wg_dev, args.dry_run)
        except KeyboardInterrupt:
            log("Daemon stopping...")
            break
        except Exception as e:
            log(f"Unexpected error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
