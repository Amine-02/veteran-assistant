"""BM25 retrieval re-weighted by trust x freshness.

A LangChain BaseRetriever, so a hybrid (BM25 + embeddings) retriever can
replace it later without touching the pipeline.
"""

from __future__ import annotations

import re

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict
from rank_bm25 import BM25Okapi

STOPWORDS = set("""
a about after all also am an and any are as at be been before being but by can
could do does doing for from get got had has have how i if in into is it its just
me more most my no not now of on or our out over please right so some than that
the their them then there these they this to too up us was we were what when
where which who why will with would you your yourself im ive dont
""".split())


def stem(token: str) -> str:
    """Very light suffix stripping so 'expires' matches 'expire'."""
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower().replace("9/11", "911"))
    return [stem(w) for w in words if w not in STOPWORDS]


class WeightedBM25Retriever(BaseRetriever):
    """Score = BM25 x trust x freshness. Drops chunks below min_score."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    docs: list[Document]
    bm25: BM25Okapi
    k: int = 5
    min_score: float = 1.0

    @classmethod
    def from_documents(cls, docs: list[Document], **kwargs) -> "WeightedBM25Retriever":
        bm25 = BM25Okapi([tokenize(d.page_content) for d in docs])
        return cls(docs=docs, bm25=bm25, **kwargs)

    def score(self, query: str) -> list[tuple[Document, float, float]]:
        """All chunks as (doc, bm25, weighted), best first."""
        raw = self.bm25.get_scores(tokenize(query))
        rows = []
        for doc, s in zip(self.docs, raw):
            weight = doc.metadata["trust"] * doc.metadata["freshness"]
            rows.append((doc, float(s), float(s) * weight))
        return sorted(rows, key=lambda r: r[2], reverse=True)

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        out = []
        for doc, raw, weighted in self.score(query)[: self.k]:
            if weighted < self.min_score:
                break
            out.append(Document(
                page_content=doc.page_content,
                metadata={**doc.metadata, "bm25": round(raw, 3), "score": round(weighted, 3)},
            ))
        return out
