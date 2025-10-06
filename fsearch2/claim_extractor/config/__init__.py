"""Configuration for the claim extractor.

Central storage for all configuration settings.
"""

from claim_extractor.config.nodes import (
    CONTEXT_WINDOWS,
    DECOMPOSITION_CONFIG,
    DISAMBIGUATION_CONFIG,
    SELECTION_CONFIG,
    VALIDATION_CONFIG,
)

__all__ = [
    # Node configurations
    "SELECTION_CONFIG",
    "DISAMBIGUATION_CONFIG",
    "DECOMPOSITION_CONFIG",
    "VALIDATION_CONFIG",
    # Context windows
    "CONTEXT_WINDOWS",
]
