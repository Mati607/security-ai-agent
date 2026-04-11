#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, List, Optional

from app.cases.constants import CaseSeverity, CaseStatus
from app.cases.export_html import render_case_pack_html
from app.cases.models import CaseCreate, CaseListParams, CaseUpdate, NoteCreate, SearchSnapshotCreate
from app.cases.service import CaseInvestigationService
from app.cases.store import CaseStore
from app.config import get_settings
from app.indexing.vector_store import VectorStore
from app.llm.contextualize import AlertContextualizer
from app.llm.retrieval import RetrievalOptions, build_default_pipeline


def _load_stack(index_dir: Optional[Path]) -> tuple[CaseStore, CaseInvestigationService]:
    settings = get_settings()
    store = VectorStore.load(settings.embedding_model_name, index_dir or settings.index_dir)
    pipeline = build_default_pipeline(store, settings)
    contextualizer = AlertContextualizer(settings.summarizer_model_name)
    case_store = CaseStore(settings.cases_db_path)
    case_store.init_db()
    svc = CaseInvestigationService(case_store, pipeline, contextualizer, settings)
    return case_store, svc


def _parse_tags(raw: Optional[List[str]]) -> List[str]:
    if not raw:
        return []
    out: List[str] = []
    for chunk in raw:
        for part in chunk.split(","):
            t = part.strip()
            if t:
                out.append(t)
    return out


def cmd_create(args: argparse.Namespace) -> int:
    case_store, _svc = _load_stack(args.index_dir)
    body = CaseCreate(
        title=args.title,
        status=CaseStatus(args.status),
        severity=CaseSeverity(args.severity) if args.severity else None,
        owner=args.owner,
        tags=_parse_tags(args.tag),
        summary=args.summary,
        external_refs=_parse_external_refs(args.ref),
    )
    detail = case_store.create_case(body)
    print(json.dumps(detail.model_dump(), indent=2))
    return 0


