#!/usr/bin/env python3

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import threading
import time
import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any
from config_manager import get_config_value, setup_defaults
from local_server.reporters import BufferReporter, WebSocketReporter, ReporterRegistry

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared state for login
login_result = None
login_received = threading.Event()

# Shared state for ping
ping_results = []
ping_received = threading.Event()

# Shared state for prompts
prompt_results = []
prompt_received = threading.Event()

# Background Claude sessions
claude_sessions: Dict[str, Dict[str, Any]] = {}
session_counter = 0
session_lock = threading.Lock()

# Hook reporters
buffer_reporter = BufferReporter(max_size=100)
ws_reporter = WebSocketReporter()

# Reporter registry - manages active reporters
reporter_registry = ReporterRegistry()
reporter_registry.add(buffer_reporter)
reporter_registry.add(ws_reporter)


@app.get("/post_login", response_class=HTMLResponse)
async def post_login(flowpad_api_key: str = Query(None, alias="flowpad-api-key")):
    """
    POST login endpoint that receives an API key.
    Validates the API key and stores it in the system keyring.

    Args:
        flowpad_api_key: The API key from the flowpad-api-key GET parameter

    Returns:
        HTML response with success or error message
    """
    global login_result

    try:
        # Import here to avoid circular dependency
        from auth import validate_api_key, set_api_key
        from app_config import set_user

        # Check if API key was provided
        if not flowpad_api_key:
            raise ValueError("No API key provided. Expected 'flowpad-api-key' parameter.")

        # Log the received API key for debugging
        print(f"[DEBUG] Received API key: {flowpad_api_key}")
        print(f"[DEBUG] API key value check: '{flowpad_api_key}' == 'dummy_key_1234567890': {flowpad_api_key == 'dummy_key_1234567890'}")

        # Validate the API key
        user_info = validate_api_key(flowpad_api_key)

        # Store the API key in keyring
        set_api_key(flowpad_api_key)

        # Store user info in app config
        set_user(user_info)

        login_result = {
            "success": True,
            "user": user_info,
            "message": "Login successful"
        }

        # Signal that login was received
        login_received.set()

        # Return success HTML
        user_id = user_info.get('id', 'Unknown')
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login Successful - Flowpad</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }}
        .success-icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        h1 {{
            color: #22c55e;
            margin-bottom: 10px;
        }}
        p {{
            color: #666;
            margin: 10px 0;
        }}
        .info {{
            background: #f0fdf4;
            border-left: 4px solid #22c55e;
            padding: 15px;
            margin: 20px 0;
            text-align: left;
            border-radius: 4px;
        }}
        .close-message {{
            background: #f8fafc;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            padding: 24px;
            margin-top: 40px;
            font-size: 18px;
            font-weight: 600;
            color: #334155;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">✓</div>
        <h1>Login Successful!</h1>
        <p>You have been successfully logged in to Flowpad.</p>

        <div class="info">
            <strong>Account Details:</strong><br>
            User ID: {user_id}
        </div>
    </div>

    <div class="close-message">
        ✓ You can now close this browser page
    </div>
</body>
</html>
"""
        return HTMLResponse(content=html_content)

    except Exception as e:
        login_result = {
            "success": False,
            "error": str(e),
            "message": "Login failed"
        }

        # Signal that login was received (even if failed)
        login_received.set()

        # Return error HTML
        error_message = str(e)
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login Failed - Flowpad</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }}
        .error-icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        h1 {{
            color: #ef4444;
            margin-bottom: 10px;
        }}
        p {{
            color: #666;
            margin: 10px 0;
        }}
        .error-info {{
            background: #fef2f2;
            border-left: 4px solid #ef4444;
            padding: 15px;
            margin: 20px 0;
            text-align: left;
            border-radius: 4px;
        }}
        .close-message {{
            background: #f8fafc;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            padding: 24px;
            margin-top: 40px;
            font-size: 18px;
            font-weight: 600;
            color: #334155;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="error-icon">✗</div>
        <h1>Login Failed</h1>
        <p>There was an error during login.</p>

        <div class="error-info">
            <strong>Error Details:</strong><br>
            {error_message}
        </div>
    </div>

    <div class="close-message">
        ✓ You can now close this browser page
    </div>
</body>
</html>
"""
        return HTMLResponse(content=html_content, status_code=400)


@app.get("/ping")
async def ping(ping_str: str):
    """
    Ping endpoint that receives a ping string for testing hooks.

    Args:
        ping_str: The ping string to store

    Returns:
        JSON response with success status
    """
    global ping_results

    result = {
        "success": True,
        "ping_str": ping_str,
        "timestamp": time.time()
    }

    # Store the ping result
    ping_results.append(result)

    # Signal that ping was received
    ping_received.set()

    return JSONResponse(content=result)


@app.get("/get_pings")
async def get_pings():
    """
    Get all received pings.

    Returns:
        JSON response with all ping results
    """
    return JSONResponse(content={"pings": ping_results})


@app.get("/prompt")
async def prompt(prompt_text: str):
    """
    Prompt endpoint that receives a user prompt for testing hooks.

    Args:
        prompt_text: The prompt text to store

    Returns:
        JSON response with success status
    """
    global prompt_results

    result = {
        "success": True,
        "prompt_text": prompt_text,
        "timestamp": time.time()
    }

    # Store the prompt result
    prompt_results.append(result)

    # Signal that prompt was received
    prompt_received.set()

    return JSONResponse(content=result)


@app.get("/get_prompts")
async def get_prompts():
    """
    Get all received prompts.

    Returns:
        JSON response with all prompt results
    """
    return JSONResponse(content={"prompts": prompt_results})


@app.get("/test_login", response_class=HTMLResponse)
async def test_login():
    """
    Serve the test login HTML page for testing authentication flow.

    Returns:
        HTML response with the test login page
    """
    # Get the path to the HTML file
    server_dir = Path(__file__).parent
    html_file = server_dir / "test_login.html"

    # Read and return the HTML content
    with open(html_file, 'r') as f:
        html_content = f.read()

    return HTMLResponse(content=html_content)


# ============================================================================
# UI API Endpoints
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the main UI."""
    server_dir = Path(__file__).parent
    html_file = server_dir / "static" / "index.html"

    if html_file.exists():
        with open(html_file, 'r') as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>Flow UI - index.html not found</h1>", status_code=404)


@app.get("/api/auth/status")
async def auth_status():
    """Check if user is logged in."""
    try:
        from auth import is_logged_in, get_api_key
        from app_config import get_user

        logged_in = is_logged_in()
        user_info = get_user() if logged_in else None

        return JSONResponse(content={
            "logged_in": logged_in,
            "user": user_info
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/auth/login-url")
async def get_login_url_endpoint():
    """Get the login URL for authentication."""
    try:
        from env_loader import get_login_url

        # Get port from env
        port = int(os.environ.get("LOCAL_SERVER_PORT", "9007"))

        callback_url = f"http://127.0.0.1:{port}/post_login"
        full_login_url = get_login_url(callback_url)

        return JSONResponse(content={"login_url": full_login_url})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/directory/current")
async def get_current_directory():
    """Get the current working directory."""
    return JSONResponse(content={"path": os.getcwd()})


@app.post("/api/directory/select")
async def select_directory(data: dict):
    """Validate and return directory info (doesn't change CWD)."""
    try:
        path = data.get("path")
        if not path:
            return JSONResponse(
                content={"error": "Path is required"},
                status_code=400
            )

        path_obj = Path(path).resolve()
        if not path_obj.exists():
            return JSONResponse(
                content={"error": "Directory does not exist"},
                status_code=400
            )
        if not path_obj.is_dir():
            return JSONResponse(
                content={"error": "Path is not a directory"},
                status_code=400
            )

        return JSONResponse(content={
            "path": str(path_obj),
            "exists": True,
            "is_dir": True
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/claude-code/detect")
async def detect_claude_code():
    """Detect if Claude Code is installed and return its path."""
    try:
        # Try to find Claude Code executable
        claude_code_path = shutil.which("claude-code")

        if claude_code_path:
            return JSONResponse(content={
                "found": True,
                "path": claude_code_path
            })
        else:
            return JSONResponse(content={
                "found": False,
                "path": None
            })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/chat/send")
async def send_chat_message(data: dict):
    """Send a chat message and spawn background Claude Code session."""
    global session_counter

    try:
        message = data.get("message")
        directory = data.get("directory")

        if not message:
            return JSONResponse(
                content={"error": "Message is required"},
                status_code=400
            )

        with session_lock:
            session_id = f"session_{session_counter}"
            session_counter += 1

            # Initialize session
            claude_sessions[session_id] = {
                "id": session_id,
                "status": "pending",
                "message": message,
                "directory": directory or os.getcwd(),
                "output": [],
                "created_at": time.time(),
                "error": None
            }

        # Start background thread to execute Claude Code
        thread = threading.Thread(
            target=_execute_claude_session,
            args=(session_id,),
            daemon=True
        )
        thread.start()

        return JSONResponse(content={
            "session_id": session_id,
            "status": "pending"
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/chat/sessions")
async def list_chat_sessions():
    """List all chat sessions."""
    return JSONResponse(content={
        "sessions": list(claude_sessions.values())
    })


@app.get("/api/chat/session/{session_id}")
async def get_chat_session(session_id: str):
    """Get details of a specific chat session."""
    if session_id not in claude_sessions:
        return JSONResponse(
            content={"error": "Session not found"},
            status_code=404
        )

    return JSONResponse(content=claude_sessions[session_id])


@app.get("/api/hooks/list")
async def list_hooks():
    """List available hooks from .claude/settings.json."""
    try:
        from pathlib import Path
        import json

        # Get current directory and look for .claude/settings.json
        cwd = Path(os.getcwd())
        settings_file = cwd / ".claude" / "settings.json"

        if not settings_file.exists():
            return JSONResponse(content={
                "hooks": [],
                "settings_file": str(settings_file),
                "exists": False
            })

        with open(settings_file, 'r') as f:
            settings = json.load(f)

        hooks = settings.get("hooks", {})

        return JSONResponse(content={
            "hooks": hooks,
            "settings_file": str(settings_file),
            "exists": True
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/hooks/toggle")
async def toggle_hook(data: dict):
    """Toggle a hook on/off in .claude/settings.json."""
    try:
        from pathlib import Path
        import json

        hook_name = data.get("hook_name")
        enabled = data.get("enabled")

        if not hook_name:
            return JSONResponse(
                content={"error": "hook_name is required"},
                status_code=400
            )

        if enabled is None:
            return JSONResponse(
                content={"error": "enabled is required"},
                status_code=400
            )

        cwd = Path(os.getcwd())
        settings_file = cwd / ".claude" / "settings.json"

        if not settings_file.exists():
            return JSONResponse(
                content={"error": ".claude/settings.json not found"},
                status_code=404
            )

        with open(settings_file, 'r') as f:
            settings = json.load(f)

        if "hooks" not in settings:
            settings["hooks"] = {}

        # Store original hook command before toggling
        original_hook_cmd = None
        if hook_name in settings["hooks"]:
            original_hook_cmd = settings["hooks"][hook_name]

        # Toggle the hook
        if hook_name in settings["hooks"]:
            if enabled:
                # If currently disabled (null), we can't re-enable without knowing the original command
                # For now, we'll only allow disabling
                if settings["hooks"][hook_name] is None:
                    return JSONResponse(
                        content={"error": f"Cannot re-enable hook {hook_name} - original command lost. Please reconfigure manually."},
                        status_code=400
                    )
            else:
                # Disable by setting to null
                settings["hooks"][hook_name] = None
        else:
            return JSONResponse(
                content={"error": f"Hook {hook_name} not found"},
                status_code=404
            )

        # Write back
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

        return JSONResponse(content={
            "success": True,
            "hook": hook_name,
            "enabled": enabled
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/hooks/output")
async def get_hook_output():
    """Get recent hook outputs."""
    outputs = await buffer_reporter.get_recent()
    return JSONResponse(content={"outputs": outputs})


@app.post("/api/hooks/report")
async def report_hook(data: dict):
    """
    Receive hook event data from flow hooks report command.

    This endpoint receives hook events and broadcasts to all registered reporters.

    Args:
        data: Hook event data (JSON from stdin)

    Returns:
        JSON response with success status
    """
    try:
        # Add timestamp if not present
        if "timestamp" not in data:
            data["timestamp"] = time.time()

        # Report to all registered reporters
        await reporter_registry.report_all(data)

        return JSONResponse(content={
            "success": True,
            "message": "Hook event recorded"
        })
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.websocket("/ws/hooks")
async def websocket_hooks(websocket: WebSocket):
    """WebSocket endpoint for streaming hook outputs in real-time."""
    await websocket.accept()
    ws_reporter.add_connection(websocket)

    try:
        # Send initial hook buffer from buffer reporter
        initial_outputs = buffer_reporter.get_recent_sync()
        await ws_reporter.send_initial(websocket, initial_outputs)

        # Keep connection alive and receive messages
        while True:
            try:
                data = await websocket.receive_text()
                # Echo back for heartbeat
                await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        ws_reporter.remove_connection(websocket)


# ============================================================================
# Helper Functions
# ============================================================================

def _execute_claude_session(session_id: str):
    """Execute a Claude Code session in the background."""
    import subprocess

    session = claude_sessions[session_id]
    session["status"] = "running"

    try:
        # Check if claude-code is available
        claude_code_path = shutil.which("claude-code")

        if not claude_code_path:
            session["status"] = "error"
            session["error"] = "Claude Code not found. Please install it first."
            return

        # Execute claude-code with the user's message
        # Change to the specified directory first
        cwd = session.get("directory", os.getcwd())

        # Run claude-code with the message
        result = subprocess.run(
            [claude_code_path, session["message"]],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=300  # 5 minute timeout
        )

        # Capture stdout
        if result.stdout:
            session["output"].append({
                "type": "stdout",
                "content": result.stdout,
                "timestamp": time.time()
            })

        # Capture stderr if any
        if result.stderr:
            session["output"].append({
                "type": "stderr",
                "content": result.stderr,
                "timestamp": time.time()
            })

        # Check return code
        if result.returncode == 0:
            session["status"] = "completed"
        else:
            session["status"] = "error"
            session["error"] = f"Claude Code exited with code {result.returncode}"

    except subprocess.TimeoutExpired:
        session["status"] = "error"
        session["error"] = "Session timed out (5 minutes)"
    except FileNotFoundError:
        session["status"] = "error"
        session["error"] = "Claude Code executable not found"
    except Exception as e:
        session["status"] = "error"
        session["error"] = str(e)


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
    if login_received.wait(timeout=timeout_sec):
        return login_result
    else:
        return {
            "success": False,
            "error": "Timeout",
            "message": f"No login received within {timeout_sec} seconds"
        }
