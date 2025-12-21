#!/usr/bin/env python3
"""
Local FastAPI server for Flow CLI.

This module initializes the FastAPI app and includes all route modules.
"""

import os
import time
import threading

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config_manager import get_config_value, setup_defaults
from local_server import state
from local_server.routes import (
    auth_router,
    hooks_router,
    chat_router,
    directory_router,
    detection_router,
    testing_router,
    ui_router,
)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth_router)
app.include_router(hooks_router)
app.include_router(chat_router)
app.include_router(directory_router)
app.include_router(detection_router)
app.include_router(testing_router)
app.include_router(ui_router)


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
    # Reset state
    state.login_result = None
    state.login_received.clear()

    # Get config values
    setup_defaults()

    # Get timeout from config if not provided
    if timeout_sec is None:
        timeout_str = get_config_value("post_login_timeout")
        timeout_sec = int(timeout_str) if timeout_str else 30

    port = int(os.environ.get("LOCAL_SERVER_PORT", "9007"))

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
    if state.login_received.wait(timeout=timeout_sec):
        return state.login_result
    else:
        return {
            "success": False,
            "error": "Timeout",
            "message": f"No login received within {timeout_sec} seconds"
        }
