#!/usr/bin/env python3

import sys
from config_manager import list_config, set_config_value, remove_config_value
from commands.setup_cmd.setup_cmd import run_setup


def main():
    if len(sys.argv) < 2:
        print("Hello flowpad")
        return

    command = sys.argv[1]

    if command == "config":
        handle_config_command()
    elif command == "setup":
        handle_setup_command()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: config, setup")


def handle_setup_command():
    if len(sys.argv) < 3:
        print("Usage: flow setup <agent_name>")
        return

    agent_name = sys.argv[2]
    run_setup(agent_name)


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
