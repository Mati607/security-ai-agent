from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class TacticRecord:
    """Enterprise ATT&CK tactic metadata bundled for offline use."""

    id: str
    name: str
    url: str


# Enterprise tactics (MITRE ATT&CK). URLs point to the public tactic pages.
_ENTERPRISE_TACTICS: tuple[TacticRecord, ...] = (
    TacticRecord(
        id="TA0043",
        name="Reconnaissance",
        url="https://attack.mitre.org/tactics/TA0043/",
    ),
    TacticRecord(
        id="TA0042",
        name="Resource Development",
        url="https://attack.mitre.org/tactics/TA0042/",
    ),
    TacticRecord(
        id="TA0001",
        name="Initial Access",
        url="https://attack.mitre.org/tactics/TA0001/",
    ),
    TacticRecord(
        id="TA0002",
        name="Execution",
        url="https://attack.mitre.org/tactics/TA0002/",
    ),
    TacticRecord(
        id="TA0003",
        name="Persistence",
        url="https://attack.mitre.org/tactics/TA0003/",
    ),
    TacticRecord(
        id="TA0004",
        name="Privilege Escalation",
        url="https://attack.mitre.org/tactics/TA0004/",
    ),
    TacticRecord(
        id="TA0005",
        name="Defense Evasion",
        url="https://attack.mitre.org/tactics/TA0005/",
    ),
    TacticRecord(
        id="TA0006",
        name="Credential Access",
        url="https://attack.mitre.org/tactics/TA0006/",
    ),
    TacticRecord(
        id="TA0007",
        name="Discovery",
        url="https://attack.mitre.org/tactics/TA0007/",
    ),
    TacticRecord(
        id="TA0008",
        name="Lateral Movement",
        url="https://attack.mitre.org/tactics/TA0008/",
    ),
    TacticRecord(
        id="TA0009",
        name="Collection",
        url="https://attack.mitre.org/tactics/TA0009/",
    ),
    TacticRecord(
        id="TA0011",
        name="Command and Control",
        url="https://attack.mitre.org/tactics/TA0011/",
    ),
    TacticRecord(
        id="TA0010",
        name="Exfiltration",
        url="https://attack.mitre.org/tactics/TA0010/",
    ),
    TacticRecord(
        id="TA0040",
        name="Impact",
        url="https://attack.mitre.org/tactics/TA0040/",
    ),
)

_TACTIC_BY_ID: Dict[str, TacticRecord] = {t.id: t for t in _ENTERPRISE_TACTICS}


def all_tactics() -> List[TacticRecord]:
    """Return tactics in canonical catalogue order."""

    return list(_ENTERPRISE_TACTICS)


def get_tactic(tactic_id: str) -> Optional[TacticRecord]:
    """Lookup tactic by id, or None if unknown to this bundle."""

    return _TACTIC_BY_ID.get(tactic_id)
