#!/usr/bin/env python3
"""
Tests for environment variable loading.
"""

import os
import pytest
from pathlib import Path
from env_loader import cli_init


def test_env_loader():
    """
    Test that cli_init loads environment variables from .env.local
    """
    # Clear the FOO variable if it exists
    if 'FOO' in os.environ:
        del os.environ['FOO']

    # Verify FOO is not set before loading
    assert os.environ.get('FOO') is None, "FOO should not be set before cli_init"

    # Call cli_init to load .env.local
    cli_init()

    # Verify FOO is now set to BAR
    assert os.environ.get('FOO') == 'BAR', f"Expected FOO=BAR, got FOO={os.environ.get('FOO')}"

    print(f"✅ Environment variable loaded: FOO={os.environ.get('FOO')}")


