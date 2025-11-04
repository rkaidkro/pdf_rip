#!/usr/bin/env python3
"""
Simple script to start the automated document processor.
"""

import sys
import subprocess
import os
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path}")
except ImportError:
    # python-dotenv not installed, skip
    pass
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")

def main():
    """Start the automated document processor using the CLI."""
    print("🚀 Starting Document Rip - Automated Folder Processor")
    print("=" * 60)
    
    # Import configuration
    try:
        from config import INPUT_FOLDER, PROCESSED_FOLDER, MARKDOWN_FOLDER, WATCH_MODE, LOG_LEVEL
    except ImportError:
        # Default values if config.py doesn't exist
        INPUT_FOLDER = "./input"
        PROCESSED_FOLDER = "./processed"
        MARKDOWN_FOLDER = "./markdown"
        WATCH_MODE = True
        LOG_LEVEL = "INFO"
    
    print(f"📁 Input folder: {INPUT_FOLDER}")
    print(f"📁 Processed folder: {PROCESSED_FOLDER}")
    print(f"📁 Markdown folder: {MARKDOWN_FOLDER}")
    print(f"👀 Watch mode: {'Enabled' if WATCH_MODE else 'Disabled'}")
    print("=" * 60)
    print("💡 Just drop PDF or Word documents into the input folder!")
    print("🛑 Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        # Build the command
        cmd = [
            sys.executable, "-m", "src", "watch",
            "--input-folder", INPUT_FOLDER,
            "--processed-folder", PROCESSED_FOLDER,
            "--markdown-folder", MARKDOWN_FOLDER,
            "--log-level", LOG_LEVEL
        ]
        
        if not WATCH_MODE:
            cmd.append("--no-watch")
        
        # Run the command
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n🛑 Stopping processor...")
        print("✅ Processor stopped safely")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
