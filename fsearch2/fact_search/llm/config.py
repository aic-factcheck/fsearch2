"""LLM configuration constants.

Central settings for language model behavior.
"""

# Model selection - use the same model as claim_extractor for consistency
MODEL_NAME = "openai:gpt-5-mini"

# Temperature settings
DEFAULT_TEMPERATURE = 0.0  # Use for exact, consistent outputs (no randomness)
