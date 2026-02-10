#!/bin/bash
# Start AxleLore services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate virtual environment
if [[ -d ".venv" ]]; then
    source .venv/bin/activate
else
    echo "Virtual environment not found. Run bin/install.sh first."
    exit 1
fi

# Ensure Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve &
    sleep 3
fi

# Start AxleLore
export PYTHONPATH="${PROJECT_DIR}/src"
echo "Starting AxleLore..."
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --log-level info
