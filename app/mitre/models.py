from __future__ import annotations

from typing import List, Optional, Sequence

from pydantic import BaseModel, Field


class TacticSummary(BaseModel):
    """High-level ATT&CK tactic the catalogue associates with techniques."""

    id: str = Field(..., description="Short tactic id, e.g. TA0002")
    name: str
    url: Optional[str] = Field(
        default=None,
        description="Optional link to MITRE's tactic page for analyst reference",
    )


class TechniqueHit(BaseModel):
    """A single scored technique inferred from alert or context text."""

    technique_id: str = Field(..., description="Technique or sub-technique id, e.g. T1059.001")
    name: str
    tactic_id: str
    tactic_name: str
    score: float = Field(..., ge=0.0, description="Unbounded raw match score before normalization")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized share of score mass among returned hits",
    )
    matched_keywords: List[str] = Field(
        default_factory=list,
        description="Distinct catalogue keywords that contributed to the score",
    )


class MitreMapOptions(BaseModel):
    """Tuning knobs for mapping runs (API, CLI, and services share these)."""

    top_n: int = Field(default=12, ge=1, le=64, description="Max techniques to return")
    min_confidence: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Drop hits whose normalized confidence falls below this threshold",
    )
    max_keyword_hits_per_term: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Cap repeated substring matches per keyword to limit spam",
    )


class MitreMapResult(BaseModel):
    """Full outcome of mapping one or more text blobs to techniques."""

    hits: List[TechniqueHit] = Field(default_factory=list)
    tactics_represented: List[TacticSummary] = Field(default_factory=list)
    source_excerpt: Optional[str] = Field(
        default=None,
        max_length=4096,
        description="Short preview of fused source text used for mapping",
    )


def fuse_context_blocks(blocks: Sequence[str], max_chars: int = 48_000) -> str:
    """Concatenate non-empty blocks with separators for a single mapper input."""

    parts: List[str] = []
    total = 0
    for raw in blocks:
        s = (raw or "").strip()
        if not s:
            continue
        chunk = s if total + len(s) <= max_chars else s[: max(0, max_chars - total)]
        if not chunk:
            break
        parts.append(chunk)
        total += len(chunk) + 2
        if total >= max_chars:
            break
    return "\n\n".join(parts)
