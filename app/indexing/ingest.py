from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

from .vector_store import Document


EVENT_TYPES = {
    "endpoint.event.crossproc": {
        "edge": "crossproc",
        "object": "PROCESS",
        "child_id": "crossproc_guid",
        "child_label": "crossproc_name",
    },
    "endpoint.event.procstart": {
        "edge": "procstart",
        "object": "PROCESS",
        "child_id": "childproc_guid",
        "child_label": "childproc_name",
    },
    "endpoint.event.filemod": {
        "edge": "filemod",
        "object": "FILE",
        "child_id": "filemod_name",
        "child_label": "filemod_name",
    },
    "endpoint.event.netconn": {
        "edge": "netconn",
        "object": "SOCKET",
        "child_id": "remote_ip",
        "child_label": "remote_ip",
    },
    "endpoint.event.moduleload": {
        "edge": "modload",
        "object": "MODULE",
        "child_id": "modload_name",
        "child_label": "modload_name",
    },
}


def _format_event(record: Dict) -> str:
    return (
        f"{record['actorname']} performed {record['action']} "
        f"on {record['object']} named {record['objectname']}"
    )


def parse_jsonl_events(file_path: Path) -> List[Dict]:
    events: List[Dict] = []
    with Path(file_path).open("r", encoding="utf-8") as f:
        for line in f:
            doc = json.loads(line)
            timestamp = doc.get("device_timestamp")
            event_type = doc.get("type")
            if event_type not in EVENT_TYPES:
                continue
            spec = EVENT_TYPES[event_type]
            parent_node_id = doc.get("process_guid")
            parent_node_label = doc.get("process_path")
            child_node_id = doc.get(spec["child_id"])  # type: ignore
            child_node_label = doc.get(spec["child_label"])  # type: ignore
            event = {
                "action": spec["edge"],
                "actorID": parent_node_id,
                "objectID": child_node_id,
                "object": spec["object"],
                "actorname": parent_node_label,
                "objectname": child_node_label,
                "timestamp": timestamp,
            }
            events.append(event)
    return events


def documents_from_events(events: Iterable[Dict], grouping: str = "actorname") -> List[Document]:
    """Aggregate raw events into one `Document` per grouping key.

    Metadata includes coarse time bounds when timestamps are present on events,
    which enables server-side filtering during retrieval without re-parsing JSONL.
    """

    grouped_lines: Dict[str, List[str]] = defaultdict(list)
    grouped_ts: Dict[str, List[str]] = defaultdict(list)

    for e in events:
        key = str(e.get(grouping, "unknown"))
        grouped_lines[key].append(_format_event(e))
        ts = e.get("timestamp")
        if ts is not None:
            grouped_ts[key].append(str(ts))

    documents: List[Document] = []
    for key, sentences in grouped_lines.items():
        text = ". ".join(sorted(set(sentences)))
        ts_list = grouped_ts.get(key, [])
        first_ts = min(ts_list) if ts_list else None
        last_ts = max(ts_list) if ts_list else None
        metadata = {
            "group": grouping,
            "key": key,
            "num_events": len(sentences),
            "first_timestamp": first_ts,
            "last_timestamp": last_ts,
        }
        documents.append(Document(doc_id=key, text=text, metadata=metadata))
    return documents


def ingest_jsonl_logs(paths: Iterable[Path], grouping: str = "actorname") -> List[Document]:
    all_events: List[Dict] = []
    for p in paths:
        all_events.extend(parse_jsonl_events(Path(p)))
    return documents_from_events(all_events, grouping=grouping)


