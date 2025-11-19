"""
Insight extraction service for Paper Companion web backend.
Ports critical appraisal extraction from CLI to web service.
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional

from ..core.claude import get_claude_client
from ..core.database import get_db_manager


class InsightExtractor:
    """
    Extracts and organizes insights from paper analysis sessions.

    Analyzes conversation history, flagged exchanges, and highlights to:
    - Identify strengths and weaknesses
    - Extract methodological insights
    - Organize findings thematically
    - Generate structured output for Zotero notes
    """

    def __init__(
        self,
        claude_client=None,
        database=None,
        model: str = "claude-haiku-4-5-20251001"
    ):
        """
        Initialize insight extractor.

        Args:
            claude_client: Optional ClaudeClient instance
            database: Optional Database instance
            model: Claude model to use for extraction (default: Haiku for cost efficiency)
        """
        self.claude = claude_client or get_claude_client()
        self.db = database or get_db_manager()
        self.model = model

    async def extract_insights(self, session_id: str) -> Dict:
        """
        Extract and thematically organize insights from a session.

        Args:
            session_id: Session ID to extract insights from

        Returns:
            Dict containing:
            - bibliographic: Metadata (title, authors, etc.)
            - strengths: Paper's genuine strengths
            - weaknesses: Methodological/conceptual weaknesses
            - methodological_notes: Technical insights
            - statistical_concerns: Stats/analysis issues
            - theoretical_contributions: Conceptual advances
            - empirical_findings: Key results discussed
            - questions_raised: Open questions
            - applications: Practical implications
            - connections: Links to other work
            - critiques: Specific critical points
            - surprising_elements: Unexpected findings
            - key_quotes: Most insightful exchanges
            - custom_themes: Session-specific themes
            - highlight_suggestions: Passages to highlight
            - metadata: Extraction metadata

        Raises:
            ValueError: If session not found
        """
        # Get session data
        async with self.db.get_connection() as conn:
            # Get session
            session = await conn.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,)
            )
            session_row = await session.fetchone()

            if not session_row:
                raise ValueError(f"Session not found: {session_id}")

            # Get all exchanges (conversation history) excluding initial analysis
            exchanges = await conn.execute(
                """
                SELECT id, role, content, model, timestamp as created_at
                FROM conversations
                WHERE session_id = ? AND exchange_id > 0
                ORDER BY timestamp ASC
                """,
                (session_id,)
            )
            exchanges_data = await exchanges.fetchall()

            # Get flagged exchanges
            flagged = await conn.execute(
                """
                SELECT c.id, c.role, c.content, f.note, f.created_at as flag_time
                FROM conversations c
                JOIN flags f ON c.exchange_id = f.exchange_id AND c.session_id = f.session_id
                WHERE c.session_id = ?
                ORDER BY f.created_at ASC
                """,
                (session_id,)
            )
            flagged_data = await flagged.fetchall()

            # Get highlights
            highlights = await conn.execute(
                """
                SELECT text, page_number, exchange_id, created_at
                FROM highlights
                WHERE session_id = ?
                ORDER BY created_at DESC
                """,
                (session_id,)
            )
            highlights_data = await highlights.fetchall()

            # Get the PDF text for context
            pdf_text_result = await conn.execute(
                "SELECT full_text FROM sessions WHERE id = ?",
                (session_id,)
            )
            pdf_text_row = await pdf_text_result.fetchone()
            pdf_text = pdf_text_row[0] if pdf_text_row else ""

            # Get initial analysis from conversations (exchange_id = 0, role = 'assistant')
            initial_result = await conn.execute(
                """
                SELECT content FROM conversations
                WHERE session_id = ? AND exchange_id = 0 AND role = 'assistant'
                LIMIT 1
                """,
                (session_id,)
            )
            initial_row = await initial_result.fetchone()
            initial_analysis = initial_row[0] if initial_row else ""

        # Prepare conversation summary (include initial analysis)
        conv_summary = self._format_conversation(exchanges_data, initial_analysis)
        flagged_summary = self._format_flagged_exchanges(exchanges_data, flagged_data)
        highlights_summary = self._format_highlights(highlights_data)

        # Build extraction prompt - use initial analysis as paper context, not full PDF
        # This ensures insights reflect what was actually discussed, not a fresh analysis
        extraction_prompt = f"""Based on our conversation about this paper, extract insights and organize them THEMATICALLY.

INITIAL PAPER SUMMARY:
{initial_analysis}

