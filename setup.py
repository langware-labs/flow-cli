from setuptools import setup, find_packages

setup(
    name="flow-cli",
    version="0.1.0",
    description="Flow CLI tool for flowpad",
    author="Langweare Labs",
    packages=find_packages(),
    py_modules=["flow_cli", "config_manager", "cli_context", "cli_command"],
    install_requires=[
        "platformdirs",
        "requests",
        "fastapi",
        "uvicorn",
        "typer>=0.9.0",
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
