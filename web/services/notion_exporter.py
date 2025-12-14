"""
Notion export service for Scholia.
Generates relevance statements and formats content for Notion Literature Reviews.
"""

import json
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from .notion_client import NotionClient, get_notion_client
from ..core.claude import get_claude_client
from ..core.database import get_db_manager

logger = logging.getLogger(__name__)


# Voice samples for relevance generation (from bjw-voice-modeling skill)
RELEVANCE_VOICE_GUIDE = """
When writing relevance statements, match Bennett's voice characteristics:
- Technical precision with accessibility: Use domain terminology correctly but explain clearly
- Substantive without excess: Direct and concise, no unnecessary preamble
- Collaborative tone: Frame connections constructively
- Explain implications: Don't just state facts, explain why they matter for the project
- Acknowledge limitations when appropriate

Examples of Bennett's connecting style:
"This paper's phecode methodology aligns with our need for phenotype classification, though the reliance on billing codes means we'll need to validate against clinical notes."

"The autoencoder architecture here could work for our EHR embedding, but their batch size assumptions won't hold with our sparse data."
"""


class NotionExporter:
    """
    Exports session insights to Notion with project-specific relevance framing.

    Uses Claude to:
    - Generate relevance statements connecting papers to project goals (Haiku)
    - Format full export content for Notion Literature Reviews (Sonnet)
    """

    def __init__(
        self,
        notion_client: Optional[NotionClient] = None,
        claude_client=None
    ):
        """
        Initialize Notion exporter.

        Args:
            notion_client: Optional NotionClient instance
            claude_client: Optional ClaudeClient instance
        """
        self.notion = notion_client or get_notion_client()
        self.claude = claude_client or get_claude_client()

    async def get_project_context(
        self,
        page_id: str,
        force_refresh: bool = False
    ) -> Dict:
        """
        Fetch and parse project context. Uses database cache unless force_refresh.

        Args:
            page_id: Notion page ID
            force_refresh: If True, bypass cache and re-fetch

        Returns:
            {
                "title": "EHR Autoencoder Project",
                "hypothesis": "Cross-modal embedding via autoencoders...",
                "themes": ["Autoencoder Use in Biology", "EHR GPT"],
                "raw_content": "..."
            }

        Raises:
            ValueError: If not authenticated with Notion
        """
        db = get_db_manager()

        # Check cache first (unless force_refresh)
        if not force_refresh:
            async with db.get_connection() as conn:
                result = await conn.execute(
                    "SELECT title, hypothesis, themes, raw_content, fetched_at "
                    "FROM notion_project_cache WHERE page_id = ?",
                    (page_id,)
                )
                row = await result.fetchone()

                if row:
                    # Check if cache is recent (less than 24 hours old)
                    fetched_at = datetime.fromisoformat(row[4])
                    if datetime.now() - fetched_at < timedelta(hours=24):
                        logger.info(f"Using cached context for page {page_id}")
                        return {
                            "title": row[0],
                            "hypothesis": row[1],
                            "themes": json.loads(row[2]) if row[2] else [],
                            "raw_content": row[3],
                            "fetched_at": row[4]
                        }

        # Fetch fresh content from Notion
        logger.info(f"Fetching fresh context for page {page_id}")
        raw_content = await self.notion.fetch_page_content(page_id)

        # Parse context using Claude
        context = await self._parse_project_context(page_id, raw_content)

        # Cache the result
        async with db.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO notion_project_cache (page_id, title, hypothesis, themes, raw_content, fetched_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(page_id) DO UPDATE SET
                    title = excluded.title,
                    hypothesis = excluded.hypothesis,
                    themes = excluded.themes,
                    raw_content = excluded.raw_content,
                    fetched_at = CURRENT_TIMESTAMP
                """,
                (
                    page_id,
                    context["title"],
                    context["hypothesis"],
                    json.dumps(context["themes"]),
                    raw_content
                )
            )
            await conn.commit()

            # Get the fetched_at timestamp we just inserted
            result = await conn.execute(
                "SELECT fetched_at FROM notion_project_cache WHERE page_id = ?",
                (page_id,)
            )
            row = await result.fetchone()
            if row:
                context["fetched_at"] = row[0]

        return context

    async def _parse_project_context(self, page_id: str, raw_content: str) -> Dict:
        """
        Parse project context from page content using Claude.

        Args:
            page_id: Notion page ID
            raw_content: Raw page content as text

        Returns:
            Parsed context dict
        """
        # Get page title from Notion API
        page = await self.notion.notion.pages.retrieve(page_id=page_id)
        title = self.notion._extract_title(page) or "Untitled Project"

        # Extract hypothesis and themes from content
        prompt = f"""Analyze this Notion project page and extract key information.

PAGE CONTENT:
{raw_content[:4000]}  # Limit to first 4000 chars

TASK:
1. Find the project hypothesis or research question (look for "Hypothesis", "Research Question", "Goal" sections)
2. Find Literature Review themes (look under "Literature Review" heading for sub-headings or categories)

Return JSON:
{{
    "hypothesis": "The main research hypothesis or question (1-2 sentences)",
    "themes": ["Theme 1", "Theme 2", ...]  // Existing theme headings found
}}

If no hypothesis found, use empty string.
If no themes found, return empty array.
"""

        response_text, _ = await self.claude.extract_structured(
            extraction_prompt=prompt,
            pdf_text="",
            conversation_context="",
            max_tokens=500
        )

        # Parse response
        try:
            import json
            match = re.search(r'\{[\s\S]*\}', response_text)
            if match:
                parsed = json.loads(match.group())
            else:
                parsed = json.loads(response_text)

            return {
                "title": title,
                "hypothesis": parsed.get("hypothesis", ""),
                "themes": parsed.get("themes", []),
                "raw_content": raw_content
            }
        except Exception as e:
            logger.error(f"Failed to parse project context: {e}")
            return {
                "title": title,
                "hypothesis": "",
                "themes": [],
                "raw_content": raw_content
            }

    async def generate_relevance(
        self,
        session_insights: Dict,
        project_context: Dict
    ) -> Dict:
        """
        Generate proposed relevance statement + theme suggestion.

        Uses Haiku and Bennett's voice from bjw-voice-modeling skill.

        Args:
            session_insights: Session insights from extract_insights()
            project_context: Project context from get_project_context()

        Returns:
            {
                "suggested_theme": "Existing Theme" or "NEW: Proposed Theme",
                "relevance_statement": "2-3 sentence relevance in Bennett's voice"
            }
        """
        # Extract key info from insights
        bibliographic = session_insights.get("bibliographic", {})
        paper_title = bibliographic.get("title", "Unknown paper")
        summary = session_insights.get("summary", "")
        learnings = session_insights.get("learnings", [])[:3]  # Top 3
        assessment = session_insights.get("assessment", {})

        prompt = f"""You are helping a researcher connect a paper they've analyzed to their ongoing project.

PROJECT CONTEXT:
Title: {project_context['title']}
Hypothesis: {project_context['hypothesis'] or 'Not specified'}
Existing Literature Review themes: {', '.join(project_context['themes']) if project_context['themes'] else 'None yet'}

PAPER SESSION INSIGHTS:
Paper: {paper_title}
Summary: {summary}
Key learnings:
{chr(10).join(f"- {l}" for l in learnings)}

VOICE GUIDANCE:
{RELEVANCE_VOICE_GUIDE}

TASK:
1. Suggest which existing theme this paper belongs under, OR propose a new theme name if none fit well
2. Write a 2-3 sentence relevance statement explaining how this paper connects to the project hypothesis

The relevance statement should:
- Use technical precision with accessibility
- Be substantive without excess (no preamble)
- Explain WHY this matters for the project, not just WHAT the paper did
- Acknowledge limitations if relevant ("though", "but", "however")
- Sound like a researcher thinking aloud, not marketing copy

Return ONLY JSON:
{{
    "suggested_theme": "Existing Theme Name" or "NEW: Proposed Theme Name",
    "relevance_statement": "2-3 sentences in Bennett's voice"
}}
"""

        response_text, _ = await self.claude.extract_structured(
            extraction_prompt=prompt,
            pdf_text="",
            conversation_context="",
            max_tokens=300
        )

        # Parse response
        try:
            match = re.search(r'\{[\s\S]*\}', response_text)
            if match:
                result = json.loads(match.group())
            else:
                result = json.loads(response_text)

            return {
                "suggested_theme": result.get("suggested_theme", "NEW: Related Work"),
                "relevance_statement": result.get("relevance_statement", "")
            }
        except Exception as e:
            logger.error(f"Failed to parse relevance response: {e}")
            return {
                "suggested_theme": "NEW: Related Work",
                "relevance_statement": "This paper relates to the project goals.",
                "error": str(e)
            }

    async def generate_export_content(
        self,
        session_insights: Dict,
        project_context: Dict,
        confirmed_theme: str,
        confirmed_relevance: str,
        include_session_notes: bool = True
    ) -> str:
        """
        Generate full formatted content for Notion export.

        Uses Sonnet for quality.

        Args:
            session_insights: Session insights from extract_insights()
            project_context: Project context
            confirmed_theme: User-confirmed theme
            confirmed_relevance: User-confirmed relevance statement
            include_session_notes: Whether to include collapsed session notes

        Returns:
            Formatted content as plain text (will be converted to Notion blocks)
        """
        bibliographic = session_insights.get("bibliographic", {})
        paper_title = bibliographic.get("title", "Unknown paper")
        authors = bibliographic.get("authors", "Unknown authors")
        year = bibliographic.get("year", "")

        # Extract last name for citation
        if authors and "," in authors:
            last_name = authors.split(",")[0].strip()
        elif authors:
            last_name = authors.split()[0].strip()
        else:
            last_name = "Unknown"

        prompt = f"""You are formatting a paper analysis for a researcher's Notion literature review.

PROJECT CONTEXT:
Title: {project_context['title']}
Hypothesis: {project_context['hypothesis'] or 'Not specified'}

CONFIRMED FRAMING:
Theme: {confirmed_theme}
Relevance: {confirmed_relevance}

PAPER INFO:
Title: {paper_title}
Authors: {authors}
Year: {year}

SESSION INSIGHTS:
{json.dumps(session_insights, indent=2)}

TASK:
Generate a literature review entry formatted for Notion.

REQUIREMENTS:
- **Key insights** (2-4 bullets): Frame findings in terms of how they matter for THIS project (not generic paper summaries)
- **Open questions** (1-3 bullets): Questions this raises specifically for THIS project's hypothesis
- **Session notes** (if included): Condense what the reader learned and engaged with

Use Bennett's voice characteristics:
- Technical precision with accessibility
- Substantive without excess
- Explain implications, not just facts
- Collaborative tone

Return ONLY the formatted content as plain text with this structure:

### {last_name} et al., {year}
{paper_title}

**Relevance**: {confirmed_relevance}

**Key insights**:
- [insight framed for project]
- [insight framed for project]

**Open questions**:
- [question for this project]

{{'**Session notes**:' if include_session_notes else ''}}
{{'[condensed learnings from session]' if include_session_notes else ''}}

DO NOT include toggle syntax (▶) or Notion formatting - just plain text with markdown.
"""

        response_text, _ = await self.claude.extract_structured(
            extraction_prompt=prompt,
            pdf_text="",
            conversation_context="",
            max_tokens=1000
        )

        return response_text.strip()

    async def export_to_notion(
        self,
        page_id: str,
        theme: str,
        content: str,
        literature_review_heading: str = "Literature Review"
    ) -> str:
        """
        Write content to Notion under Literature Review > theme.

        Args:
            page_id: Notion page ID
            theme: Theme name (existing or "NEW: Theme Name")
            content: Formatted content from generate_export_content()
            literature_review_heading: Name of the Literature Review section

        Returns:
            URL of the updated page

        Raises:
            ValueError: If Literature Review heading not found
        """
        # Parse content into Notion blocks
        blocks = self._content_to_notion_blocks(content)

        # Find the Literature Review section
        page_blocks = await self.notion._get_all_blocks(page_id)
        lit_review_block = self._find_heading_block(page_blocks, literature_review_heading)

        if not lit_review_block:
            raise ValueError(
                f"Could not find '{literature_review_heading}' heading in page. "
                "Please add this heading to your Notion page first."
            )

        # Handle new theme creation
        if theme.startswith("NEW:"):
            theme_name = theme[4:].strip()  # Remove "NEW: " prefix
            theme_block = await self._create_theme_heading(
                lit_review_block["id"],
                theme_name
            )
            target_block_id = theme_block["id"]
        else:
            # Find existing theme heading
            theme_block = self._find_heading_block(
                lit_review_block.get("children", []),
                theme
            )
            if not theme_block:
                # Theme doesn't exist, create it
                theme_block = await self._create_theme_heading(
                    lit_review_block["id"],
                    theme
                )
            target_block_id = theme_block["id"]

        # Append paper entry as children of the theme toggle
        url = await self.notion.append_to_page(
            page_id=page_id,
            blocks=blocks,
            after_block_id=target_block_id
        )

        return url

    async def _create_theme_heading(
        self,
        parent_block_id: str,
        theme_name: str
    ) -> Dict:
        """Create a new theme toggle block under Literature Review (styled as H2)."""
        toggle_block = {
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": theme_name},
                    "annotations": {
                        "bold": True,
                        "color": "default"
                    }
                }],
                "color": "default",
                "children": []
            }
        }

        # Append toggle block
        response = await self.notion.notion.blocks.children.append(
            block_id=parent_block_id,
            children=[toggle_block]
        )

        return response["results"][0]

    def _find_heading_block(
        self,
        blocks: List[Dict],
        heading_text: str
    ) -> Optional[Dict]:
        """Find a heading or toggle block by text content."""
        for block in blocks:
            block_type = block.get("type", "")

            # Check headings and toggles
            if block_type in ["heading_1", "heading_2", "heading_3", "toggle"]:
                content = block.get(block_type, {})
                rich_text = content.get("rich_text", [])
                text = "".join(part.get("plain_text", "") for part in rich_text)

                if text.strip().lower() == heading_text.strip().lower():
                    return block

        return None

    def _content_to_notion_blocks(self, content: str) -> List[Dict]:
        """
        Convert plain text content to Notion blocks.

        Parses markdown-style formatting into Notion block structure.
        """
        blocks = []
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Heading (### Title)
            if line.startswith("###"):
                title_text = line[3:].strip()
                blocks.append({
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [{"type": "text", "text": {"content": title_text}}],
                        "children": []
                    }
                })

            # Bold label (**Label**:)
            elif line.startswith("**") and "**:" in line:
                # This is a label like "**Relevance**:" or "**Key insights**:"
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": self._parse_rich_text(line)
                    }
                })

            # Bullet point
            elif line.startswith("-"):
                bullet_text = line[1:].strip()
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": bullet_text}}]
                    }
                })

            # Regular paragraph
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": line}}]
                    }
                })

            i += 1

        # Nest content under toggle (first block should be toggle)
        if blocks and blocks[0].get("type") == "toggle":
            toggle_block = blocks[0]
            toggle_block["toggle"]["children"] = blocks[1:]
            return [toggle_block]

        return blocks

    def _parse_rich_text(self, text: str) -> List[Dict]:
        """Parse markdown-style bold (**text**) into Notion rich text."""
        parts = []

        # Simple bold parsing
        pattern = r'\*\*(.*?)\*\*'
        last_end = 0

        for match in re.finditer(pattern, text):
            # Add text before bold
            if match.start() > last_end:
                parts.append({
                    "type": "text",
                    "text": {"content": text[last_end:match.start()]}
                })

            # Add bold text
            parts.append({
                "type": "text",
                "text": {"content": match.group(1)},
                "annotations": {"bold": True}
            })

            last_end = match.end()

        # Add remaining text
        if last_end < len(text):
            parts.append({
                "type": "text",
                "text": {"content": text[last_end:]}
            })

        return parts if parts else [{"type": "text", "text": {"content": text}}]


# Singleton instance
_notion_exporter: Optional[NotionExporter] = None


def get_notion_exporter() -> NotionExporter:
    """
    Get singleton NotionExporter instance.

    Returns:
        NotionExporter instance
    """
    global _notion_exporter

    if _notion_exporter is None:
        _notion_exporter = NotionExporter()

    return _notion_exporter
