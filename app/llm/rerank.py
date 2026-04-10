from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Sequence, Tuple

from app.indexing.vector_store import Document

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Re-score (query, passage) pairs with a cross-encoder for sharper ranking.

    The model is loaded lazily on first use so simple workflows that disable
    reranking avoid the extra weight and import side effects until needed.
    """

    def __init__(
        self,
        model_name: str,
        *,
        max_passage_chars: int = 8000,
        batch_size: int = 16,
    ) -> None:
        self.model_name = model_name
        self.max_passage_chars = max_passage_chars
        self.batch_size = batch_size
        self._model: CrossEncoder | None = None

    @property
    def model(self) -> "CrossEncoder":
        if self._model is None:
            from sentence_transformers import CrossEncoder as CE

            logger.info("Loading cross-encoder reranker: %s", self.model_name)
            self._model = CE(self.model_name)
        return self._model

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_passage_chars:
            return text
        return text[: self.max_passage_chars]

    def rerank(
        self,
        query: str,
        hits: Sequence[Tuple[float, Document]],
        top_k: int,
    ) -> List[Tuple[float, Document]]:
        """Return up to `top_k` documents ordered by cross-encoder relevance.

        The returned float score is the cross-encoder score (higher is better
        for typical MS MARCO-style models).
        """

        if not hits or top_k <= 0:
            return []

        docs = [d for _, d in hits]
        pairs: List[List[str]] = [[query, self._truncate(d.text)] for d in docs]

        raw_scores = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
        )

        if hasattr(raw_scores, "tolist"):
            scores_list = raw_scores.tolist()  # type: ignore[union-attr]
        else:
            scores_list = list(raw_scores)

        combined: List[Tuple[float, float, Document]] = []
        for vec_s, ce_s, doc in zip(
            (s for s, _ in hits),
            scores_list,
            docs,
        ):
            combined.append((float(ce_s), float(vec_s), doc))

        combined.sort(key=lambda t: t[0], reverse=True)
        return [(ce, doc) for ce, _vec, doc in combined[:top_k]]


def vector_order_top_k(
    hits: Sequence[Tuple[float, Document]],
    top_k: int,
) -> List[Tuple[float, Document]]:
    """Keep FAISS ordering and trim to `top_k`."""

    return list(hits)[:top_k]
