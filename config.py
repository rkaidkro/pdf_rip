#!/usr/bin/env python3
"""
Configuration file for Document Rip automated processing.
"""

from pathlib import Path

# Folder Configuration
INPUT_FOLDER = "./input"
PROCESSED_FOLDER = "./processed"
MARKDOWN_FOLDER = "./markdown"

# Processing Configuration
WATCH_MODE = True  # Set to False to process existing files only
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

# Document Processing Settings
DEFAULT_CLASSIFICATION = "UNCLASSIFIED"
ENABLE_PII_REDACTION = False
MAX_RUNTIME_SECONDS = 3600
MAX_MEMORY_MB = 8192

# Supported file extensions
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.doc'}

# Create folders if they don't exist
def ensure_folders():
    """Create necessary folders if they don't exist."""
    Path(INPUT_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(PROCESSED_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(MARKDOWN_FOLDER).mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    ensure_folders()
    print("✅ Configuration loaded and folders created!")
    print(f"📁 Input folder: {INPUT_FOLDER}")
    print(f"📁 Processed folder: {PROCESSED_FOLDER}")
    print(f"📁 Markdown folder: {MARKDOWN_FOLDER}")
    print(f"👀 Watch mode: {'Enabled' if WATCH_MODE else 'Disabled'}")
