import logging
import asyncio
from typing import Any, Dict, List, Union

from bs4 import BeautifulSoup

from claim_verifier.config import EVIDENCE_RETRIEVAL_CONFIG
from claim_verifier.schemas import ClaimVerifierState, Evidence
from fsearch2.claim_extractor.schemas import ValidatedClaim

from aic_nlp_utils.json import read_jsonl, write_json


logger = logging.getLogger(__name__)

async def mock_retrieve_evidence_node(
    state: ClaimVerifierState
) -> dict:
    
    data = read_jsonl("data/demagog/v5/demagog.jsonl")
    sample = data[1]

    # Wrap in a root tag so XML parsing works
    soup = BeautifulSoup("<data>" + sample["query"] + "</data>", "lxml-xml")


    evidence = [
        Evidence(url=f"evidence://{i}", text=e.get_text(strip=True)[:200], full_text=e.get_text(strip=True))
        for i, e in enumerate(soup.find_all("evidence"))
    ]

    statement = soup.find("statement").get_text(strip=True)
    claim = ValidatedClaim(claim_text=statement).model_dump()

    logger.info(f"Evidence documents: {len(evidence)}")

    return {
        "claim": claim,
        "evidence": evidence
    }
