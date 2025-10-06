"""Evaluate evidence node - determines claim validity based on evidence.

Analyzes evidence snippets to assess if a claim is supported, refuted, or inconclusive.
"""

import logging

from claim_verifier.schemas import (
    ClaimVerifierState,
)

logger = logging.getLogger(__name__)


async def return_evidence_node(state: ClaimVerifierState) -> dict:
    return state.model_dump()
