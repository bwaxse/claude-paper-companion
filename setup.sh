#!/bin/bash
#
# Paper Companion Setup Script
# Sets up virtual environment and shell aliases
#

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"

echo "========================================="
echo "Paper Companion Setup"
echo "========================================="
echo ""

# 1. Check Python version
echo "→ Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found. Please install Python 3.8+."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Found Python $PYTHON_VERSION"
echo ""

# 2. Create virtual environment (if it doesn't exist)
if [ -d "$VENV_DIR" ]; then
    echo "→ Virtual environment already exists at: $VENV_DIR"
else
    echo "→ Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
fi
echo ""

# 3. Activate and install dependencies
echo "→ Installing dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet
pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
echo "✓ Dependencies installed"
echo ""

# 4. Configure shell aliases
echo "→ Configuring shell aliases..."
echo ""

# Detect shell
SHELL_NAME=$(basename "$SHELL")
if [ "$SHELL_NAME" = "zsh" ]; then
    RC_FILE="$HOME/.zshrc"
elif [ "$SHELL_NAME" = "bash" ]; then
    RC_FILE="$HOME/.bashrc"
else
    RC_FILE="$HOME/.profile"
fi

echo "Detected shell: $SHELL_NAME"
echo "Config file: $RC_FILE"
echo ""

# Alias definitions
ALIAS_BLOCK="
# Paper Companion aliases (added by setup.sh)
alias pc='python $SCRIPT_DIR/chat.py'
alias pcl='python $SCRIPT_DIR/list_zotero.py'
alias pc-activate='source $VENV_DIR/bin/activate'
"

# Check if aliases already exist
if grep -q "# Paper Companion aliases" "$RC_FILE" 2>/dev/null; then
    echo "⚠ Aliases already configured in $RC_FILE"
    echo ""
    read -p "Do you want to update them? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove old aliases and add new ones
        sed -i.bak '/# Paper Companion aliases/,/^$/d' "$RC_FILE"
        echo "$ALIAS_BLOCK" >> "$RC_FILE"
        echo "✓ Aliases updated"
    else
        echo "○ Skipped alias update"
    fi
else
    # Add aliases
    echo "$ALIAS_BLOCK" >> "$RC_FILE"
    echo "✓ Aliases added to $RC_FILE"
fi
echo ""

# 5. Configure Anthropic API Key
echo "→ Checking Anthropic API key..."
echo ""

# Check if API key is already set in environment
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "✓ ANTHROPIC_API_KEY is already set in current environment"
    API_KEY_SET=true
# Check if it's in the RC file
elif grep -q "ANTHROPIC_API_KEY" "$RC_FILE" 2>/dev/null; then
    echo "✓ ANTHROPIC_API_KEY found in $RC_FILE"
    API_KEY_SET=true
else
    echo "⚠ ANTHROPIC_API_KEY not found"
    echo ""
    echo "You need an Anthropic API key to use Paper Companion."
    echo ""
    echo "To get a key:"
    echo "  1. Go to: https://console.anthropic.com/"
    echo "  2. Sign in to your account"
    echo "  3. Navigate to 'API Keys'"
    echo "  4. Click 'Create Key' (keys start with 'sk-ant-...')"
    echo "  5. Copy the key (you can only see it once!)"
    echo ""
    read -p "Do you have an API key to configure now? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your Anthropic API key: " API_KEY
        echo ""

        if [ -n "$API_KEY" ]; then
            # Add to RC file
            echo "" >> "$RC_FILE"
            echo "# Anthropic API key for Paper Companion (added by setup.sh)" >> "$RC_FILE"
            echo "export ANTHROPIC_API_KEY='$API_KEY'" >> "$RC_FILE"
            echo "✓ API key added to $RC_FILE"
            echo ""
            echo "⚠ Important: Reload your shell or run: source $RC_FILE"
            API_KEY_SET=true
        else
            echo "⚠ No key entered. You'll need to set ANTHROPIC_API_KEY manually."
            API_KEY_SET=false
        fi
    else
        echo ""
        echo "○ Skipping API key configuration"
        echo ""
        echo "To configure later, add this to $RC_FILE:"
        echo "  export ANTHROPIC_API_KEY='your-key-here'"
        echo ""
        API_KEY_SET=false
    fi
fi
echo ""

# 6. Test database initialization
echo "→ Testing database initialization..."
python3 "$SCRIPT_DIR/chat.py" --help > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Database initialized successfully"
else
    echo "⚠ Warning: Could not test database (this might be okay)"
fi
echo ""

# 7. Summary
echo "========================================="
echo "Setup Complete! 🎉"
echo "========================================="
echo ""

if [ "$API_KEY_SET" = false ]; then
    echo "⚠ IMPORTANT: You still need to configure your Anthropic API key!"
    echo ""
    echo "Add this to $RC_FILE:"
    echo "  export ANTHROPIC_API_KEY='your-key-here'"
    echo ""
    echo "Get your key at: https://console.anthropic.com/"
    echo ""
fi

echo "Available commands (after reloading shell):"
echo ""
echo "  pc zotero:KEY              # Start paper session"
echo "  pc /path/to/paper.pdf      # Start with local PDF"
echo "  pc --resume SESSION_ID     # Resume session"
echo "  pc --list-recent           # List recent Zotero items"
echo "  pcl 20                     # List 20 recent items"
echo "  pc-activate                # Activate virtual environment"
echo ""
echo "To activate changes now, run:"
echo "  source $RC_FILE"
echo ""
echo "Virtual environment location:"
echo "  $VENV_DIR"
echo ""
echo "To manually activate virtual environment:"
echo "  source $VENV_DIR/bin/activate"
echo ""
