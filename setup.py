from setuptools import setup, find_packages

# Read version from _version.py
version = {}
with open("_version.py") as f:
    exec(f.read(), version)

setup(
    name="flow-cli",
    version=version["__version__"],
    description="Flow CLI tool for flowpad",
    author="Langweare Labs",
    packages=find_packages() + ["py-sdk"],
    py_modules=["flow_cli", "config_manager", "cli_context", "cli_command", "env_loader", "auth", "app_config", "_version"],
    install_requires=[
        "platformdirs",
        "requests",
        "fastapi",
        "uvicorn[standard]",
        "typer>=0.9.0",
        "python-dotenv",
        "keyring",
        "fastmcp",
        "httpx",
        "websockets",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "flow=flow_cli:cli_main",
        ],
    },
    python_requires=">=3.7",
)
