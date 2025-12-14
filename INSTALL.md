# Installation Guide

## Prerequisites

- Python 3.8 or higher
- Zotero desktop app installed
- Terminal access (macOS Terminal, Linux terminal, or Windows WSL)

## Step 1: Get API Keys

### Anthropic API Key (Required)
1. Go to https://console.anthropic.com/
2. Create account or sign in
3. Navigate to API keys
4. Create new key
5. Copy the key (starts with `sk-ant-`)

### Zotero API Key (Required)
1. Go to https://www.zotero.org/settings/keys
2. Click "Create new private key"
3. Enter description: "Scholia"
4. Check permissions:
   - [x] Allow library access
   - [x] Allow notes access  
   - [x] Allow write access
5. Save and copy the key
6. Note your User ID (shown on same page)

## Step 2: Install Scholia

```bash
# 1. Clone repository
git clone https://github.com/yourusername/paper-companion.git
cd paper-companion

# 2. Create virtual environment
python -m venv venv

# 3. Activate it
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# 4. Install dependencies
pip install -r requirements.txt
```

## Step 3: Configure

```bash
# Run setup wizard
python setup.py

# It will ask for:
# - Zotero Library ID (from settings page)
# - Library type (usually 'user')
# - API key (from Step 1)
```

## Step 4: Set Environment Variable

### macOS/Linux (zsh/bash)

```bash
# Add to ~/.zshrc or ~/.bashrc
echo 'export ANTHROPIC_API_KEY="sk-ant-your-key-here"' >> ~/.zshrc

# Reload
source ~/.zshrc
```

### Windows (PowerShell)

```powershell
# Add to PowerShell profile
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY','sk-ant-your-key-here','User')
```

## Step 5: Add Shell Shortcuts (Recommended)

```bash
# Add to ~/.zshrc for quick access
cat >> ~/.zshrc << 'EOF'

# Scholia shortcuts
pc() {
    cd ~/Documents/scholia  # Update path
    source venv/bin/activate
    if [ $# -eq 0 ]; then
        echo "📚 Scholia ready!"
    else
        python chat.py "$@"
    fi
}

alias z20='cd ~/Documents/paper_companion && source venv/bin/activate && python list_zotero.py 20'
EOF

source ~/.zshrc
```

## Step 6: Verify Installation

```bash
# Test Zotero connection
z20
# Should show your 20 most recent papers

# Test Claude connection
pc --help
# Should show help message

# Try loading a paper
pc zotero:YOURKEY
# Should start conversation
```
