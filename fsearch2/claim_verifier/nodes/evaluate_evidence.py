"""Evaluate evidence node - determines claim validity based on evidence.

Analyzes evidence snippets to assess if a claim is supported, refuted, or inconclusive.
"""

import logging
from typing import List

from pydantic import BaseModel, Field
from utils import (
    call_llm_with_structured_output,
    get_llm,
    truncate_evidence_for_token_limit,
)

from claim_verifier.prompts import (
    EVIDENCE_EVALUATION_HUMAN_PROMPT,
    EVIDENCE_EVALUATION_SYSTEM_PROMPT,
    get_current_timestamp,
)
from claim_verifier.schemas import (
    ClaimVerifierState,
    Evidence,
    Verdict,
    VerificationResult,
)

logger = logging.getLogger(__name__)


class EvidenceEvaluationOutput(BaseModel):
    verdict: VerificationResult = Field(
        description="The final fact-checking verdict. Use 'Supported' only when evidence clearly and consistently supports the claim from reliable sources. Use 'Refuted' when evidence clearly contradicts the claim with authoritative sources. Use 'Insufficient Information' when evidence is limited, unclear, or not comprehensive enough for a definitive conclusion. Use 'Conflicting Evidence' when reliable sources provide contradictory information about the claim."
    )
    reasoning: str = Field(
        description="Clear, concise reasoning for the verdict (1-2 sentences). Explain what specific evidence led to this conclusion, mentioning the reliability of sources and any limitations in the evidence. Avoid speculation and base reasoning strictly on the provided evidence."
    )
    influential_source_indices: List[int] = Field(
        description="1-based indices of the evidence sources that were most important in reaching this verdict. These sources will be marked for prominent display in the user interface while all sources remain visible. For 'Supported' and 'Refuted' verdicts, include sources that directly support the decision. For 'Insufficient Information' and 'Conflicting Evidence' verdicts, include the most relevant sources that were considered. Select 2-4 of the most critical sources.",
        default_factory=list,
    )


def _format_evidence_snippets(snippets: List[Evidence]) -> str:
    if not snippets:
        return "No relevant evidence snippets were found."

    return "\n\n".join(
        [
            f"Source {i + 1}: {s.url}\n"
            + (f"Title: {s.title}\n" if s.title else "")
            + f"Snippet: {s.text.strip()}\n---"
            for i, s in enumerate(snippets)
        ]
    )


async def evaluate_evidence_node(state: ClaimVerifierState) -> dict:
    claim = state.claim
    evidence_snippets = state.evidence
    iteration_count = state.iteration_count

    logger.info(
        f"Final evaluation for claim '{claim.claim_text}' "
        f"with {len(evidence_snippets)} evidence snippets "
        f"after {iteration_count} iterations"
    )

    system_prompt = EVIDENCE_EVALUATION_SYSTEM_PROMPT.format(
        current_time=get_current_timestamp()
    )

    truncated_evidence = truncate_evidence_for_token_limit(
        evidence_items=evidence_snippets,
        claim_text=claim.claim_text,
        system_prompt=system_prompt,
        human_prompt_template=EVIDENCE_EVALUATION_HUMAN_PROMPT,
        format_evidence_func=_format_evidence_snippets,
    )

    messages = [
        ("system", system_prompt),
        (
            "human",
            EVIDENCE_EVALUATION_HUMAN_PROMPT.format(
                claim_text=claim.claim_text,
                evidence_snippets=_format_evidence_snippets(truncated_evidence),
            ),
        ),
    ]

    llm = get_llm(model_name="openai:gpt-5")

    response = await call_llm_with_structured_output(
        llm=llm,
        output_class=EvidenceEvaluationOutput,
        messages=messages,
        context_desc=f"evidence evaluation for claim '{claim.claim_text}'",
    )

    if not response:
        logger.warning(f"Failed to evaluate evidence for claim: '{claim.claim_text}'")
        verdict = Verdict(
            claim_text=claim.claim_text,
            disambiguated_sentence=claim.disambiguated_sentence,
            original_sentence=claim.original_sentence,
            original_index=claim.original_index,
            result=VerificationResult.REFUTED,
            reasoning="Failed to evaluate the evidence due to technical issues.",
            sources=[],
        )
    else:
        try:
            result = VerificationResult(response.verdict)
        except ValueError:
            logger.warning(
                f"Invalid verdict '{response.verdict}', defaulting to REFUTED"
            )
            result = VerificationResult.REFUTED

        influential_urls = (
            {
                truncated_evidence[idx - 1].url
                for idx in response.influential_source_indices
                if 1 <= idx <= len(truncated_evidence)
            }
            if response.influential_source_indices
            else set()
        )

        sources = [
            Evidence(
                url=source.url,
                text=source.text,
                title=source.title,
                is_influential=source.url in influential_urls,
            )
            for source in {source.url: source for source in evidence_snippets}.values()
        ]

        verdict = Verdict(
            claim_text=claim.claim_text,
            disambiguated_sentence=claim.disambiguated_sentence,
            original_sentence=claim.original_sentence,
            original_index=claim.original_index,
            result=result,
            reasoning=response.reasoning,
            sources=sources,
        )

    # Log final result
    influential_count = sum(source.is_influential for source in verdict.sources)
    logger.info(
        f"Verdict '{verdict.result}' for '{claim.claim_text}': {verdict.reasoning} "
        f"({len(verdict.sources)} sources, {influential_count} influential)"
    )

    return {"verdict": verdict}
 