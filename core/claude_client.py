import anthropic
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from core.config import settings


class ClaudeClient:
    """
    Central Claude API client used by all SYN Systems agents.
    Wraps Anthropic SDK with retry logic, logging, and token tracking.
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.total_tokens_used = 0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def chat(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Single-turn chat with Claude."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        usage = response.usage
        self.total_tokens_used += usage.input_tokens + usage.output_tokens
        logger.debug(
            f"Claude used {usage.input_tokens} input / {usage.output_tokens} output tokens"
        )
        return response.content[0].text

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def chat_with_history(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Multi-turn conversation with message history."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=messages,
        )
        usage = response.usage
        self.total_tokens_used += usage.input_tokens + usage.output_tokens
        return response.content[0].text

    def stream_chat(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
    ):
        """Streaming response — yields text chunks."""
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    def classify(
        self,
        text: str,
        categories: list[str],
        context: Optional[str] = None,
    ) -> str:
        """Classify text into one of the provided categories."""
        categories_str = ", ".join(f'"{c}"' for c in categories)
        system = (
            f"You are a precise classifier. Classify the input into exactly one of these categories: {categories_str}. "
            f"{'Context: ' + context if context else ''} "
            "Reply with ONLY the category name, nothing else."
        )
        result = self.chat(system_prompt=system, user_message=text, max_tokens=50, temperature=0.0)
        result = result.strip().strip('"')
        if result not in categories:
            logger.warning(f"Classifier returned unexpected category '{result}', defaulting to first.")
            return categories[0]
        return result

    def extract_json(self, system_prompt: str, user_message: str, max_tokens: int = 1024) -> str:
        """Ask Claude to return valid JSON only."""
        full_system = system_prompt + "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no explanation."
        return self.chat(system_prompt=full_system, user_message=user_message, max_tokens=max_tokens, temperature=0.0)


claude = ClaudeClient()
