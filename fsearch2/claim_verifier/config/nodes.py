"""Node configuration settings.

Contains settings for the claim verification pipeline nodes.
"""

# Node settings
QUERY_GENERATION_CONFIG = {
    "temperature": 0.0,  # Zero temp for consistent results
}

EVIDENCE_RETRIEVAL_CONFIG = {
    "results_per_query": 5,  # Number of search results to fetch per query
    "search_provider": "serper",  # Search provider: "exa" or "tavily"
    # "gl": "cz",  # Google Serper gl parameter
    # "hl": "cs",  # Google Serper hl parameter
    "gl": "en",  # Google Serper gl parameter
    "hl": "en",  # Google Serper hl parameter
    "google_search_opts": "-site:demagog.cz -site:politifact.com -site:factcheck.org -site:snopes.com -factcheck.afp.com -filetype:pdf -filetype:docx"
}

EVIDENCE_EVALUATION_CONFIG = {
    "temperature": 0.0,  # Zero temp for consistent results
}

ITERATIVE_SEARCH_CONFIG = {
    "max_iterations": 3,
}
