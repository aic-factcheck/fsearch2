"""Node configuration settings.

Contains settings for the pipeline nodes.
"""

# Node settings
SELECTION_CONFIG = {
    "completions": 3,
    "min_successes": 2,
    "temperature": 0.2,  # Higher temp for diverse judgments
}

DISAMBIGUATION_CONFIG = {
    "completions": 3,
    "min_successes": 2,
    "temperature": 0.2,  # Higher temp for diverse judgments
}

DECOMPOSITION_CONFIG = {
    "completions": 1,
    "min_successes": 1,
    "temperature": 0.0,  # Zero temp for consistent results
}

VALIDATION_CONFIG = {
    "temperature": 0.0,  # Zero temp for consistent results
}

# Context windows
CONTEXT_WINDOWS = {
    "selection": {
        "preceding_sentences": 5,
        "following_sentences": 5,
    },
    "disambiguation": {
        "preceding_sentences": 5,
        "following_sentences": 0,  # No following sentences here
    },
    "decomposition": {
        "preceding_sentences": 5,
        "following_sentences": 0,  # No following sentences here
    },
}
