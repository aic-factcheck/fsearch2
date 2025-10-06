"""Generate search queries node - creates effective search queries for claims.

Generates optimized queries to find evidence related to a claim.
"""

import logging
from typing import Dict

from pydantic import BaseModel, Field

from claim_verifier.prompts import (
    QUERY_GENERATION_HUMAN_PROMPT,
    QUERY_GENERATION_INITIAL_SYSTEM_PROMPT,
    QUERY_GENERATION_ITERATIVE_SYSTEM_PROMPT,
    get_current_timestamp,
)
from claim_verifier.schemas import ClaimVerifierState
from utils import get_llm, call_llm_with_structured_output

logger = logging.getLogger(__name__)


class QueryGenerationOutput(BaseModel):
    """Search query generation response.

    Generates optimized search queries designed to find comprehensive evidence
    for fact-checking claims. The query should be crafted to retrieve both
    supporting and contradictory evidence from reliable sources.
    """

    query: str = Field(
        description="An optimized search query that: (1) includes key entities and specific details from the claim, (2) uses search-friendly terms without special characters, (3) is formulated to find both supporting AND refuting evidence, (4) targets authoritative sources and fact-checking organizations when relevant"
    )


async def generate_search_query_node(
    state: ClaimVerifierState,
) -> Dict[str, str]:
    """Generate an effective search query for a claim."""

    claim = state.claim
    iteration_count = state.iteration_count
    all_queries = state.all_queries
    intermediate_assessment = state.intermediate_assessment

    logger.info(
        f"Generating search query for claim: '{claim.claim_text}' "
        f"(Iteration: {iteration_count + 1})"
    )

    llm = get_llm()

    # Build context for iterative searching
    context_parts = []

    if iteration_count > 0 and all_queries:
        context_parts.append(f"Previous queries: {', '.join(all_queries)}")

    if intermediate_assessment and intermediate_assessment.missing_aspects:
        context_parts.append(
            f"Missing aspects: {', '.join(intermediate_assessment.missing_aspects)}"
        )

    context = " | ".join(context_parts) if context_parts else ""

    current_time = get_current_timestamp()

    system_prompt = (
        QUERY_GENERATION_INITIAL_SYSTEM_PROMPT.format(current_time=current_time)
        if iteration_count == 0
        else QUERY_GENERATION_ITERATIVE_SYSTEM_PROMPT.format(
            iteration_count=iteration_count + 1,
            context=context,
            current_time=current_time,
        )
    )
    human_prompt = QUERY_GENERATION_HUMAN_PROMPT.format(claim_text=claim.claim_text)
    messages = [("system", system_prompt), ("human", human_prompt)]

    response = await call_llm_with_structured_output(
        llm=llm,
        output_class=QueryGenerationOutput,
        messages=messages,
        context_desc=f"query generation for claim '{claim.claim_text}'",
    )

    if not response or not response.query:
        logger.warning(f"Failed to generate query for claim: '{claim.claim_text}'")
        return {"query": claim.claim_text}

    logger.info(f"Generated search query: {response.query}")

    return {"query": response.query, "all_queries": all_queries + [response.query]}
