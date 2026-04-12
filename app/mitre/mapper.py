from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Set, Tuple

from app.mitre.models import MitreMapOptions, MitreMapResult, TechniqueHit, TacticSummary, fuse_context_blocks
from app.mitre.tactics import get_tactic
from app.mitre.techniques_catalog import TECHNIQUES, CatalogTechnique
from app.mitre.textutil import (
    count_bounded_substring_occurrences,
    keyword_variants,
    normalize_for_match,
)


class MitreMapper:
    """Score catalogue techniques against analyst text using keyword overlap."""

    def __init__(self, techniques: Sequence[CatalogTechnique] | None = None) -> None:
        self._techniques: Tuple[CatalogTechnique, ...] = tuple(techniques or TECHNIQUES)

    def map_text(self, text: str, options: MitreMapOptions | None = None) -> MitreMapResult:
        """Map a single fused string to the top techniques."""

        opts = options or MitreMapOptions()
        haystack = normalize_for_match(text)
        excerpt = haystack[:2000] if haystack else None

        raw_scores: List[Tuple[CatalogTechnique, float, List[str]]] = []
        for tech in self._techniques:
            score, matched = self._score_technique(haystack, tech, opts.max_keyword_hits_per_term)
            if score > 0:
                raw_scores.append((tech, score, matched))

        raw_scores.sort(key=lambda x: x[1], reverse=True)
        trimmed = raw_scores[: opts.top_n]
        total = sum(s for _, s, _ in trimmed) or 1.0

        hits: List[TechniqueHit] = []
        tactic_ids: Set[str] = set()
        for tech, sc, matched in trimmed:
            conf = sc / total
            if conf < opts.min_confidence:
                continue
            tac = get_tactic(tech.tactic_id)
            tactic_name = tac.name if tac else tech.tactic_id
            hits.append(
                TechniqueHit(
                    technique_id=tech.technique_id,
                    name=tech.name,
                    tactic_id=tech.tactic_id,
                    tactic_name=tactic_name,
                    score=round(sc, 4),
                    confidence=round(conf, 4),
                    matched_keywords=sorted(set(matched)),
                )
            )
            tactic_ids.add(tech.tactic_id)

        tactics_out = self._tactic_summaries(tactic_ids)
        return MitreMapResult(hits=hits, tactics_represented=tactics_out, source_excerpt=excerpt)

    def map_blocks(
        self,
        blocks: Sequence[str],
        *,
        options: MitreMapOptions | None = None,
        max_chars: int = 48_000,
    ) -> MitreMapResult:
        """Fuse multiple text blocks (alert, briefs, log lines) then map."""

        fused = fuse_context_blocks(blocks, max_chars=max_chars)
        return self.map_text(fused, options=options)

    def map_alert_with_hits(
        self,
        alert: str,
        retrieval_texts: Iterable[str],
        *,
        options: MitreMapOptions | None = None,
    ) -> MitreMapResult:
        """Fuse an alert with retrieved passages, then score techniques."""

        blocks: List[str] = [alert]
        blocks.extend(retrieval_texts)
        return self.map_blocks(blocks, options=options)

    def _tactic_summaries(self, tactic_ids: Set[str]) -> List[TacticSummary]:
        out: List[TacticSummary] = []
        for tid in sorted(tactic_ids):
            tac = get_tactic(tid)
            if tac is None:
                out.append(TacticSummary(id=tid, name=tid, url=None))
            else:
                out.append(TacticSummary(id=tac.id, name=tac.name, url=tac.url))
        return out

    def _score_technique(
        self,
        haystack: str,
        tech: CatalogTechnique,
        per_term_cap: int,
    ) -> Tuple[float, List[str]]:
        score = 0.0
        matched: List[str] = []
        seen_terms: Set[str] = set()

        for raw_kw in tech.keywords:
            best_local = 0.0
            best_label = raw_kw
            for variant in keyword_variants(raw_kw):
                if len(variant) < 3:
                    continue
                occ = count_bounded_substring_occurrences(haystack, variant, per_term_cap)
                if occ <= 0:
                    continue
                # Diminishing returns per keyword variant
                contrib = float(occ) / (1.0 + 0.25 * (occ - 1))
                if contrib > best_local:
                    best_local = contrib
                    best_label = raw_kw
            if best_local > 0 and best_label not in seen_terms:
                seen_terms.add(best_label)
                score += best_local + 0.15  # base bump so multi-keyword techniques surface
                matched.append(best_label)

        return score, matched


_DEFAULT_MAPPER: Optional[MitreMapper] = None


def get_default_mapper() -> MitreMapper:
    global _DEFAULT_MAPPER
    if _DEFAULT_MAPPER is None:
        _DEFAULT_MAPPER = MitreMapper()
    return _DEFAULT_MAPPER


def map_text_to_techniques(
    text: str,
    *,
    options: MitreMapOptions | None = None,
    mapper: MitreMapper | None = None,
) -> MitreMapResult:
    """Module-level helper using the process-wide default catalogue."""

    m = mapper or get_default_mapper()
    return m.map_text(text, options=options)


def map_alert_with_hits(
    alert: str,
    retrieval_texts: Iterable[str],
    *,
    options: MitreMapOptions | None = None,
    mapper: MitreMapper | None = None,
) -> MitreMapResult:
    """Convenience: fuse alert string with retrieved document passages."""

    m = mapper or get_default_mapper()
    return m.map_alert_with_hits(alert, retrieval_texts, options=options)