CONVERSATION ({len(exchanges_data) // 2} exchanges):
{conv_summary[:10000]}

FLAGGED EXCHANGES (these are especially important):
{flagged_summary}

HIGHLIGHTS FROM READING:
{highlights_summary}

Please provide a JSON object with:

1. BIBLIOGRAPHIC METADATA:
   - title: Paper title (if mentioned)
   - authors: Author list (if mentioned)
   - journal: Publication venue (if mentioned)
   - year: Publication year (if mentioned)
   - doi: DOI (if mentioned)

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

3. KEY_QUOTES: The 3-5 most insightful exchanges from our conversation
   Each as: {{"user": "question", "assistant": "answer", "theme": "category", "note": "why important"}}

4. CUSTOM_THEMES: Any recurring themes specific to our discussion that don't fit above
   (e.g., if we spent a lot of time on "reproducibility" or "ethical implications")
   Format as: {{"theme_name": ["insight 1", "insight 2"]}}

5. HIGHLIGHT_SUGGESTIONS: Specific passages to highlight, grouped by:
   - critical_passages: Must-read sections
   - questionable_claims: Passages needing scrutiny
   - methodological_details: Technical sections of interest
   - key_findings: Result sections to mark

Focus especially on the FLAGGED exchanges as these were marked as important during reading.
Provide ONLY the JSON object, no additional text.
"""

        # Call Claude to extract insights using structured extraction
        # Uses summary + conversation only (not full PDF) to ensure insights
        # reflect what was actually discussed in the session
        response_text, usage = await self.claude.extract_structured(
            extraction_prompt=extraction_prompt,
            pdf_text="",  # Don't send full PDF - use initial_analysis in prompt instead
            conversation_context="",  # Already included in extraction_prompt
            max_tokens=4000  # Sufficient for complete JSON response
        )

        # Parse JSON from response
        insights = self._parse_insights_json(response_text)

        # Add metadata
        insights["metadata"] = {
            "session_id": session_id,
            "filename": dict(session_row)["filename"],
            "extracted_at": datetime.now().isoformat(),
            "total_exchanges": len(exchanges_data) // 2,
            "flagged_count": len(flagged_data),
            "highlights_count": len(highlights_data),
            "model_used": self.model
        }

        # Add Zotero key if available
        if dict(session_row).get("zotero_key"):
            insights["metadata"]["zotero_key"] = dict(session_row)["zotero_key"]

        return insights

    def _format_conversation(self, exchanges: List, initial_analysis: str = "") -> str:
        """Format exchanges as conversation summary.

        Note: initial_analysis parameter is kept for backwards compatibility
        but is no longer included here since it's already in INITIAL PAPER SUMMARY.
        """
        conversation = []

        # Group exchanges by pairs (user, assistant)
        # Only include actual user Q&A, not the initial analysis
        for i in range(0, len(exchanges) - 1, 2):
            if i + 1 < len(exchanges):
                user_msg = dict(exchanges[i])
                assistant_msg = dict(exchanges[i + 1])

                if user_msg["role"] == "user" and assistant_msg["role"] == "assistant":
                    conversation.append(
                        f"User: {user_msg['content']}\n"
                        f"Assistant: {assistant_msg['content'][:500]}..."  # Truncate long responses
                    )

        return "\n\n".join(conversation)

    def _format_flagged_exchanges(self, all_exchanges: List, flagged: List) -> str:
        """Format flagged exchanges with context."""
        if not flagged:
            return "(No flagged exchanges)"

        # Create exchange lookup by ID
        exchange_map = {dict(ex)["id"]: dict(ex) for ex in all_exchanges}

        flagged_text = []
        for flag in flagged:
            flag_dict = dict(flag)

            # Find the user question and assistant answer
            exchange_id = flag_dict["id"]

            # Find user and assistant messages around this exchange
            user_content = None
            assistant_content = None

            for i, ex in enumerate(all_exchanges):
                ex_dict = dict(ex)
                if ex_dict["id"] == exchange_id:
                    if ex_dict["role"] == "user":
                        user_content = ex_dict["content"]
                        # Get next message (assistant response)
                        if i + 1 < len(all_exchanges):
                            assistant_content = dict(all_exchanges[i + 1])["content"]
                    elif ex_dict["role"] == "assistant":
                        assistant_content = ex_dict["content"]
                        # Get previous message (user question)
                        if i > 0:
                            user_content = dict(all_exchanges[i - 1])["content"]

            note = f"\nNote: {flag_dict['note']}" if flag_dict.get("note") else ""
            flagged_text.append(
                f"[FLAGGED at {flag_dict['flag_time']}]{note}\n"
                f"User: {user_content or 'N/A'}\n"
                f"Assistant: {assistant_content or 'N/A'}"
            )

        return "\n\n".join(flagged_text)

    def _format_highlights(self, highlights: List) -> str:
        """Format highlights summary."""
        if not highlights:
            return "(No highlights)"

        highlight_texts = []
        for h in highlights[:20]:  # Limit to 20 most recent
            h_dict = dict(h)
            page = f" (page {h_dict['page_number']})" if h_dict.get("page_number") else ""
            highlight_texts.append(f"- {h_dict['text']}{page}")

        return "\n".join(highlight_texts)

    def _parse_insights_json(self, response_text: str) -> Dict:
        """Parse JSON from Claude's response."""
        try:
            # Look for JSON block in response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                insights = json.loads(json_match.group())
            else:
                insights = json.loads(response_text)

            return insights
        except (json.JSONDecodeError, AttributeError):
            # Fallback structure
            return {
                "extraction_error": "Failed to parse structured insights",
                "raw_response": response_text[:500],
                "bibliographic": {},
                "strengths": [],
                "weaknesses": [],
                "methodological_notes": [],
                "key_quotes": []
            }

    @staticmethod
    def format_insights_html(insights: Dict) -> str:
        """
        Format thematically organized insights as HTML for Zotero.

        Args:
            insights: Extracted insights dict from extract_insights()

        Returns:
            HTML formatted insights suitable for Zotero note
        """
        metadata = insights.get("metadata", {})

        # Build HTML header
        html = f"""<h2>📚 Paper Insights - {datetime.now().strftime('%Y-%m-%d %H:%M')}</h2>"""

        # Add bibliographic info if available
        if insights.get("bibliographic"):
            bib = insights["bibliographic"]
            if any(bib.values()):
                html += "\n<h3>📄 Paper Information</h3>\n<ul>\n"
                if bib.get("title"):
                    html += f'<li><strong>Title:</strong> {bib["title"]}</li>\n'
                if bib.get("authors"):
                    authors = bib["authors"] if isinstance(bib["authors"], str) else ", ".join(bib["authors"])
                    html += f'<li><strong>Authors:</strong> {authors}</li>\n'
                if bib.get("journal"):
                    html += f'<li><strong>Publication:</strong> {bib["journal"]}</li>\n'
                if bib.get("year"):
                    html += f'<li><strong>Year:</strong> {bib["year"]}</li>\n'
                if bib.get("doi"):
                    html += f'<li><strong>DOI:</strong> {bib["doi"]}</li>\n'
                html += "</ul>\n"

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
                if items and len(items) > 0:
                    html += f"\n<h3>{icon} {title}</h3>\n<ul>\n"
                    for item in items:
                        # Handle both string items and dict items
                        if isinstance(item, dict):
                            content = item.get("content", str(item))
                            if item.get("flagged"):
                                html += f'<li><strong>⭐ {content}</strong></li>\n'
                            else:
                                html += f'<li>{content}</li>\n'
                        else:
                            html += f'<li>{item}</li>\n'
                    html += "</ul>\n"

        # Add custom themes if any emerged
        if insights.get('custom_themes'):
            html += "\n<h3>🎨 Session-Specific Themes</h3>\n"
            custom = insights['custom_themes']
            if isinstance(custom, dict):
                for theme, items in custom.items():
                    if items:
                        html += f"<h4>{theme.replace('_', ' ').title()}</h4>\n<ul>\n"
                        for item in items:
                            html += f'<li>{item}</li>\n'
                        html += "</ul>\n"

        # Add key quotes (if any)
        if insights.get('key_quotes'):
            html += "\n<h3>💬 Key Exchanges</h3>\n"
            for quote in insights['key_quotes'][:5]:
                if isinstance(quote, dict):
                    user = quote.get('user', '')
                    assistant = quote.get('assistant', '')
                    theme = quote.get('theme', 'general')
                    note = quote.get('note', '')

                    note_html = f"<br><strong>⭐ Note:</strong> <em>{note}</em>" if note else ""
                    html += f"""<blockquote style="border-left: 3px solid #ccc; padding-left: 10px; margin: 10px 0;">
<strong>Q:</strong> {user}
<br><strong>A:</strong> {assistant}{note_html}
<br><small><em>{theme}</em></small>
</blockquote>\n"""

        # Add highlight suggestions
        if insights.get('highlight_suggestions'):
            html += "\n<h3>📝 Suggested Highlights</h3>\n"
            suggestions = insights['highlight_suggestions']
            if isinstance(suggestions, dict):
                for category, items in suggestions.items():
                    if items and len(items) > 0:
                        html += f"<h4>{category.replace('_', ' ').title()}</h4>\n<ul>\n"
                        for item in items[:3]:  # Limit to top 3 per category
                            html += f'<li>{item}</li>\n'
                        html += "</ul>\n"

        # Add metadata footer
        html += f"""
<hr>
<p><small>
<em>Session: {metadata.get('filename', 'Unknown')}</em><br>
<em>Total exchanges: {metadata.get('total_exchanges', 0)}</em><br>
<em>Flagged insights: {metadata.get('flagged_count', 0)}</em><br>
<em>Highlights: {metadata.get('highlights_count', 0)}</em><br>
<em>Extracted: {metadata.get('extracted_at', 'Unknown')}</em>
</small></p>
"""

        return html


# Singleton instance
_insight_extractor: Optional[InsightExtractor] = None


def get_insight_extractor(
    claude_client=None,
    database=None,
    model: str = "claude-haiku-4-5-20251001"
) -> InsightExtractor:
    """
    Get singleton InsightExtractor instance.

    Args:
        claude_client: Optional ClaudeClient instance
        database: Optional Database instance
        model: Claude model to use

    Returns:
        InsightExtractor instance
    """
    global _insight_extractor

    if _insight_extractor is None:
        _insight_extractor = InsightExtractor(
            claude_client=claude_client,
            database=database,
            model=model
        )

    return _insight_extractor
