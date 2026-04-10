from __future__ import annotations

from app.indexing.ingest import documents_from_events


def test_documents_from_events_include_timestamp_bounds() -> None:
    events = [
        {
            "action": "netconn",
            "actorID": "p1",
            "objectID": "1.1.1.1",
            "object": "SOCKET",
            "actorname": r"C:\a.exe",
            "objectname": "1.1.1.1",
            "timestamp": "2024-01-02T00:00:00Z",
        },
        {
            "action": "netconn",
            "actorID": "p1",
            "objectID": "2.2.2.2",
            "object": "SOCKET",
            "actorname": r"C:\a.exe",
            "objectname": "2.2.2.2",
            "timestamp": "2024-01-01T00:00:00Z",
        },
    ]
    docs = documents_from_events(events, grouping="actorname")
    assert len(docs) == 1
    meta = docs[0].metadata
    assert meta["first_timestamp"] == "2024-01-01T00:00:00Z"
    assert meta["last_timestamp"] == "2024-01-02T00:00:00Z"
    assert meta["num_events"] == 2


def test_documents_without_timestamps_leave_bounds_none() -> None:
    events = [
        {
            "action": "netconn",
            "actorID": "p1",
            "objectID": "1.1.1.1",
            "object": "SOCKET",
            "actorname": r"C:\a.exe",
            "objectname": "1.1.1.1",
            "timestamp": None,
        },
    ]
    docs = documents_from_events(events, grouping="actorname")
    assert docs[0].metadata["first_timestamp"] is None
    assert docs[0].metadata["last_timestamp"] is None
