from __future__ import annotations

import json
import math
from typing import Any


def extract_keywords(text: str, top_n: int = 8) -> list[str]:
    try:
        from keybert import KeyBERT  # type: ignore
    except Exception:
        return []
    model = KeyBERT()
    keywords = model.extract_keywords(text or '', top_n=top_n, stop_words=None)
    return [kw for kw, _score in keywords]


def embed_text(text: str) -> list[float]:
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except Exception:
        return []
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    vec = model.encode(text or '', normalize_embeddings=True)
    return [float(x) for x in vec.tolist()]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def infer_topics(texts: list[str]) -> list[str]:
    try:
        from bertopic import BERTopic  # type: ignore
    except Exception:
        return []
    if not texts:
        return []
    topic_model = BERTopic(min_topic_size=2, verbose=False)
    topics, _probs = topic_model.fit_transform(texts)
    labels = []
    for topic in topics:
        if topic == -1:
            labels.append('misc')
        else:
            labels.append(topic_model.get_topic_info().set_index('Topic').loc[topic, 'Name'])
    return labels


def build_enrichment(summary: str, transcript_text: str) -> dict[str, Any]:
    text = '\n'.join(part for part in [summary, transcript_text[:4000]] if part).strip()
    return {
        'keywords': extract_keywords(text),
        'embedding': embed_text(text),
        'topic_label': None,
    }
