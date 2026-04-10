from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple

from .vector_store import Document


@dataclass
class SearchFilterSpec:
    """Declarative filters applied to vector hits after FAISS retrieval.

    All conditions are combined with logical AND. String comparisons for
    timestamps assume lexicographic ordering matches chronological ordering
    (true for ISO-8601 strings).
    """

    min_vector_score: Optional[float] = None
    min_num_events: Optional[int] = None
    max_num_events: Optional[int] = None
    group_key_contains: Optional[str] = None
    doc_id_contains: Optional[str] = None
    metadata_equals: Mapping[str, str] = field(default_factory=dict)
    metadata_contains: Mapping[str, str] = field(default_factory=dict)
    timestamp_after: Optional[str] = None
    timestamp_before: Optional[str] = None
    require_timestamp: bool = False

    def normalized(self) -> "SearchFilterSpec":
        """Return a copy with trivial defaults removed for logging and tests."""
        return SearchFilterSpec(
            min_vector_score=self.min_vector_score,
            min_num_events=self.min_num_events,
            max_num_events=self.max_num_events,
            group_key_contains=self.group_key_contains,
            doc_id_contains=self.doc_id_contains,
            metadata_equals=dict(self.metadata_equals),
            metadata_contains=dict(self.metadata_contains),
            timestamp_after=self.timestamp_after,
            timestamp_before=self.timestamp_before,
            require_timestamp=self.require_timestamp,
        )


def _get_meta_int(meta: Mapping[str, Any], key: str) -> Optional[int]:
    raw = meta.get(key)
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _get_meta_str(meta: Mapping[str, Any], key: str) -> Optional[str]:
    raw = meta.get(key)
    if raw is None:
        return None
    return str(raw)


def _normalize_contains(pattern: Optional[str]) -> Optional[str]:
    if pattern is None:
        return None
    p = pattern.strip()
    return p or None


def _metadata_value_contains(meta: Mapping[str, Any], key: str, needle: str) -> bool:
    hay = meta.get(key)
    if hay is None:
        return False
    return needle.lower() in str(hay).lower()


def _metadata_equals(meta: Mapping[str, Any], key: str, expected: str) -> bool:
    actual = meta.get(key)
    if actual is None:
        return False
    return str(actual) == expected


def document_matches_filters(
    score: float,
    doc: Document,
    spec: SearchFilterSpec,
) -> bool:
    """Return True if (score, doc) satisfies every active constraint in spec."""

    if spec.min_vector_score is not None and score < spec.min_vector_score:
        return False

    meta = doc.metadata
    num_events = _get_meta_int(meta, "num_events")
    if spec.min_num_events is not None:
        if num_events is None or num_events < spec.min_num_events:
            return False
    if spec.max_num_events is not None:
        if num_events is None or num_events > spec.max_num_events:
            return False

    gkc = _normalize_contains(spec.group_key_contains)
    if gkc is not None:
        key = _get_meta_str(meta, "key")
        if key is None or gkc.lower() not in key.lower():
            return False

    dic = _normalize_contains(spec.doc_id_contains)
    if dic is not None and dic.lower() not in doc.doc_id.lower():
        return False

    for mk, mv in spec.metadata_equals.items():
        if not _metadata_equals(meta, mk, mv):
            return False

    for mk, needle in spec.metadata_contains.items():
        if not _metadata_value_contains(meta, mk, needle):
            return False

    first_ts = _get_meta_str(meta, "first_timestamp")
    last_ts = _get_meta_str(meta, "last_timestamp")

    if spec.require_timestamp and first_ts is None and last_ts is None:
        return False

    if spec.timestamp_after is not None:
        bound = spec.timestamp_after
        if last_ts is not None:
            if last_ts <= bound:
                return False
        elif first_ts is not None:
            if first_ts <= bound:
                return False
        else:
            return False

    if spec.timestamp_before is not None:
        bound = spec.timestamp_before
        if first_ts is not None:
            if first_ts >= bound:
                return False
        elif last_ts is not None:
            if last_ts >= bound:
                return False
        else:
            return False

    return True


def filter_hits(
    hits: Iterable[Tuple[float, Document]],
    spec: Optional[SearchFilterSpec],
) -> List[Tuple[float, Document]]:
    """Apply `spec` to hits; pass-through when spec is None."""

    if spec is None:
        return list(hits)
    return [(s, d) for s, d in hits if document_matches_filters(s, d, spec)]


