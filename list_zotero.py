#!/usr/bin/env python3
"""
List recent items from Zotero library
"""

import json
from pathlib import Path
from pyzotero import zotero
from rich.console import Console
from rich.table import Table

console = Console()

def list_recent_items(limit=20):
    """List recent items from Zotero with their keys"""
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
    
    # Create table
    table = Table(title=f"Recent Zotero Items (Last {limit})")
    table.add_column("Key", style="cyan", width=12)
    table.add_column("Title", style="white", width=50)
    table.add_column("Authors", style="yellow", width=25)
    table.add_column("Year", style="green", width=6)
    table.add_column("PDF", style="blue", width=4)
    
    for item in items:
        data = item['data']
        key = item['key']
        title = data.get('title', 'Untitled')[:50]
        
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
        
        # Get year
        date = data.get('date', '')
        year = date[:4] if date else 'N/A'
        
        # Check for PDF attachment
        children = zot.children(key)
        has_pdf = any(
            child['data'].get('contentType') == 'application/pdf' 
            for child in children
        )
        pdf_indicator = "✓" if has_pdf else ""
        
        table.add_row(key, title, authors, year, pdf_indicator)
    
    console.print(table)
    console.print("\n[bold]To load a paper:[/bold]")
    console.print("  python chat.py zotero:KEY")
    console.print("\n[bold]To search:[/bold]")
    console.print('  python chat.py "zotero:search:your keywords"')

if __name__ == "__main__":
    list_recent_items()
