"""Unified LLM model instances and factory functions.

Provides access to configured language model instances for all modules.
"""

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from utils.settings import settings


def get_llm(
    model_name: str = "openai:gpt-5-mini",
    temperature: float = 0.0,
    completions: int = 1,
) -> BaseChatModel:
    """Get LLM with specified configuration.

    Args:
        model_name: The model to use
        temperature: Temperature for generation
        completions: How many completions we need (affects temperature for diversity)

    Returns:
        Configured LLM instance
    """
    # Use higher temp when doing multiple completions for diversity
    if completions > 1 and temperature == 0.0:
        temperature = 0.2

    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not found in environment variables")

    return init_chat_model(
        model=model_name,
        api_key=settings.openai_api_key#,
        #temperature=temperature if model_name.startswith("openai:gpt") else None,
    )


def get_default_llm() -> BaseChatModel:
    """Get default LLM instance."""
    return get_llm()
