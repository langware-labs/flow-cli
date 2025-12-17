#!/usr/bin/env python3
"""
Claude Code hook script for UserPromptSubmit event.
Receives user prompt via stdin and forwards to 'flow prompt' command.
"""

import json
import sys
import subprocess
import os


def main():
    try:
        # Read the hook input from stdin
        input_data = json.load(sys.stdin)

        # Extract the user's prompt
        user_prompt = input_data.get("prompt", "")

        # Run the flow prompt command (pass environment for LOCAL_SERVER_PORT etc.)
        result = subprocess.run(
            ["flow", "prompt", user_prompt],
            capture_output=True,
            text=True,
            env=os.environ.copy()
        )

        # Print any output from the flow command
        if result.stdout:
            print(result.stdout, end='')

        # Exit with 0 to allow the prompt to proceed
        sys.exit(0)

    except Exception as e:
        # Log error but don't block the prompt
        print(f"Flow hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
