from __future__ import annotations

from typing import Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.api.mitre_routes import MitreMapRequest, mitre_options_from_request
from app.api.schemas import ContextRequest, SearchRequest, TriageRequest, options_from_controls
from app.auth.models import UserPublic
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
    store_getter: Callable[[], CaseStore],
    case_service_getter: Callable[[], CaseInvestigationService],
    settings: Settings,
    current_user_dep: Callable[..., UserPublic],
) -> APIRouter:
    router = APIRouter()

    def _nf() -> None:
        raise HTTPException(status_code=404, detail="case not found")

    def _assert_owned(case_id: str, current_user: UserPublic) -> CaseDetail:
        store = store_getter()
        d = store.get_case(case_id)
        if d is None or d.user_id != current_user.id:
            _nf()
        return d

    @router.post("", response_model=CaseDetail)
    def create_case(
        body: CaseCreate,
        *,
        current_user: UserPublic = Depends(current_user_dep),
    ) -> CaseDetail:
        return store_getter().create_case(body, user_id=current_user.id)

    @router.get("", response_model=list[CaseSummary])
    def list_cases(
        *,
        current_user: UserPublic = Depends(current_user_dep),
        status: Optional[CaseStatus] = None,
        owner: Optional[str] = None,
        title_contains: Optional[str] = Query(default=None, max_length=256),
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[CaseSummary]:
        params = CaseListParams(
            status=status,
            owner=owner,
            user_id=current_user.id,
            title_contains=title_contains,
            limit=limit,
            offset=offset,
        )
        return store_getter().list_cases(params)

    @router.get("/{case_id}", response_model=CaseDetail)
    def get_case(
        case_id: str,
        *,
        current_user: UserPublic = Depends(current_user_dep),
    ) -> CaseDetail:
        return _assert_owned(case_id, current_user)

    @router.patch("/{case_id}", response_model=CaseDetail)
    def patch_case(
        case_id: str,
        body: CaseUpdate,
        *,
        current_user: UserPublic = Depends(current_user_dep),
    ) -> CaseDetail:
        _assert_owned(case_id, current_user)
        try:
            return store_getter().update_case(case_id, body)
        except CaseStoreError:
            _nf()

    @router.post("/{case_id}/notes", response_model=CaseDetail)
    def add_note(
        case_id: str,
        body: NoteCreate,
        *,
        current_user: UserPublic = Depends(current_user_dep),
    ) -> CaseDetail:
        _assert_owned(case_id, current_user)
        try:
            return case_service_getter().add_note(case_id, body)
        except CaseStoreError:
            _nf()

    @router.post("/{case_id}/snapshots/search", response_model=CaseDetail)
    def attach_search_snapshot(
        case_id: str,
        body: SearchSnapshotCreate,
        *,
        current_user: UserPublic = Depends(current_user_dep),
    ) -> CaseDetail:
        _assert_owned(case_id, current_user)
        try:
            return case_service_getter().attach_search_snapshot(case_id, body)
        except CaseStoreError:
            _nf()

    @router.post("/{case_id}/snapshots/search-run", response_model=CaseDetail)
    def run_search_snapshot(
        case_id: str,
        body: SearchRequest,
        *,
        current_user: UserPublic = Depends(current_user_dep),
    ) -> CaseDetail:
        _assert_owned(case_id, current_user)
        top_k = body.top_k or settings.search_top_k
        opts = options_from_controls(body)
        try:
            return case_service_getter().run_search_and_attach(case_id, body.query, top_k, opts)
        except CaseStoreError:
            _nf()

    @router.post("/{case_id}/snapshots/triage")
    def run_triage_snapshot(
        case_id: str,
        body: TriageRequest,
        *,
        current_user: UserPublic = Depends(current_user_dep),
    ) -> dict:
        _assert_owned(case_id, current_user)
        top_k = body.top_k or settings.search_top_k
        opts = options_from_controls(body)
        try:
            payload, detail = case_service_getter().run_triage_and_attach(
                case_id, body.alert, top_k, opts
            )
        except CaseStoreError:
            _nf()
        return {
            "case": detail.model_dump(),
            "triage": payload.model_dump(),
        }

    @router.get("/{case_id}/iocs", response_model=IOCAggregate)
    def get_case_iocs(
        case_id: str,
        *,
        current_user: UserPublic = Depends(current_user_dep),
    ) -> IOCAggregate:
        _assert_owned(case_id, current_user)
        try:
            return case_service_getter().aggregate_iocs(case_id)
        except CaseStoreError:
            _nf()

    @router.post("/{case_id}/iocs/signal", response_model=CaseDetail)
    def add_ioc_signal(
        case_id: str,
        body: IOCSignalCreate,
        *,
        current_user: UserPublic = Depends(current_user_dep),
    ) -> CaseDetail:
        _assert_owned(case_id, current_user)
        try:
            return case_service_getter().record_ioc_signal(case_id, title=body.title, body=body.body)
        except CaseStoreError:
            _nf()

    @router.post("/{case_id}/mitre/map")
    def case_mitre_map(
        case_id: str,
        body: MitreMapRequest,
        *,
        current_user: UserPublic = Depends(current_user_dep),
    ) -> dict:
        _assert_owned(case_id, current_user)
        opts = mitre_options_from_request(body, settings)
        try:
            mitre_res, detail = case_service_getter().run_mitre_map_from_text(case_id, body.text, opts)
        except CaseStoreError:
            _nf()
        return {"mitre": mitre_res.model_dump(), "case": detail.model_dump()}

    @router.post("/{case_id}/mitre/map-with-context")
    def case_mitre_map_with_context(
        case_id: str,
        body: ContextRequest,
        *,
        current_user: UserPublic = Depends(current_user_dep),
    ) -> dict:
        _assert_owned(case_id, current_user)
        top_k = body.top_k or settings.search_top_k
        opts = options_from_controls(body)
        try:
            mitre_res, doc_ids, detail = case_service_getter().run_mitre_map_from_alert_with_retrieval(
                case_id,
                body.alert,
                top_k,
                opts,
            )
        except CaseStoreError:
            _nf()
        return {
            "mitre": mitre_res.model_dump(),
            "context_doc_ids": doc_ids,
            "case": detail.model_dump(),
        }

    @router.get("/{case_id}/export.html")
    def export_case_html(
        case_id: str,
        *,
        current_user: UserPublic = Depends(current_user_dep),
    ) -> HTMLResponse:
        detail = _assert_owned(case_id, current_user)
        try:
            iocs = case_service_getter().aggregate_iocs(case_id)
        except CaseStoreError:
            _nf()
        html_out = render_case_pack_html(detail, iocs)
        return HTMLResponse(content=html_out, status_code=200)

    return router
