"""
Zotero integration for Paper Companion
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from pyzotero import zotero
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from utils.helpers import format_authors, parse_selection

console = Console()


class ZoteroClient:
    """Handles all Zotero-related operations"""

    def __init__(self):
        """Initialize Zotero connection from config file"""
        self.zot = None
        self.config_path = Path.home() / '.zotero_config.json'
        self._load_config()

    def _load_config(self):
        """Load Zotero configuration from file"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                config = json.load(f)
                self.zot = zotero.Zotero(
                    config['library_id'],
                    config['library_type'],
                    config['api_key']
                )
        else:
            console.print("[yellow]Zotero config not found. Create ~/.zotero_config.json with:")
            console.print(json.dumps({
                "library_id": "your_library_id",
                "library_type": "user",
                "api_key": "your_api_key"
            }, indent=2))

    def is_configured(self) -> bool:
        """Check if Zotero is configured"""
        return self.zot is not None

    def load_from_zotero(self, zotero_input: str) -> tuple[Path, Optional[Dict], List[Path]]:
        """
        Load PDF(s) from Zotero.

        Args:
            zotero_input: Either "zotero:ITEM_KEY" or "zotero:search:QUERY"

        Returns:
            Tuple of (main_pdf_path, zotero_item, supplement_paths)
        """
        if not self.zot:
            console.print("[red]Zotero not configured[/red]")
            return None, None, []

        # Parse input
        if zotero_input.startswith('zotero:search:'):
            query = zotero_input.replace('zotero:search:', '')
            items = self.search_items(query)
        elif zotero_input.startswith('zotero:'):
            item_key = zotero_input.replace('zotero:', '')
            try:
                item = self.zot.item(item_key)
                items = [item] if item else []
            except Exception as e:
                console.print(f"[red]Error fetching item from Zotero: {e}[/red]")
                items = []
        else:
            items = []

        if not items:
            console.print("[red]No items found in Zotero[/red]")
            return None, None, []

        # Choose one item if multiple found
        item = self.choose_item(items) if len(items) > 1 else items[0]

        # Get PDF attachments
        attachments = [a for a in self.zot.children(item['key'])
                      if a['data'].get('contentType') == 'application/pdf']

        if not attachments:
            console.print("[red]No PDF attachments found for this item[/red]")
            return None, item, []

        # Identify main paper
        main_pdf = next((a for a in attachments if a['data'].get('title') == 'Full Text PDF'), None)
        if not main_pdf:
            main_pdf = attachments[0]  # fallback

        # Handle supplement selection
        supplements = [a for a in attachments if a != main_pdf]
        selected_supplements = []

        if supplements:
            console.print(f"\n[yellow]Found {len(supplements)} supplemental PDF(s):[/yellow]")
            for i, s in enumerate(supplements, 1):
                console.print(f"  {i}. {s['data'].get('title', 'Untitled')}")

            console.print("\n[cyan]Select supplements to include:[/cyan]")
            console.print("  • Enter numbers ('1,3' or '1-3'), 'all', 'first 2'")
            console.print("  • Enter 'none' or press Enter for main PDF only")

            selection = Prompt.ask("Selection", default="none").strip().lower()

            if selection == 'all':
                selected_supplements = supplements
            elif selection == 'none' or selection == '':
                selected_supplements = []
            elif selection.startswith('first '):
                try:
                    n = int(selection.split()[1])
                    selected_supplements = supplements[:n]
                    console.print(f"[green]✓ Including first {n} supplements[/green]")
                except (ValueError, IndexError):
                    console.print("[red]Invalid 'first N' format[/red]")
            else:
                # Parse specific selections
                selected_indices = parse_selection(selection, len(supplements))
                selected_supplements = [supplements[i-1] for i in selected_indices if 0 < i <= len(supplements)]

                if selected_supplements:
                    console.print(f"[green]✓ Selected {len(selected_supplements)} supplement(s)[/green]")
                else:
                    console.print("[yellow]No supplements selected[/yellow]")

        # Download PDFs
        temp_dir = Path(tempfile.gettempdir())

        def download_attachment(att, label="PDF"):
            pdf_temp_path = temp_dir / f"{item['key']}_{att['key']}.pdf"
            try:
                self.zot.dump(att['key'], filename=pdf_temp_path.name, path=str(temp_dir))
                console.print(f"[green]✓ Downloaded: {att['data'].get('title', 'Untitled')}[/green]")
                return pdf_temp_path
            except Exception as e:
                console.print(f"[red]Failed to download {att['data'].get('title')}: {e}[/red]")
                return None

        # Download main PDF
        main_path = download_attachment(main_pdf)
        if not main_path:
            return None, item, []

        # Download selected supplements
        supplement_paths = []
        for supp in selected_supplements:
            supp_path = download_attachment(supp)
            if supp_path:
                supplement_paths.append(supp_path)

        # Show summary
        total_docs = 1 + len(supplement_paths)
        if supplement_paths:
            console.print(f"\n[bold green]Loading {total_docs} document(s): main + {len(supplement_paths)} supplement(s)[/bold green]")
        else:
            console.print(f"\n[bold green]Loading main PDF only[/bold green]")

        return main_path, item, supplement_paths

    def search_items(self, query: str) -> List[Dict]:
        """
        Search Zotero library for items.

        Args:
            query: Search query (DOI, title, etc.)

        Returns:
            List of matching Zotero items
        """
        import re

        console.print(f"[cyan]Searching Zotero for: {query}[/cyan]")

        # Try as DOI
        if re.match(r'10\.\d+/.*', query):
            results = self.zot.items(q=query)
        else:
            # Try title search
            results = self.zot.items(q=query, limit=10)

        return results

    def choose_item(self, items: List[Dict]) -> Dict:
        """
        Let user choose from multiple Zotero items.

        Args:
            items: List of Zotero items

        Returns:
            Selected item
        """
        table = Table(title="Select Zotero Item")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Title", style="white", width=50)
        table.add_column("Authors", style="yellow", width=30)
        table.add_column("Year", style="green", width=6)

        for i, item in enumerate(items[:10], 1):
            data = item['data']
            title = data.get('title', 'Untitled')[:50]

            # Get first author
            creators = data.get('creators', [])
            if creators:
                first_author = creators[0]
                if 'lastName' in first_author:
                    authors = f"{first_author['lastName']} et al."
                else:
                    authors = first_author.get('name', 'Unknown')
            else:
                authors = "Unknown"

            year = data.get('date', 'N/A')[:4] if data.get('date') else 'N/A'

            table.add_row(str(i), title, authors, year)

        console.print(table)

        while True:
            choice = Prompt.ask("Select item number", default="1")
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(items):
                    return items[idx]
            except:
                pass
            console.print("[red]Invalid choice[/red]")

    def show_metadata(self, zotero_item: Dict):
        """
        Display Zotero metadata for an item.

        Args:
            zotero_item: Zotero item dict
        """
        data = zotero_item['data']

        panel_content = f"""[bold]Existing Zotero Metadata:[/bold]

📚 [cyan]{data.get('title', 'Untitled')}[/cyan]
👥 {format_authors(data.get('creators', []))}
📅 {data.get('date', 'No date')}
📖 {data.get('publicationTitle', 'No journal')}
🔗 DOI: {data.get('DOI', 'None')}
🏷️ Tags: {', '.join([t['tag'] for t in zotero_item.get('tags', [])][:5])}
        """

        console.print(Panel(panel_content, title="Zotero Item", border_style="green"))

    def find_related_papers(self, zotero_item: Dict) -> List[Dict]:
        """
        Find related papers in Zotero library based on tags.

        Args:
            zotero_item: Current Zotero item

        Returns:
            List of related items
        """
        if not self.zot:
            return []

        tags = [t['tag'] for t in zotero_item.get('tags', [])]

        related = []
        for tag in tags[:3]:  # Search top 3 tags
            items = self.zot.items(tag=tag, limit=5)
            for item in items:
                if item['key'] != zotero_item['key']:
                    related.append(item)

        return related[:5]  # Return top 5 unique

    def get_item(self, item_key: str) -> Optional[Dict]:
        """
        Get a Zotero item by key.

        Args:
            item_key: Zotero item key

        Returns:
            Zotero item or None
        """
        if not self.zot:
            return None

        try:
            return self.zot.item(item_key)
        except Exception as e:
            console.print(f"[yellow]Could not load Zotero item: {e}[/yellow]")
            return None

    def save_note(self, parent_item: Dict, note_html: str, tags: List[str]) -> bool:
        """
        Save a note to Zotero.

        Args:
            parent_item: Parent Zotero item
            note_html: HTML content of note
            tags: List of tags for the note

        Returns:
            True if successful
        """
        if not self.zot:
            console.print("[yellow]Zotero not configured - skipping[/yellow]")
            return False

        try:
            note_template = self.zot.item_template('note')
            note_template['note'] = note_html
            note_template['parentItem'] = parent_item['key']
            note_template['tags'] = [{"tag": tag} for tag in tags]

            self.zot.create_items([note_template])
            console.print("[green]✓ Note saved to Zotero[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Failed to save note: {e}[/red]")
            return False
