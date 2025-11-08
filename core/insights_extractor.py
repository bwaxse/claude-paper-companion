"""
Insights extraction and formatting for Paper Companion
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from anthropic import Anthropic
from rich.console import Console

console = Console()


class InsightsExtractor:
    """Handles extracting and formatting insights from conversations"""

    def __init__(self, anthropic_client: Anthropic = None, model: str = "claude-haiku-4-5-20251001"):
        """
        Initialize insights extractor.

        Args:
            anthropic_client: Anthropic client instance
            model: Claude model to use
        """
        self.anthropic = anthropic_client or Anthropic()
        self.model = model

    def extract_insights(
        self,
        messages: List[Dict],
        flagged_exchanges: List[Dict],
        pdf_path: Path,
        pdf_hash: str,
        session_id: str,
        zotero_item: Dict = None
    ) -> Dict:
        """
        Extract and thematically organize insights from conversation.

        Args:
            messages: List of conversation messages
            flagged_exchanges: List of flagged exchanges
            pdf_path: Path to PDF file
            pdf_hash: PDF hash
            session_id: Session ID
            zotero_item: Optional Zotero item

        Returns:
            Dict of extracted insights
        """
        console.print("\n[cyan]Extracting and organizing insights...[/cyan]")

        # Prepare conversation for extraction
        conv_summary = "\n\n".join([
            f"User: {msg['content']}\nAssistant: {messages[i+1]['content']}"
            for i, msg in enumerate(messages[:-1:2])
            if msg["role"] == "user" and i+1 < len(messages)
        ])

        flagged_summary = "\n\n".join([
            f"[FLAGGED at {ex['timestamp']}]" +
            (f"\nNote: {ex['note']}" if ex.get('note') else "") +
            f"\nUser: {ex['user']}\nAssistant: {ex['assistant']}"
            for ex in flagged_exchanges
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
            model=self.model,
            max_tokens=3000,
            messages=[{"role": "user", "content": extraction_prompt}]
        )

        # Parse JSON from response
        response_text = response.content[0].text

        # Try to extract JSON from the response
        try:
            # Look for JSON block in response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                insights = json.loads(json_match.group())
            else:
                insights = json.loads(response_text)
        except:
            # Fallback structure
            insights = {
                "title": pdf_path.stem,
                "extraction_error": "Failed to parse structured insights",
                "raw_response": response_text[:500]
            }

        # Add metadata
        insights["pdf_hash"] = pdf_hash
        insights["pdf_path"] = str(pdf_path)
        insights["session_id"] = session_id
        insights["timestamp"] = datetime.now().isoformat()
        insights["flagged_count"] = len(flagged_exchanges)

        # If loaded from Zotero, add the item key
        if zotero_item:
            insights["zotero_key"] = zotero_item['key']

        return insights

    @staticmethod
    def format_insights_html(
        insights: Dict,
        session_id: str,
        messages: List[Dict],
        flagged_exchanges: List[Dict]
    ) -> str:
        """
        Format thematically organized insights as HTML for Zotero.

        Args:
            insights: Extracted insights dict
            session_id: Session ID
            messages: Conversation messages
            flagged_exchanges: Flagged exchanges

        Returns:
            HTML formatted insights
        """
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
<em>Session ID: {session_id[:16]}</em><br>
<em>Total exchanges: {len(messages) // 2}</em><br>
<em>Flagged insights: {len(flagged_exchanges)}</em><br>
<em>Themes identified: {len([k for k in theme_config.keys() if k in insights and insights[k]])}</em>
</small></p>
"""

        return html

    @staticmethod
    def save_local_backup(
        insights: Dict,
        messages: List[Dict],
        flagged_exchanges: List[Dict],
        pdf_path: Path,
        pdf_images_count: int,
        zotero_item: Dict = None
    ) -> Path:
        """
        Save JSON backup locally.

        Args:
            insights: Extracted insights
            messages: Conversation messages
            flagged_exchanges: Flagged exchanges
            pdf_path: PDF path
            pdf_images_count: Number of PDF images
            zotero_item: Optional Zotero item

        Returns:
            Path to backup file
        """
        backup_dir = Path.home() / '.paper_companion' / 'sessions'
        backup_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{pdf_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = backup_dir / filename

        # Include full conversation in backup
        full_data = {
            "insights": insights,
            "conversation": messages,
            "flagged_exchanges": flagged_exchanges,
            "pdf_images_count": pdf_images_count,
            "zotero_item_key": zotero_item['key'] if zotero_item else None
        }

        with open(backup_path, 'w') as f:
            json.dump(full_data, f, indent=2)

        console.print(f"[green]✓ Backup saved: {backup_path}[/green]")
        return backup_path
