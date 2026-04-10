from __future__ import annotations

import pytest

from app.indexing.search_filters import (
    SearchFilterSpec,
    describe_filter_spec,
    document_matches_filters,
    extract_query_signals,
    filter_hits,
    filter_hits_by_ioc_overlap,
    filter_spec_from_mapping,
    hit_text_matches_any_needle,
)
from app.indexing.vector_store import Document


def _doc(**kwargs) -> Document:
    defaults = {"doc_id": "id1", "text": "hello world", "metadata": {}}
    defaults.update(kwargs)
    return Document(**defaults)


def test_min_vector_score_filters_low_scores() -> None:
    spec = SearchFilterSpec(min_vector_score=0.5)
    d = _doc()
    assert document_matches_filters(0.4, d, spec) is False
    assert document_matches_filters(0.6, d, spec) is True


def test_num_events_bounds() -> None:
    spec = SearchFilterSpec(min_num_events=5, max_num_events=20)
    d = _doc(metadata={"num_events": 4})
    assert document_matches_filters(1.0, d, spec) is False
    d2 = _doc(metadata={"num_events": 10})
    assert document_matches_filters(1.0, d2, spec) is True
    d3 = _doc(metadata={"num_events": 25})
    assert document_matches_filters(1.0, d3, spec) is False


def test_num_events_missing_fails_min() -> None:
    spec = SearchFilterSpec(min_num_events=1)
    d = _doc(metadata={})
    assert document_matches_filters(1.0, d, spec) is False


def test_group_key_contains_case_insensitive() -> None:
    spec = SearchFilterSpec(group_key_contains="power")
    d = _doc(metadata={"key": r"C:\Windows\PowerShell.exe"})
    assert document_matches_filters(1.0, d, spec) is True


def test_doc_id_contains() -> None:
    spec = SearchFilterSpec(doc_id_contains="HOST")
    d = _doc(doc_id="workstation-HOST-12")
    assert document_matches_filters(1.0, d, spec) is True


def test_metadata_equals_and_contains() -> None:
    spec = SearchFilterSpec(
        metadata_equals={"group": "actorname"},
        metadata_contains={"key": "svchost"},
    )
    d = _doc(metadata={"group": "actorname", "key": r"C:\svchost.exe"})
    assert document_matches_filters(1.0, d, spec) is True
    d2 = _doc(metadata={"group": "other", "key": r"C:\svchost.exe"})
    assert document_matches_filters(1.0, d2, spec) is False


def test_timestamp_after_uses_last_timestamp() -> None:
    spec = SearchFilterSpec(timestamp_after="2024-01-10T11:00:00Z")
    d = _doc(metadata={"last_timestamp": "2024-01-10T12:00:00Z"})
    assert document_matches_filters(1.0, d, spec) is True
    d2 = _doc(metadata={"last_timestamp": "2024-01-10T10:00:00Z"})
    assert document_matches_filters(1.0, d2, spec) is False


def test_timestamp_before_uses_first_timestamp() -> None:
    spec = SearchFilterSpec(timestamp_before="2024-01-10T10:00:00Z")
    d = _doc(metadata={"first_timestamp": "2024-01-09T12:00:00Z"})
    assert document_matches_filters(1.0, d, spec) is True
    d2 = _doc(metadata={"first_timestamp": "2024-01-11T12:00:00Z"})
    assert document_matches_filters(1.0, d2, spec) is False


def test_require_timestamp() -> None:
    spec = SearchFilterSpec(require_timestamp=True)
    d = _doc(metadata={})
    assert document_matches_filters(1.0, d, spec) is False
    d2 = _doc(metadata={"first_timestamp": "2024-01-01T00:00:00Z"})
    assert document_matches_filters(1.0, d2, spec) is True


def test_filter_hits_none_spec_is_passthrough() -> None:
    hits = [(1.0, _doc()), (0.5, _doc(doc_id="2"))]
    assert filter_hits(hits, None) == hits


def test_filter_hits_applies_spec() -> None:
    spec = SearchFilterSpec(min_num_events=5)
    hits = [
        (1.0, _doc(doc_id="a", metadata={"num_events": 10})),
        (0.9, _doc(doc_id="b", metadata={"num_events": 1})),
    ]
    out = filter_hits(hits, spec)
    assert [d.doc_id for _, d in out] == ["a"]


