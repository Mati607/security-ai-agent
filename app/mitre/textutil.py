from __future__ import annotations

import re
import unicodedata
from typing import Iterable, List


_WS_RE = re.compile(r"\s+")
_NON_ALNUM_BOUNDARY = re.compile(r"[^a-z0-9./\\_-]+", re.IGNORECASE)


def normalize_for_match(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace — stable substring search."""

    if not text:
        return ""
    nf = unicodedata.normalize("NFKD", text)
    ascii_fold = "".join(c for c in nf if not unicodedata.combining(c))
    lowered = ascii_fold.lower()
    return _WS_RE.sub(" ", lowered).strip()


def split_context_windows(text: str, window: int = 256) -> List[str]:
    """Rough overlapping windows for long inputs (mapper uses full text too)."""

    n = len(text)
    if n <= window:
        return [text] if text else []
    out: List[str] = []
    step = max(window // 2, 64)
    for i in range(0, n, step):
        out.append(text[i : i + window])
        if i + window >= n:
            break
    return out


def count_bounded_substring_occurrences(
    haystack: str,
    needle: str,
    cap: int,
) -> int:
    """Count non-overlapping occurrences of needle in haystack, capped at `cap`."""

    if not needle or not haystack:
        return 0
    count = 0
    start = 0
    nlen = len(needle)
    while count < cap:
        pos = haystack.find(needle, start)
        if pos < 0:
            break
        count += 1
        start = pos + nlen
    return count


def keyword_variants(term: str) -> Iterable[str]:
    """Yield the normalized term plus a few delimiter-relaxed variants."""

    t = normalize_for_match(term)
    if not t:
        return
    yield t
    compact = _NON_ALNUM_BOUNDARY.sub("", t)
    if compact and compact != t:
        yield compact
    if " " in t:
        yield t.replace(" ", "")
    if "/" in t:
        yield t.replace("/", "\\")
        yield t.replace("/", " ")
