from __future__ import annotations

from enum import Enum


class CaseStatus(str, Enum):
    """Lifecycle state for an analyst-owned investigation case."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    CLOSED = "closed"


class CaseSeverity(str, Enum):
    """Optional priority / impact hint for routing and reporting."""

    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TimelineKind(str, Enum):
    """Types of entries appended to a case timeline."""

    NOTE = "note"
    STATUS_CHANGE = "status_change"
    TRIAGE_SNAPSHOT = "triage_snapshot"
    SEARCH_SNAPSHOT = "search_snapshot"
    IOC_SIGNAL = "ioc_signal"
    MITRE_MAPPING = "mitre_mapping"


SCHEMA_VERSION = 1
