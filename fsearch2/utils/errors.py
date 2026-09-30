"""Errors that must reach the user instead of being handled by node fallbacks.

Import as `from utils.errors import ...` everywhere: the codebase is importable both
as `utils` and `fsearch2.utils`, which would create two distinct exception classes.
"""


class CreditsExhaustedError(Exception):
    """An external API (OpenAI, Serper) has no credits left for our account."""

    def __init__(self, provider: str, detail: str = ""):
        self.provider = provider  # "openai" or "serper"
        self.detail = detail
        super().__init__(f"No {provider} credits available: {detail}" if detail else f"No {provider} credits available")
