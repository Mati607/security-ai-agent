from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import faiss  # type: ignore
import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass
class Document:
    """A single document to index and search."""

    doc_id: str
    text: str
    metadata: Dict[str, Any]


class VectorStore:
    """FAISS-backed vector store with Sentence-Transformers embeddings.

    Persists two files in the target directory:
      - index.faiss: the FAISS binary index
      - docs.jsonl: JSONL with one document per line, aligned to FAISS IDs
    """

    def __init__(self, model_name: str, index_dir: Path) -> None:
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embedding_size = self.model.get_sentence_embedding_dimension()
        self.index: faiss.IndexIDMap = faiss.IndexIDMap(
            faiss.IndexFlatIP(self.embedding_size)
        )
        self._docs: List[Document] = []

    # ---------------------------- Persistence ---------------------------- #
    @property
    def faiss_path(self) -> Path:
        return self.index_dir / "index.faiss"

    @property
    def docs_path(self) -> Path:
        return self.index_dir / "docs.jsonl"

    def save(self) -> None:
        """Write through temp files and `os.replace` to reduce torn reads on crash."""

        self.index_dir.mkdir(parents=True, exist_ok=True)
        pid = os.getpid()
        tmp_faiss = self.index_dir / f".index.faiss.{pid}.tmp"
        tmp_docs = self.index_dir / f".docs.jsonl.{pid}.tmp"
        try:
            faiss.write_index(self.index, str(tmp_faiss))
            with tmp_docs.open("w", encoding="utf-8") as f:
                for doc in self._docs:
                    f.write(
                        json.dumps({
                            "doc_id": doc.doc_id,
                            "text": doc.text,
                            "metadata": doc.metadata,
                        })
                        + "\n"
                    )
            os.replace(tmp_docs, self.docs_path)
            os.replace(tmp_faiss, self.faiss_path)
        except BaseException:
            tmp_faiss.unlink(missing_ok=True)
            tmp_docs.unlink(missing_ok=True)
            raise

    @classmethod
    def load(cls, model_name: str, index_dir: Path) -> "VectorStore":
        store = cls(model_name=model_name, index_dir=index_dir)
        if store.faiss_path.exists():
            store.index = faiss.read_index(str(store.faiss_path))  # type: ignore
        if store.docs_path.exists():
            docs: List[Document] = []
            with store.docs_path.open("r", encoding="utf-8") as f:
                for line in f:
                    obj = json.loads(line)
                    docs.append(Document(**obj))
            store._docs = docs
        if store.faiss_path.exists() and store.docs_path.exists() and store._docs:
            n_index = int(store.index.ntotal)
            n_docs = len(store._docs)
            if n_index != n_docs:
                raise ValueError(
                    f"Index vector count ({n_index}) does not match docs.jsonl rows ({n_docs}); "
                    "refuse to load inconsistent store"
                )
        return store

    # ------------------------------ Indexing ---------------------------- #
    def _encode(self, texts: List[str]) -> np.ndarray:
        embeddings = self.model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        if isinstance(embeddings, list):
            embeddings = np.array(embeddings, dtype=np.float32)
        return embeddings.astype(np.float32)

    def add_documents(self, documents: Iterable[Document]) -> None:
        new_docs = list(documents)
        if not new_docs:
            return
        start_id = len(self._docs)
        self._docs.extend(new_docs)
        vectors = self._encode([d.text for d in new_docs])
        ids = np.arange(start_id, start_id + len(new_docs)).astype(np.int64)
        self.index.add_with_ids(vectors, ids)

    def build_from_documents(self, documents: Iterable[Document]) -> None:
        self._docs = []
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.embedding_size))
        self.add_documents(documents)

    def index_info(self) -> Dict[str, Any]:
        """Lightweight introspection for health dashboards and API metadata."""

        n_docs = len(self._docs)
        n_faiss = int(self.index.ntotal)
        persisted = self.faiss_path.exists() and self.docs_path.exists()
        return {
            "embedding_model_name": self.model_name,
            "embedding_dimension": self.embedding_size,
            "document_count": n_docs,
            "faiss_vector_total": n_faiss,
            "index_dir": str(self.index_dir.resolve()),
            "persisted_index_files": persisted,
            "index_consistent": (not persisted or not n_docs) or (n_faiss == n_docs),
        }

    # ------------------------------ Search ------------------------------ #
    def search_candidates(self, query: str, retrieve_k: int) -> List[Tuple[float, Document]]:
        """Return up to `retrieve_k` nearest neighbors by embedding similarity."""

        if not self._docs:
            return []
        k = min(max(1, retrieve_k), len(self._docs))
        query_vec = self._encode([query])
        scores, ids = self.index.search(query_vec, k)
        results: List[Tuple[float, Document]] = []
        for score, idx in zip(scores[0], ids[0]):
            if idx == -1:
                continue
            doc = self._docs[int(idx)]
            results.append((float(score), doc))
        return results

    def search(self, query: str, top_k: int = 10) -> List[Tuple[float, Document]]:
        return self.search_candidates(query, top_k)


