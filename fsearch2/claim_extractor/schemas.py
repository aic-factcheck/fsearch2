"""Data models for the claim extraction pipeline.

All the structured types used throughout the workflow.
"""

from operator import add
from typing import Annotated, List, Optional

from pydantic import BaseModel, Field


class ContextualSentence(BaseModel):
    """A sentence with its surrounding context."""

    original_sentence: str = Field(description="The raw sentence from the source text")
    context_for_llm: str = Field(
        description="Full context for the LLM including surrounding sentences and metadata"
    )
    metadata: Optional[str] = Field(
        default=None, description="Additional metadata about the source"
    )
    original_index: int = Field(
        description="Index of the sentence in the original text"
    )


class SelectedContent(BaseModel):
    """Content selected as potentially verifiable."""

    processed_sentence: str = Field(
        description="Original or modified verifiable sentence after selection"
    )
    original_context_item: ContextualSentence = Field(
        description="Reference to the original contextual sentence"
    )


class DisambiguatedContent(BaseModel):
    """Content with pronoun references and ambiguities resolved."""

    disambiguated_sentence: str = Field(
        description="Sentence with ambiguities resolved"
    )
    original_selected_item: SelectedContent = Field(
        description="Reference to the original selected content"
    )


class PotentialClaim(BaseModel):
    """A factual claim extracted from disambiguated content."""

    claim_text: str = Field(description="Text of the potential claim")
    disambiguated_sentence: str = Field(
        description="The disambiguated sentence the claim was extracted from"
    )
    original_sentence: str = Field(
        description="The original sentence from the answer text"
    )
    original_index: int = Field(
        description="Index of the original sentence in the answer text"
    )


class ValidatedClaim(BaseModel):
    """A claim validated as a properly formed sentence."""

    claim_text: str = Field(description="Text of the validated claim")
    is_complete_declarative: bool = Field(
        description="Whether the claim is a complete declarative sentence", default=True
    )
    disambiguated_sentence: str = Field(
        description="The disambiguated sentence the claim was extracted from", default=""
    )
    original_sentence: str = Field(
        description="The original sentence from the answer text", default=""
    )
    original_index: int = Field(
        description="Index of the original sentence in the answer text", default=0
    )


class State(BaseModel):
    """The workflow graph state object."""

    answer_text: str = Field(description="The answer text being analyzed")
    contextual_sentences: List[ContextualSentence] = Field(
        default_factory=list, description="Sentences with their surrounding context"
    )
    selected_contents: Annotated[List[SelectedContent], add] = Field(
        default_factory=list, description="Contents selected as potentially verifiable"
    )
    disambiguated_contents: Annotated[List[DisambiguatedContent], add] = Field(
        default_factory=list, description="Contents with ambiguities resolved"
    )
    potential_claims: Annotated[List[PotentialClaim], add] = Field(
        default_factory=list, description="Potential claims extracted from content"
    )
    validated_claims: Annotated[List[ValidatedClaim], add] = Field(
        default_factory=list,
        description="Claims validated as complete declarative sentences",
    )
    metadata: Optional[str] = Field(
        default=None, description="Additional metadata about the source"
    )
