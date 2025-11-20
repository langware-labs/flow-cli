#!/usr/bin/env python3

import sys
import requests
from enum import Enum
from cli_context import CLIContext
from cli_command import CLICommand
from config_manager import list_config, set_config_value, remove_config_value, setup_defaults, get_config_value
from commands.setup_cmd.setup_cmd import run_setup
from commands.prompt_cmd import run_prompt_command


class FlowCommand(Enum):
    """Enumeration of available flow CLI commands."""
    CONFIG = "config"
    SETUP = "setup"
    PROMPT = "prompt"
    PING = "ping"

    @classmethod
    def from_string(cls, command_str: str):
        """
        Get FlowCommand from string.

        Args:
            command_str: Command string to parse

        Returns:
            FlowCommand enum value or None if not found
        """
        try:
            return cls(command_str)
        except ValueError:
            return None

    @classmethod
    def list_commands(cls):
        """Get list of all available command names."""
        return [cmd.value for cmd in cls]


def main():
    # Initialize CLI context
    context = CLIContext()

    # Ensure config defaults are set
    setup_defaults()

    if len(sys.argv) < 2:
        print("Hello flowpad")
        return

    # Parse command using CLICommand
    command_str = " ".join(sys.argv[1:])
    cli_cmd = CLICommand(command_str)

    # Get the FlowCommand enum
    flow_command = FlowCommand.from_string(cli_cmd.subcommand) if cli_cmd.subcommand else None

    if flow_command == FlowCommand.CONFIG:
        handle_config_command()
    elif flow_command == FlowCommand.SETUP:
        handle_setup_command(context)
    elif flow_command == FlowCommand.PROMPT:
        handle_prompt_command()
    elif flow_command == FlowCommand.PING:
        handle_ping_command()
    else:
        print(f"Unknown command: {cli_cmd.subcommand}")
        print(f"Available commands: {', '.join(FlowCommand.list_commands())}")


def handle_setup_command(context: CLIContext):
    if len(sys.argv) < 3:
        print("Usage: flow setup <agent_name>")
        return

    agent_name = sys.argv[2]

    # Set first_time_prompt flag when running setup
    set_config_value("first_time_prompt", "true")

    run_setup(agent_name, context)


def handle_prompt_command():
    if len(sys.argv) < 3:
        # No prompt provided, just exit silently
        return

    # Get the prompt from all remaining arguments (in case it has spaces)
    user_prompt = " ".join(sys.argv[2:])
    run_prompt_command(user_prompt)


def handle_ping_command():
    """
    Handle the ping command to test hook integration.
    Sends a ping string to the local server.
    """
    if len(sys.argv) < 3:
        print("Usage: flow ping <ping-string>")
        return

    # Get the ping string from all remaining arguments
    ping_str = " ".join(sys.argv[2:])

    # Get the local server port from config
    setup_defaults()
    port_str = get_config_value("local_cli_port")
    port = int(port_str) if port_str else 9006

    # Send ping to local server
    try:
        url = f"http://127.0.0.1:{port}/ping"
        response = requests.get(url, params={"ping_str": ping_str}, timeout=5)

        if response.status_code == 200:
            print(f"Ping sent successfully: {ping_str}")
        else:
            print(f"Ping failed with status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending ping: {e}")


def handle_config_command():
    if len(sys.argv) < 3:
        print("Usage: flow config <list|set|remove>")
        return

    subcommand = sys.argv[2]

    if subcommand == "list":
        config = list_config()
        if not config:
            print("No configuration values set.")
        else:
            for key, value in config.items():
                print(f"{key}={value}")

    elif subcommand == "set":
        if len(sys.argv) < 4:
            print("Usage: flow config set key=value")
            return

        try:
            key_value = sys.argv[3]
            if "=" not in key_value:
                print("Error: Expected format key=value")
                return

            key, value = key_value.split("=", 1)
            key = key.strip()
            value = value.strip()

            if not key:
                print("Error: Key cannot be empty")
                return

            set_config_value(key, value)
            print(f"Set {key}={value}")

        except Exception as e:
            print(f"Error setting config: {e}")

    elif subcommand == "remove":
        if len(sys.argv) < 4:
            print("Usage: flow config remove key")
            return

        key = sys.argv[3]
        if remove_config_value(key):
            print(f"Removed {key}")
        else:
            print(f"Key '{key}' not found")

    else:
        print(f"Unknown config subcommand: {subcommand}")
        print("Available subcommands: list, set, remove")


if __name__ == "__main__":
    main()
