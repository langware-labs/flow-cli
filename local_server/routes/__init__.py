"""
Route modules for the local server.
"""

from local_server.routes.auth import router as auth_router
from local_server.routes.hooks import router as hooks_router
from local_server.routes.chat import router as chat_router
from local_server.routes.directory import router as directory_router
from local_server.routes.detection import router as detection_router
from local_server.routes.testing import router as testing_router
from local_server.routes.ui import router as ui_router

__all__ = [
    "auth_router",
    "hooks_router",
    "chat_router",
    "directory_router",
    "detection_router",
    "testing_router",
    "ui_router",
]
