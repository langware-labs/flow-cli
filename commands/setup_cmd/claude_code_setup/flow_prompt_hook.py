#!/usr/bin/env python3
"""
Claude Code hook script for UserPromptSubmit event.
Receives hook data via stdin and forwards to 'flow hooks report' command.
"""

import json
import sys
import subprocess
import os


def main():
    try:
        # Read the hook input from stdin
        input_data = json.load(sys.stdin)

        # Add hook_type if not present (this script is for UserPromptSubmit)
        if "hook_type" not in input_data:
            input_data["hook_type"] = "UserPromptSubmit"

        # Run the flow hooks report command (pass environment for LOCAL_SERVER_PORT etc.)
        proc = subprocess.Popen(
            ["flow", "hooks", "report"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy()
        )
        stdout, stderr = proc.communicate(input=json.dumps(input_data))

        # Print any output from the flow command
        if stdout:
            print(stdout, end='')

        # Exit with 0 to allow the prompt to proceed
        sys.exit(0)

    except Exception as e:
        # Log error but don't block the prompt
        print(f"Flow hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
