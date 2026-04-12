"""MITRE ATT&CK–oriented mapping helpers for SOC alerts and case text.

Maps free-text alerts (plus optional retrieval context) to likely Enterprise
techniques using a bundled, keyword-scored catalogue. This is heuristic
coverage guidance—not a substitute for human attribution or official intel.
"""

from app.mitre.mapper import MitreMapper, get_default_mapper, map_alert_with_hits, map_text_to_techniques
from app.mitre.models import MitreMapOptions, MitreMapResult, TechniqueHit, TacticSummary, fuse_context_blocks

__all__ = [
    "MitreMapper",
    "MitreMapOptions",
    "MitreMapResult",
    "TacticSummary",
    "TechniqueHit",
    "fuse_context_blocks",
    "get_default_mapper",
    "map_alert_with_hits",
    "map_text_to_techniques",
]
