#!/usr/bin/env python3
"""Verify that the project structure is set up correctly."""
import os
import sys

def check_file_exists(filepath):
    """Check if a file exists."""
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    print(f"{status} {filepath}")
    return exists

def check_directory_exists(dirpath):
    """Check if a directory exists."""
    exists = os.path.isdir(dirpath)
    status = "✓" if exists else "✗"
    print(f"{status} {dirpath}/")
    return exists

def main():
    """Run verification checks."""
    print("=" * 60)
    print("Project Structure Verification")
    print("=" * 60)
    print()
    
    all_good = True
    
    # Check directories
    print("Checking directories...")
    dirs = [
        "src",
        "src/infrastructure",
        "src/agents",
        "src/orchestrator",
        "tests",
        "scripts"
    ]
    for d in dirs:
        if not check_directory_exists(d):
            all_good = False
    print()
    
    # Check configuration files
    print("Checking configuration files...")
    config_files = [
        "setup.py",
        "requirements.txt",
        "pytest.ini",
        ".gitignore",
        ".env.example",
        "README.md"
    ]
    for f in config_files:
        if not check_file_exists(f):
            all_good = False
    print()
    
    # Check infrastructure modules
    print("Checking infrastructure modules...")
    infra_files = [
        "src/infrastructure/__init__.py",
        "src/infrastructure/aws_config.py",
        "src/infrastructure/setup_s3.py",
        "src/infrastructure/setup_dynamodb.py",
        "src/infrastructure/setup_ses.py",
        "src/infrastructure/setup_iam.py",
        "src/infrastructure/setup_bedrock_kb.py"
    ]
    for f in infra_files:
        if not check_file_exists(f):
            all_good = False
    print()
    
    # Check scripts
    print("Checking setup scripts...")
    script_files = [
        "scripts/setup_infrastructure.py",
        "scripts/check_ses_status.py",
        "scripts/verify_setup.py"
    ]
    for f in script_files:
        if not check_file_exists(f):
            all_good = False
    print()
    
    # Check tests
    print("Checking test files...")
    test_files = [
        "tests/__init__.py",
        "tests/test_infrastructure_setup.py"
    ]
    for f in test_files:
        if not check_file_exists(f):
            all_good = False
    print()
    
    # Summary
    print("=" * 60)
    if all_good:
        print("✓ All checks passed! Project structure is set up correctly.")
        print()
        print("Next steps:")
        print("1. Create a virtual environment: python -m venv venv")
        print("2. Activate it: venv\\Scripts\\activate (Windows) or source venv/bin/activate (Unix)")
        print("3. Install dependencies: pip install -r requirements.txt")
        print("4. Configure AWS credentials: aws configure")
        print("5. Copy .env.example to .env and update values")
        print("6. Run infrastructure setup: python scripts/setup_infrastructure.py")
    else:
        print("✗ Some checks failed. Please review the output above.")
        return 1
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
