#!/bin/bash
# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv could not be found. Please install it first."
    exit 1
fi

# Run the application
uv run src/run.py --host 0.0.0.0