def test_describe_filter_spec_empty() -> None:
    assert describe_filter_spec(SearchFilterSpec()) == "(no filters)"


def test_describe_filter_spec_nonempty() -> None:
    s = SearchFilterSpec(min_num_events=3, group_key_contains="foo")
    text = describe_filter_spec(s)
    assert "events>=3" in text
    assert "key~'foo'" in text


def test_filter_spec_from_mapping_coercion() -> None:
    spec = filter_spec_from_mapping(
        {
            "min_vector_score": "0.25",
            "min_num_events": "2",
            "metadata_equals": {"group": "actorname"},
            "require_timestamp": True,
        }
    )
    assert spec.min_vector_score == 0.25
    assert spec.min_num_events == 2
    assert spec.metadata_equals["group"] == "actorname"
    assert spec.require_timestamp is True


def test_filter_spec_from_mapping_rejects_bad_meta_equals() -> None:
    with pytest.raises(TypeError):
        filter_spec_from_mapping({"metadata_equals": "nope"})


def test_extract_query_signals_ipv4_and_hash_and_domain() -> None:
    text = (
        "Beacon to 198.51.100.10 and evil.example.com "
        "with file hash e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    sig = extract_query_signals(text)
    assert "198.51.100.10" in sig.ipv4
    assert "evil.example.com" in sig.domains
    assert (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" in sig.sha256
    )


def test_hit_text_matches_any_needle() -> None:
    d = _doc(text="hello 10.0.0.5 world", metadata={"note": "none"})
    assert hit_text_matches_any_needle(d, ["10.0.0.5"]) is True
    assert hit_text_matches_any_needle(d, ["10.0.0.6"]) is False


def test_filter_hits_by_ioc_overlap_noop_without_iocs() -> None:
    hits = [(1.0, _doc(text="no indicators here"))]
    assert filter_hits_by_ioc_overlap(hits, "plain text alert") == hits


def test_filter_hits_by_ioc_overlap_keeps_overlap() -> None:
    hits = [
        (1.0, _doc(doc_id="a", text="random noise")),
        (0.9, _doc(doc_id="b", text="saw 203.0.113.1 in logs")),
    ]
    out = filter_hits_by_ioc_overlap(hits, "investigate 203.0.113.1")
    assert [d.doc_id for _, d in out] == ["b"]


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("min_vector_score", None, None),
        ("min_num_events", "", None),
        ("group_key_contains", "", None),
    ],
)
def test_filter_spec_from_mapping_optional_blanks(field: str, value: object, expected: object) -> None:
    spec = filter_spec_from_mapping({field: value})
    assert getattr(spec, field) == expected


def test_timestamp_after_fallback_to_first_timestamp() -> None:
    spec = SearchFilterSpec(timestamp_after="2024-01-01T00:00:00Z")
    d = _doc(metadata={"first_timestamp": "2024-01-02T00:00:00Z", "last_timestamp": None})
    assert document_matches_filters(1.0, d, spec) is True


def test_timestamp_before_fallback_to_last_timestamp() -> None:
    spec = SearchFilterSpec(timestamp_before="2024-02-01T00:00:00Z")
    d = _doc(metadata={"first_timestamp": None, "last_timestamp": "2024-01-15T00:00:00Z"})
    assert document_matches_filters(1.0, d, spec) is True


def test_group_key_contains_blank_skips_constraint() -> None:
    spec = SearchFilterSpec(group_key_contains="   ")
    d = _doc(metadata={"key": "anything"})
    assert document_matches_filters(1.0, d, spec) is True


def test_metadata_equals_missing_key_fails() -> None:
    spec = SearchFilterSpec(metadata_equals={"group": "actorname"})
    d = _doc(metadata={})
    assert document_matches_filters(1.0, d, spec) is False


def test_max_num_events_missing_fails() -> None:
    spec = SearchFilterSpec(max_num_events=5)
    d = _doc(metadata={})
    assert document_matches_filters(1.0, d, spec) is False


def test_filter_hits_preserves_order() -> None:
    spec = SearchFilterSpec(min_vector_score=0.0)
    hits = [(0.2, _doc(doc_id="z")), (0.8, _doc(doc_id="y"))]
    out = filter_hits(hits, spec)
    assert [d.doc_id for _, d in out] == ["z", "y"]
