from __future__ import annotations

from pathlib import Path

import pytest

from app.cases.constants import CaseStatus, TimelineKind
from app.cases.models import CaseCreate, CaseListParams, CaseUpdate
from app.cases.store import CaseStore, CaseStoreError


@pytest.fixture
def case_store(tmp_path: Path) -> CaseStore:
    db = tmp_path / "cases_unit.db"
    store = CaseStore(db)
    store.init_db()
    return store


def test_create_and_roundtrip(case_store: CaseStore) -> None:
    detail = case_store.create_case(
        CaseCreate(
            title="Beaconing on host-7",
            tags=["beacon", "tier1"],
            summary="Initial escalation from EDR.",
        )
    )
    assert detail.title == "Beaconing on host-7"
    assert detail.tags == ["beacon", "tier1"]
    assert detail.timeline == []

    again = case_store.get_case(detail.id)
    assert again is not None
    assert again.model_dump() == detail.model_dump()


def test_list_cases_filters(case_store: CaseStore) -> None:
    a = case_store.create_case(CaseCreate(title="Alpha open", status=CaseStatus.OPEN))
    b = case_store.create_case(CaseCreate(title="Beta closed", status=CaseStatus.CLOSED))

    open_only = case_store.list_cases(CaseListParams(status=CaseStatus.OPEN, limit=20))
    ids = {r.id for r in open_only}
    assert a.id in ids
    assert b.id not in ids

    hits = case_store.list_cases(CaseListParams(title_contains="Beta", limit=20))
    assert len(hits) == 1
    assert hits[0].id == b.id


def test_status_change_writes_timeline(case_store: CaseStore) -> None:
    d = case_store.create_case(CaseCreate(title="Track status"))
    case_store.update_case(d.id, CaseUpdate(status=CaseStatus.IN_PROGRESS))
    full = case_store.get_case(d.id)
    assert full is not None
    assert full.status == CaseStatus.IN_PROGRESS
    kinds = [e.kind for e in full.timeline]
    assert TimelineKind.STATUS_CHANGE in kinds


def test_add_timeline_and_foreign_key(case_store: CaseStore) -> None:
    d = case_store.create_case(CaseCreate(title="Notes"))
    case_store.add_timeline(
        d.id,
        kind=TimelineKind.NOTE,
        title="Shift handoff",
        body="Watch C2 at 203.0.113.50",
        payload=None,
    )
    full = case_store.get_case(d.id)
    assert full is not None
    assert len(full.timeline) == 1
    assert full.timeline[0].body is not None
    assert "203.0.113.50" in full.timeline[0].body


def test_update_case_missing_raises(case_store: CaseStore) -> None:
    with pytest.raises(CaseStoreError):
        case_store.update_case("nonexistent", CaseUpdate(title="x"))


def test_delete_case_cascades_timeline(case_store: CaseStore) -> None:
    d = case_store.create_case(CaseCreate(title="To delete"))
    case_store.add_timeline(d.id, kind=TimelineKind.NOTE, body="x")
    assert case_store.delete_case(d.id) is True
    assert case_store.get_case(d.id) is None
