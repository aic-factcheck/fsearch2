"""LLM interaction utilities.

Helper functions for working with language models.
"""

import asyncio
import logging
from typing import Any, Callable, List, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel
from langchain_core.language_models.chat_models import BaseChatModel

T = TypeVar("T")
R = TypeVar("R")
M = TypeVar("M", bound=BaseModel)

logger = logging.getLogger(__name__)


def estimate_token_count(text: str) -> int:
    return len(text) // 4


def truncate_evidence_for_token_limit(
    evidence_items: List[Any],
    claim_text: str,
    system_prompt: str,
    human_prompt_template: str,
    max_tokens: int = 120000,
    format_evidence_func: Callable[[List[Any]], str] = None,
) -> List[Any]:
    if not evidence_items:
        return evidence_items

    format_func = format_evidence_func or (
        lambda items: "\n\n".join(
            f"Evidence {i + 1}: {str(item)}" for i, item in enumerate(items)
        )
    )

    base_tokens = estimate_token_count(
        system_prompt
        + human_prompt_template.format(claim_text=claim_text, evidence_snippets="")
    )
    available_tokens = max_tokens - base_tokens - 1000

    if available_tokens <= 0:
        return evidence_items[:1]

    selected = []
    for evidence in reversed(evidence_items):
        test_tokens = estimate_token_count(format_func(selected + [evidence]))
        if test_tokens <= available_tokens:
            selected.append(evidence)
        else:
            break

    result = [e for e in evidence_items if e in selected]

    if len(result) < len(evidence_items):
        logger.info(f"Truncated evidence: {len(evidence_items)} → {len(result)} items")

    return result


async def call_llm_with_structured_output(
    llm: BaseChatModel,
    output_class: Type[M],
    messages: List[Tuple[str, str]],
    context_desc: str = "",
) -> Optional[M]:
    """Call LLM with structured output and consistent error handling.

    Args:
        llm: LLM instance
        output_class: Pydantic model for structured output
        messages: Messages to send to the LLM
        context_desc: Description for error logs

    Returns:
        Structured output or None if error
    """
    try:
        return await llm.with_structured_output(output_class).ainvoke(messages)
    except Exception as e:
        logger.error(f"Error in LLM call for {context_desc}: {e}")
        return None


async def process_with_voting(
    items: List[T],
    processor: Callable[[T, Any], Tuple[bool, Optional[R]]],
    llm: Any,
    completions: int,
    min_successes: int,
    result_factory: Callable[[R, T], Any],
    description: str = "item",
) -> List[Any]:
    """Process items with multiple LLM attempts and consensus voting.

    Args:
        items: Items to process
        processor: Function that processes each item
        llm: LLM instance
        completions: How many attempts per item
        min_successes: How many must succeed
        result_factory: Function to create final result
        description: Item type for logs

    Returns:
        List of successfully processed results
    """
    results = []

    for item in items:
        # Make multiple attempts
        attempts = await asyncio.gather(
            *[processor(item, llm) for _ in range(completions)]
        )

        # Count successes
        success_count = sum(1 for success, _ in attempts if success)

        # Only proceed if we have enough successes
        if success_count < min_successes:
            logger.info(
                f"Not enough successes ({success_count}/{min_successes}) for {description}"
            )
            continue

        # Use the first successful result
        for success, result in attempts:
            if success and result is not None:
                processed_result = result_factory(result, item)
                if processed_result:
                    results.append(processed_result)
                    break

    return results
