from __future__ import annotations

from typing import List, Tuple

import streamlit as st
from transformers import pipeline

from app.db.database import fetch_unlabeled_texts, update_sentiments


@st.cache_resource(show_spinner=False)
def get_sentiment_pipeline(mode: str = "fast"):
    model_name = (
        "distilbert-base-uncased-finetuned-sst-2-english" if mode == "fast" else "siebert/sentiment-roberta-large-english"
    )
    # Force CPU for broader compatibility and to avoid long MPS warmup on macOS.
    return pipeline("sentiment-analysis", model=model_name, device=-1)


def analyze_unlabeled_mentions(connection, company_id: int, batch_size: int = 32, mode: str = "fast") -> int:
    try:
        remaining = fetch_unlabeled_texts(connection, company_id, limit=batch_size)
    except Exception as e:
        st.warning(f"Database busy/unavailable during fetch: {e}")
        return 0

    if not remaining:
        return 0

    pipe = get_sentiment_pipeline(mode)
    texts: List[str] = [t for _, t in remaining]
    results = pipe(texts, truncation=True)

    labeled: List[Tuple[int, str, float]] = []
    for (mention_id, _), r in zip(remaining, results):
        label: str = r["label"].upper()
        score: float = float(r["score"])
        labeled.append((mention_id, label, score))
    try:
        update_sentiments(connection, labeled)
    except Exception as e:
        st.warning(f"Database busy/unavailable during update: {e}")
        return 0
    return len(labeled) 