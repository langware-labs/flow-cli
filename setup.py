from setuptools import setup, find_packages

setup(
    name="flow-cli",
    version="0.1.0",
    description="Flow CLI tool for flowpad",
    author="Langweare Labs",
    py_modules=["flow_cli"],
    install_requires=[],
    entry_points={
        "console_scripts": [
            "flow=flow_cli:main",
        ],
    },
    python_requires=">=3.7",
)
