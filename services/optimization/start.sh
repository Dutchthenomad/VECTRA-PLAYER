#!/bin/bash
set -e

cd "$(dirname "$0")"

# Activate virtualenv if exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Start the service
python -m src.main
