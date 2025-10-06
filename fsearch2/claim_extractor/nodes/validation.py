"""Validation node - verifies claims are properly formed sentences.

Makes sure claims are complete declarative sentences ready for fact-checking.
"""

import asyncio
import logging
from typing import Dict, Sequence

from pydantic import BaseModel, Field
from claim_extractor.prompts import VALIDATION_HUMAN_PROMPT, VALIDATION_SYSTEM_PROMPT
from claim_extractor.schemas import PotentialClaim, State, ValidatedClaim
from utils import get_llm, call_llm_with_structured_output

logger = logging.getLogger(__name__)


class ValidationOutput(BaseModel):
    """Response schema for validation LLM calls."""

    is_complete_declarative: bool = Field(
        description="Whether the claim is a complete declarative sentence"
    )


async def _validate_claim(potential_claim: PotentialClaim) -> ValidatedClaim:
    """Check if a claim is a properly formed complete sentence.

    Args:
        potential_claim: Claim to validate

    Returns:
        Validation result
    """
    logger.debug(f"Validating claim: '{potential_claim.claim_text}'")

    messages = [
        ("system", VALIDATION_SYSTEM_PROMPT),
        ("human", VALIDATION_HUMAN_PROMPT.format(claim=potential_claim.claim_text)),
    ]

    # Use zero-temp LLM for consistent results
    llm = get_llm()  # Uses default temperature for consistent results

    # Call the LLM
    response = await call_llm_with_structured_output(
        llm=llm,
        output_class=ValidationOutput,
        messages=messages,
        context_desc=f"validation of claim '{potential_claim.claim_text}'",
    )

    # Check if valid
    is_valid = False
    if response and response.is_complete_declarative:
        is_valid = True

    log_level = logging.INFO if is_valid else logging.WARNING
    logger.log(
        log_level,
        f"Claim validation {'succeeded' if is_valid else 'failed'}: '{potential_claim.claim_text}'",
    )

    # Return result
    return ValidatedClaim(
        claim_text=potential_claim.claim_text,
        is_complete_declarative=is_valid,
        disambiguated_sentence=potential_claim.disambiguated_sentence,
        original_sentence=potential_claim.original_sentence,
        original_index=potential_claim.original_index,
    )


async def validation_node(state: State) -> Dict[str, Sequence[ValidatedClaim]]:
    """Validate claims as complete, properly formed sentences.

    Args:
        state: Current workflow state

    Returns:
        Dictionary with validated_claims key
    """
    potential_claims = state.potential_claims or []

    if not potential_claims:
        logger.warning("No claims to validate")
        return {}

    # Validate all claims in parallel
    validation_results = await asyncio.gather(
        *[_validate_claim(claim) for claim in potential_claims]
    )

    # Filter out invalid and duplicate claims
    validated_claims = []
    seen_claims = set()

    for validated in validation_results:
        if (
            validated.is_complete_declarative
            and validated.claim_text not in seen_claims
        ):
            validated_claims.append(validated)
            seen_claims.add(validated.claim_text)
            logger.info(f"Valid claim: '{validated.claim_text}'")
        else:
            reason = (
                "invalid format"
                if not validated.is_complete_declarative
                else "duplicate"
            )
            logger.info(f"Discarded claim ({reason}): '{validated.claim_text}'")

    logger.info(f"Validated {len(validated_claims)} of {len(potential_claims)} claims")
    return {"validated_claims": validated_claims}
