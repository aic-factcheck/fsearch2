"""Selection node - identifies verifiable content in sentences.

Filters out fluff and keeps only sentences with factual claims.
"""

import logging
from typing import Dict, List, Optional, Tuple

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from utils import call_llm_with_structured_output, get_llm, process_with_voting

from claim_extractor.config import SELECTION_CONFIG
from claim_extractor.prompts import HUMAN_PROMPT, SELECTION_SYSTEM_PROMPT
from claim_extractor.schemas import ContextualSentence, SelectedContent, State

logger = logging.getLogger(__name__)


COMPLETIONS = SELECTION_CONFIG["completions"]
MIN_SUCCESSES = SELECTION_CONFIG["min_successes"]


class SelectionOutput(BaseModel):
    """Response schema for selection LLM calls."""

    processed_sentence: Optional[str] = Field(
        default=None, description="The processed sentence containing verifiable content"
    )
    no_verifiable_claims: bool = Field(
        description="Flag indicating if no verifiable claims were found"
    )
    remains_unchanged: bool = Field(
        description="Flag indicating if the sentence remains unchanged"
    )


async def _single_selection_attempt(
    contextual_item: ContextualSentence, llm
) -> Tuple[bool, Optional[str]]:
    """Make a single selection attempt.

    Args:
        contextual_item: Sentence with context
        llm: LLM instance

    Returns:
        (success, processed_sentence)
    """
    sentence = contextual_item.original_sentence

    # Prepare the prompt
    messages = ChatPromptTemplate(
        [
            ("system", SELECTION_SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT),
        ]
    )

    prompt_messages = messages.invoke(
        {
            "excerpt": contextual_item.context_for_llm,
            "sentence": sentence,
        }
    )

    # Call the LLM
    selection_response = await call_llm_with_structured_output(
        llm=llm,
        output_class=SelectionOutput,
        messages=prompt_messages,
        context_desc=f"selection attempt for '{sentence}'",
    )

    # If LLM call failed or no verifiable content
    if (
        not selection_response
        or not selection_response.processed_sentence
        or selection_response.no_verifiable_claims
    ):
        return False, None

    # Check if we're keeping it as-is or using the processed version
    if selection_response.remains_unchanged:
        processed = sentence
    else:
        processed = selection_response.processed_sentence.strip()

    return True, processed


def _create_selected_content(
    processed_sentence: str, contextual_item: ContextualSentence
) -> SelectedContent:
    """Package up the selected content.

    Args:
        processed_sentence: The selected content
        contextual_item: Original context

    Returns:
        SelectedContent object
    """
    sentence = contextual_item.original_sentence
    logger.info(f"Selected content: '{processed_sentence}' from original: '{sentence}'")
    return SelectedContent(
        processed_sentence=processed_sentence,
        original_context_item=contextual_item,
    )


async def selection_node(state: State) -> Dict[str, List[SelectedContent]]:
    """Filter sentences that contain verifiable claims.

    Args:
        state: Current workflow state

    Returns:
        Dictionary with selected_contents key
    """
    contextual_sentences = state.contextual_sentences or []

    if not contextual_sentences:
        logger.warning("No sentences to process")
        return {}

    # Get LLM with temperature 0.2 since we're using multiple completions
    llm = get_llm(completions=COMPLETIONS)

    # Process all sentences with voting
    selected_contents = await process_with_voting(
        items=contextual_sentences,
        processor=_single_selection_attempt,
        llm=llm,
        completions=COMPLETIONS,
        min_successes=MIN_SUCCESSES,
        result_factory=_create_selected_content,
        description="sentence",
    )

    if not selected_contents:
        logger.info("No verifiable claims found")
        return {}

    logger.info(
        f"Selected {len(selected_contents)} of {len(contextual_sentences)} sentences as verifiable"
    )
    return {"selected_contents": selected_contents}
