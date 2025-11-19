import json
import pytest
from pathlib import Path
from commands.setup_cmd.claude_code_setup.setup_claude import setup_claude_code
from commands.setup_cmd.claude_code_setup.hook_parser import HookParser


@pytest.fixture
def temp_hooks_file(tmp_path):
    """Create a temporary hooks file for testing."""
    hooks_file = tmp_path / "hooks.json"
    return hooks_file


@pytest.fixture
def hook_parser(temp_hooks_file):
    """Create a HookParser instance with a temporary file."""
    return HookParser(hooks_file_path=str(temp_hooks_file))


def test_hook_parser_initialization(hook_parser, temp_hooks_file):
    """Test that HookParser initializes correctly."""
    assert hook_parser.hooks_file_path == temp_hooks_file
    assert hook_parser.hooks_data == {"hooks": {}}


def test_add_hook_with_matcher(hook_parser, temp_hooks_file):
    """Test adding a hook with a matcher."""
    hook_parser.add_hook(
        event_name="tool_use",
        matcher="Grep",
        hook_type="command",
        command="flow track grep"
    )

    hook_parser.save_hooks()

    # Verify the file was created
    assert temp_hooks_file.exists()

    # Load and verify the JSON content
    with open(temp_hooks_file, 'r') as f:
        data = json.load(f)

    assert "hooks" in data
    assert "tool_use" in data["hooks"]
    assert len(data["hooks"]["tool_use"]) == 1

    entry = data["hooks"]["tool_use"][0]
    assert entry["matcher"] == "Grep"
    assert len(entry["hooks"]) == 1
    assert entry["hooks"][0]["type"] == "command"
    assert entry["hooks"][0]["command"] == "flow track grep"


def test_add_hook_without_matcher(hook_parser, temp_hooks_file):
    """Test adding a hook without a matcher (like UserPromptSubmit)."""
    hook_parser.add_hook(
        event_name="UserPromptSubmit",
        matcher=None,
        hook_type="command",
        command="/path/to/flow_prompt_hook.py"
    )

    hook_parser.save_hooks()

    # Load and verify the JSON content
    with open(temp_hooks_file, 'r') as f:
        data = json.load(f)

    assert "hooks" in data
    assert "UserPromptSubmit" in data["hooks"]
    assert len(data["hooks"]["UserPromptSubmit"]) == 1

    entry = data["hooks"]["UserPromptSubmit"][0]
    assert "matcher" not in entry
    assert len(entry["hooks"]) == 1
    assert entry["hooks"][0]["type"] == "command"
    assert entry["hooks"][0]["command"] == "/path/to/flow_prompt_hook.py"


def test_add_multiple_hooks_same_event(hook_parser, temp_hooks_file):
    """Test adding multiple hooks to the same event."""
    hook_parser.add_hook(
        event_name="tool_use",
        matcher="Grep",
        hook_type="command",
        command="flow track grep"
    )

    hook_parser.add_hook(
        event_name="tool_use",
        matcher="Read",
        hook_type="command",
        command="flow track read"
    )

    hook_parser.save_hooks()

    # Load and verify the JSON content
    with open(temp_hooks_file, 'r') as f:
        data = json.load(f)

    assert len(data["hooks"]["tool_use"]) == 2

    matchers = [entry["matcher"] for entry in data["hooks"]["tool_use"]]
    assert "Grep" in matchers
    assert "Read" in matchers


def test_get_event_hooks(hook_parser):
    """Test retrieving hooks for a specific event."""
    hook_parser.add_hook(
        event_name="tool_use",
        matcher="*",
        hook_type="command",
        command="flow track all"
    )

    event_hooks = hook_parser.get_event_hooks("tool_use")
    assert len(event_hooks) == 1
    assert event_hooks[0]["matcher"] == "*"


def test_list_events(hook_parser):
    """Test listing all configured events."""
    hook_parser.add_hook(
        event_name="tool_use",
        matcher="*",
        hook_type="command",
        command="flow track"
    )

    hook_parser.add_hook(
        event_name="UserPromptSubmit",
        matcher=None,
        hook_type="command",
        command="flow prompt"
    )

    events = hook_parser.list_events()
    assert len(events) == 2
    assert "tool_use" in events
    assert "UserPromptSubmit" in events


def test_remove_hook_by_command(hook_parser, temp_hooks_file):
    """Test removing a hook by command."""
    hook_parser.add_hook(
        event_name="tool_use",
        matcher="*",
        hook_type="command",
        command="flow track"
    )

    hook_parser.save_hooks()

    # Verify it was added
    with open(temp_hooks_file, 'r') as f:
        data = json.load(f)
    assert "tool_use" in data["hooks"]

    # Remove it
    removed = hook_parser.remove_hook(
        event_name="tool_use",
        command="flow track"
    )

    assert removed is True
    hook_parser.save_hooks()

    # Verify it was removed
    with open(temp_hooks_file, 'r') as f:
        data = json.load(f)
    assert "tool_use" not in data["hooks"]


def test_clear_event(hook_parser):
    """Test clearing all hooks for an event."""
    hook_parser.add_hook(
        event_name="tool_use",
        matcher="*",
        hook_type="command",
        command="flow track"
    )

    cleared = hook_parser.clear_event("tool_use")
    assert cleared is True
    assert "tool_use" not in hook_parser.hooks_data["hooks"]


def test_json_format_structure(hook_parser, temp_hooks_file):
    """Test that the saved JSON has the correct structure."""
    hook_parser.add_hook(
        event_name="UserPromptSubmit",
        matcher=None,
        hook_type="command",
        command="/usr/local/bin/flow_hook.py"
    )

    hook_parser.save_hooks()

    # Read the JSON and verify its structure
    with open(temp_hooks_file, 'r') as f:
        data = json.load(f)

    # Check top-level structure
    assert isinstance(data, dict)
    assert "hooks" in data
    assert isinstance(data["hooks"], dict)

    # Check event structure
    assert "UserPromptSubmit" in data["hooks"]
    assert isinstance(data["hooks"]["UserPromptSubmit"], list)

    # Check entry structure
    entry = data["hooks"]["UserPromptSubmit"][0]
    assert isinstance(entry, dict)
    assert "hooks" in entry
    assert isinstance(entry["hooks"], list)

    # Check hook structure
    hook = entry["hooks"][0]
    assert isinstance(hook, dict)
    assert "type" in hook
    assert "command" in hook
    assert hook["type"] == "command"
    assert hook["command"] == "/usr/local/bin/flow_hook.py"
