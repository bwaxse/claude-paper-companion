#!/usr/bin/env python3
"""
Debug Zotero PDF storage and attachment issues
"""

import json
import sys
from pathlib import Path
from pyzotero import zotero
from rich.console import Console
from rich.tree import Tree
from rich.table import Table
from rich.panel import Panel

console = Console()

def debug_zotero_item(item_key=None):
    """Debug a specific Zotero item or show general info"""
    
    # Load config
    config_path = Path.home() / '.zotero_config.json'
    if not config_path.exists():
        console.print("[red]Zotero config not found at ~/.zotero_config.json[/red]")
        return
    
    with open(config_path) as f:
        config = json.load(f)
    
    console.print(Panel(f"[cyan]Zotero Debug Info[/cyan]\n"
                       f"Library ID: {config['library_id']}\n"
                       f"Library Type: {config['library_type']}", 
                       title="Configuration"))
    
    # Initialize Zotero
    zot = zotero.Zotero(
        config['library_id'],
        config['library_type'],
        config['api_key']
    )
    
    # Check Zotero storage locations
    console.print("\n[bold]Checking Zotero Storage Locations:[/bold]")
    
    possible_locations = [
        Path.home() / 'Zotero' / 'storage',
        Path.home() / 'Documents' / 'Zotero' / 'storage',
        Path('/Users/Shared/Zotero/storage'),
        Path.home() / 'Library' / 'Application Support' / 'Zotero' / 'storage',
    ]
    
    storage_found = None
    for loc in possible_locations:
        if loc.exists():
            console.print(f"✓ Found: {loc}")
            storage_found = loc
            # Count items
            subdirs = list(loc.iterdir()) if loc.is_dir() else []
            console.print(f"  → Contains {len(subdirs)} item folders")
        else:
            console.print(f"✗ Not found: {loc}")
    
    if not storage_found:
        console.print("\n[red]⚠️  No Zotero storage directory found![/red]")
        console.print("Please check Zotero → Preferences → Files & Folders → Data Directory Location")
        return
    
    # If specific item requested
    if item_key:
        console.print(f"\n[bold]Debugging Item: {item_key}[/bold]\n")
        
        try:
            # Get item details
            item = zot.item(item_key)
            data = item['data']
            
            # Display item info
            info_table = Table(title="Item Details", show_header=False)
            info_table.add_column("Field", style="cyan")
            info_table.add_column("Value", style="white")
            
            info_table.add_row("Title", data.get('title', 'N/A'))
            info_table.add_row("Item Type", data.get('itemType', 'N/A'))
            info_table.add_row("Date", data.get('date', 'N/A'))
            info_table.add_row("DOI", data.get('DOI', 'N/A'))
            
            creators = data.get('creators', [])
            if creators:
                author_names = []
                for c in creators[:3]:
                    if 'lastName' in c:
                        author_names.append(f"{c.get('firstName', '')} {c['lastName']}")
                    elif 'name' in c:
                        author_names.append(c['name'])
                info_table.add_row("Authors", ", ".join(author_names))
            
            console.print(info_table)
            
            # Get attachments
            console.print("\n[bold]Checking Attachments:[/bold]")
            children = zot.children(item_key)
            
            if not children:
                console.print("[yellow]No attachments found for this item[/yellow]")
            else:
                # Create attachment tree
                tree = Tree(f"[bold]Attachments for {item_key}[/bold]")
                
                for i, child in enumerate(children, 1):
                    child_data = child['data']
                    child_key = child['key']
                    
                    # Attachment info
                    att_type = child_data.get('itemType', 'unknown')
                    content_type = child_data.get('contentType', 'unknown')
                    title = child_data.get('title', 'Untitled')
                    filename = child_data.get('filename', '')
                    
                    # Create branch for this attachment
                    branch_text = f"{i}. [{att_type}] {title}"
                    if content_type == 'application/pdf':
                        branch_text = f"[green]{branch_text}[/green]"
                    
                    branch = tree.add(branch_text)
                    branch.add(f"Key: {child_key}")
                    branch.add(f"Content Type: {content_type}")
                    
                    if filename:
                        branch.add(f"Filename: {filename}")
                    
                    # Check if linkMode indicates linked file vs stored
                    link_mode = child_data.get('linkMode', '')
                    if link_mode:
                        branch.add(f"Link Mode: {link_mode}")
                    
                    # Check storage location
                    if storage_found:
                        attachment_dir = storage_found / child_key
                        if attachment_dir.exists():
                            branch.add(f"[green]✓ Storage folder exists: {attachment_dir}[/green]")
                            
                            # List files in attachment directory
                            files = list(attachment_dir.iterdir())
                            if files:
                                files_branch = branch.add("Files:")
                                for file in files:
                                    size = file.stat().st_size / 1024 / 1024  # MB
                                    files_branch.add(f"{file.name} ({size:.1f} MB)")
                                    
                                    # Full path for debugging
                                    if file.suffix.lower() == '.pdf':
                                        console.print(f"\n[green]✓ PDF FOUND:[/green] {file}")
                            else:
                                branch.add("[red]✗ Storage folder is empty[/red]")
                        else:
                            branch.add(f"[red]✗ Storage folder not found: {attachment_dir}[/red]")
                    
                    # URL if linked
                    url = child_data.get('url', '')
                    if url:
                        branch.add(f"URL: {url[:50]}...")
                
                console.print(tree)
            
            # Check for specific PDF attachment
            pdf_attachments = [
                c for c in children 
                if c['data'].get('contentType') == 'application/pdf'
            ]
            
            if pdf_attachments:
                console.print(f"\n[green]Found {len(pdf_attachments)} PDF attachment(s)[/green]")
                
                for pdf in pdf_attachments:
                    pdf_key = pdf['key']
                    pdf_path = storage_found / pdf_key
                    
                    if pdf_path.exists():
                        pdfs = list(pdf_path.glob('*.pdf'))
                        if pdfs:
                            console.print(f"PDF location: {pdfs[0]}")
                            
                            # Try to identify why it might not be loading
                            console.print("\n[bold]Diagnostic Info:[/bold]")
                            console.print(f"1. PDF exists: [green]Yes[/green]")
                            console.print(f"2. Path accessible: [green]{pdfs[0].exists()}[/green]")
                            console.print(f"3. File size: {pdfs[0].stat().st_size / 1024:.1f} KB")
                            console.print(f"4. File permissions: {oct(pdfs[0].stat().st_mode)[-3:]}")
                        else:
                            console.print(f"[red]Directory exists but no PDF found in: {pdf_path}[/red]")
                            # List what IS in the directory
                            files = list(pdf_path.iterdir())
                            if files:
                                console.print("Files in directory:")
                                for f in files:
                                    console.print(f"  - {f.name}")
            else:
                console.print("\n[yellow]No PDF attachments found[/yellow]")
                console.print("This might be because:")
                console.print("  1. PDF is linked (not stored) in Zotero")
                console.print("  2. Item has no PDF attached")
                console.print("  3. PDF attachment has different content type")
                
        except Exception as e:
            console.print(f"[red]Error accessing item {item_key}: {e}[/red]")
            import traceback
            traceback.print_exc()
    
    else:
        # General debug info
        console.print("\n[bold]Recent Items with Attachments:[/bold]")
        
        items = zot.items(limit=5, sort='dateModified', direction='desc')
        
        for item in items:
            key = item['key']
            title = item['data'].get('title', 'Untitled')[:50]
            
            console.print(f"\n{key}: {title}")
            
            children = zot.children(key)
            pdf_count = sum(1 for c in children if c['data'].get('contentType') == 'application/pdf')
            
            if pdf_count:
                console.print(f"  → Has {pdf_count} PDF(s)")
                
                # Check storage
                for child in children:
                    if child['data'].get('contentType') == 'application/pdf':
                        child_key = child['key']
                        pdf_dir = storage_found / child_key if storage_found else None
                        
                        if pdf_dir and pdf_dir.exists():
                            pdfs = list(pdf_dir.glob('*.pdf'))
                            if pdfs:
                                console.print(f"  ✓ PDF stored at: {pdfs[0].name}")
                            else:
                                console.print(f"  ✗ Directory exists but no PDF")
                        else:
                            console.print(f"  ✗ Storage directory not found")
            else:
                console.print("  → No PDFs")

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        item_key = sys.argv[1]
        console.print(f"[cyan]Debugging Zotero item: {item_key}[/cyan]\n")
        debug_zotero_item(item_key)
    else:
        console.print("[cyan]General Zotero Debug Info[/cyan]\n")
        debug_zotero_item()
        console.print("\n[dim]Tip: Run with an item key to debug specific item:[/dim]")
        console.print("[dim]python debug_zotero.py 9Z3ZYK65[/dim]")

if __name__ == "__main__":
    main()
