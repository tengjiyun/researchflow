from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Path, UploadFile
from starlette.concurrency import run_in_threadpool

from app.errors import ApiError
from app.schemas.documents import (
    ChunkList, DocumentCreate, DocumentStatus, FullTextSource, SectionList, SourceList,
)
from app.schemas.errors import ErrorResponse
from app.services.documents import DocumentStore, get_document_store
from app.services.library import PaperLibrary, get_paper_library
from app.services.openalex import OpenAlexSearchError, OpenAlexService, get_openalex_service
from app.services.pdf_download import DocumentError, MAX_PDF_BYTES, validate_source_url

router = APIRouter(tags=["documents"], responses={
    status: {"model": ErrorResponse} for status in (400, 404, 409, 413, 422, 502, 503)
})
Identifier = Annotated[int, Path(ge=1, le=9223372036854775807)]
Store = Annotated[DocumentStore, Depends(get_document_store)]
Library = Annotated[PaperLibrary, Depends(get_paper_library)]
Sources = Annotated[OpenAlexService, Depends(get_openalex_service)]


async def find_sources(service: OpenAlexService, openalex_id: str) -> list[FullTextSource]:
    try:
        return [FullTextSource.model_validate(source) for source in await service.full_text_sources(openalex_id)]
    except OpenAlexSearchError as exc:
        raise ApiError(status_code=502, code="full_text_source_lookup_failed",
                       message="The full-text source service is unavailable.", retryable=True) from exc


@router.get("/papers/{paper_id}/full-text-sources", response_model=SourceList)
async def full_text_sources(paper_id: Identifier, library: Library, service: Sources):
    paper = await run_in_threadpool(library.get, paper_id)
    return SourceList(sources=await find_sources(service, paper.openalex_id))


@router.post("/papers/{paper_id}/documents", status_code=202, response_model=DocumentStatus)
async def create_document(
    paper_id: Identifier, body: DocumentCreate, library: Library, service: Sources, store: Store,
):
    paper = await run_in_threadpool(library.get, paper_id)
    try:
        validate_source_url(body.source_url)
    except DocumentError as exc:
        raise ApiError(status_code=400, code=exc.code, message=exc.message, retryable=False) from exc
    sources = await find_sources(service, paper.openalex_id)
    source = next((item for item in sources if item.source_url == body.source_url), None)
    if source is None:
        raise ApiError(status_code=400, code="full_text_source_not_found",
                       message="The URL is not an open-access PDF source for this paper.", retryable=False)
    return await run_in_threadpool(store.create, paper_id, source)


@router.get("/documents/{document_id}", response_model=DocumentStatus)
def document_status(document_id: Identifier, store: Store):
    return store.get(document_id)


@router.post('/papers/{paper_id}/documents/upload', status_code=202, response_model=DocumentStatus)
async def upload_document(
    paper_id: Identifier, store: Store,
    file: Annotated[UploadFile, File()], confirmed: Annotated[bool, Form()],
):
    try:
        if not confirmed:
            raise ApiError(status_code=400, code='upload_confirmation_required',
                           message='Confirm that the PDF belongs to this paper and you may process it.', retryable=False)
        if file.size is not None and file.size > MAX_PDF_BYTES:
            raise ApiError(status_code=413, code='pdf_too_large',
                           message='The PDF exceeds the 25 MiB size limit.', retryable=False)
        return await run_in_threadpool(store.create_upload, paper_id, file.file, file.filename or 'upload.pdf')
    finally:
        await file.close()


@router.post("/documents/{document_id}/retry", status_code=202, response_model=DocumentStatus)
def retry_document(document_id: Identifier, store: Store):
    return store.retry(document_id)


@router.get("/documents/{document_id}/sections", response_model=SectionList)
def document_sections(document_id: Identifier, store: Store):
    return SectionList(sections=store.sections(document_id))


@router.get("/documents/{document_id}/chunks", response_model=ChunkList)
def document_chunks(document_id: Identifier, store: Store):
    return ChunkList(chunks=store.chunks(document_id=document_id))


@router.get("/sections/{section_id}/chunks", response_model=ChunkList)
def section_chunks(section_id: Identifier, store: Store):
    return ChunkList(chunks=store.chunks(section_id=section_id))
