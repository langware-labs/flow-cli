#!/usr/bin/env python3

import threading
import time
import requests
from local_server.server import wait_for_post_login
from config_manager import get_config_value, setup_defaults


def simulate_login_success():
    """Simulate a login request after 2 seconds."""
    time.sleep(2)
    setup_defaults()
    port = get_config_value("local_cli_port")
    url = f"http://127.0.0.1:{port}/post_login?api_key=test_api_key_123"
    try:
        response = requests.get(url)
        print(f"Login request sent: {response.json()}")
    except Exception as e:
        print(f"Error sending login request: {e}")


def test_success():
    """Test successful login within timeout."""
    print("=== Test 1: Successful login ===")

    # Start a thread to simulate login after 2 seconds
    login_thread = threading.Thread(target=simulate_login_success, daemon=True)
    login_thread.start()

    # Wait for login with 10 second timeout
    result = wait_for_post_login(timeout_sec=10)

    print(f"Result: {result}")
    print()


def test_timeout():
    """Test timeout when no login is received."""
    print("=== Test 2: Timeout (no login) ===")

    # Wait for login with 3 second timeout (no login will be sent)
    result = wait_for_post_login(timeout_sec=3)

    print(f"Result: {result}")
    print()


if __name__ == "__main__":
    print("Testing local server with wait_for_post_login\n")

    # Test 1: Successful login
    test_success()

    # Wait a bit before next test
    time.sleep(2)

    # Test 2: Timeout
    test_timeout()

    print("Tests complete!")
