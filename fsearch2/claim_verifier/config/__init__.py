"""Configuration for the claim verifier.

Central storage for all configuration settings.
"""

from claim_verifier.config.nodes import (
    QUERY_GENERATION_CONFIG,
    EVIDENCE_RETRIEVAL_CONFIG,
    EVIDENCE_EVALUATION_CONFIG,
    ITERATIVE_SEARCH_CONFIG,
)

__all__ = [
    # Node configurations
    "QUERY_GENERATION_CONFIG",
    "EVIDENCE_RETRIEVAL_CONFIG",
    "EVIDENCE_EVALUATION_CONFIG",
    "ITERATIVE_SEARCH_CONFIG",
]
