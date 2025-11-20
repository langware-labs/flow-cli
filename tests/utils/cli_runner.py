"""CLI runner utility for testing flow commands."""

import os
import subprocess
from pathlib import Path


def self_run_cli(command: str):
    """
    Run the flow CLI as if it was invoked from command line.

    Args:
        command: The command string (e.g., "ping hello" or "setup claude-code")

    Returns:
        subprocess.CompletedProcess result
    """
    # Get the path to flow_cli.py
    project_root = Path(__file__).parent.parent.parent
    flow_cli_path = project_root / "flow_cli.py"

    # Split the command into arguments
    args = command.split()

    # Set up environment with PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)

    # Run the CLI
    result = subprocess.run(
        ["python3", str(flow_cli_path)] + args,
        capture_output=True,
        text=True,
        env=env,
        timeout=10
    )

    return result
