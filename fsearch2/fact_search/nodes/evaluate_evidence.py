"""Evaluate evidence node - determines claim validity based on evidence.

Analyzes evidence snippets to assess if a claim is supported, refuted, or inconclusive.
"""

from datetime import datetime, timezone, timedelta
import logging
from pathlib import Path
import re
from typing import List, Literal, Dict

from pydantic import BaseModel, Field

from jinja2 import Environment, FileSystemLoader, Template
from langgraph.runtime import get_runtime
from langgraph.runtime import Runtime

from aic_nlp_utils.json import read_json

from fsearch2.fact_search.config.nodes import EVIDENCE_EVALUATION_CONFIG
from utils import (
    call_llm_with_structured_output,
    get_llm
)

from claim_verifier.schemas import (
    ClaimVerifierState,
    Evidence,
)

from fact_search.schemas import ContextSchema, Verdict

logger = logging.getLogger(__name__)

# Retrieval settings
MODEL_NAME = EVIDENCE_EVALUATION_CONFIG["model_name"]
MAX_LENGTH = EVIDENCE_EVALUATION_CONFIG["max_length"]

TEMPLATE_DIR = EVIDENCE_EVALUATION_CONFIG["template_dir"]
TEMPLATE_PREDICT = EVIDENCE_EVALUATION_CONFIG["template_predict"]
GENERATE_VERDICT_INSTRUCTIONS = EVIDENCE_EVALUATION_CONFIG["generate_verdict_instructions"]

class AssessmentResult(BaseModel):
    assessment: str = Field(description="Explanation of the verdict")
    veracity: Literal["untrue", "true", "unverifiable"] = Field(description="Claim classification")


def renumber_assessment_references(assessment: str, evidence: List[Evidence]) -> tuple[str, List[Evidence]]:
    """
    Renumber references in assessment to appear in increasing order.
    Rearrange sources list to match the new numbering.
    
    Args:
        assessment: The assessment text with references like [1], [6], etc.
        evidence: List of evidence sources
    
    Returns:
        Tuple of (renumbered_assessment, reordered_sources)
    """
    # Find all references in order of appearance
    references = re.findall(r'\[(\d+)\]', assessment)
    
    if not references:
        return assessment, evidence
    
    # Create mapping from old reference numbers to new ones
    # Using dict to preserve order of first appearance
    old_to_new: Dict[int, int] = {}
    new_number = 1
    
    for ref in references:
        old_ref = int(ref)
        if old_ref not in old_to_new:
            old_to_new[old_ref] = new_number
            new_number += 1
    
    # Replace references in assessment
    # We need to replace all occurrences, so we'll use a single pass with a function
    def replace_ref(match):
        old_ref = int(match.group(1))
        return f'[{old_to_new.get(old_ref, old_ref)}]'
    
    new_assessment = re.sub(r'\[(\d+)\]', replace_ref, assessment)
    
    # Reorder sources: referenced sources first (in new order), then unreferenced
    referenced_sources = []
    unreferenced_sources = []
    
    # Convert to 0-based indexing for list access
    old_indices_used = {old_ref - 1: new_ref for old_ref, new_ref in old_to_new.items()}
    
    # First, add referenced sources in their new order
    for old_idx in sorted(old_indices_used.keys(), key=lambda x: old_indices_used[x]):
        if old_idx < len(evidence):
            source = evidence[old_idx]
            # Mark as influential since it's referenced
            referenced_sources.append(
                Evidence(
                    url=source.url,
                    title=source.title,
                    text=source.text,
                    full_text=source.full_text,
                    is_influential=True,
                )
            )
    
    # Then, add unreferenced sources
    for idx, source in enumerate(evidence):
        if idx not in old_indices_used:
            unreferenced_sources.append(
                Evidence(
                    url=source.url,
                    title=source.title,
                    text=source.text,
                    full_text=source.full_text,
                    is_influential=False,
                )
            )
    
    reordered_sources = referenced_sources + unreferenced_sources
    
    return new_assessment, reordered_sources


async def evaluate_evidence_node(state: ClaimVerifierState, runtime: Runtime[ContextSchema]) -> dict:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template_predict = env.get_template(TEMPLATE_PREDICT)
    instructions = Path(TEMPLATE_DIR, GENERATE_VERDICT_INSTRUCTIONS).read_text()
    schema = AssessmentResult.model_json_schema()
    
    tz = timezone(timedelta(hours=1))
    now = datetime.now(tz)
    formatted_now = now.strftime("%Y-%m-%d %H:%M:%S %z")
  
    claim = state.claim
    evidence = state.evidence
    iteration_count = state.iteration_count

    runtime = get_runtime(ContextSchema)
    
    lengths = [len(ev.full_text) for ev in evidence]
    logger.info(f"evidence lengths: {lengths}")
    
    if any(l > MAX_LENGTH for l in lengths):
        text_reducer = runtime.context["text_reducer"]
        for didx, ev in enumerate(evidence):
            if len(ev.full_text) > MAX_LENGTH:
                logger.info(f"Will reduce document idx: {didx}")
                reduced_text = text_reducer.reduce(query=claim.claim_text, document=ev.full_text, maxLength=MAX_LENGTH)
                logger.info(f"reduced to {len(reduced_text)}")
                ev.full_text = reduced_text
                
    logger.info(
        f"Final evaluation for claim '{claim.claim_text}' "
        f"with {len(evidence)} evidence documents "
        f"after {iteration_count} iterations"
    )
    
    query = f"""<date>{formatted_now}</date>
<statement>{claim.claim_text}</statement>
<evidences>
"""
    idx = 1
    for ev in evidence:
        query += f'<evidence id="{idx}">\n'
        query += ev.text if len(ev.full_text) == 0 else ev.full_text
        query += '</evidence>\n'
        idx += 1 
    query += '</evidences>'
    
    prompt_predict = template_predict.render(prompt=instructions, query=query, schema=schema)

    messages = [("user", prompt_predict)]

    # llm = get_llm(model_name="openai:gpt-5")
    llm = get_llm(model_name=MODEL_NAME)

    response = await call_llm_with_structured_output(
        llm=llm,
        output_class=AssessmentResult,
        messages=messages,
        context_desc=f"generating verdict for claim '{claim.claim_text}'",
    )
    
    print(response)

    if not response:
        logger.warning(f"Failed to evaluate evidence for claim: '{claim.claim_text}'")
        verdict = Verdict(
            claim_text=claim.claim_text,
            assessment="Failed to evaluate the evidence due to technical issues",
            veracity="unverifiable",
            sources=[])
    else:
        # Renumber references and reorder sources
        renumbered_assessment, reordered_sources = renumber_assessment_references(
            response.assessment, 
            evidence
        )

        verdict = Verdict(
            claim_text=claim.claim_text,
            assessment=renumbered_assessment,
            veracity=response.veracity,
            sources=reordered_sources,
        )

    # Log final result
    influential_count = sum(source.is_influential for source in verdict.sources)
    logger.info(
        f"Veracity '{verdict.veracity}' for '{claim.claim_text}': {verdict.assessment} "
        f"({influential_count}/{len(verdict.sources)} sources)"
    )

    return {"verdict": verdict.model_dump()}