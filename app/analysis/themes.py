from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer


def _extract_top_terms(texts: List[str], top_k: int = 10) -> List[Tuple[str, int]]:
    if not texts:
        return []
    vectorizer = CountVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2)
    X = vectorizer.fit_transform(texts)
    counts = np.asarray(X.sum(axis=0)).ravel()
    terms = np.array(vectorizer.get_feature_names_out())
    order = counts.argsort()[::-1]
    top_terms = [(str(terms[i]), int(counts[i])) for i in order[:top_k]]
    return top_terms


def compute_themes(df: pd.DataFrame, positive_threshold: float = 0.9, negative_threshold: float = 0.1, top_k: int = 10):
    df = df.dropna(subset=["content"]) if not df.empty else df
    pos_texts = df[(df.get("sentiment_label") == "POSITIVE") & (df.get("sentiment_score", 0) >= positive_threshold)][
        "content"
    ].astype(str).tolist()
    neg_texts = df[(df.get("sentiment_label") == "NEGATIVE") & (df.get("sentiment_score", 0) <= negative_threshold)][
        "content"
    ].astype(str).tolist()

    pos = _extract_top_terms(pos_texts, top_k=top_k)
    neg = _extract_top_terms(neg_texts, top_k=top_k)
    return pos, neg 