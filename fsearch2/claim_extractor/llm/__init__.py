"""LLM utilities for claim extraction.

Access to language models and related configuration.
"""

from claim_extractor.llm.config import (
    DEFAULT_TEMPERATURE,
    MODEL_NAME,
    MULTI_COMPLETION_TEMPERATURE,
)

__all__ = [
    # Models
    "get_llm",
    "openai_llm",
    # Config
    "MODEL_NAME",
    "DEFAULT_TEMPERATURE",
    "MULTI_COMPLETION_TEMPERATURE",
]
