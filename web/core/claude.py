"""
Claude API integration for Paper Companion Web Backend.
Handles all Claude API interactions with retry logic, rate limiting, and cost tracking.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
import logging

from anthropic import Anthropic, APIError, RateLimitError, APIConnectionError
from anthropic.types import Message

from .config import get_settings

logger = logging.getLogger(__name__)


# Model configurations
MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-5-20250929",
}

# Development mode - set to True to use haiku for all queries (cost savings)
USE_DEV_MODE = True


class TokenUsage:
    """Track token usage and costs for monitoring."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_creation_tokens = 0
        self.cache_read_tokens = 0

    def add_usage(self, usage: Any) -> None:
        """
        Add usage from API response.

        Args:
            usage: Usage object from Anthropic API response
        """
        self.input_tokens += getattr(usage, "input_tokens", 0)
        self.output_tokens += getattr(usage, "output_tokens", 0)
        self.cache_creation_tokens += getattr(usage, "cache_creation_input_tokens", 0)
        self.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0)

    def calculate_cost(self, model: str) -> float:
        """
        Calculate total cost based on token usage.
        Note: Pricing calculation removed. Check Anthropic's pricing page for current rates.

        Args:
            model: Model name

        Returns:
            Always returns 0.0 (pricing calculation removed)
        """
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
        }


