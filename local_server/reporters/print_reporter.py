"""
Print reporter - formats and prints hook events to console.
"""

import json
from datetime import datetime
from typing import Dict, Any
from .base import BaseReporter

# ANSI color codes
COLORS = {
    'UserPromptSubmit': '\033[95m',   # Magenta
    'PreToolUse': '\033[93m',          # Yellow
    'PostToolUse': '\033[92m',         # Green
    'SessionStart': '\033[97m',        # White
    'SessionEnd': '\033[90m',          # Gray
    'Stop': '\033[91m',                # Red
    'Notification': '\033[96m',        # Cyan
    'SubagentStop': '\033[94m',        # Blue
}
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

# Event icons
ICONS = {
    'UserPromptSubmit': '💬',
    'PreToolUse': '🔧',
    'PostToolUse': '✅',
    'SessionStart': '🚀',
    'SessionEnd': '🏁',
    'Stop': '⏹️',
    'Notification': '📢',
    'SubagentStop': '🤖',
}


class PrintReporter(BaseReporter):
    """
    Reporter that formats and prints hook events to console.

    Features:
    - Colored output based on event type
    - Icons for visual identification
    - Formatted timestamps
    - Truncated long content
    """

    def __init__(self):
        """Initialize the print reporter."""
        pass

    def _format_event(self, event: Dict[str, Any]) -> str:
        """Format a hook event for console display."""
        hook_type = event.get('hook_type', event.get('type', 'Unknown'))
        timestamp = datetime.now().strftime('%H:%M:%S')

        color = COLORS.get(hook_type, '\033[0m')
        icon = ICONS.get(hook_type, '📌')

        lines = []
        lines.append(f"\n{color}{BOLD}{icon} [{timestamp}] ═══ {hook_type} ═══{RESET}")

        # Event-specific formatting
        if hook_type == 'UserPromptSubmit':
            prompt = event.get('prompt', '')
            lines.append(f"{color}  Prompt: {prompt[:200]}{'...' if len(prompt) > 200 else ''}{RESET}")

        elif hook_type == 'PreToolUse':
            tool_name = event.get('tool_name', 'unknown')
            tool_input = event.get('tool_input', {})
            lines.append(f"{color}  Tool: {tool_name}{RESET}")
            if tool_input:
                input_str = json.dumps(tool_input, indent=2)[:300]
                lines.append(f"{DIM}  Input: {input_str}{'...' if len(str(tool_input)) > 300 else ''}{RESET}")

        elif hook_type == 'PostToolUse':
            tool_name = event.get('tool_name', 'unknown')
            response = str(event.get('tool_response', ''))[:200]
            lines.append(f"{color}  Tool: {tool_name}{RESET}")
            lines.append(f"{DIM}  Response: {response}{'...' if len(str(event.get('tool_response', ''))) > 200 else ''}{RESET}")

        elif hook_type == 'Notification':
            message = event.get('message', '')
            lines.append(f"{color}  Message: {message}{RESET}")

        elif hook_type in ('SessionStart', 'SessionEnd', 'Stop'):
            session_id = event.get('session_id', '')[:16]
            if session_id:
                lines.append(f"{color}  Session: {session_id}...{RESET}")

        lines.append(f"{color}{'─' * 50}{RESET}")

        return '\n'.join(lines)

    async def report(self, event: Dict[str, Any]) -> None:
        """
        Format and print event to console.

        Args:
            event: Hook event data dictionary
        """
        output = self._format_event(event)
        print(output, flush=True)

    async def get_recent(self) -> list:
        """
        Print reporter doesn't store events.

        Returns:
            Empty list (print reporter doesn't maintain history)
        """
        return []
