#!/usr/bin/env python3
"""
Script to setup upload directories and static file serving for violation images
"""

import os
from pathlib import Path

def setup_upload_directories():
    """Create necessary upload directories"""
    base_dir = Path("uploads")
    
    # Create main directories
    directories = [
        base_dir / "violations",
        base_dir / "evidence", 
        base_dir / "plates",
        base_dir / "locations"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Create .gitkeep files to ensure directories are tracked
    for directory in directories:
        gitkeep_file = directory / ".gitkeep"
        if not gitkeep_file.exists():
            gitkeep_file.touch()
            print(f"Created .gitkeep: {gitkeep_file}")

if __name__ == "__main__":
    setup_upload_directories()
    print("Upload directories setup completed!")