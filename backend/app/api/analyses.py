from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from app.schemas.analyses import AnalysisCreate, AnalysisList, AnalysisStatus, FindingDetail, FindingList, FindingType
from app.schemas.errors import ErrorResponse
from app.services.analyses import AnalysisStore, get_analysis_store
from app.services.analysis_evidence import analysis_error

router = APIRouter(tags=['analyses'], responses={
    status: {'model': ErrorResponse} for status in (404, 409, 422, 503)
})
Identifier = Annotated[int, Path(ge=1, le=9223372036854775807)]
Store = Annotated[AnalysisStore, Depends(get_analysis_store)]


def configured_model(request: Request) -> str:
    if not request.app.state.analysis_client.api_key or not request.app.state.analysis_model:
        raise analysis_error('analysis_not_configured', 'Configure OPENROUTER_API_KEY and OPENROUTER_MODEL.', 503)
    return request.app.state.analysis_model


@router.post('/documents/{document_id}/analyses', status_code=202, response_model=AnalysisStatus)
def create_analysis(document_id: Identifier, body: AnalysisCreate, request: Request, store: Store):
    return store.create(document_id, configured_model(request))


@router.get('/analyses/{analysis_id}', response_model=AnalysisStatus)
def analysis_status(analysis_id: Identifier, store: Store):
    return store.get(analysis_id)


@router.get('/documents/{document_id}/analyses', response_model=AnalysisList)
def list_analyses(
    document_id: Identifier,
    store: Store,
    page: Annotated[int, Query(ge=1, le=2147483647)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return store.list_for_document(document_id, page=page, page_size=page_size)


@router.post('/analyses/{analysis_id}/retry', status_code=202, response_model=AnalysisStatus)
def retry_analysis(analysis_id: Identifier, request: Request, store: Store):
    configured_model(request)
    return store.retry(analysis_id)


@router.get('/analyses/{analysis_id}/findings', response_model=FindingList)
def list_findings(analysis_id: Identifier, store: Store, finding_type: FindingType | None = None):
    return FindingList(findings=store.findings(analysis_id, finding_type))


@router.get('/findings/{finding_id}', response_model=FindingDetail)
def finding_detail(finding_id: Identifier, store: Store):
    return store.finding(finding_id)
