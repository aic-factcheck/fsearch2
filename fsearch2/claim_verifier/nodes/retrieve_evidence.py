"""Retrieve evidence node - fetches evidence for claims using Exa AI, Tavily, or Serper (Google) Search.

Uses search queries to retrieve relevant evidence snippets from the web using neural or keyword search.
"""

import logging
import asyncio
from typing import Any, Dict, List

import httpx
from langchain_exa import ExaSearchRetriever
from langchain_tavily import TavilySearch
from langchain_community.utilities import GoogleSerperAPIWrapper
                
from claim_verifier.config import EVIDENCE_RETRIEVAL_CONFIG
from claim_verifier.schemas import ClaimVerifierState, Evidence
from fsearch2.utils.markdown import html_to_markdown

logger = logging.getLogger(__name__)

# Retrieval settings
RESULTS_PER_QUERY = EVIDENCE_RETRIEVAL_CONFIG["results_per_query"]
SEARCH_PROVIDER = EVIDENCE_RETRIEVAL_CONFIG["search_provider"]
GOOGLE_SEARCH_OPTS = EVIDENCE_RETRIEVAL_CONFIG["google_search_opts"]


async def fetch_full_text(url: str) -> str:
    """
    Fetch content from a URL and return it as Markdown or plain text.
    Handles HTML pages and PDFs.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code != 200:
                return ""

            content_type = resp.headers.get("Content-Type", "").lower()

            if "text/html" in content_type:
                return html_to_markdown(resp.text)
            elif "application/pdf" in content_type or url.lower().endswith(".pdf"):
                # do not use for now
                # return pdf_to_text(resp.content)
                return ""
            else:
                logger.warning(f"Unsupported content type for {url}: {content_type}")
                return ""

    except Exception as e:
        logger.warning(f"Failed to fetch full text from {url}: {e}")
        return ""


class SearchProviders:
    @staticmethod
    async def exa(query: str) -> List[Evidence]:
        logger.info(f"Searching with Exa: '{query}'")
        try:
            retriever = ExaSearchRetriever(
                k=RESULTS_PER_QUERY,
                text_contents_options={"max_characters": 2000},
                type="neural",
            )
            results = await retriever.ainvoke(query)
            evidence = [
                Evidence(
                    url=doc.metadata.get("url", ""),
                    text=doc.page_content[:2000],
                    title=doc.metadata.get("title"),
                )
                for doc in results
            ]
            logger.info(f"Retrieved {len(evidence)} evidence items")
            return evidence
        except Exception as e:
            logger.error(f"Exa search failed for '{query}': {e}")
            return []


    @staticmethod
    async def tavily(query: str) -> List[Evidence]:
        logger.info(f"Searching with Tavily: '{query}'")
        try:
            search = TavilySearch(
                max_results=RESULTS_PER_QUERY,
                topic="general",
                include_raw_content="markdown",
            )
            results = await search.ainvoke(query)
            evidence = SearchProviders._parse_tavily_results(results)
            logger.info(f"Retrieved {len(evidence)} evidence items")
            return evidence
        except Exception as e:
            logger.error(f"Tavily search failed for '{query}': {e}")
            return []


    @staticmethod
    async def serper(query: str, gl: str = "cz", hl: str = "cs") -> List[Evidence]:
        hl, gl = EVIDENCE_RETRIEVAL_CONFIG.get("hl", hl), EVIDENCE_RETRIEVAL_CONFIG.get("gl", gl)
        logger.info(f"Searching with Serper: '{query}'")
        try:
            wrapper = GoogleSerperAPIWrapper(gl=gl, hl=hl)
            raw = await wrapper.aresults(query)
            if not isinstance(raw, dict):
                # Fallback: treat as plain text
                return [Evidence(url="", text=str(raw), title="Serper Search Result")]

            organic = raw.get("organic", []) or []
            evidence: List[Evidence] = []
            for item in organic[:RESULTS_PER_QUERY]:
                if not isinstance(item, dict):
                    continue
                
                url = item.get("link", "") or item.get("url", "")
                text = (item.get("snippet") or item.get("content") or "")[:2000]
                full_text = await fetch_full_text(url) if url else None
    
                evidence.append(
                    Evidence(
                        url=url,
                        title=item.get("title", ""),
                        text=text,
                        full_text=full_text,
                    )
                )
                
            # If nothing parsed, try summary field
            if not evidence and (summary := raw.get("answer_box") or raw.get("knowledgeGraph")):
                evidence.append(
                    Evidence(
                        url="",
                        title="Serper Summary",
                        text=str(summary)[:2000],
                        full_text=str(summary),
                    )
                )

            logger.info(f"Retrieved {len(evidence)} evidence items")
            return evidence
        except Exception as e:
            logger.error(f"Serper search failed for '{query}': {e}")
            return []


    @staticmethod
    def _parse_tavily_results(results: Any) -> List[Evidence]:
        match results:
            case {"results": search_results} if isinstance(search_results, list):
                return [
                    Evidence(
                        url=result.get("url", ""),
                        text=result.get("raw_content") or result.get("content", ""),
                        title=result.get("title", ""),
                    )
                    for result in search_results
                    if isinstance(result, dict)
                ][:RESULTS_PER_QUERY]
            case str():
                return [Evidence(url="", text=results, title="Tavily Search Result")]
            case _:
                return []


async def _search_query(query: str, gl: str = "cz", hl: str = "cs") -> List[Evidence]:
    query += " " + GOOGLE_SEARCH_OPTS
    logger.debug(f"_search_query: {query}")
    match SEARCH_PROVIDER.lower():
        case "tavily":
            return await SearchProviders.tavily(query)
        case "serper":
            return await SearchProviders.serper(query, gl=gl, hl=hl)
        case _:
            return await SearchProviders.exa(query)


async def retrieve_evidence_node(
    state: ClaimVerifierState,
    gl: str = "cz",
    hl: str = "cs",
) -> Dict[str, List[Evidence]]:
    if not state.query:
        logger.warning("No search query to process")
        return {"evidence": []}

    evidence = await _search_query(state.query, gl=gl, hl=hl)
    logger.info(f"Retrieved {len(evidence)} total evidence snippets")

    return {"evidence": [item.model_dump() for item in evidence]}
