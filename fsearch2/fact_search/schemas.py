"""Data models for claim verification.

All the structured types used throughout the verification workflow.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated, List, Literal, Optional
from pydantic import BaseModel, Field
from operator import add


from claim_verifier.schemas import Evidence
from fsearch2.utils.text_reducer import TextReducer

@dataclass
class ContextSchema:
    text_reducer: TextReducer
    
    
class Verdict(BaseModel):
    """The result of fact-checking a single claim."""

    claim_text: str = Field(description="The text of the claim that was checked")

    assessment: str = Field(description="Explanation of the verdict")
    
    veracity: Literal["untrue", "true", "unverifiable"] = Field(description="Claim classification")
    
    sources: List[Evidence] = Field(
        default_factory=list, description="List of evidence sources"
    )

