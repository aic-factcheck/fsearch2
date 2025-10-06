"""LLM utilities for claim verification.

Access to language models and related configuration.
"""

from claim_verifier.llm.config import DEFAULT_TEMPERATURE, MODEL_NAME

__all__ = [
    # Models
    "get_llm",
    # Config
    "MODEL_NAME",
    "DEFAULT_TEMPERATURE",
]
