# Usage Guide & Workflow Examples

## Quick Setup for Power Users

Add these functions to your `~/.zshrc` or `~/.bashrc`:

```bash
# ============================================
# Scholia Shortcuts
# ============================================

# Main Scholia function
pc() {
    cd ~/Documents/scholia
    source venv/bin/activate

    if [ $# -eq 0 ]; then
        echo "📚 Scholia ready! Usage:"
        echo "  pc paper.pdf             # Load local PDF"
        echo "  pc zotero:KEY            # Load from Zotero"
        echo "  pc 'zotero:search:query' # Search Zotero"
        echo "  pcl                      # List recent papers"
        echo "  pch                      # Just activate environment"
        echo "  zl 20                    # List 20 recent Zotero items"
    else
        python chat.py "$@"
    fi
}

# Shortcuts
alias pcl='pc --list-recent'                    # List papers
alias pcs='pc "zotero:search:'                  # Search (add terms after)
alias pch='cd ~/Documents/paper_companion && source venv/bin/activate'  # Just go there

# Smart Zotero listing function
zl() {
    cd ~/Documents/paper_companion
    source venv/bin/activate
    python list_zotero.py ${1:-20} ${2}
}
```

Then reload: `source ~/.zshrc`

## Daily Workflow Examples

### Morning Research Session

```bash
# 1. Check what's new in your library
zl 10

# Output:
# Recent Zotero Items (Last 10)
# ┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━┳━━━━┓
# ┃ Key        ┃ Title                    ┃ Authors   ┃ Year ┃ PDF ┃
# ┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━╇━━━━┫
# │ ABCD1234   │ Attention Is All You... │ Vaswani   │ 2017 │  ✓  │
# │ EFGH5678   │ BERT: Pre-training...   │ Devlin    │ 2018 │  ✓  │

# 2. Pick a paper to discuss
pc zotero:ABCD1234

# 3. Have focused conversation
You: What's the key innovation compared to RNNs?
Claude: The key innovation is eliminating recurrence entirely...

You: /flag  # Mark important insight

You: How would this apply to time series?
Claude: ...

# 4. Get highlighting suggestions
You: /highlight
Claude: Key passages to highlight:
  • Page 3: "multi-head attention allows..."
  • Page 5: "positional encodings are added..."

# 5. Find related work
You: /related

# 6. Save insights and exit
You: /exit
```

### Quick Paper Review

```bash
# Search for specific topic
pc "zotero:search:transformer attention mechanism"
# Select from results, then discuss

# Or grab a PDF from downloads
pc ~/Downloads/new_paper.pdf
# This creates/updates Zotero entry automatically
```

### Building Knowledge Connections

```bash
# Morning: Read paper on transformers
pc zotero:ABC123
You: What are the computational bottlenecks?
You: /flag
You: /exit

# Afternoon: Read paper on efficient attention
pc zotero:DEF456  
You: How does this address transformer bottlenecks?
You: Compare with ABC123's approach
You: /exit

# Later: Search your notes in Zotero
# Tags: topic:attention, method:efficient-attention
# Your insights are connected!
```

## Key Commands During Chat

| Command | Purpose | Example Output |
|---------|---------|----------------|
| `/flag` | Mark important exchange | "✓ Exchange flagged" |
| `/highlight` | Get passages to highlight | "Page 3: 'Multi-head attention...'" | 
| `/related` | Find similar papers | "Related: BERT (2018), GPT-2 (2019)" |
| `/img N` | Check figure N | "Figure 2 from page 5" |
| `/exit` | End and save insights | "✓ Insights saved to Zotero" |

## Workflow Tips

### 1. Pre-reading Strategy
```bash
# Quick scan before deep read
pc zotero:KEY
You: Give me a 3-sentence summary
You: What should I focus on given my interest in [topic]?
You: /exit

# Then read PDF in Zotero with this guidance
```

### 2. Post-reading Deep Dive
```bash
# After highlighting in Zotero
pc zotero:KEY
You: I highlighted the section on [X]. Why is this approach better than [Y]?
You: Can you explain the math in equation 3?
You: What are the unstated assumptions here?
You: /flag  # For each key insight
You: /exit
```

### 3. Literature Review Mode
```bash
# Process multiple related papers
for key in ABC123 DEF456 GHI789; do
    echo "Processing $key"
    pc zotero:$key << EOF
What is the main contribution?
How does the methodology differ from previous work?
What datasets were used?
/exit
EOF
done

# Then search in Zotero for all your tagged insights
```

### 4. Writing Support
```bash
# When writing your paper
pc "zotero:search:related work transformers"

You: Help me write a paragraph comparing these three approaches
You: What's the proper way to cite the attention mechanism?
You: /exit
```

## Advanced Zotero Integration

### Finding Papers by Tags
After using Scholia, your Zotero library has rich tags:
- `claude-analyzed` - All processed papers
- `session-20240115` - When you discussed it
- `method:transformer` - Technical approaches
- `topic:attention` - Research areas
- `focus:efficiency` - Your specific interests

### Search Strategies in Zotero
1. **By method**: Tag = "method:attention"
2. **By your focus**: Tag = "focus:optimization"  
3. **By session**: Tag = "session-202401"
4. **Combined**: Tag = "method:transformer" AND "topic:efficiency"

### Building Knowledge Graphs
```bash
# Export all your insights
cd ~/.paper_companion/sessions/
cat *.json | jq '.insights.focus_areas' | sort | uniq -c
# See what topics you focus on most

# Find connection patterns
grep -h "transformer" *.json | wc -l
# How many papers discuss transformers?
```

## Troubleshooting Common Issues

### "Key not found"
```bash
# Key might have changed, search instead:
pc "zotero:search:title words"
```

### Want to reprocess a paper?
```bash
# Your insights are additive, just run again:
pc zotero:KEY
# New session adds to existing notes
```

### Need to batch process?
```bash
# Create a questions file
cat > standard_questions.txt << EOF
What is the main contribution?
What problem does this solve?
What are the limitations?
/exit
EOF

# Run on multiple papers
pc zotero:KEY < standard_questions.txt
```

## Daily Checklist

- [ ] Morning: `zl 10` - Check new additions
- [ ] Pick paper: `pc zotero:KEY` 
- [ ] Ask specific questions about methods
- [ ] `/flag` important insights
- [ ] `/highlight` to get key passages
- [ ] `/exit` to save structured notes
- [ ] Open in Zotero to highlight suggested passages
- [ ] Review tags in Zotero for patterns

## Why This Workflow Works

1. **Conversations → Understanding**: Discussing forces deeper engagement than just reading
2. **Structured Notes**: Not just highlights, but your interpretations and connections
3. **Searchable Insights**: Your actual questions and interests become searchable
4. **Progressive Building**: Each session builds on previous understanding
5. **No Context Switching**: Terminal → Zotero → Terminal flow is seamless

## Example Session Output

After a week of using Scholia:
- 15 papers discussed
- 47 flagged insights
- 120+ tagged concepts
- Zotero search for "method:attention AND focus:efficiency" → 3 papers
- Each paper has structured notes with YOUR interpretations

Your literature review writes itself!
