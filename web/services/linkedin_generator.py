"""
LinkedIn post generation service for Scholia.
Generates LinkedIn-style posts from session insights that avoid LLM patterns.
"""

from typing import Dict, Optional, List
import logging

from ..core.claude import get_claude_client

logger = logging.getLogger(__name__)


# Voice samples - Bennett's authentic voice for matching tone and style
VOICE_SAMPLES = """
SAMPLE 1 - Technical Discussion (Email):
"I just wanted to clarify one item. The current workflow removes all ICD codes occurring between days -7 to +30 before identifying the earliest post-index PASC occurrence, meaning that many participants identified as having new PASC category codes after the index_date could have had their first incident PASC codes between days 0 and 30. In other words, this identifies people who have incident PASC codes after day 0, not day 30. Just wanted to make sure that was the intended functionality.

Most PASC codes occur at the index date, which aligns with our finding that providers often code for Long COVID and acute COVID simultaneously. This plot shows when long COVID ICD codes occur relative to detected COVID infection. We took this to indicate that providers are coding patients for long COVID and COVID at the same time in many instances, and overall, it might look different in your dataset but just wanted to call that to attention in case you see similar patterns."

Key elements of this sample:
- Opens with acknowledgment of their work
- Frames observation as clarification, not criticism
- Provides concrete data to support the point
- Explains implications clearly
- Ends by noting this may be dataset-specific

SAMPLE 2 - Sharing Findings (Email):
"Sorry it took a while to run this in All of Us, but the short answer is that I don't think we'll see a difference.

A thorough handling of this would likely require a target trial emulation to create a rigorous matched cohort that was subject to bias, so I did an incomplete but quick analysis this weekend to see if crude food allergy/intolerance incidence was higher than that in a cohort matched simply on age and length of EHR data available.

I found 4081 participants on PrEP without prior food allergy. In this group, food allergy developed in 45, resulting in an incidence rate of 2.20 per 1,000 person-years (95% CI: 1.60 - 2.94). I matched this with a group of 33249 not on PrEP and without food allergy diagnosis in their first year of EHR data. 404 developed food allergies, which was an incidence rate of 2.12 per 1,000 person-years. This results in a crude hazard ratio of 1.04, which is well below minimum detectable HR for the PrEP cohort (1.63) with its current size and incidence.

Sorry it probably won't be helpful for the paper. If it turns out that a null result would be helpful (or if there are any other scenarios you'd be interested in) let me know and we could always turn this into a more robust analysis!"

Key elements of this sample:
- Upfront with the disappointing finding
- Acknowledges analysis limitations honestly
- Presents data clearly with appropriate statistics
- Apologizes for negative result but offers constructive alternatives
- Maintains collaborative tone despite null finding

SAMPLE 3 - Narrative Building (Speech):
"Three years have passed since I came to Chicago for residency, and as I reflect on who I am as a growing physician, I'm struck by just how much the doctor I try to be is a product of my resident mentors.

On my hardest intern rotation - the Medical ICU - I was lucky to have Danny as my senior. Here, I learned that a Lucent outpatient scholar could also be a calm, confident, adept, and - important for me - patient senior in the critical care unit as well. Danny taught me how to think critically and deeply about sick patients, in him I saw a man always aware of his own limits, asking for help when needed, and most importantly, he never neglected the humanity of the person attached to the ventilator or IVs."

Key elements of this sample:
- Opens with self-aware humor
- Uses specific, concrete examples to illustrate abstract qualities
- Builds narrative through accumulated detail
- Shows rather than tells (uses actual examples as evidence)
- Maintains warmth without being saccharine

SAMPLE 4 - Reflective Analysis (Personal Statement):
"As I reflect on this training, and look forward to a combined Med-Peds Infectious Diseases Fellowship rooted in primary research, I feel confident in the progress I've made as a clinician, and proud of the work I will be presenting at the American Thoracic Society conference in May, but I can still see gaps in my training when it comes to outcomes research methods.

While these projects in basic and clinical research differ drastically, they are united by an interest in using data and computer programming to identify differences that are otherwise difficult to appreciate. In fellowship, I hope to continue this strategy by using big data to identify or exclude infections earlier than we can by clinical gestalt and lab tests alone.

Another aspect that unites these projects, is that while I feel confident in basic research methods, I have always relied on collaboration for statistical analysis and clinical trial design."

Key elements of this sample:
- Balances confidence with acknowledged limitations
- Connects disparate experiences thematically
- Explicitly names what needs development
- Closes with forward-looking perspective
- Formal but retains personal voice

VOICE CHARACTERISTICS TO MATCH:
- Technical precision with accessibility: Uses domain terminology correctly but explains clearly
- Substantive without excess: Direct and concise, no unnecessary preamble
- Appropriately humble: Acknowledges limitations, offers alternatives vs overconfident claims
- Pedagogical: Explains WHY things matter, not just WHAT they are
- Collaborative tone: Points out considerations without being pedantic
- Varied sentence length: Mix of longer analytical sentences with shorter declarative ones
- Natural imperfections: Occasional fragments or conversational constructions that feel authentic

USAGE GUIDELINES - When drafting as Bennett:
1. Lead with substance: Avoid long preambles or excessive formatting
2. Use specifics: Concrete examples > abstract descriptions
3. Acknowledge uncertainty: "I think", "it seems", "might be" when appropriate
4. Offer alternatives: Don't just identify problems, suggest paths forward
5. Stay collaborative: Frame critiques as clarifications or considerations
6. Explain implications: Don't just present data, interpret what it means
"""


