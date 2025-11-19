#!/usr/bin/env python3
"""
Test script for HookParser class.
Demonstrates how to use the HookParser to manage Claude Code hooks.
"""

from commands.setup_cmd.claude_code_setup.hook_parser import HookParser
import json
import tempfile
import os


def test_hook_parser():
    """Test the HookParser functionality."""

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_file = f.name

    try:
        print("=== Testing HookParser ===\n")

        # Initialize parser with test file
        parser = HookParser(test_file)

        # Test 1: Add a hook
        print("1. Adding a hook for 'tool_use' event with 'Grep' matcher...")
        parser.add_hook(
            event_name="tool_use",
            matcher="Grep",
            hook_type="command",
            command="flow track grep"
        )
        print("✓ Hook added\n")

        # Test 2: Add another hook with same matcher
        print("2. Adding another hook for 'tool_use' event with 'Grep' matcher...")
        parser.add_hook(
            event_name="tool_use",
            matcher="Grep",
            hook_type="command",
            command="echo 'Grep used'"
        )
        print("✓ Hook added\n")

        # Test 3: Add hook with different matcher
        print("3. Adding a hook for 'tool_use' event with '*' matcher...")
        parser.add_hook(
            event_name="tool_use",
            matcher="*",
            hook_type="command",
            command="flow track all-tools"
        )
        print("✓ Hook added\n")

        # Test 4: List events
        print("4. Listing all events...")
        events = parser.list_events()
        print(f"   Events: {events}\n")

        # Test 5: List matchers for an event
        print("5. Listing matchers for 'tool_use' event...")
        matchers = parser.list_matchers("tool_use")
        print(f"   Matchers: {matchers}\n")

        # Test 6: Get hook details
        print("6. Getting hook details for 'tool_use' event with 'Grep' matcher...")
        details = parser.get_hook_details("tool_use", "Grep")
        print(f"   Details: {json.dumps(details, indent=4)}\n")

        # Test 7: Update matcher
        print("7. Updating matcher from 'Grep' to 'GrepTool'...")
        updated = parser.update_matcher("tool_use", "Grep", "GrepTool")
        print(f"   Updated: {updated}\n")

        # Test 8: Save hooks
        print("8. Saving hooks to file...")
        parser.save_hooks()
        print("✓ Hooks saved\n")

        # Test 9: Display current hooks structure
        print("9. Current hooks structure:")
        print(parser)
        print()

        # Test 10: Remove a specific hook by command
        print("10. Removing hook with command 'flow track grep'...")
        removed = parser.remove_hook("tool_use", command="flow track grep")
        print(f"    Removed: {removed}\n")

        # Test 11: Remove entire matcher
        print("11. Removing entire matcher '*'...")
        removed = parser.remove_hook("tool_use", matcher="*")
        print(f"    Removed: {removed}\n")

        # Test 12: Display final structure
        print("12. Final hooks structure:")
        print(parser)
        print()

        # Test 13: Clear all hooks
        print("13. Clearing all hooks...")
        parser.clear_all()
        parser.save_hooks()
        print("✓ All hooks cleared\n")

        print("=== All tests completed successfully! ===")

    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.unlink(test_file)


if __name__ == "__main__":
    test_hook_parser()
