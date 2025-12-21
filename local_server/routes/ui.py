"""
UI serving routes for the local server.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the main UI."""
    server_dir = Path(__file__).parent.parent
    html_file = server_dir / "static" / "index.html"

    if html_file.exists():
        with open(html_file, 'r') as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>Flow UI - index.html not found</h1>", status_code=404)
