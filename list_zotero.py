#!/usr/bin/env python3
"""
List recent items from Zotero library with responsive layout
"""

import json
import os
from pathlib import Path
from pyzotero import zotero
from rich.console import Console
from rich.table import Table

console = Console()

def get_terminal_width():
    """Get terminal width for responsive layout"""
    try:
        return os.get_terminal_size().columns
    except:
        return 80  # Default fallback

def list_recent_items(limit=20, compact=None):
    """
    List recent items from Zotero with their keys
    
    Args:
        limit: Number of items to show
        compact: Force compact mode (auto-detect if None)
    """
    config_path = Path.home() / '.zotero_config.json'
    
    if not config_path.exists():
        console.print("[red]Zotero not configured. Run: python chat.py --setup[/red]")
        return
    
    with open(config_path) as f:
        config = json.load(f)
    
    zot = zotero.Zotero(
        config['library_id'],
        config['library_type'],
        config['api_key']
    )
    
    # Get recent items
    items = zot.items(limit=limit, sort='dateModified', direction='desc')
    
    # Auto-detect compact mode based on terminal width
    term_width = get_terminal_width()
    if compact is None:
        compact = term_width < 100
    
    # Create table with appropriate layout
    if compact:
        # Compact mode for narrow terminals
        table = Table(
            title=f"Recent Zotero Items ({limit})",
            show_header=True,
            header_style="bold cyan",
            show_lines=False,
            expand=False
        )
        
        table.add_column("Key", style="cyan", min_width=10, no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Year", style="green", width=4)
        table.add_column("PDF", style="blue", width=3, justify="center")
        
        for item in items:
            data = item['data']
            key = item['key']
            
            # Title - more aggressive truncation in compact mode
            title = data.get('title', 'Untitled')
            max_title_len = term_width - 25  # Leave room for other columns
            if len(title) > max_title_len:
                title = title[:max_title_len-3] + "..."
            
            # Get year
            date = data.get('date', '')
            year = date[:4] if date else 'N/A'
            
            # PDF indicator (simplified check)
            pdf_indicator = "✓" if data.get('itemType') != 'note' else ""
            
            table.add_row(key, title, year, pdf_indicator)
    
    else:
        # Full mode for wide terminals
        table = Table(
            title=f"Recent Zotero Items (Last {limit})",
            show_header=True,
            header_style="bold magenta",
            show_lines=False,
            expand=False
        )
        
        # Ensure Key column is never truncated
        table.add_column("Key", style="cyan", width=12, min_width=10, no_wrap=True)
        table.add_column("Title", style="white", width=None, ratio=2)
        table.add_column("Authors", style="yellow", width=None, ratio=1)
        table.add_column("Year", style="green", width=6, no_wrap=True)
        table.add_column("PDF", style="blue", width=3, justify="center")
        
        for item in items:
            data = item['data']
            key = item['key']
            
            # Ensure key is always shown in full
            key_display = key[:12] if len(key) > 12 else key
            
            # Title - truncate with ellipsis if needed
            title = data.get('title', 'Untitled')
            if len(title) > 60:
                title = title[:57] + "..."
            
            # Get first author
            creators = data.get('creators', [])
            if creators:
                first = creators[0]
                if 'lastName' in first:
                    authors = f"{first['lastName']}"
                    if len(creators) > 1:
                        authors += " et al."
                else:
                    authors = first.get('name', 'Unknown')
            else:
                authors = "Unknown"
            
            # Truncate authors if too long
            if len(authors) > 25:
                authors = authors[:22] + "..."
            
            # Get year
            date = data.get('date', '')
            year = date[:4] if date else 'N/A'
            
            # Check for PDF attachment (cached to avoid multiple API calls)
            try:
                children = zot.children(key)
                has_pdf = any(
                    child['data'].get('contentType') == 'application/pdf' 
                    for child in children
                )
                pdf_indicator = "✓" if has_pdf else "·"
            except:
                pdf_indicator = "?"
            
            table.add_row(key_display, title, authors, year, pdf_indicator)
    
    console.print(table)
    
    # Show usage hints
    if compact:
        console.print("\n[yellow]Compact mode (narrow terminal)[/yellow]")
    
    console.print("\n[bold]Commands:[/bold]")
    console.print("  python chat.py zotero:KEY            # Load paper")
    console.print('  python chat.py "zotero:search:..."   # Search')
    console.print("  python list_zotero.py 20             # List 20 recent")

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    args = sys.argv[1:]
    limit = 20
    compact = None
    
    for arg in args:
        if arg == '--compact':
            compact = True
        elif arg == '--full':
            compact = False
        else:
            try:
                limit = int(arg)
            except ValueError:
                pass
    
    list_recent_items(limit, compact)