def merge_filter_dicts(
    base: MutableMapping[str, Any],
    overrides: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Shallow merge for building filter specs from API JSON fragments."""

    out = dict(base)
    if overrides:
        out.update(dict(overrides))
    return out


def describe_filter_spec(spec: SearchFilterSpec) -> str:
    """Human-readable single-line summary for logs and CLI output."""

    parts: List[str] = []
    if spec.min_vector_score is not None:
        parts.append(f"score>={spec.min_vector_score}")
    if spec.min_num_events is not None:
        parts.append(f"events>={spec.min_num_events}")
    if spec.max_num_events is not None:
        parts.append(f"events<={spec.max_num_events}")
    if spec.group_key_contains:
        parts.append(f"key~{spec.group_key_contains!r}")
    if spec.doc_id_contains:
        parts.append(f"id~{spec.doc_id_contains!r}")
    if spec.metadata_equals:
        parts.append("meta=" + ",".join(f"{k}={v}" for k, v in spec.metadata_equals.items()))
    if spec.metadata_contains:
        parts.append(
            "meta~"
            + ",".join(f"{k}~{v}" for k, v in spec.metadata_contains.items())
        )
    if spec.timestamp_after:
        parts.append(f"ts>{spec.timestamp_after!r}")
    if spec.timestamp_before:
        parts.append(f"ts<{spec.timestamp_before!r}")
    if spec.require_timestamp:
        parts.append("ts_required")
    return "; ".join(parts) if parts else "(no filters)"


def filter_spec_from_mapping(data: Mapping[str, Any]) -> SearchFilterSpec:
    """Build SearchFilterSpec from a plain dict (e.g. JSON body)."""

    def opt_str(key: str) -> Optional[str]:
        v = data.get(key)
        if v is None or v == "":
            return None
        return str(v)

    def opt_float(key: str) -> Optional[float]:
        v = data.get(key)
        if v is None or v == "":
            return None
        return float(v)

    def opt_int(key: str) -> Optional[int]:
        v = data.get(key)
        if v is None or v == "":
            return None
        return int(v)

    meta_eq = data.get("metadata_equals") or {}
    meta_sub = data.get("metadata_contains") or {}
    if not isinstance(meta_eq, Mapping):
        raise TypeError("metadata_equals must be an object")
    if not isinstance(meta_sub, Mapping):
        raise TypeError("metadata_contains must be an object")

    return SearchFilterSpec(
        min_vector_score=opt_float("min_vector_score"),
        min_num_events=opt_int("min_num_events"),
        max_num_events=opt_int("max_num_events"),
        group_key_contains=opt_str("group_key_contains"),
        doc_id_contains=opt_str("doc_id_contains"),
        metadata_equals={str(k): str(v) for k, v in meta_eq.items()},
        metadata_contains={str(k): str(v) for k, v in meta_sub.items()},
        timestamp_after=opt_str("timestamp_after"),
        timestamp_before=opt_str("timestamp_before"),
        require_timestamp=bool(data.get("require_timestamp", False)),
    )


# --- Heuristic IOC extraction (lightweight, no external deps) ---

_IPV4_RE = re.compile(
    r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])",
)
_SHA256_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")
_DOMAIN_RE = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b",
)


@dataclass
class ExtractedQuerySignals:
    """Structured hints parsed from free-text alerts or analyst queries."""

    ipv4: Tuple[str, ...] = ()
    sha256: Tuple[str, ...] = ()
    domains: Tuple[str, ...] = ()


def extract_query_signals(text: str) -> ExtractedQuerySignals:
    """Pull common IOC-shaped tokens from arbitrary alert text."""

    if not text:
        return ExtractedQuerySignals()
    ips = tuple(dict.fromkeys(m.group(0) for m in _IPV4_RE.finditer(text)))
    hashes = tuple(dict.fromkeys(m.group(0).lower() for m in _SHA256_RE.finditer(text)))
    domains = tuple(dict.fromkeys(m.group(0).lower() for m in _DOMAIN_RE.finditer(text)))
    return ExtractedQuerySignals(ipv4=ips, sha256=hashes, domains=domains)


def hit_text_matches_any_needle(doc: Document, needles: Iterable[str]) -> bool:
    """Case-insensitive substring match against document text and metadata values."""

    text_l = doc.text.lower()
    for n in needles:
        nl = n.lower()
        if nl in text_l:
            return True
        for _k, v in doc.metadata.items():
            if nl in str(v).lower():
                return True
    return False


def filter_hits_by_ioc_overlap(
    hits: List[Tuple[float, Document]],
    alert: str,
) -> List[Tuple[float, Document]]:
    """Keep hits whose text/metadata overlaps extracted IOCs from the alert.

    When no IOCs are extracted, returns the input list unchanged.
    """

    sig = extract_query_signals(alert)
    needles = list(sig.ipv4) + list(sig.sha256) + list(sig.domains)
    if not needles:
        return hits
    return [(s, d) for s, d in hits if hit_text_matches_any_needle(d, needles)]
