#!/bin/bash

# Convenience script to activate the virtual environment and run pdfrip
# Usage: ./activate_env.sh [pdfrip command and arguments]

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate the virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# If arguments are provided, run the command
if [ $# -gt 0 ]; then
    exec "$@"
else
    # If no arguments, just activate the environment and show help
    echo "Virtual environment activated!"
    echo "Available commands:"
    echo "  pdfrip --help     - Show pdfrip help"
    echo "  pdfrip watch      - Start automated folder processing"
    echo "  pdfrip convert    - Convert PDF/Word documents to Markdown"
    echo "  pdfrip test       - Run tests"
    echo "  pdfrip audit      - Show compliance audit"
    echo ""
    echo "Examples:"
    echo "  ./start_processor.py                    # Start automated processing"
    echo "  pdfrip watch                           # Start automated processing"
    echo "  pdfrip watch --no-watch                # Process existing files only"
    echo "  pdfrip convert document.pdf --output-dir ./output"
    echo "  pdfrip convert document.docx --output-dir ./output"
    echo ""
    echo "You can also run: ./activate_env.sh pdfrip --help"
fi
