#!/usr/bin/env python3
"""
Paper Companion: Interactive PDF research assistant with Zotero integration
Enhanced to work directly with Zotero's PDF storage
"""

import sys
import os
import json
import tempfile
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import hashlib
import re

from anthropic import Anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt

# Database imports
from db import get_db
from db.schema import initialize_database
from storage.paper_repository import SQLitePaperRepository
from storage.session_repository import SQLiteSessionRepository
from storage.cache_repository import SQLiteCacheRepository

# Extracted modules
from core.pdf_processor import PDFProcessor
from core.insights_extractor import InsightsExtractor
from integrations.zotero_client import ZoteroClient
from integrations.claude_client import ClaudeClient
from utils.helpers import format_authors

console = Console()

class PaperCompanion:
    def __init__(self, pdf_input: Optional[str] = None, resume_session: Optional[str] = None):
        """
        Initialize with either:
        - Direct PDF path: /path/to/paper.pdf
        - Zotero item key: zotero:ABCD1234
        - Zotero search: zotero:search:transformer attention
        - Resume existing session: resume_session=SESSION_ID
        """
        # Initialize database
        self.db = get_db()
        initialize_database(self.db)

        # Initialize repositories
        self.paper_repo = SQLitePaperRepository(self.db)
        self.session_repo = SQLiteSessionRepository(self.db)
        self.cache_repo = SQLiteCacheRepository(self.db)

        # Initialize clients
        self.zotero_client = ZoteroClient()
        self.claude_client = ClaudeClient()
        self.insights_extractor = InsightsExtractor()

        # Session state
        self.zotero_item = None
        self.pdf_path = None
        self.pdf_hash = None
        self.session_id = None
        self.paper_id = None
        self.messages = []
        self.flagged_exchanges = []
        self.pdf_content = None
        self.pdf_images = []
        self.supplement_paths = []

        # Handle resume vs new session
        if resume_session:
            self._resume_session(resume_session)
        elif pdf_input:
            self._start_new_session(pdf_input)
        else:
            raise ValueError("Must provide either pdf_input or resume_session")

    def _start_new_session(self, pdf_input: str):
        """Start a new session with a PDF"""
        console.print("[cyan]Starting new session...[/cyan]")

        # Handle different input types
        if pdf_input.startswith('zotero:'):
            self.pdf_path, self.zotero_item, self.supplement_paths = self.zotero_client.load_from_zotero(pdf_input)
        else:
            self.pdf_path = Path(pdf_input)
            self.supplement_paths = []

        if not self.pdf_path or not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_input}")

        self.pdf_hash = PDFProcessor.compute_pdf_hash(self.pdf_path)

        # Find or create paper record
        paper = self.paper_repo.find_by_hash(self.pdf_hash)
        if paper:
            console.print(f"[green]Found existing paper in database: {paper.get('title', 'Untitled')}[/green]")
            self.paper_id = paper['id']
        else:
            # Create new paper record
            metadata = {}
            if self.zotero_item:
                data = self.zotero_item['data']
                metadata = {
                    'title': data.get('title'),
                    'authors': format_authors(data.get('creators', [])),
                    'doi': data.get('DOI'),
                    'zotero_key': self.zotero_item['key'],
                    'pdf_path': str(self.pdf_path)
                }
            else:
                metadata = {
                    'pdf_path': str(self.pdf_path)
                }

            self.paper_id = self.paper_repo.create(
                pdf_hash=self.pdf_hash,
                **metadata
            )
            console.print(f"[green]Created new paper record (ID: {self.paper_id})[/green]")

        # Create session record
        self.session_id = self.session_repo.create(
            paper_id=self.paper_id,
            model_used="claude-haiku-4-5-20251001"
        )
        console.print(f"[green]Created session: {self.session_id[:16]}...[/green]")

        # Load PDF content
        self.pdf_content, self.pdf_images = PDFProcessor.load_pdf_with_supplements(
            self.pdf_path,
            self.supplement_paths
        )

        # Show Zotero metadata if available
        if self.zotero_item:
            self.zotero_client.show_metadata(self.zotero_item)

    def _resume_session(self, session_id: str):
        """Resume an existing session from the database"""
        console.print(f"[cyan]Resuming session {session_id[:16]}...[/cyan]")

        # Load session from database
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        self.session_id = session_id
        self.paper_id = session['paper_id']

        # Load paper info
        paper = self.paper_repo.find_by_id(self.paper_id)
        if not paper:
            raise ValueError(f"Paper not found for session: {session_id}")

        self.pdf_hash = paper['pdf_hash']
        self.pdf_path = Path(paper['pdf_path']) if paper['pdf_path'] else None

        console.print(f"[green]Loaded paper: {paper.get('title', 'Untitled')}[/green]")

        # Load PDF if path is available
        if self.pdf_path and self.pdf_path.exists():
            self.pdf_content, self.pdf_images = PDFProcessor.load_pdf_with_supplements(
                self.pdf_path,
                self.supplement_paths
            )
        else:
            console.print("[yellow]PDF file not found - loading from database cache[/yellow]")
            # TODO: Could load cached PDF chunks from database here

        # Load Zotero item if available
        if paper.get('zotero_key'):
            self.zotero_item = self.zotero_client.get_item(paper['zotero_key'])

        # Load message history
        messages = self.session_repo.get_messages(session_id, include_summaries=False)
        self.messages = [
            {"role": msg['role'], "content": msg['content']}
            for msg in messages
        ]
        console.print(f"[green]Loaded {len(self.messages)} messages[/green]")

        # Load flagged exchanges
        flags = self.session_repo.get_flags(session_id)
        self.flagged_exchanges = [
            {
                "user": flag['user_content'],
                "assistant": flag['assistant_content'],
                "timestamp": flag['created_at'],
                "note": flag.get('note')
            }
            for flag in flags
        ]
        console.print(f"[green]Loaded {len(self.flagged_exchanges)} flagged exchanges[/green]")

        # Display session stats
        stats = self.session_repo.get_session_stats(session_id)
        console.print(f"\n[bold cyan]Session Stats:[/bold cyan]")
        console.print(f"  Exchanges: {stats.get('exchanges', 0)}")
        console.print(f"  Flagged: {stats.get('flags', 0)}")
        console.print(f"  Status: {stats.get('status', 'unknown')}")
        console.print()

    def _load_from_zotero(self, zotero_input: str) -> Path:
        """Load the main PDF (Full Text PDF) from Zotero, and optionally supplements."""
        if not self.zot:
            console.print("[red]Zotero not configured[/red]")
            return None

        # Parse input
        if zotero_input.startswith('zotero:search:'):
            query = zotero_input.replace('zotero:search:', '')
            items = self._search_zotero_items(query)
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
            return None
    
        # Choose one item if multiple found
        item = self._choose_zotero_item(items) if len(items) > 1 else items[0]
        self.zotero_item = item
    
        # List attachments
        attachments = [a for a in self.zot.children(item['key']) 
                       if a['data'].get('contentType') == 'application/pdf']
        
        if not attachments:
            console.print("[red]No PDF attachments found for this item[/red]")
            return None
        
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
                selected_indices = self._parse_selection(selection, len(supplements))
                selected_supplements = [supplements[i-1] for i in selected_indices if 0 < i <= len(supplements)]
                
                if selected_supplements:
                    console.print(f"[green]✓ Selected {len(selected_supplements)} supplement(s)[/green]")
                else:
                    console.print("[yellow]No supplements selected[/yellow]")
        
        # Download PDFs
        temp_dir = Path(tempfile.gettempdir())
        pdf_paths = []
        
        def _download_attachment(att, label="PDF"):
            pdf_temp_path = temp_dir / f"{item['key']}_{att['key']}.pdf"
            try:
                self.zot.dump(att['key'], filename=pdf_temp_path.name, path=str(temp_dir))
                console.print(f"[green]✓ Downloaded: {att['data'].get('title', 'Untitled')}[/green]")
                return pdf_temp_path
            except Exception as e:
                console.print(f"[red]Failed to download {att['data'].get('title')}: {e}[/red]")
                return None
        
        # Download main PDF (always)
        main_path = _download_attachment(main_pdf)
        if not main_path:
            return None
        
        # Download selected supplements
        for supp in selected_supplements:
            supp_path = _download_attachment(supp)
            if supp_path:
                pdf_paths.append(supp_path)
        
        # Store for later loading
        self.supplement_paths = pdf_paths
        
        # Show summary
        total_docs = 1 + len(pdf_paths)
        if pdf_paths:
            console.print(f"\n[bold green]Loading {total_docs} document(s): main + {len(pdf_paths)} supplement(s)[/bold green]")
        else:
            console.print(f"\n[bold green]Loading main PDF only[/bold green]")
        
        return main_path

    def _parse_selection(self, selection: str, max_val: int) -> List[int]:
        """Parse selection string like '1,3,5-7' into list of indices."""
        indices = set()
        
        # Split by comma
        parts = selection.replace(' ', '').split(',')
        
        for part in parts:
            if '-' in part:
                # Range selection (e.g., "2-5")
                try:
                    start, end = part.split('-')
                    start, end = int(start), int(end)
                    if start <= end:
                        indices.update(range(start, min(end + 1, max_val + 1)))
                except ValueError:
                    console.print(f"[yellow]Invalid range: {part}[/yellow]")
            else:
                # Single number
                try:
                    num = int(part)
                    if 1 <= num <= max_val:
                        indices.add(num)
                except ValueError:
                    console.print(f"[yellow]Invalid number: {part}[/yellow]")
        
        return sorted(list(indices))

    def _search_zotero_items(self, query: str) -> List:
        """Search Zotero library for items"""
        console.print(f"[cyan]Searching Zotero for: {query}[/cyan]")
        
        # Search by multiple strategies
        results = []
        
        # Try as DOI
        if re.match(r'10\.\d+/.*', query):
            results = self.zot.items(q=query)
        
        # Try title search
        if not results:
            results = self.zot.items(q=query, limit=10)
        
        return results
    
    def _choose_zotero_item(self, items: List) -> Dict:
        """Let user choose from multiple Zotero items"""
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
    
    def _compute_pdf_hash(self) -> str:
        """Compute SHA256 hash of PDF for unique identification"""
        with open(self.pdf_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    
    def setup_zotero(self):
        """Initialize Zotero connection"""
        config_path = Path.home() / '.zotero_config.json'
        
        if config_path.exists():
            with open(config_path) as f:
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
            self.zot = None
    
    def _load_pdf(self):
        """Extract text and images from main and supplemental PDFs"""
        def extract_from_pdf(pdf_path: Path, label: str) -> Tuple[str, List[Dict]]:
            """Helper: extract text and images from a single PDF"""
            console.print(f"[cyan]Loading {label}: {pdf_path.name}[/cyan]")
            doc = fitz.open(pdf_path)
            
            text_content = []
            images = []
            
            for page_num, page in enumerate(doc, 1):
                # Text extraction
                text = page.get_text()
                if text.strip():
                    text_content.append(f"[Page {page_num}]\n{text}")
                
                # Image extraction
                for img_index, img in enumerate(page.get_images(full=True)):
                    try:
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        
                        # Only include substantial images (likely figures)
                        if pix.width > 200 and pix.height > 200:
                            if pix.n - pix.alpha < 4:  # RGB or grayscale
                                img_data = pix.tobytes("png")
                                img_base64 = base64.b64encode(img_data).decode()
                                images.append({
                                    "source": pdf_path.name,
                                    "page": page_num,
                                    "index": img_index,
                                    "data": img_base64,
                                    "type": "image/png"
                                })
                        pix = None
                    except Exception:
                        continue
            
            doc.close()
            console.print(f"[green]✓ Loaded {len(text_content)} pages, {len(images)} figures from {label}[/green]")
            return "\n\n".join(text_content), images
    
        # === MAIN PDF ===
        main_text, main_images = extract_from_pdf(self.pdf_path, "main PDF")
    
        # === SUPPLEMENTAL PDFs (if any) ===
        combined_text = main_text
        combined_images = main_images
    
        if hasattr(self, "supplement_paths") and self.supplement_paths:
            for supp_path in self.supplement_paths:
                supp_text, supp_images = extract_from_pdf(supp_path, "supplemental PDF")
                combined_text += f"\n\n=== SUPPLEMENTAL MATERIAL: {supp_path.name} ===\n\n" + supp_text
                combined_images.extend(supp_images)
    
        self.pdf_content = combined_text
        self.pdf_images = combined_images
    
        # Show summary
        console.print(f"[bold green]✓ Total: {len(self.pdf_images)} figures across all PDFs[/bold green]")
    
        # Show existing Zotero metadata (if available)
        if self.zotero_item:
            self._show_zotero_metadata()
    
    def _show_zotero_metadata(self):
        """Display existing Zotero metadata"""
        data = self.zotero_item['data']
        
        panel_content = f"""[bold]Existing Zotero Metadata:[/bold]
        
📚 [cyan]{data.get('title', 'Untitled')}[/cyan]
👥 {self._format_authors(data.get('creators', []))}
📅 {data.get('date', 'No date')}
📖 {data.get('publicationTitle', 'No journal')}
🔗 DOI: {data.get('DOI', 'None')}
🏷️ Tags: {', '.join([t['tag'] for t in self.zotero_item.get('tags', [])][:5])}
        """
        
        console.print(Panel(panel_content, title="Zotero Item", border_style="green"))
    
    def _format_authors(self, creators: List) -> str:
        """Format author list for display"""
        if not creators:
            return "No authors"
        
        authors = []
        for c in creators[:3]:  # First 3 authors
            if 'lastName' in c:
                authors.append(f"{c.get('firstName', '')} {c['lastName']}".strip())
            elif 'name' in c:
                authors.append(c['name'])
        
        if len(creators) > 3:
            authors.append("et al.")
        
        return ", ".join(authors)
    
    def get_initial_summary(self) -> str:
        """Get Claude's concise, actionable summary of the paper"""
        summary = self.claude_client.get_initial_summary(
            self.pdf_content,
            self.pdf_images,
            self.zotero_item
        )

        # Store in conversation history
        self.messages.append({"role": "assistant", "content": summary})

        return summary

    def get_full_critical_review(self) -> str:
        """Get Claude's critical analysis of the paper"""
        summary = self.claude_client.get_full_critical_review(
            self.pdf_content,
            self.pdf_images,
            self.zotero_item
        )

        # Store in conversation history
        self.messages.append({"role": "assistant", "content": summary})

        return summary
    
    def chat_loop(self):
        """Main interactive chat loop - enhanced with new commands"""
        console.print("\n[bold cyan]Let's explore this paper together. Commands:[/bold cyan]")
        console.print("  [yellow]/flag [note][/yellow] - Mark this exchange as important (with optional note)")
        console.print("  [yellow]/fullreview[/yellow] - Get comprehensive critical analysis")
        console.print("  [yellow]/methods[/yellow] - Deep dive into methodology")
        console.print("  [yellow]/stats[/yellow] - Statistical analysis check")
        console.print("  [yellow]/compare[/yellow] - Compare to related work")
        console.print("  [yellow]/figures[/yellow] - List all figures")
        console.print("  [yellow]/fig N[/yellow] - Analyze figure N")
        console.print("  [yellow]/related[/yellow] - Find related papers in Zotero")
        console.print("  [yellow]/exit[/yellow] - End session and save insights")
        console.print()
        
        while True:
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            # Handle commands
            if user_input.lower() == '/exit':
                break
            elif user_input.lower().startswith('/flag'):
                # Extract optional note after /flag
                note = user_input[5:].strip()  # Everything after '/flag'
                self._flag_last_exchange(note if note else None)
                continue
            elif user_input.lower() == '/fullreview':
                response = self.get_full_critical_review()
                console.print("\n[bold blue]Full Critical Review:[/bold blue]")
                console.print(Markdown(response))
                self.messages.append({"role": "assistant", "content": response})
                continue
            elif user_input.lower() == '/methods':
                response = self._analyze_methods()
                console.print("\n[bold blue]Methods Analysis:[/bold blue]")
                console.print(Markdown(response))
                continue
            elif user_input.lower() == '/stats':
                response = self._check_statistics()
                console.print("\n[bold blue]Statistical Check:[/bold blue]")
                console.print(Markdown(response))
                continue
            elif user_input.lower().startswith('/fig'):
                self._analyze_figure(user_input)
                continue
            elif user_input.lower() == '/related':
                self._find_related_papers()
                continue
            
            # Regular conversation
            response = self._get_claude_response(user_input)

            # Display response
            console.print("\n[bold blue]Claude:[/bold blue]")
            console.print(Markdown(response))

            # Store exchange in memory
            self.messages.append({"role": "user", "content": user_input})
            self.messages.append({"role": "assistant", "content": response})

            # Save to database
            self.session_repo.add_message(self.session_id, "user", user_input)
            self.session_repo.add_message(self.session_id, "assistant", response)

    def _find_related_papers(self):
        """Find related papers in Zotero library"""
        if not self.zotero_client.is_configured():
            console.print("[yellow]Zotero not configured[/yellow]")
            return

        if self.zotero_item:
            tags = [t['tag'] for t in self.zotero_item.get('tags', [])]
            console.print(f"[cyan]Searching for papers with similar tags: {', '.join(tags[:5])}[/cyan]")

            related = self.zotero_client.find_related_papers(self.zotero_item)

            if related:
                console.print("\n[bold]Related papers in your library:[/bold]")
                for item in related[:5]:
                    data = item['data']
                    console.print(f"• {data.get('title', 'Untitled')} ({data.get('date', 'N/A')[:4]})")
            else:
                console.print("[yellow]No related papers found[/yellow]")
        else:
            console.print("[yellow]Load paper from Zotero to find related items[/yellow]")
    
    def _get_claude_response(self, user_input: str) -> str:
        """Get response from Claude with full context"""
        return self.claude_client.get_response(
            user_input,
            self.pdf_content,
            self.messages
        )
    
    def _flag_last_exchange(self, note: Optional[str] = None):
        """Flag the last exchange as important with an optional note"""
        if len(self.messages) >= 2:
            # Add to in-memory list
            last_exchange = {
                "user": self.messages[-2]["content"],
                "assistant": self.messages[-1]["content"],
                "timestamp": datetime.now().isoformat()
            }
            if note:
                last_exchange["note"] = note
                console.print(f"[yellow]✓ Exchange flagged: {note}[/yellow]")
            else:
                console.print("[yellow]✓ Exchange flagged[/yellow]")
            self.flagged_exchanges.append(last_exchange)

            # Save to database
            # Get the last two message IDs from the database
            messages = self.session_repo.get_recent_messages(self.session_id, count=2)
            if len(messages) >= 2:
                user_msg_id = messages[-2]['id']
                assistant_msg_id = messages[-1]['id']
                self.session_repo.add_flag(
                    self.session_id,
                    user_msg_id,
                    assistant_msg_id,
                    note
                )
        else:
            console.print("[red]No exchange to flag[/red]")
    
    def _show_image(self, command: str):
        """Display image info from paper"""
        try:
            img_num = int(command.split()[1]) - 1
            if 0 <= img_num < len(self.pdf_images):
                img = self.pdf_images[img_num]
                console.print(f"[cyan]Figure {img_num + 1} from page {img['page']}[/cyan]")
                console.print("[dim]To view: Check the PDF in Zotero[/dim]")
            else:
                console.print(f"[red]Figure {img_num + 1} not found[/red]")
        except:
            console.print("[red]Usage: /img N (where N is figure number)[/red]")
    
    def extract_insights(self) -> Dict:
        """Extract and thematically organize insights from conversation"""
        return self.insights_extractor.extract_insights(
            self.messages,
            self.flagged_exchanges,
            self.pdf_path,
            self.pdf_hash,
            self.session_id,
            self.zotero_item
        )
    
    def save_to_zotero(self, insights: Dict):
        """Save insights as Zotero note"""
        if not self.zotero_client.is_configured():
            console.print("[yellow]Zotero not configured - skipping[/yellow]")
            return

        console.print("[cyan]Saving to Zotero...[/cyan]")

        # Use existing Zotero item if loaded from there
        if self.zotero_item:
            console.print(f"[green]Using existing item: {self.zotero_item['data'].get('title', 'Untitled')}[/green]")

            # Create note with insights
            note_html = InsightsExtractor.format_insights_html(
                insights,
                self.session_id,
                self.messages,
                self.flagged_exchanges
            )

            # Build tags
            tags = [
                "claude-insights",
                f"session-{self.session_id[:10]}"
            ]

            # Add focus area tags
            if insights.get('focus_areas'):
                for area in insights['focus_areas'][:2]:
                    if isinstance(area, str):
                        tags.append(f"focus:{area[:30]}")

            # Save note using ZoteroClient
            self.zotero_client.save_note(self.zotero_item, note_html, tags)
        else:
            console.print("[yellow]No Zotero item - skipping note save[/yellow]")
    
    def _find_or_create_item(self, insights: Dict):
        """Find existing or create new Zotero item"""
        # Implementation continues from the main file...
        # [Rest of the Zotero methods from the original implementation]
        pass
    
    def _update_item_metadata(self, item, insights: Dict):
        """Update existing item with better metadata"""
        # Implementation from the main file...
        pass
    
    def _format_insights_html(self, insights: Dict) -> str:
        """Format thematically organized insights as HTML for Zotero"""
        
        # Build a dynamic HTML based on which themes have content
        html = f"""<h2>📚 Paper Insights - {datetime.now().strftime('%Y-%m-%d %H:%M')}</h2>"""
        
        # Define theme display order and icons
        theme_config = {
            'strengths': ('💪', 'Strengths'),
            'weaknesses': ('⚠️', 'Weaknesses & Limitations'),
            'methodological_notes': ('🔬', 'Methodological Insights'),
            'statistical_concerns': ('📊', 'Statistical Issues'),
            'theoretical_contributions': ('💡', 'Theoretical Contributions'),
            'empirical_findings': ('📈', 'Key Empirical Findings'),
            'questions_raised': ('❓', 'Open Questions'),
            'applications': ('🚀', 'Applications & Implications'),
            'connections': ('🔗', 'Connections to Other Work'),
            'critiques': ('🎯', 'Specific Critiques'),
            'surprising_elements': ('😲', 'Surprising Elements'),
        }
        
        # Add themed sections (only if they have content)
        for theme_key, (icon, title) in theme_config.items():
            if theme_key in insights and insights[theme_key]:
                items = insights[theme_key]
                if items:
                    html += f"\n<h3>{icon} {title}</h3>\n<ul>\n"
                    for item in items:
                        # If this item came from a flagged exchange, mark it
                        if isinstance(item, dict) and item.get('flagged'):
                            html += f'<li><strong>⭐ {item["content"]}</strong></li>\n'
                        else:
                            html += f'<li>{item}</li>\n'
                    html += "</ul>\n"
        
        # Add custom themes if any emerged
        if 'custom_themes' in insights:
            html += "\n<h3>🎨 Session-Specific Themes</h3>\n"
            for theme, items in insights['custom_themes'].items():
                html += f"<h4>{theme.replace('_', ' ').title()}</h4>\n<ul>\n"
                for item in items:
                    html += f'<li>{item}</li>\n'
                html += "</ul>\n"
        
        # Add key quotes (if any)
        if insights.get('key_quotes'):
            html += "\n<h3>💬 Key Exchanges</h3>\n"
            for quote in insights['key_quotes'][:5]:
                note_html = f"<br><strong>⭐ Note:</strong> <em>{quote.get('note')}</em>" if quote.get('note') else ""
                html += f"""<blockquote style="border-left: 3px solid #ccc; padding-left: 10px; margin: 10px 0;">
                <strong>Q:</strong> {quote.get('user', '')}
                <br><strong>A:</strong> {quote.get('assistant', '')}{note_html}
                <br><small><em>{quote.get('theme', 'general')}</em></small>
                </blockquote>\n"""
        
        # Add highlight suggestions
        if insights.get('highlight_suggestions'):
            html += "\n<h3>📝 Suggested Highlights</h3>\n"
            for category, suggestions in insights['highlight_suggestions'].items():
                if suggestions:
                    html += f"<h4>{category.replace('_', ' ').title()}</h4>\n<ul>\n"
                    for s in suggestions[:3]:  # Limit to top 3 per category
                        html += f'<li>{s}</li>\n'
                    html += "</ul>\n"
        
        # Add metadata footer
        html += f"""
    <hr>
    <p><small>
    <em>Session ID: {self.session_id[:16]}</em><br>
    <em>Total exchanges: {len(self.messages) // 2}</em><br>
    <em>Flagged insights: {len(self.flagged_exchanges)}</em><br>
    <em>Themes identified: {len([k for k in theme_config.keys() if k in insights and insights[k]])}</em>
    </small></p>
    """
        
        return html
    
    def save_local_backup(self, insights: Dict):
        """Save JSON backup locally"""
        InsightsExtractor.save_local_backup(
            insights,
            self.messages,
            self.flagged_exchanges,
            self.pdf_path,
            len(self.pdf_images),
            self.zotero_item
        )

    def _save_insights_to_db(self, insights: Dict):
        """Save insights to database"""
        # Define insight categories
        categories = [
            'strengths', 'weaknesses', 'methodological_notes', 'statistical_concerns',
            'theoretical_contributions', 'empirical_findings', 'questions_raised',
            'applications', 'connections', 'critiques', 'surprising_elements'
        ]

        # Save insights by category
        for category in categories:
            if category in insights and insights[category]:
                items = insights[category]
                if isinstance(items, list):
                    for item in items:
                        content = item if isinstance(item, str) else str(item)
                        self.session_repo.add_insight(
                            self.session_id,
                            category,
                            content,
                            from_flag=False
                        )

        # Save custom themes if present
        if 'custom_themes' in insights:
            for theme, items in insights['custom_themes'].items():
                if isinstance(items, list):
                    for item in items:
                        self.session_repo.add_insight(
                            self.session_id,
                            f"custom_{theme}",
                            str(item),
                            from_flag=False
                        )

        console.print("[green]✓ Insights saved to database[/green]")

    def run(self):
        """Main execution flow - now conversational"""
        try:
            # Initial concise summary (only for new sessions)
            if not self.messages:
                summary = self.get_initial_summary()
                console.print("\n[bold]Key Points:[/bold]")
                console.print(Markdown(summary))

                # Save initial summary to database
                self.session_repo.add_message(self.session_id, "assistant", summary)
            else:
                # Resuming session - show last few exchanges
                console.print("\n[bold cyan]Recent conversation:[/bold cyan]")
                for msg in self.messages[-4:]:
                    role_label = "[bold green]You[/bold green]" if msg['role'] == 'user' else "[bold blue]Claude[/bold blue]"
                    console.print(f"\n{role_label}")
                    console.print(msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content'])

            # Prompt for focus
            console.print("\n[cyan]What would you like to explore?[/cyan]")
            console.print("[dim]You can ask about specific sections, methods, results, or use commands above[/dim]")

            # Interactive chat
            self.chat_loop()

            # Extract and save insights
            insights = self.extract_insights()

            # Save insights to database
            self._save_insights_to_db(insights)

            # Save to Zotero
            self.save_to_zotero(insights)

            # Local backup
            self.save_local_backup(insights)

            # Mark session as completed
            self.session_repo.complete_session(self.session_id)

            console.print("\n[bold green]Session complete! Insights saved.[/bold green]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Session interrupted - saving backup...[/yellow]")
            # Mark session as interrupted
            self.session_repo.update_status(self.session_id, 'interrupted')
            self.save_local_backup({"interrupted": True, "messages": self.messages})

def list_sessions_for_paper(pdf_input: str):
    """List all sessions for a given paper"""
    # Initialize database
    db = get_db()
    initialize_database(db)
    paper_repo = SQLitePaperRepository(db)
    session_repo = SQLiteSessionRepository(db)

    # Try to find paper
    if pdf_input.startswith('zotero:'):
        # Extract zotero key
        zotero_key = pdf_input.replace('zotero:', '').replace('search:', '')
        paper = paper_repo.find_by_zotero_key(zotero_key)
    else:
        # Compute hash from PDF
        pdf_path = Path(pdf_input)
        if pdf_path.exists():
            with open(pdf_path, 'rb') as f:
                pdf_hash = hashlib.sha256(f.read()).hexdigest()[:16]
            paper = paper_repo.find_by_hash(pdf_hash)
        else:
            console.print(f"[red]PDF not found: {pdf_input}[/red]")
            return

    if not paper:
        console.print("[yellow]No sessions found for this paper[/yellow]")
        return

    # List sessions
    sessions = session_repo.list_for_paper(paper['id'])

    if not sessions:
        console.print("[yellow]No sessions found for this paper[/yellow]")
        return

    # Display sessions in a table
    table = Table(title=f"Sessions for: {paper.get('title', 'Untitled')[:60]}")
    table.add_column("#", style="cyan", width=3)
    table.add_column("Session ID", style="white", width=20)
    table.add_column("Started", style="yellow", width=20)
    table.add_column("Status", style="green", width=12)
    table.add_column("Exchanges", style="blue", width=10)

    for i, session in enumerate(sessions, 1):
        session_id = session['id'][:16] + "..."
        started = session['started_at'][:16] if session['started_at'] else 'N/A'
        status = session['status']
        exchanges = str(session.get('total_exchanges', 0))

        table.add_row(str(i), session_id, started, status, exchanges)

    console.print(table)
    console.print(f"\nTo resume a session: python chat.py --resume SESSION_ID")
    console.print(f"To resume the most recent: python chat.py --resume-last {pdf_input}")

def main():
    """Enhanced main with Zotero integration and session management"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Paper Companion - Interactive PDF research assistant',
        epilog="""
Examples:
  # New session
  python chat.py paper.pdf                           # Load local PDF
  python chat.py zotero:ABC123XY                     # Load by Zotero item key
  python chat.py "zotero:search:transformer"         # Search and load from Zotero

  # Resume session
  python chat.py --resume SESSION_ID                 # Resume specific session
  python chat.py --resume-last paper.pdf             # Resume most recent session for PDF
  python chat.py --list-sessions paper.pdf           # List all sessions for PDF

  # Other
  python chat.py --list-recent                       # List recent Zotero items
        """
    )

    parser.add_argument('pdf', nargs='?', help='PDF path or Zotero reference')
    parser.add_argument('--resume', type=str, metavar='SESSION_ID',
                       help='Resume specific session by ID')
    parser.add_argument('--resume-last', type=str, metavar='PDF',
                       help='Resume most recent session for specified PDF')
    parser.add_argument('--list-sessions', type=str, metavar='PDF',
                       help='List all sessions for specified PDF')
    parser.add_argument('--list-recent', action='store_true',
                       help='List recent items from Zotero')
    parser.add_argument('--setup', action='store_true',
                       help='Run setup wizard')

    args = parser.parse_args()

    if args.setup:
        from setup import main as setup_main
        setup_main()
        return

    if args.list_recent:
        # List recent Zotero items
        try:
            from list_zotero import list_recent_items
            list_recent_items()
        except:
            console.print("[yellow]Run with --setup first to configure Zotero[/yellow]")
        return

    if args.list_sessions:
        list_sessions_for_paper(args.list_sessions)
        return

    if args.resume_last:
        # Resume most recent session for PDF
        db = get_db()
        initialize_database(db)
        paper_repo = SQLitePaperRepository(db)
        session_repo = SQLiteSessionRepository(db)

        # Find paper
        pdf_input = args.resume_last
        if pdf_input.startswith('zotero:'):
            zotero_key = pdf_input.replace('zotero:', '').replace('search:', '')
            paper = paper_repo.find_by_zotero_key(zotero_key)
        else:
            pdf_path = Path(pdf_input)
            if pdf_path.exists():
                with open(pdf_path, 'rb') as f:
                    pdf_hash = hashlib.sha256(f.read()).hexdigest()[:16]
                paper = paper_repo.find_by_hash(pdf_hash)
            else:
                console.print(f"[red]PDF not found: {pdf_input}[/red]")
                return

        if not paper:
            console.print("[yellow]No sessions found for this paper[/yellow]")
            return

        # Get most recent session
        sessions = session_repo.list_for_paper(paper['id'], limit=1)
        if not sessions:
            console.print("[yellow]No sessions found for this paper[/yellow]")
            return

        session_id = sessions[0]['id']
        console.print(f"[cyan]Resuming most recent session: {session_id[:16]}...[/cyan]")
        companion = PaperCompanion(resume_session=session_id)
        companion.run()
        return

    if args.resume:
        # Resume specific session
        companion = PaperCompanion(resume_session=args.resume)
        companion.run()
        return

    if not args.pdf:
        parser.print_help()
        return

    # Start new session
    companion = PaperCompanion(pdf_input=args.pdf)
    companion.run()

if __name__ == "__main__":
    main()
