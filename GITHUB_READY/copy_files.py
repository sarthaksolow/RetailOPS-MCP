"""
Automated File Copier for GitHub Ready Folder
Copies only essential files from walmart_mcp to GITHUB_READY
"""
import shutil
import os
from pathlib import Path

# Paths
SOURCE = Path(r"D:\walmart_mcp")
DEST = Path(r"D:\walmart_mcp\GITHUB_READY")

def copy_file_safe(src, dst):
    """Copy file with error handling"""
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"✅ Copied: {src.name}")
        return True
    except Exception as e:
        print(f"❌ Failed to copy {src.name}: {e}")
        return False

def copy_dir_safe(src, dst, skip_patterns=None):
    """Copy directory recursively, skipping patterns"""
    if skip_patterns is None:
        skip_patterns = ['__pycache__', '.venv', '.git', '*.pyc', '.env']
    
    try:
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*skip_patterns))
        print(f"✅ Copied directory: {src.name}")
        return True
    except FileExistsError:
        print(f"⚠️ Directory already exists: {dst}")
        return False
    except Exception as e:
        print(f"❌ Failed to copy {src.name}: {e}")
        return False

print("="*70)
print("🚀 COPYING FILES TO GITHUB_READY")
print("="*70)

# 1. Client files (already have orchestrator.py and cli.py)
print("\n📁 CLIENT FILES:")
client_files = [
    'nlp_interface.py',
    'examples.py', 
    'test_client.py',
    'README.md',
    'QUICKSTART.md',
    '__init__.py'
]

for file in client_files:
    src = SOURCE / "client" / file
    dst = DEST / "client" / file
    if src.exists():
        copy_file_safe(src, dst)

# 2. Forecasting Server
print("\n📊 FORECASTING SERVER:")
forecast_src = SOURCE / "servers" / "forecasting"
forecast_dst = DEST / "servers" / "forecasting"

# Copy essential files
forecast_files = ['server.py', 'README.md', 'pyproject.toml', 'schema.json', 'main.py']
for file in forecast_files:
    src = forecast_src / file
    dst = forecast_dst / file
    if src.exists():
        copy_file_safe(src, dst)

# Copy data directory
data_src = forecast_src / "data"
data_dst = forecast_dst / "data"
if data_src.exists():
    copy_dir_safe(data_src, data_dst)

# 3. Replenishment Server
print("\n📦 REPLENISHMENT SERVER:")
replen_src = SOURCE / "servers" / "replenishment"
replen_dst = DEST / "servers" / "replenishment"

replen_files = ['server.py', 'mock_replenishment_inputs.json', 'test_replenishment_graph.py']
for file in replen_files:
    src = replen_src / file
    dst = replen_dst / file
    if src.exists():
        copy_file_safe(src, dst)

# 4. Pricing Strategy Server
print("\n💰 PRICING STRATEGY SERVER:")
pricing_src = SOURCE / "servers" / "pricing-strategy"
pricing_dst = DEST / "servers" / "pricing-strategy"

pricing_files = ['server.py', 'README.md', 'pyproject.toml', 'mock_pricing_inputs.json', 'test_pricing.py']
for file in pricing_files:
    src = pricing_src / file
    dst = pricing_dst / file
    if src.exists():
        copy_file_safe(src, dst)

# Copy data directory
pricing_data_src = pricing_src / "data"
pricing_data_dst = pricing_dst / "data"
if pricing_data_src.exists():
    copy_dir_safe(pricing_data_src, pricing_data_dst)

# 5. Documentation
print("\n📚 DOCUMENTATION:")
docs_dst = DEST / "docs"
docs_dst.mkdir(exist_ok=True)

doc_files = {
    'ARCHITECTURE_DIAGRAM.md': 'ARCHITECTURE.md',
    'PROJECT_ANALYSIS.md': 'TECHNICAL_DOCS.md',
    'USAGE.md': 'USAGE_GUIDE.md'
}

for src_name, dst_name in doc_files.items():
    src = SOURCE / src_name
    dst = docs_dst / dst_name
    if src.exists():
        copy_file_safe(src, dst)

# 6. Test integration
print("\n🧪 TESTS:")
test_src = SOURCE / "test_integration.py"
test_dst = DEST / "test_integration.py"
if test_src.exists():
    copy_file_safe(test_src, test_dst)

print("\n" + "="*70)
print("✅ FILE COPYING COMPLETE!")
print("="*70)
print(f"\n📂 Check your clean folder at: {DEST}")
print("\nNext step: Run 'create_final_files.py' to generate README, .gitignore, etc.")
