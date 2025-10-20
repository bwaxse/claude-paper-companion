# Paper Companion 📚

An intelligent command-line tool for having conversations with Claude about scientific PDFs, with automatic insight extraction and deep Zotero integration. Works seamlessly with papers already in your Zotero library!

## 📖 Documentation

- **[INSTALL.md](INSTALL.md)** - Step-by-step installation guide
- **[USAGE.md](USAGE.md)** - Real workflow examples & shell shortcuts  
- **[README.md](#features)** - Features and overview (this file)

## Quick Start (For Experienced Users)

```bash
# Setup
git clone [repository]
cd paper-companion
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python setup.py  # Configure Zotero

# Add to ~/.zshrc (see USAGE.md for full shortcuts)
alias z20='cd ~/Documents/paper_companion && source venv/bin/activate && python list_zotero.py 20'
alias pc='cd ~/Documents/paper_companion && source venv/bin/activate && python chat.py'

# Daily workflow
z20                           # List recent papers
pc zotero:ABCD1234           # Discuss paper
pc "zotero:search:attention"  # Search and discuss
```

**📖 See [USAGE.md](USAGE.md) for complete workflow examples and shell shortcuts**

## Features

### Core Capabilities
- **Interactive PDF Analysis**: Claude reads your paper (including figures) and provides structured summaries
- **Conversational Interface**: Ask questions, discuss methods, explore implications
- **Smart Flagging**: Mark important exchanges during conversation with `/flag`
- **Structured Extraction**: Automatically extracts key insights, methods, findings, and your specific interests
- **Comprehensive Metadata**: Extracts and preserves complete bibliographic information

### Zotero Integration 🔄
- **Load from Zotero**: Open papers directly from your Zotero library by key or search
- **Automatic Detection**: Finds existing Zotero items to avoid duplicates
- **Metadata Enhancement**: Updates incomplete Zotero records with extracted metadata
- **Smart Deduplication**: Uses PDF hash to prevent duplicate entries
- **Highlight Suggestions**: Get recommendations for key passages to highlight
- **Related Papers**: Find similar papers in your library based on tags/topics
- **Searchable Notes**: Creates structured HTML notes attached to papers

## Installation

1. **Clone and setup environment:**
```bash
git clone [repository]
cd paper-companion
python -m venv venv
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

2. **Configure API keys:**
```bash
# Add to ~/.zshrc or ~/.bashrc
export ANTHROPIC_API_KEY="sk-ant-..."

# Run setup script for Zotero
python setup.py
```

3. **Get Zotero credentials:**
- Visit https://www.zotero.org/settings/keys
- Create new API key with read/write permissions
- Note your Library ID (in settings)
- Run `python setup.py` to configure

## Usage

### Three Ways to Load Papers

#### 1. From local file:
```bash
python chat.py path/to/paper.pdf
```

#### 2. From Zotero by item key:
```bash
# First, list recent papers to get keys
python chat.py --list-recent

# Then load by key
python chat.py zotero:ABC123XY
```

#### 3. Search and load from Zotero:
```bash
python chat.py "zotero:search:transformer attention"
python chat.py "zotero:search:10.1234/doi"  # Search by DOI
```

### During Conversation

- Ask questions naturally about the paper
- `/flag` - Mark current exchange as important
- `/img N` - View info about figure N
- `/highlight` - Get suggestions for passages to highlight in Zotero
- `/related` - Find related papers in your library
- `/exit` - End session and save insights

### Example Session

```
$ python chat.py "zotero:search:attention is all you need"

Searching Zotero for: attention is all you need
Loading PDF from Zotero: Attention Is All You Need

Existing Zotero Metadata:
📚 Attention Is All You Need
👥 Ashish Vaswani, Noam Shazeer, Niki Parmar et al.
📅 2017-06
📖 arXiv
🔗 DOI: 10.48550/arXiv.1706.03762
🏷️ Tags: transformer, attention, deep-learning

Initial Analysis:
================
**Title & Authors**: Verified - Attention Is All You Need by Vaswani et al.

**Main Research Question**: Can we create a high-performance sequence transduction 
model based solely on attention mechanisms?

**Your Highlights**: 
- Section 3.2: Multi-head attention mechanism
- Table 2: Performance comparisons
- Section 5: Why self-attention works

You: How does positional encoding preserve sequence order without recurrence?

Claude: The positional encodings use sine and cosine functions of different 
frequencies. Each dimension corresponds to a sinusoid...

You: /flag

✓ Exchange flagged

You: /highlight

Highlighting Suggestions:
1. Page 3: "We propose a new simple network architecture..." 
   Key contribution statement
2. Page 5: "Multi-head attention allows the model to jointly..."
   Core mechanism explanation

You: /related

Related papers in your library:
• BERT: Pre-training of Deep Bidirectional Transformers (2019)
• GPT-3: Language Models are Few-Shot Learners (2020)

You: /exit

Extracting insights from conversation...
✓ Insights saved to Zotero
✓ Backup saved: ~/.paper_companion/sessions/attention_20240115_143022.json
```

## Zotero Workflow Integration

### Recommended Workflow

1. **Import to Zotero First**: Add papers to Zotero using the browser connector
2. **Load for Discussion**: `python chat.py zotero:ITEMKEY`
3. **Have Conversation**: Discuss methods, findings, implications
4. **Get Highlight Suggestions**: Use `/highlight` command
5. **Manual Highlighting**: Open PDF in Zotero, highlight suggested passages
6. **Save Insights**: Exit to create searchable note with your interpretations

### Finding Papers Later

In Zotero, search for:
- **Tags**: `claude-analyzed`, `method:transformer`, `topic:attention`
- **Notes**: Your specific interpretations and questions
- **Extra field**: PDF hash, ArXiv ID, session dates

### Metadata Fields Captured

**Bibliographic**:
- Title, authors (structured)
- Journal name & abbreviation
- Volume, issue, pages
- Publication date
- DOI, ArXiv ID, PMID, ISSN
- Abstract and language

**Your Insights**:
- Focus areas (what you concentrated on)
- Key methods (technical approaches discussed)
- Main findings (results you explored)
- Your interpretations (personal connections)
- Limitations (weaknesses identified)
- Open questions (for follow-up)
- Application ideas

## Advanced Features

### Batch Processing
```bash
# Process multiple papers
for key in ABC123 DEF456 GHI789; do
    python chat.py zotero:$key < standard_questions.txt
done
```

### Custom Templates
Edit extraction prompts in `chat.py` to focus on field-specific aspects.

### Query Your Knowledge Base
```python
# Coming soon: Cross-paper analysis
python query.py "papers using transformer architecture"
python compare.py paper1.pdf paper2.pdf
```

## File Structure

```
~/.paper_companion/
├── sessions/              # JSON backups of all conversations
├── cache/                # PDF processing cache
└── .zotero_config.json   # Zotero API credentials (mode 0600)

~/Zotero/storage/         # Your existing Zotero PDFs
├── ITEM_KEY_1/
│   └── paper.pdf
└── ITEM_KEY_2/
    └── article.pdf
```

## Tips

### Effective Usage
1. **Flag liberally**: Mark any exchange that sparks ideas
2. **Be specific**: Ask about particular methods or implications
3. **Use commands**: `/highlight` and `/related` enhance your research
4. **One paper per session**: Keeps insights focused and clean

### Zotero Organization
- Create collections for projects
- Use saved searches for `claude-analyzed` items
- Export insights for sharing with collaborators
- Combine with Zotero's citation features

## Privacy & Security

- API keys stored locally only (`~/.zotero_config.json`)
- Papers processed locally before sending to Claude
- No data leaves your control
- Local backups of all conversations
- Zotero credentials protected (mode 0600)

## Troubleshooting

**"PDF not found in Zotero storage"**
- Ensure PDF is downloaded in Zotero (not just linked)
- Check: Zotero Preferences > Files & Folders > Storage Location

**"No items found in Zotero"**
- Verify search terms or item key
- Check Zotero sync is complete
- Ensure API key has read permissions

**Extraction errors**
- Check JSON backup in `~/.paper_companion/sessions/`
- Verify PDF is text-based (not scanned image)

## Contributing

Ideas and contributions welcome! Priority areas:
- Automatic highlight integration via Zotero API
- Citation network visualization  
- Semantic similarity search
- Integration with Obsidian/Roam
- Multi-paper conversation support

## License

MIT
