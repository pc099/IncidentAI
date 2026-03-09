"""
Update only the orchestrator Lambda code (no configuration changes)
"""

import boto3
import os
import shutil
import zipfile
from pathlib import Path

def create_deployment_package():
    """Create deployment package for orchestrator"""
    print("📦 Creating deployment package...")
    
    # Create temp directory
    temp_dir = Path("temp_lambda_package")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()
    
    # Copy orchestrator handler
    shutil.copy("lambda_handlers/orchestrator_handler.py", temp_dir / "orchestrator_handler.py")
    
    # Copy src directory
    src_dest = temp_dir / "src"
    shutil.copytree("src", src_dest, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    
    # Also copy to root for imports
    for item in (Path("src")).rglob("*.py"):
        if "__pycache__" not in str(item):
            rel_path = item.relative_to("src")
            dest = temp_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(item, dest)
    
    # Create ZIP
    zip_path = "orchestrator_update.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in temp_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(temp_dir)
                zipf.write(file, arcname)
    
    # Cleanup
    shutil.rmtree(temp_dir)
    
    print(f"  ✓ Created {zip_path}")
    return zip_path


def update_lambda_code(function_name, zip_path):
    """Update Lambda function code only"""
    lambda_client = boto3.client('lambda')
    
    print(f"🚀 Updating {function_name} code...")
    
    with open(zip_path, 'rb') as f:
        zip_content = f.read()
    
    try:
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        print(f"  ✓ Code updated successfully")
        print(f"  LastUpdateStatus: {response.get('LastUpdateStatus')}")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("Update Orchestrator Lambda Code Only")
    print("=" * 60)
    
    # Create package
    zip_path = create_deployment_package()
    
    # Update Lambda
    success = update_lambda_code("incident-orchestrator", zip_path)
    
    # Cleanup
    os.remove(zip_path)
    
    if success:
        print("\n✅ Orchestrator code updated successfully!")
        print("\nTest with:")
        print("  python scripts/test_realistic_scenario.py 2")
    else:
        print("\n❌ Update failed")


if __name__ == "__main__":
    main()
