#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from app.config import get_settings
from app.indexing.ingest import ingest_jsonl_logs
from app.indexing.vector_store import VectorStore


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append new JSONL-derived documents to an existing FAISS index",
    )
    parser.add_argument("inputs", nargs="+", help="Paths to additional JSONL log files")
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=None,
        help="Directory with existing index.faiss and docs.jsonl",
    )
    parser.add_argument(
        "--grouping",
        type=str,
        default="actorname",
        help="Field to group events by into documents (default: actorname)",
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default=None,
        help="Sentence-Transformers model name (must match the existing index)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and count documents without writing the index",
    )
    args = parser.parse_args()

    settings = get_settings()
    index_dir = args.index_dir if args.index_dir else settings.index_dir
    model_name = args.embedding_model or settings.embedding_model_name

    docs = ingest_jsonl_logs([Path(p) for p in args.inputs], grouping=args.grouping)
    if not docs:
        print("No documents produced from inputs; nothing to append.")
        return

    if args.dry_run:
        print(f"Dry run: would append {len(docs)} documents to {index_dir}")
        return

    store = VectorStore.load(model_name=model_name, index_dir=index_dir)
    before = len(store._docs)
    store.add_documents(docs)
    store.save()
    after = len(store._docs)
    print(f"Appended {after - before} documents (total {after}) under {index_dir}")


if __name__ == "__main__":
    main()
