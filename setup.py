from setuptools import setup, find_packages

setup(
    name="flow-cli",
    version="0.1.0",
    description="Flow CLI tool for flowpad",
    author="Langweare Labs",
    packages=find_packages(),
    py_modules=["flow_cli", "config_manager"],
    install_requires=[
        "platformdirs",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "flow=flow_cli:main",
        ],
    },
    python_requires=">=3.7",
)
