"""Sentence splitting and context creation.

Chunks input text into sentences and builds context windows for each one.
"""

import logging
from typing import Dict, List, Optional

import nltk

from claim_extractor.config import CONTEXT_WINDOWS
from claim_extractor.schemas import ContextualSentence, State

# Configure module logger
logger = logging.getLogger(__name__)


def ensure_nltk_resources() -> None:
    """Download NLTK stuff if needed."""
    resources = ["tokenizers/punkt_tab", "tokenizers/punkt"]

    for resource in resources:
        try:
            nltk.data.find(resource)
            return
        except LookupError:
            continue

    # None found, download both
    logger.info("Downloading NLTK resources...")
    nltk.download("punkt_tab", quiet=True)
    nltk.download("punkt", quiet=True)


async def _sentence_splitter_and_context_creator(
    answer_text: str,
    p_sentences: int = 1,
    f_sentences: int = 1,
    include_metadata: bool = False,
    metadata: Optional[str] = None,
) -> List[ContextualSentence]:
    """Split text into sentences and add context windows.

    Args:
        answer_text: Text to split
        p_sentences: Number of preceding sentences for context
        f_sentences: Number of following sentences for context
        include_metadata: Whether to include metadata
        metadata: Source metadata

    Returns:
        List of sentences with context
    """
    logger.info("Stage 1: Sentence Splitting and Context Creation")

    # Get tokenizer
    ensure_nltk_resources()

    # Split by paragraphs first, then sentences
    # This handles bullet lists and paragraph breaks better
    paragraphs = [p.strip() for p in answer_text.split("\\n") if p.strip()]
    raw_sentences_from_paragraphs: List[str] = []
    for paragraph in paragraphs:
        raw_sentences_from_paragraphs.extend(nltk.sent_tokenize(paragraph))

    # Use the paragraph-aware sentences
    raw_sentences = raw_sentences_from_paragraphs

    # Merge short fragments (< 5 chars) with next sentence
    # Avoids processing meaningless bits like bullet points
    merged_sentences: List[str] = []
    i = 0
    while i < len(raw_sentences):
        current_sentence = raw_sentences[i].strip()

        # Keep merging tiny sentences with the next one
        while len(current_sentence) < 5 and (i + 1) < len(raw_sentences):
            i += 1
            current_sentence += f" {raw_sentences[i].strip()}"

        if current_sentence:  # Skip empty ones
            merged_sentences.append(current_sentence)
        i += 1

    # Create context windows for each sentence
    contextual_sentences: List[ContextualSentence] = []

    for i, sentence in enumerate(merged_sentences):
        context_parts: List[str] = []

        # Add metadata if available
        if include_metadata and metadata:
            context_parts.append(f"[Document Metadata: {metadata}]")

        # Add preceding sentences
        start_index = max(0, i - p_sentences)
        if start_index < i:
            context_parts.append("\n[Preceding Sentences:]")
            for j in range(start_index, i):
                context_parts.append(merged_sentences[j])

        # Add the sentence itself
        context_parts.append(f"\n[Sentence of Interest for current task:]\n{sentence}")

        # Add following sentences
        end_index = min(len(merged_sentences), i + 1 + f_sentences)
        if (i + 1) < end_index:
            context_parts.append("\n[Following Sentences:]")
            for j in range(i + 1, end_index):
                context_parts.append(merged_sentences[j])

        # Package it up
        full_context_str = "\n".join(context_parts)
        contextual_sentences.append(
            ContextualSentence(
                original_sentence=sentence,
                context_for_llm=full_context_str,
                metadata=metadata,
                original_index=i,
            )
        )

        # Log a preview
        sentence_preview = sentence[:30] + ("..." if len(sentence) > 30 else "")
        logger.debug(f"Context created for: '{sentence_preview}'")

    logger.info(f"Processed {len(contextual_sentences)} sentences with context")
    return contextual_sentences


async def sentence_splitter_node(state: State) -> Dict[str, List[ContextualSentence]]:
    """Split text into sentences and create context windows.

    Args:
        state: Current workflow state

    Returns:
        Dictionary with contextual_sentences key
    """
    # Get what we need from state
    answer_text = state.answer_text
    metadata = state.metadata

    # Use config-defined context window sizes
    p_sentences = CONTEXT_WINDOWS["selection"]["preceding_sentences"]
    f_sentences = CONTEXT_WINDOWS["selection"]["following_sentences"]

    # Process the text
    contextual_sentences = await _sentence_splitter_and_context_creator(
        answer_text, p_sentences, f_sentences, bool(metadata), metadata
    )

    return {"contextual_sentences": contextual_sentences}
