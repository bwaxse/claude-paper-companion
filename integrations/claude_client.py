"""
Claude API integration for Paper Companion
"""

from typing import Dict, List, Optional

from anthropic import Anthropic
from rich.console import Console

from utils.helpers import format_authors

console = Console()


class ClaudeClient:
    """Handles all Claude API interactions"""

    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        """
        Initialize Claude client.

        Args:
            model: Claude model to use
        """
        self.anthropic = Anthropic()
        self.model = model

    def get_initial_summary(
        self,
        pdf_content: str,
        pdf_images: List[Dict],
        zotero_item: Optional[Dict] = None
    ) -> str:
        """
        Get Claude's concise summary of the paper.

        Args:
            pdf_content: Extracted PDF text
            pdf_images: List of extracted images
            zotero_item: Optional Zotero metadata

        Returns:
            Summary text
        """
        console.print("[cyan]Analyzing paper...[/cyan]")

        # Include Zotero metadata if available
        context = ""
        if zotero_item:
            data = zotero_item['data']
            context = f"""This paper is already in your Zotero library with:
- Title: {data.get('title', 'Unknown')}
- Authors: {format_authors(data.get('creators', []))}
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
{pdf_content[:100000]}"""
            }
        ]

        # Add figures
        for img in pdf_images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img["type"],
                    "data": img["data"]
                }
            })

        response = self.anthropic.messages.create(
            model=self.model,
            max_tokens=800,  # Keep it concise
            messages=[{"role": "user", "content": content}]
        )

        return response.content[0].text

    def get_full_critical_review(
        self,
        pdf_content: str,
        pdf_images: List[Dict],
        zotero_item: Optional[Dict] = None
    ) -> str:
        """
        Get Claude's critical analysis of the paper.

        Args:
            pdf_content: Extracted PDF text
            pdf_images: List of extracted images (first 6 used)
            zotero_item: Optional Zotero metadata

        Returns:
            Critical review text
        """
        console.print("[cyan]Performing critical analysis...[/cyan]")

        # Include Zotero metadata if available
        context = ""
        if zotero_item:
            data = zotero_item['data']
            context = f"""This paper is already in your Zotero library with:
- Title: {data.get('title', 'Unknown')}
- Authors: {format_authors(data.get('creators', []))}
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

{pdf_content[:100000]}
"""
            }
        ]

        # Add first few images
        for img in pdf_images[:6]:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img["type"],
                    "data": img["data"]
                }
            })

        response = self.anthropic.messages.create(
            model=self.model,
            max_tokens=2500,
            messages=[{"role": "user", "content": content}]
        )

        return response.content[0].text

    def get_response(
        self,
        user_input: str,
        pdf_content: str,
        conversation_history: List[Dict]
    ) -> str:
        """
        Get Claude's response to user question.

        Args:
            user_input: User's question
            pdf_content: PDF content
            conversation_history: Recent conversation messages

        Returns:
            Claude's response
        """
        # Build conversation context
        messages = []

        # Add paper context
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

LENGTH REQUIREMENT - CRITICAL:
- Maximum 1-2 SHORT paragraphs per response
- NO fancy formatting, headers, boxes, or tables
- If the topic is complex, give a brief answer and say "Ask if you want details on X"
- The user will ask follow-ups if they want more depth
- Brevity > completeness

Point to specific sections/figures when relevant.

Paper content:
{pdf_content[:100000]}"""
        })

        # Add conversation history (recent)
        for msg in conversation_history[-10:]:
            messages.append(msg)

        # Add current question
        messages.append({"role": "user", "content": user_input})

        response = self.anthropic.messages.create(
            model=self.model,
            max_tokens=400,  # Enforce brevity
            temperature=0.6,
            messages=messages
        )

        return response.content[0].text
