"""
Insight extraction service for Scholia web backend.
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
        extraction_prompt = f"""You are synthesizing insights from a paper analysis session.

INITIAL PAPER SUMMARY:
{initial_analysis}

CONVERSATION ({len(exchanges_data) // 2} exchanges):
{conv_summary[:10000]}

STARRED EXCHANGES (reader marked these as important):
{flagged_summary}

HIGHLIGHTS FROM READING:
{highlights_summary}

Return a JSON object with this LEAN structure:

{{
  "summary": "2-3 sentence bottom line: what this paper contributes and its key limitations",

  "learnings": [
    "Most important insight from conversation (user engaged with this)",
    "Another key takeaway discussed",
    "Methodological lesson if relevant"
  ],

  "assessment": {{
    "strengths": ["genuine strength 1", "strength 2"],
    "limitations": ["critical weakness 1", "weakness 2"]
  }},

  "open_questions": [
    "Unresolved question to revisit",
    "Claim to scrutinize (with page/figure reference if available)"
  ],

  "bibliographic": {{
    "title": "paper title",
    "authors": "author list if mentioned",
    "year": "publication year if mentioned"
  }}
}}

CRITICAL RULES:
- "learnings" ONLY includes what actually came up in conversation (not generic paper analysis)
- If conversation is minimal, learnings may be empty or very short
- Include page/figure references in open_questions when available (e.g., "Fig 3 methodology unclear")
- Keep each bullet concise (1-2 sentences max)
- Prioritize what the reader actually engaged with over comprehensive coverage

Return ONLY valid JSON.
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
            "flagged_count": len(flagged_data) // 2,  # Divide by 2 since each exchange has user + assistant messages
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
            # Fallback structure matching new lean format
            return {
                "extraction_error": "Failed to parse structured insights",
                "raw_response": response_text[:500],
                "summary": "",
                "learnings": [],
                "assessment": {"strengths": [], "limitations": []},
                "open_questions": [],
                "bibliographic": {}
            }

    @staticmethod
    def format_insights_html(insights: Dict) -> str:
        """Format session insights as HTML for both UI and Zotero."""
        metadata = insights.get("metadata", {})
        bib = insights.get("bibliographic", {})
        summary = insights.get("summary", "")
        learnings = insights.get("learnings", [])
        assessment = insights.get("assessment", {})
        open_questions = insights.get("open_questions", [])

        # Title line
        title = bib.get("title", metadata.get("filename", "Unknown"))
        html = f"<h2>Session Insights - {datetime.now().strftime('%Y-%m-%d')}</h2>\n"
        html += f"<p><strong>{title}</strong></p>\n"

        # Summary
        if summary:
            html += f"<h3>Summary</h3>\n<p>{summary}</p>\n"

        # What I Learned (only if there are learnings)
        if learnings and len(learnings) > 0:
            html += "<h3>What I Learned</h3>\n<ul>\n"
            for item in learnings:
                html += f"<li>{item}</li>\n"
            html += "</ul>\n"

        # Paper Assessment (strengths & limitations)
        has_assessment = (assessment.get("strengths") or assessment.get("limitations"))
        if has_assessment:
            html += "<h3>Paper Assessment</h3>\n"

            if assessment.get("strengths"):
                html += "<p><strong>Strengths:</strong></p>\n<ul>\n"
                for item in assessment["strengths"]:
                    html += f"<li>{item}</li>\n"
                html += "</ul>\n"

            if assessment.get("limitations"):
                html += "<p><strong>Limitations:</strong></p>\n<ul>\n"
                for item in assessment["limitations"]:
                    html += f"<li>{item}</li>\n"
                html += "</ul>\n"

        # Open Questions
        if open_questions and len(open_questions) > 0:
            html += "<h3>Open Questions</h3>\n<ul>\n"
            for item in open_questions:
                html += f"<li>{item}</li>\n"
            html += "</ul>\n"

        # Minimal footer
        html += f"<hr>\n<p><small>{metadata.get('total_exchanges', 0)} exchanges"
        if metadata.get('flagged_count', 0) > 0:
            html += f" | {metadata['flagged_count']} flagged"
        html += f" | {metadata.get('extracted_at', '')[:10]}</small></p>\n"

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
