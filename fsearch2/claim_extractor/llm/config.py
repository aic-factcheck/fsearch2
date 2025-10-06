"""LLM configuration constants.

Central settings for language model behavior.
"""

# Model selection
MODEL_NAME = "openai:gpt-5-mini"

# Temperature settings
DEFAULT_TEMPERATURE = 0.0  # Use for exact, consistent outputs
MULTI_COMPLETION_TEMPERATURE = 0.2  # Use for voting with diverse outputs
