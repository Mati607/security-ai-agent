from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.api.schemas import SearchRequest, TriageRequest, options_from_controls
from app.cases.constants import CaseStatus
from app.cases.export_html import render_case_pack_html
from app.cases.models import (
    CaseCreate,
    CaseDetail,
    CaseListParams,
    CaseSummary,
    CaseUpdate,
    IOCAggregate,
    NoteCreate,
    SearchSnapshotCreate,
)
from app.cases.service import CaseInvestigationService
from app.cases.store import CaseStore, CaseStoreError
from app.config import Settings


class IOCSignalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    body: Optional[str] = Field(default=None, max_length=65_536)


def create_cases_router(
    store: CaseStore,
    case_service: CaseInvestigationService,
    settings: Settings,
) -> APIRouter:
    router = APIRouter()

    def _nf() -> None:
        raise HTTPException(status_code=404, detail="case not found")

    @router.post("", response_model=CaseDetail)
    def create_case(body: CaseCreate) -> CaseDetail:
        return store.create_case(body)

    @router.get("", response_model=list[CaseSummary])
    def list_cases(
        status: Optional[CaseStatus] = None,
        owner: Optional[str] = None,
        title_contains: Optional[str] = Query(default=None, max_length=256),
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[CaseSummary]:
        params = CaseListParams(
            status=status,
            owner=owner,
            title_contains=title_contains,
            limit=limit,
            offset=offset,
        )
        return store.list_cases(params)

    @router.get("/{case_id}", response_model=CaseDetail)
    def get_case(case_id: str) -> CaseDetail:
        row = store.get_case(case_id)
        if row is None:
            _nf()
        return row

    @router.patch("/{case_id}", response_model=CaseDetail)
    def patch_case(case_id: str, body: CaseUpdate) -> CaseDetail:
        try:
            return store.update_case(case_id, body)
        except CaseStoreError:
            _nf()

    @router.post("/{case_id}/notes", response_model=CaseDetail)
    def add_note(case_id: str, body: NoteCreate) -> CaseDetail:
        try:
            return case_service.add_note(case_id, body)
        except CaseStoreError:
            _nf()

    @router.post("/{case_id}/snapshots/search", response_model=CaseDetail)
    def attach_search_snapshot(case_id: str, body: SearchSnapshotCreate) -> CaseDetail:
        try:
            return case_service.attach_search_snapshot(case_id, body)
        except CaseStoreError:
            _nf()

    @router.post("/{case_id}/snapshots/search-run", response_model=CaseDetail)
    def run_search_snapshot(case_id: str, body: SearchRequest) -> CaseDetail:
        top_k = body.top_k or settings.search_top_k
        opts = options_from_controls(body)
        try:
            return case_service.run_search_and_attach(case_id, body.query, top_k, opts)
        except CaseStoreError:
            _nf()

    @router.post("/{case_id}/snapshots/triage")
    def run_triage_snapshot(case_id: str, body: TriageRequest) -> dict:
        top_k = body.top_k or settings.search_top_k
        opts = options_from_controls(body)
        try:
            payload, detail = case_service.run_triage_and_attach(case_id, body.alert, top_k, opts)
        except CaseStoreError:
            _nf()
        return {
            "case": detail.model_dump(),
            "triage": payload.model_dump(),
        }

    @router.get("/{case_id}/iocs", response_model=IOCAggregate)
    def get_case_iocs(case_id: str) -> IOCAggregate:
        try:
            return case_service.aggregate_iocs(case_id)
        except CaseStoreError:
            _nf()

    @router.post("/{case_id}/iocs/signal", response_model=CaseDetail)
    def add_ioc_signal(case_id: str, body: IOCSignalCreate) -> CaseDetail:
        try:
            return case_service.record_ioc_signal(case_id, title=body.title, body=body.body)
        except CaseStoreError:
            _nf()

    @router.get("/{case_id}/export.html")
    def export_case_html(case_id: str) -> HTMLResponse:
        detail = store.get_case(case_id)
        if detail is None:
            _nf()
        try:
            iocs = case_service.aggregate_iocs(case_id)
        except CaseStoreError:
            _nf()
        html_out = render_case_pack_html(detail, iocs)
        return HTMLResponse(content=html_out, status_code=200)

    return router
