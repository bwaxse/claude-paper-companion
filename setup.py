#!/usr/bin/env python3
"""
Setup script for Paper Companion
Configures Zotero API access and validates environment
"""

import json
import os
from pathlib import Path
from getpass import getpass

def setup_zotero():
    """Configure Zotero API credentials"""
    print("\n🔧 Zotero Setup")
    print("-" * 40)
    print("Get your API credentials from: https://www.zotero.org/settings/keys")
    print("\nYou'll need:")
    print("1. Library ID (found in your Zotero settings)")
    print("2. API Key (create new key with read/write access)")
    
    library_id = input("\nLibrary ID: ").strip()
    library_type = input("Library type (user/group) [user]: ").strip() or "user"
    api_key = getpass("API Key: ").strip()
    
    config = {
        "library_id": library_id,
        "library_type": library_type,
        "api_key": api_key
    }
    
    config_path = Path.home() / '.zotero_config.json'
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Set restrictive permissions
    config_path.chmod(0o600)
    
    print(f"✅ Zotero config saved to: {config_path}")
    return config

def verify_anthropic():
    """Check if Anthropic API key is set"""
    print("\n🤖 Checking Anthropic API...")
    
    if 'ANTHROPIC_API_KEY' in os.environ:
        print("✅ ANTHROPIC_API_KEY found in environment")
        return True
    else:
        print("❌ ANTHROPIC_API_KEY not found")
        print("\nAdd to your ~/.zshrc or ~/.bashrc:")
        print('export ANTHROPIC_API_KEY="your-key-here"')
        return False

def create_directories():
    """Create necessary directories"""
    dirs = [
        Path.home() / '.paper_companion' / 'sessions',
        Path.home() / '.paper_companion' / 'cache'
    ]
    
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {dir_path}")

def test_imports():
    """Test that all dependencies are installed"""
    print("\n📦 Testing dependencies...")
    
    try:
        import anthropic
        print("✅ anthropic")
    except ImportError:
        print("❌ anthropic - run: pip install anthropic")
        return False
    
    try:
        import pyzotero
        print("✅ pyzotero")
    except ImportError:
        print("❌ pyzotero - run: pip install pyzotero")
        return False
    
    try:
        import fitz
        print("✅ PyMuPDF")
    except ImportError:
        print("❌ PyMuPDF - run: pip install PyMuPDF")
        return False
    
    try:
        import rich
        print("✅ rich")
    except ImportError:
        print("❌ rich - run: pip install rich")
        return False
    
    return True

def main():
    print("🚀 Paper Companion Setup")
    print("=" * 40)
    
    # Check dependencies
    if not test_imports():
        print("\n⚠️  Please install missing dependencies:")
        print("pip install -r requirements.txt")
        return
    
    # Check Anthropic
    anthropic_ok = verify_anthropic()
    
    # Setup Zotero
    if input("\nConfigure Zotero now? (y/n): ").lower() == 'y':
        setup_zotero()
    else:
        print("⏩ Skipping Zotero setup (you can run this script again later)")
    
    # Create directories
    create_directories()
    
    print("\n" + "=" * 40)
    if anthropic_ok:
        print("✅ Setup complete! You can now run:")
        print("python chat.py path/to/paper.pdf")
    else:
        print("⚠️  Setup partially complete. Please set ANTHROPIC_API_KEY")
    
    print("\n📝 Optional: Create an alias in ~/.zshrc:")
    print("alias paper='python ~/path/to/chat.py'")

if __name__ == "__main__":
    main()
