#!/usr/bin/env python3
"""Check SES email verification status."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from infrastructure.setup_ses import check_verification_status


if __name__ == "__main__":
    print("Checking SES verification status...")
    print()
    
    try:
        check_verification_status()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
