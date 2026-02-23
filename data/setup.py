#!/usr/bin/env python3
"""
ReconX Data Setup
Initialize data directory structure
"""

import sys
from pathlib import Path

def setup_data_directory():
    """Create all required data directories"""
    base_dir = Path("data")
    
    directories = [
        base_dir,
        base_dir / "cache",
        base_dir / "cache" / "httpx",
        base_dir / "cache" / "nuclei",
        base_dir / "cache" / "downloads",
        base_dir / "cache" / "temp",
        base_dir / "state",
        base_dir / "backups",
        base_dir / "exports"
    ]
    
    created = 0
    for d in directories:
        if not d.exists():
            d.mkdir(parents=True)
            print(f"Created: {d}")
            created += 1
        else:
            print(f"Exists:  {d}")
    
    # Initialize database
    from data.schema import init_database
    if init_database():
        print("\n✅ Database initialized successfully")
    else:
        print("\n❌ Database initialization failed")
        return False
    
    print(f"\n📊 Created {created} new directories")
    return True

if __name__ == "__main__":
    success = setup_data_directory()
    sys.exit(0 if success else 1)
