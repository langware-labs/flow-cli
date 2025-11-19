#!/usr/bin/env python3

import requests
from config_manager import get_config_value, setup_defaults


def healthcheck_api_server():
    """
    Perform a healthcheck on the API server.

    Returns:
        tuple: (status_code, success) where success is True if status_code is 200
    """
    # Ensure defaults are set
    setup_defaults()

    api_host = get_config_value("flowpad_api_server_host")
    if not api_host:
        return None, False

    # Ensure the URL has a scheme
    if not api_host.startswith(("http://", "https://")):
        api_url = f"http://{api_host}"
    else:
        api_url = api_host

    try:
        response = requests.get(api_url, timeout=5)
        return response.status_code, response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API server: {e}")
        return None, False


def run_setup(agent_name):
    """
    Run the setup command for the specified coding agent.

    Args:
        agent_name: The name of the coding agent (e.g., 'claude-code', 'github-copilot', 'cursor')

    Returns:
        str: Setup instructions or result message
    """
    if not agent_name:
        agent_name = "unknown"

    result = f"Setting up flowpad for {agent_name}..."
    print(result)
    print(f"Agent: {agent_name}")

    # Perform healthcheck
    print("\nPerforming API server healthcheck...")
    status_code, success = healthcheck_api_server()

    if status_code is None:
        print("❌ API server healthcheck failed: Unable to connect")
    elif success:
        print(f"✓ API server healthcheck passed (Status: {status_code})")
    else:
        print(f"⚠ API server responded with status: {status_code} (expected 200)")

    print("\nSetup complete!")

    return result
