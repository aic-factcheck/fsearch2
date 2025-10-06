from typing import List
import logging

import fasttext
import numpy as np
import re

from aic_nlp_utils.split_merge import split_node_to_list

logger = logging.getLogger(__name__)

class TextReducer:
    def __init__(self, vectors:str) -> str:
        logger.info(f"Loading FastText model: {vectors}")
        self.model = fasttext.load_model(vectors)
        
        
    def reduce(self, query: str, document: str, maxLength: int):
        def tokenize(text: str):
            return re.findall(r"\w+", text.lower(), flags=re.UNICODE)

        def get_embedding(text: str):
            tokens = tokenize(text)
            if not tokens:
                return np.zeros(self.model.get_dimension())
            vectors = [self.model.get_word_vector(tok) for tok in tokens]
            return np.mean(vectors, axis=0)

        def cosine(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        
        corpus = split_node_to_list(document, maxLength=maxLength)
        logger.info(f"running for maxLength={maxLength}")

        logger.info(f"query={query}")
        query_vec = get_embedding(query)
        scores = []
        for doc in corpus:
            doc_vec = get_embedding(doc)
            sim = cosine(query_vec, doc_vec)
            scores.append(sim)

        ranking = np.argsort(scores)[::-1]
        
        idx = ranking[0]
        best = corpus[idx]
        
        print(f"\nBest doc {idx} (score={scores[idx]:.3f}):")
        print(best[:200] + "...")
        
        return best