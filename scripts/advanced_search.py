#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import get_settings
from app.indexing.search_filters import SearchFilterSpec, describe_filter_spec
from app.indexing.vector_store import VectorStore
from app.llm.retrieval import RetrievalOptions, build_default_pipeline


def _build_spec(args: argparse.Namespace) -> SearchFilterSpec | None:
    meta_eq: dict[str, str] = {}
    if args.meta_eq:
        for pair in args.meta_eq:
            if "=" not in pair:
                raise SystemExit(f"--meta-eq expects key=value, got {pair!r}")
            k, v = pair.split("=", 1)
            meta_eq[k.strip()] = v.strip()

    meta_sub: dict[str, str] = {}
    if args.meta_contains:
        for pair in args.meta_contains:
            if "=" not in pair:
                raise SystemExit(f"--meta-contains expects key=value, got {pair!r}")
            k, v = pair.split("=", 1)
            meta_sub[k.strip()] = v.strip()

    spec = SearchFilterSpec(
        min_vector_score=args.min_score,
        min_num_events=args.min_events,
        max_num_events=args.max_events,
        group_key_contains=args.group_key_contains,
        doc_id_contains=args.doc_id_contains,
        metadata_equals=meta_eq,
        metadata_contains=meta_sub,
        timestamp_after=args.timestamp_after,
        timestamp_before=args.timestamp_before,
        require_timestamp=args.require_timestamp,
    )
    normalized = spec.normalized()
    desc = describe_filter_spec(normalized)
    if desc == "(no filters)":
        return None
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query the FAISS index with filters, wide retrieval, and optional reranking",
    )
    parser.add_argument("query", type=str, help="Search query or alert text")
    parser.add_argument("--top-k", type=int, default=None, help="Final number of hits")
    parser.add_argument(
        "--retrieve-k",
        type=int,
        default=None,
        help="FAISS neighbor count before filtering/rerank",
    )
    parser.add_argument("--index-dir", type=Path, default=None, help="Index directory")
    parser.add_argument("--embedding-model", type=str, default=None, help="Embedding model id")
    parser.add_argument("--rerank", action="store_true", help="Enable cross-encoder reranking")
    parser.add_argument(
        "--ioc-narrow",
        action="store_true",
        help="Keep hits whose text/metadata overlaps extracted IOCs from the query",
    )
    parser.add_argument("--min-score", type=float, default=None, help="Minimum vector similarity")
    parser.add_argument("--min-events", type=int, default=None, help="Minimum metadata num_events")
    parser.add_argument("--max-events", type=int, default=None, help="Maximum metadata num_events")
    parser.add_argument(
        "--group-key-contains",
        type=str,
        default=None,
        help="Substring filter on metadata key (grouping value)",
    )
    parser.add_argument("--doc-id-contains", type=str, default=None, help="Substring filter on doc_id")
    parser.add_argument(
        "--meta-eq",
        action="append",
        default=[],
        metavar="KEY=VAL",
        help="Metadata equality constraint (repeatable)",
    )
    parser.add_argument(
        "--meta-contains",
        action="append",
        default=[],
        metavar="KEY=VAL",
        help="Metadata substring constraint (repeatable)",
    )
    parser.add_argument("--timestamp-after", type=str, default=None)
    parser.add_argument("--timestamp-before", type=str, default=None)
    parser.add_argument(
        "--require-timestamp",
        action="store_true",
        help="Drop documents without first/last timestamp metadata",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON lines instead of text")
    args = parser.parse_args()

    settings = get_settings()
    top_k = args.top_k or settings.search_top_k
    index_dir = args.index_dir or settings.index_dir
    model_name = args.embedding_model or settings.embedding_model_name

    store = VectorStore.load(model_name=model_name, index_dir=index_dir)
    pipeline = build_default_pipeline(store, settings)
    spec = _build_spec(args)
    opts = RetrievalOptions(
        retrieve_k=args.retrieve_k,
        filter_spec=spec,
        use_rerank=True if args.rerank else None,
        narrow_by_ioc_overlap=args.ioc_narrow,
    )

    results = pipeline.retrieve(args.query, top_k=top_k, options=opts)

    if args.json:
        for rank, (score, doc) in enumerate(results, start=1):
            row = {
                "rank": rank,
                "score": score,
                "doc_id": doc.doc_id,
                "text": doc.text,
                "metadata": doc.metadata,
            }
            print(json.dumps(row, ensure_ascii=False))
        return

    for rank, (score, doc) in enumerate(results, start=1):
        print(
            f"[{rank}] score={score:.4f} id={doc.doc_id} "
            f"events={doc.metadata.get('num_events')} meta={doc.metadata}"
        )


if __name__ == "__main__":
    main()
