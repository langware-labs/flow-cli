#!/usr/bin/env python3

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import threading
import time
from config_manager import get_config_value, setup_defaults

app = FastAPI()

# Shared state for login
login_result = None
login_received = threading.Event()


@app.get("/post_login")
async def post_login(api_key: str):
    """
    POST login endpoint that receives an API key.

    Args:
        api_key: The API key to store

    Returns:
        JSON response with success status
    """
    global login_result

    login_result = {
        "success": True,
        "api_key": api_key,
        "message": "Login successful"
    }

    # Signal that login was received
    login_received.set()

    return JSONResponse(content=login_result)


def start_server(port: int):
    """
    Start the FastAPI server in the current thread.

    Args:
        port: Port number to listen on
    """
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def wait_for_post_login(timeout_sec: int = None):
    """
    Wait for the post_login endpoint to be called.
    Runs the server in a separate thread and waits for login.

    Args:
        timeout_sec: Timeout in seconds (if None, uses config default)

    Returns:
        dict: Login result if received, or timeout error
    """
    global login_result, login_received

    # Reset state
    login_result = None
    login_received.clear()

    # Get config values
    setup_defaults()

    # Get timeout from config if not provided
    if timeout_sec is None:
        timeout_str = get_config_value("post_login_timeout")
        timeout_sec = int(timeout_str) if timeout_str else 30

    port_str = get_config_value("local_cli_port")
    port = int(port_str) if port_str else 9006

    # Start server in daemon thread
    server_thread = threading.Thread(
        target=start_server,
        args=(port,),
        daemon=True
    )
    server_thread.start()

    # Give server time to start
    time.sleep(1)

    print(f"Local server started on http://127.0.0.1:{port}")
    print(f"Waiting for login (timeout: {timeout_sec}s)...")

    # Wait for login with timeout
    if login_received.wait(timeout=timeout_sec):
        return login_result
    else:
        return {
            "success": False,
            "error": "Timeout",
            "message": f"No login received within {timeout_sec} seconds"
        }
