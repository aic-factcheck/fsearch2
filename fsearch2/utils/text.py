"""Text processing utilities.

Helper functions for manipulating text content.
"""

import logging

logger = logging.getLogger(__name__)


def remove_following_sentences(context_for_llm: str) -> str:
    """Strips out the following sentences section from context.

    Our context looks like:
    [Preceding Sentences:]
    ...
    [Sentence of Interest for current task:]
    ...
    [Following Sentences:]
    ...

    Args:
        context_for_llm: The full context string

    Returns:
        Context with following sentences removed
    """
    # Split by the marker
    parts = context_for_llm.split("\n[Following Sentences:]")

    # If there are following sentences, return only the part before them
    if len(parts) > 1:
        return parts[0]

    # No following sentences? Return as is
    return context_for_llm
