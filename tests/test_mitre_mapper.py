from __future__ import annotations

from app.mitre.mapper import MitreMapper, map_alert_with_hits, map_text_to_techniques
from app.mitre.models import MitreMapOptions, fuse_context_blocks
from app.mitre.textutil import normalize_for_match


def test_normalize_for_match_strips_accents() -> None:
    assert "credential" in normalize_for_match("Crédential")


def test_fuse_context_blocks_respects_max_chars() -> None:
    a = "x" * 30
    b = "y" * 30
    fused = fuse_context_blocks([a, b], max_chars=40)
    assert len(fused) <= 40


def test_map_text_powershell_finds_execution_techniques() -> None:
    text = "User ran encoded powershell -enc abc with suspicious cmdlet invoke-expression"
    res = map_text_to_techniques(text, options=MitreMapOptions(top_n=8, min_confidence=0.01))
    ids = {h.technique_id for h in res.hits}
    assert "T1059" in ids or "T1059.001" in ids


def test_map_alert_with_hits_merges_passages() -> None:
    alert = "rdp lateral movement to file server"
    ctx = ["mstsc.exe connected over port 3389", "routine windows update"]
    res = map_alert_with_hits(alert, ctx, options=MitreMapOptions(top_n=15, min_confidence=0.01))
    ids = {h.technique_id for h in res.hits}
    assert "T1021.001" in ids or "T1021" in ids


def test_mapper_respects_top_n() -> None:
    mapper = MitreMapper()
    blob = "powershell mimikatz lsass dump ransomware encrypted files dns tunnel https beacon"
    res = mapper.map_text(blob, options=MitreMapOptions(top_n=3, min_confidence=0.0))
    assert len(res.hits) <= 3


def test_confidence_sums_normalized() -> None:
    res = map_text_to_techniques(
        "powershell and cmd and wmi subscription",
        options=MitreMapOptions(top_n=20, min_confidence=0.0),
    )
    assert res.hits
    total_conf = sum(h.confidence for h in res.hits)
    assert abs(total_conf - 1.0) < 0.02  # confidences are rounded for API payloads
