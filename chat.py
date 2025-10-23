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

import fitz  # PyMuPDF
from anthropic import Anthropic
from pyzotero import zotero
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

console = Console()

class PaperCompanion:
    def __init__(self, pdf_input: str):
        """
        Initialize with either:
        - Direct PDF path: /path/to/paper.pdf
        - Zotero item key: zotero:ABCD1234
        - Zotero search: zotero:search:transformer attention
        """
        self.setup_zotero()
        self.zotero_item = None  # Store linked Zotero item
        
        # Handle different input types
        if pdf_input.startswith('zotero:'):
            self.pdf_path = self._load_from_zotero(pdf_input)
        else:
            self.pdf_path = Path(pdf_input)
            
        if not self.pdf_path or not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_input}")
            
        self.pdf_hash = self._compute_pdf_hash()
        self.session_id = datetime.now().isoformat()
        
        # Initialize APIs
        self.anthropic = Anthropic()
        
        # Session state
        self.messages = []
        self.flagged_exchanges = []
        self.pdf_content = None
        self.pdf_images = []
        
        # Load one or multiple PDFs
        if isinstance(self.pdf_path, list):
            for path in self.pdf_path:
                self.pdf_path = path
                self._load_pdf()
        else:
            self._load_pdf()

    def _load_from_zotero(self, zotero_input: str) -> Path:
        """Load PDFs from Zotero with granular selection."""
        if not self.zot:
            console.print("[red]Zotero not configured[/red]")
            return None
        
        # [Previous parsing code remains the same...]
        
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
            console.print("  • Enter numbers (e.g., '1,3' or '1-3')")
            console.print("  • Enter 'all' to include everything")
            console.print("  • Enter 'none' or press Enter for main PDF only")
            console.print("  • Enter 'first N' for first N supplements (e.g., 'first 2')")
            
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
        console.print("[cyan]Analyzing paper...[/cyan]")
        
        # Include Zotero metadata if available
        context = ""
        if self.zotero_item:
            data = self.zotero_item['data']
            context = f"""This paper is already in your Zotero library with:
- Title: {data.get('title', 'Unknown')}
- Authors: {self._format_authors(data.get('creators', []))}
- Journal: {data.get('publicationTitle', 'Unknown')}
- DOI: {data.get('DOI', 'None')}
"""
        
        # Prepare content for Claude
        content = [
            {
                "type": "text",
                "text": f"""{context}
    
    You are a prominent senior scientist reviewing this paper. Be direct and intellectually honest. 
    Please provide a CONCISE 5-bullet summary of this paper's most important aspects according to your review (i.e. not just according to their text).
    
    Format each bullet as:
    - [ASPECT]: One clear, specific sentence
    
    Focus on what matters most:
    - Core innovation (if any)
    - Key methodological strength or flaw
    - Most significant finding
    - Critical limitation(s)
    - Real-world impact/applicability
    
    Paper text:
    {self.pdf_content[:100000]}"""
            }
        ]
        
        # Add figures
        for img in self.pdf_images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img["type"],
                    "data": img["data"]
                }
            })
        
        response = self.anthropic.messages.create(
            model="claude-haiku-4-5-20251001", #claude-sonnet-4-5-20250929
            max_tokens=800, #keep it concise
            messages=[{"role": "user", "content": content}]
        )
        
        summary = response.content[0].text

        # Store in conversation history
        self.messages.append({"role": "assistant", "content": summary})

        return summary

    def get_full_critical_review(self) -> str:
        """Get Claude's critical analysis of the paper"""
        console.print("[cyan]Performing critical analysis...[/cyan]")
        
        # Include Zotero metadata if available
        context = ""
        if self.zotero_item:
            data = self.zotero_item['data']
            context = f"""This paper is already in your Zotero library with:
- Title: {data.get('title', 'Unknown')}
- Authors: {self._format_authors(data.get('creators', []))}
- Journal: {data.get('publicationTitle', 'Unknown')}
- DOI: {data.get('DOI', 'None')}

Please verify and enhance this metadata if possible.
"""
        
        # Prepare content for Claude
        content = [
            {
                "type": "text",
                "text": f"""{context}

Please provide a CRITICAL SENIOR SCIENTIST REVIEW of this paper. Be direct and intellectually honest.

## 1. CORE CLAIM ASSESSMENT
- What is the paper claiming?
- Is this genuinely novel or incremental dressed as revolutionary?
- What would a skeptical reviewer ask immediately?

## 2. METHODOLOGICAL SCRUTINY
- What are they NOT telling us about their methods?
- Where are the potential p-hacking or cherry-picking risks?
- What controls are missing?
- Other concerns (e.g., sample size, statistical power)?

## 3. RESULTS REALITY CHECK
- Do the results actually support the claims and/or conclusions?
- Anything in the supplementary materials they hope we won't check?
- Are effect sizes meaningful or just statistically significant?
- Any suspicious data patterns? (too clean, missing variance, etc.)

## 4. HIDDEN LIMITATIONS
- What limitations did they bury in the discussion?
- What caveats make their findings less generalizable?
- What would fail to replicate?

## 5. ACTUAL CONTRIBUTION
- Strip away the hype: what's the real advance here?
- Who actually benefits from this work?
- What's the next obvious experiment they didn't do?

## 6. RED FLAGS & CONCERNS
- Overclaimed findings
- Conflicts of interest
- Questionable citations or self-citation padding
- Technical issues glossed over

## 7. WORTH YOUR TIME?
- Should you deeply engage with this paper?
- What specific sections deserve careful scrutiny?
- What should you highlight for your future self?

Be blunt. Point out bullshit. Identify real insights. Think like a reviewer who's seen every trick.

Here's the paper text:

{self.pdf_content[:100000]}  # Truncate for initial summary
"""
            }
        ]
        
        # Add first few images if available
        for img in self.pdf_images[:6]:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img["type"],
                    "data": img["data"]
                }
            })
        
        response = self.anthropic.messages.create(
            model="claude-haiku-4-5-20251001", #claude-sonnet-4-5-20250929
            max_tokens=2500,
            messages=[{"role": "user", "content": content}]
        )
        
        summary = response.content[0].text

        # Store in conversation history
        self.messages.append({"role": "assistant", "content": summary})

        return summary
    
    def chat_loop(self):
        """Main interactive chat loop - enhanced with new commands"""
        console.print("\n[bold cyan]Let's explore this paper together. Commands:[/bold cyan]")
        console.print("  [yellow]/flag[/yellow] - Mark this exchange as important")
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
            elif user_input.lower() == '/flag':
                self._flag_last_exchange()
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
            
            # Store exchange
            self.messages.append({"role": "user", "content": user_input})
            self.messages.append({"role": "assistant", "content": response})

    def _find_related_papers(self):
        """Find related papers in Zotero library"""
        if not self.zot:
            console.print("[yellow]Zotero not configured[/yellow]")
            return
        
        # Get current paper's tags and keywords
        if self.zotero_item:
            tags = [t['tag'] for t in self.zotero_item.get('tags', [])]
            
            console.print(f"[cyan]Searching for papers with similar tags: {', '.join(tags[:5])}[/cyan]")
            
            related = []
            for tag in tags[:3]:  # Search top 3 tags
                items = self.zot.items(tag=tag, limit=5)
                for item in items:
                    if item['key'] != self.zotero_item['key']:
                        related.append(item)
            
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
        # Build conversation context
        messages = []

        # Add paper context (truncated)
        messages.append({
            "role": "user",
        "content": f"""I'm analyzing this paper. Be direct and rigorous.
        

RESPONSE RULES:
- If I'm wrong: "Wrong." then explain why
- If I'm right: "Right." then push deeper  
- If partially right: "Partially correct:" then specify exactly what's right/wrong
- If the paper's wrong: "The paper's error:" then explain
- Never use: "Good catch", "Interesting point", "That's a great question"
- Assume I understand basics (I'll ask when I don't)—build on ideas, don't re-explain
- Distinguish: paper's claims vs actual truth vs unknowns
- Be precise with technical language
- If something's overstated, say "This is overstated because..."

Keep responses 1-3 paragraphs. Shorter if the answer is simple.
Point to specific sections/figures when relevant.
If I ask about something specific, dive deep but stay focused, going short paragraph by short paragraph.

Paper content:
{self.pdf_content[:100000]}"""
    })

        # Add conversation history (recent)
        for msg in self.messages[-10:]:
            messages.append(msg)

        # Add current question
        messages.append({"role": "user", "content": user_input})

        response = self.anthropic.messages.create(
            model="claude-haiku-4-5-20251001", #claude-sonnet-4-5-20250929
            max_tokens=1000,
            temperature=0.6,  # Lower for more consistency
            messages=messages
        )

        return response.content[0].text
    
    def _flag_last_exchange(self):
        """Flag the last exchange as important"""
        if len(self.messages) >= 2:
            last_exchange = {
                "user": self.messages[-2]["content"],
                "assistant": self.messages[-1]["content"],
                "timestamp": datetime.now().isoformat()
            }
            self.flagged_exchanges.append(last_exchange)
            console.print("[yellow]✓ Exchange flagged[/yellow]")
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
        console.print("\n[cyan]Extracting and organizing insights...[/cyan]")
        
        # Prepare conversation for extraction
        conv_summary = "\n\n".join([
            f"User: {msg['content']}\nAssistant: {self.messages[i+1]['content']}"
            for i, msg in enumerate(self.messages[:-1:2])
            if msg["role"] == "user" and i+1 < len(self.messages)
        ])
        
        flagged_summary = "\n\n".join([
            f"[FLAGGED at {ex['timestamp']}]\nUser: {ex['user']}\nAssistant: {ex['assistant']}"
            for ex in self.flagged_exchanges
        ])
        
        extraction_prompt = f"""Based on our conversation about this paper, extract insights and organize them THEMATICALLY.
    
    CONVERSATION:
    {conv_summary[:10000]}
    
    FLAGGED EXCHANGES (these are especially important):
    {flagged_summary}
    
    Please provide a JSON object with:
    
    1. BIBLIOGRAPHIC METADATA (title, authors, journal, doi, etc. as before)
    
    2. THEMATICALLY ORGANIZED INSIGHTS:
       - strengths: List of paper's genuine strengths we discussed
       - weaknesses: Methodological or conceptual weaknesses identified  
       - methodological_notes: Specific technical/methods insights
       - statistical_concerns: Any stats/analysis issues raised
       - theoretical_contributions: Conceptual advances or frameworks
       - empirical_findings: Key results and data points discussed
       - questions_raised: Open questions and uncertainties we explored
       - applications: Practical implications discussed
       - connections: Links to other work/ideas mentioned
       - critiques: Specific critical points made (beyond general weaknesses)
       - surprising_elements: Unexpected findings or approaches noted
       
    3. KEY_QUOTES: The 3-5 most insightful exchanges from our conversation, categorized by theme
    
    4. CUSTOM_THEMES: Any recurring themes specific to our discussion that don't fit above
       (e.g., if we spent a lot of time on "reproducibility" or "ethical implications")
    
    5. HIGHLIGHT_SUGGESTIONS: Specific passages to highlight, grouped by:
       - critical_passages: Must-read sections
       - questionable_claims: Passages needing scrutiny  
       - methodological_details: Technical sections of interest
       - key_findings: Result sections to mark
    
    Focus especially on the FLAGGED exchanges as these were marked as important during reading.
    """
        
        response = self.anthropic.messages.create(
            model="claude-haiku-4-5-20251001", #claude-sonnet-4-5-20250929
            max_tokens=3000,
            messages=[{"role": "user", "content": extraction_prompt}]
        )
        
        # Parse JSON from response
        response_text = response.content[0].text
        
        # Try to extract JSON from the response
        try:
            # Look for JSON block in response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                insights = json.loads(json_match.group())
            else:
                insights = json.loads(response_text)
        except:
            # Fallback structure
            insights = {
                "title": self.pdf_path.stem,
                "extraction_error": "Failed to parse structured insights",
                "raw_response": response_text[:500]
            }
        
        # Add metadata
        insights["pdf_hash"] = self.pdf_hash
        insights["pdf_path"] = str(self.pdf_path)
        insights["session_id"] = self.session_id
        insights["timestamp"] = datetime.now().isoformat()
        insights["flagged_count"] = len(self.flagged_exchanges)
        
        # If loaded from Zotero, add the item key
        if self.zotero_item:
            insights["zotero_key"] = self.zotero_item['key']
        
        return insights
    
    def save_to_zotero(self, insights: Dict):
        """Save insights as Zotero note"""
        if not self.zot:
            console.print("[yellow]Zotero not configured - skipping[/yellow]")
            return
        
        console.print("[cyan]Saving to Zotero...[/cyan]")
        
        # Use existing Zotero item if loaded from there
        if self.zotero_item:
            parent_item = self.zotero_item
            console.print(f"[green]Using existing item: {parent_item['data'].get('title', 'Untitled')}[/green]")
            # Update metadata if we found better information
            self._update_item_metadata(parent_item, insights)
        else:
            # Find or create item
            parent_item = self._find_or_create_item(insights)
        
        if not parent_item:
            console.print("[red]Failed to create/find Zotero item[/red]")
            return
        
        # Create note with insights
        note_html = self._format_insights_html(insights)
        
        note_template = self.zot.item_template('note')
        note_template['note'] = note_html
        note_template['parentItem'] = parent_item['key']
        note_template['tags'] = [
            {"tag": "claude-insights"},
            {"tag": f"session-{self.session_id[:10]}"}
        ]
        
        # Add focus area tags
        if insights.get('focus_areas'):
            for area in insights['focus_areas'][:2]:
                if isinstance(area, str):
                    note_template['tags'].append({"tag": f"focus:{area[:30]}"})
        
        self.zot.create_items([note_template])
        console.print("[green]✓ Insights saved to Zotero[/green]")
    
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
                html += f"""<blockquote style="border-left: 3px solid #ccc; padding-left: 10px; margin: 10px 0;">
                <strong>Q:</strong> {quote.get('user', '')}
                <br><strong>A:</strong> {quote.get('assistant', '')}
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
        backup_dir = Path.home() / '.paper_companion' / 'sessions'
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{self.pdf_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = backup_dir / filename
        
        # Include full conversation in backup
        full_data = {
            "insights": insights,
            "conversation": self.messages,
            "flagged_exchanges": self.flagged_exchanges,
            "pdf_images_count": len(self.pdf_images),
            "zotero_item_key": self.zotero_item['key'] if self.zotero_item else None
        }
        
        with open(backup_path, 'w') as f:
            json.dump(full_data, f, indent=2)
        
        console.print(f"[green]✓ Backup saved: {backup_path}[/green]")
    
    def run(self):
        """Main execution flow - now conversational"""
        try:
            # Initial concise summary
            summary = self.get_initial_summary()
            console.print("\n[bold]Key Points:[/bold]")
            console.print(Markdown(summary))
            
            # Prompt for focus
            console.print("\n[cyan]What would you like to explore first?[/cyan]")
            console.print("[dim]You can ask about specific sections, methods, results, or use commands above[/dim]")
            
            # Interactive chat
            self.chat_loop()
            
            # Extract and save insights
            insights = self.extract_insights()
            
            # Save to Zotero
            self.save_to_zotero(insights)
            
            # Local backup
            self.save_local_backup(insights)
            
            console.print("\n[bold green]Session complete! Insights saved.[/bold green]")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Session interrupted - saving backup...[/yellow]")
            self.save_local_backup({"interrupted": True, "messages": self.messages})

def main():
    """Enhanced main with Zotero integration"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Paper Companion - Interactive PDF research assistant',
        epilog="""
Examples:
  python chat.py paper.pdf                    # Load local PDF
  python chat.py zotero:ABC123XY              # Load by Zotero item key  
  python chat.py "zotero:search:transformer"  # Search and load from Zotero
  python chat.py --list-recent                # List recent Zotero items
        """
    )
    
    parser.add_argument('pdf', nargs='?', help='PDF path or Zotero reference')
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
    
    if not args.pdf:
        parser.print_help()
        return
    
    companion = PaperCompanion(args.pdf)
    companion.run()

if __name__ == "__main__":
    main()
