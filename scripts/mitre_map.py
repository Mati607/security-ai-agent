#!/usr/bin/env python3
"""CLI: map alert text or files to MITRE ATT&CK techniques (bundled keyword catalogue).

Examples:

  PYTHONPATH=. python scripts/mitre_map.py --text "encoded powershell beacon to https c2"

  PYTHONPATH=. python scripts/mitre_map.py --file alert.txt --top-n 8 --min-confidence 0.05

  cat logs/snippet.txt | PYTHONPATH=. python scripts/mitre_map.py --stdin
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from app.mitre.mapper import get_default_mapper
from app.mitre.models import MitreMapOptions, MitreMapResult


def _read_stdin(max_bytes: int) -> str:
    data = sys.stdin.buffer.read(max_bytes + 1)
    if len(data) > max_bytes:
        print("stdin exceeds --max-chars; truncating", file=sys.stderr)
    return data[:max_bytes].decode("utf-8", errors="replace")


def _read_file(path: Path, max_bytes: int) -> str:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        print(f"warning: truncating {path} to {max_bytes} bytes", file=sys.stderr)
        raw = raw[:max_bytes]
    return raw.decode("utf-8", errors="replace")


def _gather_text(args: argparse.Namespace) -> str:
    parts: List[str] = []
    if args.text:
        parts.append(args.text.strip())
    for p in args.file or []:
        parts.append(_read_file(Path(p), args.max_chars).strip())
    if args.stdin:
        parts.append(_read_stdin(args.max_chars).strip())
    return "\n\n".join(s for s in parts if s)


def _print_table(result: MitreMapResult) -> None:
    if not result.hits:
        print("No techniques met the confidence threshold.")
        return
    print(f"{'ID':<14} {'Confidence':>10}  {'Tactic':<28}  Name")
    print("-" * 90)
    for h in result.hits:
        tac = f"{h.tactic_name} ({h.tactic_id})"
        print(f"{h.technique_id:<14} {h.confidence:10.4f}  {tac:<28}  {h.name}")
        if h.matched_keywords:
            print(f"    terms: {', '.join(h.matched_keywords)}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", type=str, help="Inline alert or log text")
    parser.add_argument(
        "--file",
        action="append",
        metavar="PATH",
        help="Path to UTF-8 text (repeatable)",
    )
    parser.add_argument("--stdin", action="store_true", help="Read text from stdin")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=200_000,
        help="Maximum characters to read per file or stdin",
    )
    parser.add_argument("--top-n", type=int, default=12, help="Max techniques to return")
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.02,
        help="Drop hits below this normalized confidence",
    )
    parser.add_argument(
        "--max-keyword-hits",
        type=int,
        default=4,
        help="Cap substring hits per catalogue keyword",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit MitreMapResult as JSON instead of a text table",
    )
    args = parser.parse_args(argv)
    if not args.text and not args.file and not args.stdin:
        parser.error("Provide at least one of --text, --file, or --stdin")

    blob = _gather_text(args)
    if not blob.strip():
        print("error: no input text", file=sys.stderr)
        return 2

    opts = MitreMapOptions(
        top_n=args.top_n,
        min_confidence=args.min_confidence,
        max_keyword_hits_per_term=args.max_keyword_hits,
    )
    mapper = get_default_mapper()
    result = mapper.map_text(blob, options=opts)

    if args.json:
        print(json.dumps(result.model_dump(), indent=2))
    else:
        _print_table(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
