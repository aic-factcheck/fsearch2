"""Claim Verifier - Verify factual claims against external evidence.

A pipeline for evaluating the accuracy of factual claims using web searches.
"""

from claim_verifier.agent import create_graph, graph
from claim_verifier.schemas import (
    Evidence,
    Verdict,
    ClaimVerifierState,
    VerificationResult,
    IntermediateAssessment,
)

__all__ = [
    # Main functionality
    "create_graph",
    "graph",
    # Data models
    "ClaimVerifierState",
    "Evidence",
    "Verdict",
    "VerificationResult",
    "IntermediateAssessment",
]