class ClaudeClient:
    """
    Wrapper for Claude API with enterprise features.

    Features:
    - Automatic retry with exponential backoff
    - Rate limit handling
    - Token usage tracking and cost monitoring
    - Support for both Haiku and Sonnet models
    - PDF document analysis with prompt caching
    - Conversational query handling
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
    ):
        """
        Initialize Claude client.

        Args:
            api_key: Anthropic API key (uses settings if not provided)
            max_retries: Maximum number of retry attempts
            initial_retry_delay: Initial delay in seconds for exponential backoff
        """
        if api_key:
            self.api_key = api_key
        else:
            settings = get_settings()
            self.api_key = settings.anthropic_api_key
        self.client = Anthropic(api_key=self.api_key)
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.token_usage = TokenUsage()

    async def _retry_with_backoff(
        self,
        func,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with exponential backoff retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                # Run in thread pool since anthropic client is sync
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: func(*args, **kwargs))
                return result

            except RateLimitError as e:
                last_exception = e
                # Rate limit - use longer backoff
                delay = self.initial_retry_delay * (3 ** attempt)
                logger.warning(f"Rate limit hit, retrying in {delay}s... (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(delay)

            except APIConnectionError as e:
                last_exception = e
                # Network error - retry with exponential backoff
                delay = self.initial_retry_delay * (2 ** attempt)
                logger.warning(f"Connection error, retrying in {delay}s... (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(delay)

            except APIError as e:
                # Other API errors - check if retryable
                if e.status_code and 500 <= e.status_code < 600:
                    # Server error - retry
                    last_exception = e
                    delay = self.initial_retry_delay * (2 ** attempt)
                    logger.warning(f"Server error {e.status_code}, retrying in {delay}s... (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                else:
                    # Client error - don't retry
                    raise

            except Exception as e:
                # Unexpected error - don't retry
                logger.error(f"Unexpected error in Claude API call: {e}")
                raise

        # All retries exhausted
        logger.error(f"All {self.max_retries} retries exhausted")
        raise last_exception

    async def initial_analysis(
        self,
        pdf_path: str,
        pdf_text: str,
        max_tokens: int = 800,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Get initial analysis of paper using Claude Haiku with PDF.

        This method uses Haiku for cost-effective initial analysis.
        Supports sending full PDF text with prompt caching for efficiency.

        Args:
            pdf_path: Path to PDF file (for caching)
            pdf_text: Extracted PDF text content
            max_tokens: Maximum tokens in response

        Returns:
            Tuple of (analysis_text, usage_dict)
        """
        logger.info(f"Starting initial analysis with Haiku (text length: {len(pdf_text)} chars)")

        # Build prompt
        prompt = f"""You are a prominent senior scientist reviewing this paper. Be direct and intellectually honest.

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
{pdf_text[:100000]}"""

        # Make API call with retry logic
        response = await self._retry_with_backoff(
            self.client.messages.create,
            model=MODELS["haiku"],
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        # Track token usage
        self.token_usage.add_usage(response.usage)

        # Extract response text
        response_text = response.content[0].text if response.content else ""

        # Build usage stats
        usage_stats = {
            "model": MODELS["haiku"],
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cost": self._calculate_call_cost(response.usage, MODELS["haiku"]),
        }

        logger.info(f"Initial analysis complete. Tokens: {response.usage.input_tokens} in, {response.usage.output_tokens} out")

        return response_text, usage_stats

    async def query(
        self,
        user_query: str,
        pdf_text: str,
        conversation_history: List[Dict[str, str]],
        use_sonnet: bool = True,
        max_tokens: int = 400,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Handle conversational query about the paper.

        Args:
            user_query: User's question
            pdf_text: Full PDF text content
            conversation_history: List of previous messages [{"role": "user/assistant", "content": "..."}]
            use_sonnet: Use Sonnet (True) or Haiku (False) - ignored if USE_DEV_MODE is True
            max_tokens: Maximum tokens in response

        Returns:
            Tuple of (response_text, usage_dict)
        """
        # In dev mode, always use haiku for cost savings
        if USE_DEV_MODE:
            model = MODELS["haiku"]
        else:
            model = MODELS["sonnet"] if use_sonnet else MODELS["haiku"]
        logger.info(f"Processing query with {model} (query length: {len(user_query)} chars)")

        # Build messages
        messages = []

        # Add system context with paper content
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
{pdf_text[:100000]}"""
        })

        # Add conversation history (recent messages only)
        for msg in conversation_history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Add current query
        messages.append({
            "role": "user",
            "content": user_query
        })

        # Make API call with retry logic
        response = await self._retry_with_backoff(
            self.client.messages.create,
            model=model,
            max_tokens=max_tokens,
            temperature=0.6,
            messages=messages,
        )

        # Track token usage
        self.token_usage.add_usage(response.usage)

        # Extract response text
        response_text = response.content[0].text if response.content else ""

        # Build usage stats
        usage_stats = {
            "model": model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cost": self._calculate_call_cost(response.usage, model),
        }

        logger.info(f"Query complete. Tokens: {response.usage.input_tokens} in, {response.usage.output_tokens} out")

        return response_text, usage_stats

    async def extract_structured(
        self,
        extraction_prompt: str,
        pdf_text: str,
        conversation_context: str = "",
        max_tokens: int = 4000,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Extract structured data (JSON) from paper and conversation.

        Unlike query(), this method:
        - Uses higher token limits for complete JSON responses
        - Does not include brevity constraints
        - Is optimized for data extraction tasks

        Args:
            extraction_prompt: Prompt describing what to extract
            pdf_text: Full PDF text content
            conversation_context: Formatted conversation history for context
            max_tokens: Maximum tokens in response (default 4000 for JSON)

        Returns:
            Tuple of (response_text, usage_dict)
        """
        # In dev mode, always use haiku for cost savings
        if USE_DEV_MODE:
            model = MODELS["haiku"]
        else:
            model = MODELS["haiku"]  # Use Haiku for extraction (cost efficiency)

        logger.info(f"Extracting structured data with {model}")

        # Build messages - NO brevity constraints for extraction
        messages = []

        # System context focused on accurate extraction
        system_content = """You are analyzing a research paper and extracting structured insights.

Your task is to extract information and return it as valid JSON.
Be thorough and complete - include all relevant information.
Focus on accuracy and completeness over brevity."""

        # Add paper content if provided
        if pdf_text:
            system_content += f"\n\nPaper content:\n{pdf_text[:100000]}"

        # Add conversation context if provided
        if conversation_context:
            system_content += f"\n\nConversation context:\n{conversation_context}"

        messages.append({
            "role": "user",
            "content": system_content
        })

        # Add extraction prompt
        messages.append({
            "role": "user",
            "content": extraction_prompt
        })

        # Make API call with retry logic
        response = await self._retry_with_backoff(
            self.client.messages.create,
            model=model,
            max_tokens=max_tokens,
            temperature=0.3,  # Lower temperature for structured output
            messages=messages,
        )

        # Track token usage
        self.token_usage.add_usage(response.usage)

        # Extract response text
        response_text = response.content[0].text if response.content else ""

        # Build usage stats
        usage_stats = {
            "model": model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cost": self._calculate_call_cost(response.usage, model),
        }

        logger.info(f"Extraction complete. Tokens: {response.usage.input_tokens} in, {response.usage.output_tokens} out")

        return response_text, usage_stats

    def _calculate_call_cost(self, usage: Any, model: str) -> float:
        """
        Calculate cost for a single API call.
        Note: Pricing calculation removed. Check Anthropic's pricing page for current rates.
        """
        return 0.0

    def get_total_usage(self) -> Dict[str, Any]:
        """
        Get total token usage and cost for this client instance.

        Returns:
            Dictionary with usage stats and cost
        """
        return {
            **self.token_usage.to_dict(),
            "cost_estimate": self.token_usage.calculate_cost(MODELS["sonnet"]),  # Conservative estimate
        }

    def reset_usage(self) -> None:
        """Reset token usage tracking."""
        self.token_usage = TokenUsage()


# Convenience functions for dependency injection
_claude_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """
    Get global Claude client instance (singleton pattern).

    Returns:
        ClaudeClient: Configured Claude client
    """
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client


async def initial_analysis(pdf_path: str, pdf_text: str) -> Tuple[str, Dict[str, Any]]:
    """Convenience function for initial analysis."""
    client = get_claude_client()
    return await client.initial_analysis(pdf_path, pdf_text)


async def query(
    user_query: str,
    pdf_text: str,
    conversation_history: List[Dict[str, str]],
    use_sonnet: bool = True,
) -> Tuple[str, Dict[str, Any]]:
    """Convenience function for queries."""
    client = get_claude_client()
    return await client.query(user_query, pdf_text, conversation_history, use_sonnet)
