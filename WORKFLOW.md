# Development Workflow

## One-Time Setup

Run the setup script once on your machine:

```bash
cd ~/Documents/claude-paper-companion
./setup.sh
```

This will:
- ✓ Create virtual environment (if needed)
- ✓ Install all dependencies
- ✓ Configure shell aliases (pc, pcl, pc-activate)
- ✓ Configure Anthropic API key (prompts if not found)
- ✓ Initialize database

**Important:** You need an Anthropic API key to use Paper Companion.
- The setup script will prompt you to enter it
- If you don't have one, create it at: https://console.anthropic.com/
- Keys can only be viewed once when created, so save it!

After setup, reload your shell:
```bash
source ~/.bashrc  # or source ~/.zshrc
```

---

## Daily Workflow

### When pulling changes from GitHub:

```bash
cd ~/Documents/claude-paper-companion
git pull origin claude/todo-next-steps-011CUuZMovhjSs25CY9UAn7W
```

That's it! You **don't** need to recreate the venv or reinstall dependencies unless `requirements.txt` changed.

### If dependencies changed:

```bash
pc-activate                      # Activate venv
pip install -r requirements.txt  # Update dependencies
```

---

## Using Paper Companion

### With shell aliases (recommended):

```bash
pc zotero:KEY              # Load from Zotero
pc /path/to/paper.pdf      # Load local PDF
pc --resume SESSION_ID     # Resume session
pc --list-sessions FILE    # List sessions for paper
pcl 20                     # List 20 recent Zotero items
```

### Without aliases:

```bash
source venv/bin/activate              # Activate venv first
python chat.py zotero:KEY             # Load from Zotero
python chat.py /path/to/paper.pdf     # Load local PDF
python list_zotero.py 20              # List recent items
```

---

## Common Tasks

### Pull latest changes
```bash
git pull origin claude/todo-next-steps-011CUuZMovhjSs25CY9UAn7W
```

### Check what branch you're on
```bash
git branch
```

### See recent commits
```bash
git log --oneline -5
```

### Update dependencies (rare)
```bash
pc-activate
pip install -r requirements.txt
```

### Run tests
```bash
pc-activate
python test_db.py
```

---

## Troubleshooting

### "command not found: pc"
You need to reload your shell after setup:
```bash
source ~/.bashrc  # or source ~/.zshrc
```

### "ModuleNotFoundError"
Activate the virtual environment:
```bash
pc-activate  # or: source venv/bin/activate
```

### "Could not resolve authentication method" (API key error)
You need to set your Anthropic API key:

**Option 1: Add to your shell config (recommended)**
```bash
# Add to ~/.bashrc or ~/.zshrc
export ANTHROPIC_API_KEY='sk-ant-your-key-here'

# Then reload
source ~/.bashrc  # or source ~/.zshrc
```

**Option 2: Set for current session only**
```bash
export ANTHROPIC_API_KEY='sk-ant-your-key-here'
pc zotero:KEY
```

**Get a new API key:**
1. Go to https://console.anthropic.com/
2. Navigate to "API Keys"
3. Click "Create Key"
4. Copy the key (you can only see it once!)

**Check if it's set:**
```bash
echo $ANTHROPIC_API_KEY
```

### "Permission denied"
Make sure setup.sh is executable:
```bash
chmod +x setup.sh
```

### Import errors after git pull
Make sure you pulled the latest changes and dependencies are installed:
```bash
git pull origin claude/todo-next-steps-011CUuZMovhjSs25CY9UAn7W
pc-activate
pip install -r requirements.txt
```

---

## Virtual Environment Notes

**DO NOT** recreate the virtual environment every time!

- ✅ Create once: `python -m venv venv` (done by setup.sh)
- ✅ Activate when needed: `pc-activate` or `source venv/bin/activate`
- ✅ Keep it: The `venv/` folder stays on your machine
- ❌ Don't recreate it every time you pull changes
- ❌ Don't commit it to git (it's in .gitignore)

The venv is like your workspace - you set it up once and keep using it.
