#!/usr/bin/env python3

from local_server.server import wait_for_post_login

print("Starting local server...")
print("Send a GET request to: http://127.0.0.1:9006/post_login?api_key=YOUR_API_KEY")
print("Or use curl: curl 'http://127.0.0.1:9006/post_login?api_key=my_key_123'")
print()

result = wait_for_post_login(timeout_sec=30)

print(f"\nFinal result: {result}")
