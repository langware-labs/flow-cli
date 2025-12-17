"""
Hook reporters module.

Provides pluggable reporters for handling hook events:
- BufferReporter: Stores events in memory buffer
- WebSocketReporter: Broadcasts events to WebSocket clients
- PrintReporter: Formats and prints events to console
- ReporterRegistry: Manages active reporters
"""

from .base import BaseReporter
from .buffer_reporter import BufferReporter
from .ws_reporter import WebSocketReporter
from .print_reporter import PrintReporter
from .registry import ReporterRegistry

__all__ = [
    "BaseReporter",
    "BufferReporter",
    "WebSocketReporter",
    "PrintReporter",
    "ReporterRegistry",
]
