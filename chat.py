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
        
        # Load PDF
        self._load_pdf()

    def _load_from_zotero(self, zotero_input: str) -> Path:
        """Load PDF from Zotero library (cloud-based, not local)"""
        if not self.zot:
            console.print("[red]Zotero not configured[/red]")
            return None
    
        # Parse input format
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
    
        # If multiple items, let user choose
        if len(items) > 1:
            item = self._choose_zotero_item(items)
        else:
            item = items[0]
        
        self.zotero_item = item

        # Find PDF attachment
        attachments = self.zot.children(item['key'])
        pdf_attachment = None

        for att in attachments:
            if att['data'].get('contentType') == 'application/pdf':
                pdf_attachment = att
                break
        
        if not pdf_attachment:
            console.print("[red]No PDF attachment found for this item[/red]")
            return None
            
        # Create a temporary file to store downloaded PDF
        pdf_temp_path = Path(tempfile.gettempdir()) / f"{item_key}.pdf"
    
        try:
            # Download the PDF from Zotero's cloud
            self.zot.dump(
                pdf_attachment['key'],
                filename=pdf_temp_path.name,
                path=str(pdf_temp_path.parent)
            )
            console.print(f"[green]✓ Downloaded PDF from Zotero cloud: {item['data'].get('title', 'Untitled')}[/green]")
            return pdf_temp_path
        except Exception as e:
            console.print(f"[red]Failed to download PDF from Zotero: {e}[/red]")
            return None
    
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
        """Extract text and images from PDF"""
        console.print(f"[cyan]Loading PDF: {self.pdf_path.name}[/cyan]")
        
        doc = fitz.open(self.pdf_path)
        
        # Extract text
        text_content = []
        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            if text.strip():
                text_content.append(f"[Page {page_num}]\n{text}")
        
        self.pdf_content = "\n\n".join(text_content)
        
        # Extract images (limit to significant ones)
        for page_num, page in enumerate(doc, 1):
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    # Only include substantial images (likely figures)
                    if pix.width > 200 and pix.height > 200:
                        if pix.n - pix.alpha < 4:  # RGB or gray
                            img_data = pix.tobytes("png")
                            img_base64 = base64.b64encode(img_data).decode()
                            
                            self.pdf_images.append({
                                "page": page_num,
                                "index": img_index,
                                "data": img_base64,
                                "type": "image/png"
                            })
                    
                    pix = None
                except:
                    continue
        
        doc.close()
        console.print(f"[green]✓ Loaded {len(text_content)} pages, {len(self.pdf_images)} figures[/green]")
        
        # If loaded from Zotero, show existing metadata
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
- What is the paper actually claiming? (not what they say they're claiming)
- Is this genuinely novel or incremental dressed as revolutionary?
- What would a skeptical reviewer ask immediately?

## 2. METHODOLOGICAL SCRUTINY
- What are they NOT telling us about their methods?
- Where are the potential p-hacking or cherry-picking risks?
- What controls are missing?
- Sample size and statistical power concerns?

## 3. RESULTS REALITY CHECK
- Do the results actually support the conclusions?
- What's in the supplementary materials they hope we won't check?
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

{self.pdf_content[:50000]}  # Truncate for initial summary
"""
            }
        ]
        
        # Add first few images if available
        for img in self.pdf_images[:3]:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img["type"],
                    "data": img["data"]
                }
            })
        
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2500,
            messages=[{"role": "user", "content": content}]
        )
        
        summary = response.content[0].text
        
        # Store in conversation history
        self.messages.append({"role": "system", "content": f"Paper loaded: {self.pdf_path.name}"})
        self.messages.append({"role": "assistant", "content": summary})
        
        return summary
    
    def chat_loop(self):
        """Main interactive chat loop"""
        console.print("\n[bold cyan]Starting conversation. Commands:[/bold cyan]")
        console.print("  [yellow]/flag[/yellow] - Mark this exchange as important")
        console.print("  [yellow]/exit[/yellow] - End session and save insights")
        console.print("  [yellow]/img N[/yellow] - Show figure N from the paper")
        console.print("  [yellow]/highlight[/yellow] - Suggest text to highlight in Zotero")
        console.print("  [yellow]/related[/yellow] - Find related papers in your Zotero library")
        console.print()
        
        while True:
            # Get user input
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            # Handle commands
            if user_input.lower() == '/exit':
                break
            elif user_input.lower() == '/flag':
                self._flag_last_exchange()
                continue
            elif user_input.lower().startswith('/img'):
                self._show_image(user_input)
                continue
            elif user_input.lower() == '/highlight':
                self._suggest_highlights()
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
    
    def _suggest_highlights(self):
        """Suggest key passages to highlight in Zotero"""
        prompt = """Based on our conversation and the paper content, suggest 5-7 key passages 
        that would be most valuable to highlight in Zotero. For each passage, provide:
        1. The page number
        2. A brief excerpt (first few words... last few words)
        3. Why it's important to highlight
        
        Focus on: methodology details, key findings, limitations, and future work."""
        
        response = self._get_claude_response(prompt)
        console.print("\n[bold yellow]Highlighting Suggestions:[/bold yellow]")
        console.print(Markdown(response))
        
        # Store this as a flagged exchange
        self.messages.append({"role": "user", "content": prompt})
        self.messages.append({"role": "assistant", "content": response})
        self.flagged_exchanges.append({
            "user": "Highlighting suggestions requested",
            "assistant": response,
            "timestamp": datetime.now().isoformat()
        })
    
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
            "content": f"I'm reading a paper. Here's the content:\n\n{self.pdf_content[:30000]}"
        })
        
        # Add conversation history (recent)
        for msg in self.messages[-10:]:
            messages.append(msg)
        
        # Add current question
        messages.append({"role": "user", "content": user_input})
        
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
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
        """Extract structured insights from conversation"""
        console.print("\n[cyan]Extracting insights from conversation...[/cyan]")
        
        # Prepare conversation summary for extraction
        conv_summary = "\n\n".join([
            f"User: {msg['content']}\nAssistant: {self.messages[i+1]['content']}"
            for i, msg in enumerate(self.messages[:-1:2])
            if msg["role"] == "user" and i+1 < len(self.messages)
        ])
        
        flagged_summary = "\n\n".join([
            f"User: {ex['user']}\nAssistant: {ex['assistant']}"
            for ex in self.flagged_exchanges
        ])
        
        extraction_prompt = f"""Based on our conversation about this paper, extract comprehensive metadata and insights:

CONVERSATION:
{conv_summary[:10000]}

FLAGGED EXCHANGES:
{flagged_summary}

Please provide a JSON object with:

BIBLIOGRAPHIC METADATA:
- title: Full paper title
- authors: List of author names (format: [{{"firstName": "John", "lastName": "Doe"}}])
- journal: Journal/conference name
- journal_abbr: Journal abbreviation if known
- volume: Volume number
- issue: Issue number  
- pages: Page range (e.g., "123-145")
- date: Publication date (YYYY-MM-DD or YYYY-MM or YYYY)
- doi: DOI if mentioned
- arxiv_id: ArXiv ID if applicable
- pmid: PubMed ID if applicable
- issn: ISSN if known
- abstract: Paper abstract or summary
- language: Language (default "en")

CONVERSATION INSIGHTS:
- focus_areas: List of topics I specifically focused on
- key_methods: Technical methods/approaches we discussed
- main_findings: Key findings we covered in depth
- user_interests: My specific interests/interpretations/connections
- limitations: Limitations or weaknesses we discussed
- open_questions: Unresolved questions from our discussion
- key_quotes: Most important/insightful exchanges from our conversation
- potential_applications: Applications or implications I was interested in
- highlight_suggestions: Passages worth highlighting in Zotero
"""
        
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
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
        """Format insights as HTML for Zotero note"""
        html = f"""<h2>Claude Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')}</h2>
        
<h3>📍 Focus Areas</h3>
<ul>
{''.join(f'<li>{area}</li>' for area in insights.get('focus_areas', []))}
</ul>

<h3>🔬 Key Methods Discussed</h3>
<p>{', '.join(insights.get('key_methods', [])) if insights.get('key_methods') else 'No specific methods discussed'}</p>

<h3>📊 Main Findings We Covered</h3>
<ul>
{''.join(f'<li>{finding}</li>' for finding in insights.get('main_findings', []))}
</ul>

<h3>💡 My Specific Interests & Interpretations</h3>
<p>{'<br>'.join(insights.get('user_interests', [])) if insights.get('user_interests') else 'No specific interests noted'}</p>

<h3>🔍 Suggested Highlights</h3>
<ul>
{''.join(f'<li>{highlight}</li>' for highlight in insights.get('highlight_suggestions', [])[:5])}
</ul>

<h3>⚠️ Limitations Discussed</h3>
<p>{', '.join(insights.get('limitations', [])) if insights.get('limitations') else 'No limitations discussed'}</p>

<h3>❓ Open Questions</h3>
<ul>
{''.join(f'<li>{q}</li>' for q in insights.get('open_questions', []))}
</ul>

<hr>
<p><small>
<em>Session ID: {self.session_id[:16]}</em><br>
<em>PDF Hash: {self.pdf_hash}</em><br>
<em>Flagged exchanges: {len(self.flagged_exchanges)}</em><br>
<em>Total exchanges: {len(self.messages) // 2}</em>
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
        """Main execution flow"""
        try:
            # Initial summary
            summary = self.get_initial_summary()
            console.print("\n[bold]Initial Analysis:[/bold]")
            console.print(Markdown(summary))
            
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
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            import traceback
            traceback.print_exc()


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
