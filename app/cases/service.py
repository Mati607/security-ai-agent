from __future__ import annotations

import json
from typing import Any, Dict, List, Set

from app.cases.constants import TimelineKind
from app.cases.models import (
    CaseDetail,
    IOCAggregate,
    NoteCreate,
    SearchSnapshotCreate,
    TriageSnapshotPayload,
)
from app.cases.store import CaseStore, CaseStoreError
from app.config import Settings
from app.indexing.search_filters import extract_query_signals
from app.indexing.vector_store import Document
from app.llm.contextualize import AlertContextualizer
from app.llm.retrieval import RetrievalOptions, RetrievalPipeline


class CaseInvestigationService:
    """High-level workflows: notes, RAG snapshots, triage capture, IOC rollups."""

    def __init__(
        self,
        store: CaseStore,
        pipeline: RetrievalPipeline,
        contextualizer: AlertContextualizer,
        settings: Settings,
    ) -> None:
        self._store = store
        self._pipeline = pipeline
        self._contextualizer = contextualizer
        self._settings = settings

    def add_note(self, case_id: str, note: NoteCreate) -> CaseDetail:
        if not self._store.case_exists(case_id):
            raise CaseStoreError(f"case not found: {case_id}")
        self._store.add_timeline(
            case_id,
            kind=TimelineKind.NOTE,
            title=note.title,
            body=note.body,
            payload=None,
        )
        full = self._store.get_case(case_id)
        assert full is not None
        return full

    def attach_search_snapshot(self, case_id: str, body: SearchSnapshotCreate) -> CaseDetail:
        if not self._store.case_exists(case_id):
            raise CaseStoreError(f"case not found: {case_id}")
        title = f"Search snapshot ({len(body.results)} hits)"
        payload: Dict[str, Any] = {
            "query": body.query,
            "top_k": body.top_k,
            "results": body.results,
        }
        self._store.add_timeline(
            case_id,
            kind=TimelineKind.SEARCH_SNAPSHOT,
            title=title,
            body=None,
            payload=payload,
        )
        full = self._store.get_case(case_id)
        assert full is not None
        return full

    def run_search_and_attach(
        self,
        case_id: str,
        query: str,
        top_k: int,
        options: RetrievalOptions | None = None,
    ) -> CaseDetail:
        """Execute retrieval for `query` and persist hits as a search snapshot."""

        if not self._store.case_exists(case_id):
            raise CaseStoreError(f"case not found: {case_id}")
        opts = options or RetrievalOptions()
        hits = self._pipeline.retrieve(query, top_k=top_k, options=opts)
        results: List[Dict[str, Any]] = []
        for score, doc in hits:
            results.append(_hit_to_payload(score, doc))
        snap = SearchSnapshotCreate(query=query, top_k=top_k, results=results)
        return self.attach_search_snapshot(case_id, snap)

    def run_triage_and_attach(
        self,
        case_id: str,
        alert: str,
        top_k: int,
        options: RetrievalOptions | None = None,
    ) -> tuple[TriageSnapshotPayload, CaseDetail]:
        """Mirror API /triage behavior and store the outcome on the case timeline."""

        if not self._store.case_exists(case_id):
            raise CaseStoreError(f"case not found: {case_id}")
        opts = options or RetrievalOptions()
        results = self._pipeline.retrieve(alert, top_k=top_k, options=opts)
        passages = [doc.text for _, doc in results]
        brief = self._contextualizer.summarize(alert, passages)
        search_results: List[Dict[str, Any]] = [
            {"score": float(score), "doc_id": doc.doc_id, "metadata": doc.metadata}
            for score, doc in results
        ]
        rerank = opts.use_rerank if opts.use_rerank is not None else self._settings.rerank_enabled
        payload_model = TriageSnapshotPayload(
            alert=alert,
            brief=brief,
            rerank=rerank,
            search_results=search_results,
        )
        payload = payload_model.model_dump()
        self._store.add_timeline(
            case_id,
            kind=TimelineKind.TRIAGE_SNAPSHOT,
            title="Triage run",
            body=brief[:2000] + ("…" if len(brief) > 2000 else ""),
            payload=payload,
        )
        detail = self._store.get_case(case_id)
        assert detail is not None
        return payload_model, detail

    def aggregate_iocs(self, case_id: str) -> IOCAggregate:
        """Collect IOC-shaped tokens from case text and timeline content."""

        detail = self._store.get_case(case_id)
        if detail is None:
            raise CaseStoreError(f"case not found: {case_id}")

        chunks: List[str] = [detail.title]
        if detail.summary:
            chunks.append(detail.summary)
        for entry in detail.timeline:
            if entry.title:
                chunks.append(entry.title)
            if entry.body:
                chunks.append(entry.body)
            if entry.payload:
                try:
                    chunks.append(json.dumps(entry.payload, ensure_ascii=False))
                except (TypeError, ValueError):
                    chunks.append(str(entry.payload))

        ipv4: Set[str] = set()
        sha256: Set[str] = set()
        domains: Set[str] = set()
        for text in chunks:
            if not text:
                continue
            sig = extract_query_signals(text)
            ipv4.update(sig.ipv4)
            sha256.update(sig.sha256)
            domains.update(sig.domains)

        return IOCAggregate(
            ipv4=sorted(ipv4),
            sha256=sorted(sha256),
            domains=sorted(domains),
        )

    def record_ioc_signal(
        self,
        case_id: str,
        *,
        title: str,
        body: str | None = None,
        extra_payload: Dict[str, Any] | None = None,
    ) -> CaseDetail:
        """Append an explicit IOC or enrichment marker to the timeline."""

        if not self._store.case_exists(case_id):
            raise CaseStoreError(f"case not found: {case_id}")
        payload = dict(extra_payload or {})
        agg = self.aggregate_iocs(case_id)
        payload["rollup"] = agg.model_dump()
        self._store.add_timeline(
            case_id,
            kind=TimelineKind.IOC_SIGNAL,
            title=title,
            body=body,
            payload=payload or None,
        )
        full = self._store.get_case(case_id)
        assert full is not None
        return full


def _hit_to_payload(score: float, doc: Document) -> Dict[str, Any]:
    return {
        "score": float(score),
        "doc_id": doc.doc_id,
        "text": doc.text,
        "metadata": dict(doc.metadata),
    }