class LinkedInGenerator:
    """
    Generates LinkedIn posts from session insights.

    Focuses on creating authentic-sounding posts that:
    - Avoid common LLM patterns
    - Match user's voice and style
    - Work within LinkedIn's preview constraints
    """

    def __init__(
        self,
        claude_client=None,
        model: str = "claude-sonnet-4-5-20250929"
    ):
        """
        Initialize LinkedIn generator.

        Args:
            claude_client: Optional ClaudeClient instance
            model: Claude model to use (default: Sonnet for quality)
        """
        self.claude = claude_client or get_claude_client()
        self.model = model

    async def generate_linkedin_post(
        self,
        insights: Dict,
        voice_samples: Optional[str] = None
    ) -> Dict:
        """
        Generate LinkedIn post from session insights.

        Args:
            insights: Session insights dictionary from extract_insights()
            voice_samples: Optional voice samples (uses default if not provided)

        Returns:
            {
                "hook": "First 1-2 sentences",
                "body": "Full post text with [PAPER LINK] placeholder",
                "endings": {
                    "question": "...",
                    "declarative": "...",
                    "forward_looking": "..."
                },
                "full_post_options": ["body + each ending variant"]
            }
        """
        logger.info("Generating LinkedIn post from insights")

        # Use provided voice samples or default
        voice_text = voice_samples or VOICE_SAMPLES

        # Extract key components from insights
        summary = insights.get("summary", "")
        learnings = insights.get("learnings", [])
        assessment = insights.get("assessment", {})
        open_questions = insights.get("open_questions", [])
        bibliographic = insights.get("bibliographic", {})

        # Build generation prompt
        prompt = self._build_generation_prompt(
            summary=summary,
            learnings=learnings,
            assessment=assessment,
            open_questions=open_questions,
            bibliographic=bibliographic,
            voice_samples=voice_text
        )

        # Call Claude to generate post
        response_text, usage = await self.claude.extract_structured(
            extraction_prompt=prompt,
            pdf_text="",  # No PDF needed - working from insights
            conversation_context="",
            max_tokens=1500  # Enough for post + multiple endings
        )

        # Parse response into structured format
        post_data = self._parse_post_response(response_text)

        # Build full post options (body + each ending)
        full_options = self._build_full_post_options(
            body=post_data.get("body", ""),
            endings=post_data.get("endings", {}),
            sign_off="\n\n[I've been reading papers with Scholia, a tool I built for critical paper analysis.]"
        )
        post_data["full_post_options"] = full_options

        logger.info("LinkedIn post generated successfully")

        return post_data

    def _build_generation_prompt(
        self,
        summary: str,
        learnings: List[str],
        assessment: Dict,
        open_questions: List[str],
        bibliographic: Dict,
        voice_samples: str
    ) -> str:
        """Build the generation prompt for LinkedIn post."""

        # Format assessment
        strengths = assessment.get("strengths", [])
        limitations = assessment.get("limitations", [])

        assessment_text = ""
        if strengths:
            assessment_text += "Strengths:\n" + "\n".join(f"- {s}" for s in strengths)
        if limitations:
            if assessment_text:
                assessment_text += "\n\n"
            assessment_text += "Limitations:\n" + "\n".join(f"- {l}" for l in limitations)

        # Format learnings
        learnings_text = "\n".join(f"- {l}" for l in learnings) if learnings else "None"

        # Format open questions
        questions_text = "\n".join(f"- {q}" for q in open_questions) if open_questions else "None"

        # Format paper info
        paper_info = f"Title: {bibliographic.get('title', 'Unknown')}"
        if bibliographic.get('authors'):
            paper_info += f"\nAuthors: {bibliographic['authors']}"
        if bibliographic.get('year'):
            paper_info += f"\nYear: {bibliographic['year']}"

        prompt = f"""Generate a LinkedIn post from these paper insights. The post should start with "What I'm Reading: " followed by a newline.

PAPER INFORMATION:
{paper_info}

SUMMARY:
{summary}

WHAT THE READER LEARNED:
{learnings_text}

PAPER ASSESSMENT:
{assessment_text}

OPEN QUESTIONS:
{questions_text}

VOICE SAMPLES (match this tone and style - notice sentence rhythm, formality level, technical concept introduction):
{voice_samples}

REQUIREMENTS:

1. STRUCTURE:
   - Hook: First 1-2 sentences that work as LinkedIn preview (LinkedIn truncates early)
   - Body: 150-300 words total, first-person, warm but substantive
   - Include placeholder: [PAPER LINK] where citation should go
   - Generate 3 alternative endings separately (don't include in body):
     a) question: Invites discussion with a question/call to action
     b) declarative: Clean declarative close
     c) forward_looking: "I'm curious to explore..." style

2. CONTENT FOCUS:
   - Draw primarily from "What the Reader Learned" (what they engaged with, connections made)
   - Use summary bottom line for context
   - Focus on ONE to THREE insights or tensions, not comprehensive summary
   - Feel like sharing a thought, not reviewing a paper

3. ANTI-LLM-PATTERN CONSTRAINTS (critical):
   - No emojis
   - No "Here's the thing:" or "Let's dive in" or similar
   - No exactly-three-part structure
   - No "This paper is a must-read for anyone interested in..."
   - Vary sentence length; allow fragments
   - Don't start with "I just read..." (too common)
   - Don't end every paragraph with a rhetorical question
   - Allowed to be slightly unpolished - that reads as authentic
   - Avoid too many em-dashes
   - Don't use obvious AI phrases

4. TONE:
   - Match the voice samples provided
   - First-person, warm but substantive
   - Sounds like a real person sharing an interesting finding
   - Not overly polished or formal

Return ONLY a JSON object with this structure:
{{
  "hook": "First 1-2 sentences for LinkedIn preview",
  "body": "Full post body (150-300 words) with [PAPER LINK] placeholder. DO NOT include the ending here.",
  "endings": {{
    "question": "Question/call to action ending",
    "declarative": "Clean declarative ending",
    "forward_looking": "Forward-looking ending starting with curiosity"
  }}
}}

IMPORTANT: The body should NOT include any of the endings. They will be added by the user's selection.
"""

        return prompt

    def _parse_post_response(self, response_text: str) -> Dict:
        """Parse Claude's response into structured post data."""
        import json
        import re

        try:
            # Look for JSON block in response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                post_data = json.loads(json_match.group())
            else:
                post_data = json.loads(response_text)

            # Validate structure
            if not all(k in post_data for k in ["hook", "body", "endings"]):
                raise ValueError("Missing required keys in response")

            return post_data

        except (json.JSONDecodeError, AttributeError, ValueError) as e:
            logger.error(f"Failed to parse LinkedIn post response: {e}")
            # Return fallback structure
            return {
                "hook": "I've been exploring an interesting paper.",
                "body": "The insights have given me a lot to think about. [PAPER LINK]",
                "endings": {
                    "question": "What are your thoughts on this approach?",
                    "declarative": "Looking forward to seeing how this develops.",
                    "forward_looking": "I'm curious to explore the implications further."
                },
                "error": f"Failed to parse response: {str(e)}"
            }

    def _build_full_post_options(
        self,
        body: str,
        endings: Dict,
        sign_off: str
    ) -> List[str]:
        """Build full post options by combining body with each ending."""

        full_posts = []

        for ending_type, ending_text in endings.items():
            # Combine body + ending + sign-off
            full_post = body.strip()

            # Add ending with appropriate spacing
            if ending_text:
                full_post += f"\n\n{ending_text.strip()}"

            # Add sign-off
            full_post += sign_off

            full_posts.append(full_post)

        return full_posts


# Singleton instance
_linkedin_generator: Optional[LinkedInGenerator] = None


def get_linkedin_generator(
    claude_client=None,
    model: str = "claude-sonnet-4-5-20250929"
) -> LinkedInGenerator:
    """
    Get singleton LinkedInGenerator instance.

    Args:
        claude_client: Optional ClaudeClient instance
        model: Claude model to use

    Returns:
        LinkedInGenerator instance
    """
    global _linkedin_generator

    if _linkedin_generator is None:
        _linkedin_generator = LinkedInGenerator(
            claude_client=claude_client,
            model=model
        )

    return _linkedin_generator
