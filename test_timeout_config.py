#!/usr/bin/env python3

from local_server.server import wait_for_post_login
from config_manager import get_config_value, set_config_value

print("=== Test 1: Using default timeout from config ===")
print(f"Default timeout: {get_config_value('post_login_timeout')}s")
print("Starting server with default timeout...")
print("(Will timeout after 30 seconds if no login)\n")

# This will use the default 30 seconds from config
# result = wait_for_post_login()
# Commented out to avoid waiting 30 seconds

print("=== Test 2: Override timeout via parameter ===")
print("Starting server with 5 second timeout...")
result = wait_for_post_login(timeout_sec=5)
print(f"Result: {result}")
print()

print("=== Test 3: Change config value ===")
set_config_value("post_login_timeout", "10")
print(f"Changed timeout to: {get_config_value('post_login_timeout')}s")
print("Starting server with new config timeout...")
result = wait_for_post_login()
print(f"Result: {result}")
print()

# Reset to default
set_config_value("post_login_timeout", "30")
print("Reset timeout to 30s")