def _parse_external_refs(pairs: Optional[List[str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    if not pairs:
        return out
    for p in pairs:
        if "=" not in p:
            raise SystemExit(f"Invalid --ref {p!r}, expected key=value")
        k, v = p.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def cmd_list(args: argparse.Namespace) -> int:
    case_store, _svc = _load_stack(args.index_dir)
    params = CaseListParams(
        status=CaseStatus(args.status) if args.status else None,
        owner=args.owner,
        title_contains=args.title_contains,
        limit=args.limit,
        offset=args.offset,
    )
    rows = case_store.list_cases(params)
    print(json.dumps([r.model_dump() for r in rows], indent=2))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    case_store, _svc = _load_stack(args.index_dir)
    row = case_store.get_case(args.case_id)
    if row is None:
        print("Case not found", file=sys.stderr)
        return 1
    print(json.dumps(row.model_dump(), indent=2))
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    case_store, _svc = _load_stack(args.index_dir)
    data: dict[str, Any] = {}
    if args.title is not None:
        data["title"] = args.title
    if args.status is not None:
        data["status"] = CaseStatus(args.status)
    if args.severity is not None:
        data["severity"] = CaseSeverity(args.severity)
    if args.owner is not None:
        data["owner"] = args.owner
    if args.tags is not None:
        data["tags"] = _parse_tags(args.tags)
    if args.summary is not None:
        data["summary"] = args.summary
    if not data:
        print("No fields to update", file=sys.stderr)
        return 1
    try:
        detail = case_store.update_case(args.case_id, CaseUpdate(**data))
    except Exception as exc:  # noqa: BLE001
        print(exc, file=sys.stderr)
        return 1
    print(json.dumps(detail.model_dump(), indent=2))
    return 0


def cmd_note(args: argparse.Namespace) -> int:
    case_store, svc = _load_stack(args.index_dir)
    try:
        detail = svc.add_note(args.case_id, NoteCreate(title=args.title, body=args.body))
    except Exception as exc:  # noqa: BLE001
        print(exc, file=sys.stderr)
        return 1
    print(json.dumps(detail.model_dump(), indent=2))
    return 0


def cmd_triage_snapshot(args: argparse.Namespace) -> int:
    case_store, svc = _load_stack(args.index_dir)
    settings = get_settings()
    top_k = args.top_k or settings.search_top_k
    opts = RetrievalOptions(
        retrieve_k=args.retrieve_k,
        use_rerank=args.rerank,
        narrow_by_ioc_overlap=args.ioc_narrow,
    )
    try:
        payload, detail = svc.run_triage_and_attach(args.case_id, args.alert, top_k, opts)
    except Exception as exc:  # noqa: BLE001
        print(exc, file=sys.stderr)
        return 1
    print(json.dumps({"triage": payload.model_dump(), "case": detail.model_dump()}, indent=2))
    return 0


def cmd_search_run(args: argparse.Namespace) -> int:
    case_store, svc = _load_stack(args.index_dir)
    settings = get_settings()
    top_k = args.top_k or settings.search_top_k
    opts = RetrievalOptions(
        retrieve_k=args.retrieve_k,
        use_rerank=args.rerank,
        narrow_by_ioc_overlap=args.ioc_narrow,
    )
    try:
        detail = svc.run_search_and_attach(args.case_id, args.query, top_k, opts)
    except Exception as exc:  # noqa: BLE001
        print(exc, file=sys.stderr)
        return 1
    print(json.dumps(detail.model_dump(), indent=2))
    return 0


def cmd_search_attach_json(args: argparse.Namespace) -> int:
    case_store, svc = _load_stack(args.index_dir)
    raw = Path(args.results_json).read_text(encoding="utf-8")
    results_obj = json.loads(raw)
    if not isinstance(results_obj, list):
        print("JSON root must be a list of hit objects", file=sys.stderr)
        return 1
    body = SearchSnapshotCreate(query=args.query, top_k=args.top_k, results=results_obj)
    try:
        detail = svc.attach_search_snapshot(args.case_id, body)
    except Exception as exc:  # noqa: BLE001
        print(exc, file=sys.stderr)
        return 1
    print(json.dumps(detail.model_dump(), indent=2))
    return 0


def cmd_iocs(args: argparse.Namespace) -> int:
    _case_store, svc = _load_stack(args.index_dir)
    try:
        agg = svc.aggregate_iocs(args.case_id)
    except Exception as exc:  # noqa: BLE001
        print(exc, file=sys.stderr)
        return 1
    print(json.dumps(agg.model_dump(), indent=2))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    case_store, svc = _load_stack(args.index_dir)
    detail = case_store.get_case(args.case_id)
    if detail is None:
        print("Case not found", file=sys.stderr)
        return 1
    agg = svc.aggregate_iocs(args.case_id)
    html_out = render_case_pack_html(detail, agg)
    Path(args.out).write_text(html_out, encoding="utf-8")
    print("Wrote", args.out)
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    case_store, _svc = _load_stack(args.index_dir)
    if not args.yes:
        print("Refusing to delete without --yes", file=sys.stderr)
        return 1
    if case_store.delete_case(args.case_id):
        print("Deleted", args.case_id)
        return 0
    print("Case not found", file=sys.stderr)
    return 1


def _retrieval_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--top-k", type=int, default=None)
    p.add_argument("--retrieve-k", type=int, default=None)
    p.add_argument("--rerank", action="store_true", help="Enable cross-encoder rerank")
    p.add_argument("--ioc-narrow", action="store_true", help="Narrow by IOC overlap")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage SOC investigation cases (SQLite + optional index)")
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=None,
        help="FAISS index directory (for triage/search-run only)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_c = sub.add_parser("create", help="Open a new case")
    p_c.add_argument("title", type=str)
    p_c.add_argument("--status", default="open", choices=[s.value for s in CaseStatus])
    p_c.add_argument("--severity", default=None, choices=[s.value for s in CaseSeverity])
    p_c.add_argument("--owner", default=None)
    p_c.add_argument("--tag", action="append", default=None, help="Repeatable or comma-separated via one value")
    p_c.add_argument("--summary", default=None)
    p_c.add_argument("--ref", action="append", default=None, metavar="KEY=VAL", help="External reference")
    p_c.set_defaults(func=cmd_create)

    p_l = sub.add_parser("list", help="List cases")
    p_l.add_argument("--status", default=None, choices=[s.value for s in CaseStatus])
    p_l.add_argument("--owner", default=None)
    p_l.add_argument("--title-contains", default=None)
    p_l.add_argument("--limit", type=int, default=50)
    p_l.add_argument("--offset", type=int, default=0)
    p_l.set_defaults(func=cmd_list)

    p_s = sub.add_parser("show", help="Show case JSON including timeline")
    p_s.add_argument("case_id", type=str)
    p_s.set_defaults(func=cmd_show)

    p_u = sub.add_parser("update", help="Patch case metadata")
    p_u.add_argument("case_id", type=str)
    p_u.add_argument("--title", default=None)
    p_u.add_argument("--status", default=None, choices=[s.value for s in CaseStatus])
    p_u.add_argument("--severity", default=None, choices=[s.value for s in CaseSeverity])
    p_u.add_argument("--owner", default=None)
    p_u.add_argument("--tags", action="append", default=None)
    p_u.add_argument("--summary", default=None)
    p_u.set_defaults(func=cmd_update)

    p_n = sub.add_parser("note", help="Append a timeline note")
    p_n.add_argument("case_id", type=str)
    p_n.add_argument("body", type=str)
    p_n.add_argument("--title", default=None)
    p_n.set_defaults(func=cmd_note)

    p_t = sub.add_parser("triage-snapshot", help="Run retrieval + brief and attach to case")
    p_t.add_argument("case_id", type=str)
    p_t.add_argument("alert", type=str)
    _retrieval_flags(p_t)
    p_t.set_defaults(func=cmd_triage_snapshot)

    p_q = sub.add_parser("search-run", help="Run vector search and attach hits to case")
    p_q.add_argument("case_id", type=str)
    p_q.add_argument("query", type=str)
    _retrieval_flags(p_q)
    p_q.set_defaults(func=cmd_search_run)

    p_j = sub.add_parser("search-attach-json", help="Attach precomputed hit JSON to case")
    p_j.add_argument("case_id", type=str)
    p_j.add_argument("query", type=str)
    p_j.add_argument("results_json", type=Path)
    p_j.add_argument("--top-k", type=int, default=10)
    p_j.set_defaults(func=cmd_search_attach_json)

    p_i = sub.add_parser("iocs", help="Print IOC rollup for case text + timeline")
    p_i.add_argument("case_id", type=str)
    p_i.set_defaults(func=cmd_iocs)

    p_e = sub.add_parser("export", help="Write HTML case pack")
    p_e.add_argument("case_id", type=str)
    p_e.add_argument("--out", type=Path, required=True)
    p_e.set_defaults(func=cmd_export)

    p_d = sub.add_parser("delete", help="Delete case and timeline")
    p_d.add_argument("case_id", type=str)
    p_d.add_argument("--yes", action="store_true")
    p_d.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
