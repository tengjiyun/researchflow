from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.errors import ApiError
from app.schemas.errors import ErrorResponse
from app.schemas.papers import (
    PaperCreate, PaperDetail, PaperListResponse, PaperSearchResponse, SavedPaper,
)
from app.services.library import PaperLibrary, get_paper_library
from app.services.openalex import (
    OpenAlexSearchError,
    OpenAlexService,
    get_openalex_service,
)

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get(
    "/search",
    response_model=PaperSearchResponse,
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Request parameters are invalid.",
        },
        502: {
            "model": ErrorResponse,
            "description": "The paper search service failed.",
        },
    },
)
async def search_papers(
    q: Annotated[str, Query(min_length=1)],
    page: Annotated[int, Query(ge=1)] = 1,
    service: OpenAlexService = Depends(get_openalex_service),
) -> PaperSearchResponse:
    query = q.strip()
    if not query:
        raise ApiError(
            status_code=422,
            code="invalid_request",
            message="Request parameters are invalid.",
            retryable=False,
        )

    try:
        return await service.search_papers(query=query, page=page)
    except OpenAlexSearchError as exc:
        raise ApiError(
            status_code=502,
            code="paper_search_failed",
            message="The paper search service is unavailable.",
            retryable=True,
        ) from exc


Library = Annotated[PaperLibrary, Depends(get_paper_library)]
PaperId = Annotated[int, Path(ge=1, le=9223372036854775807)]
LIBRARY_ERRORS = {
    422: {"model": ErrorResponse, "description": "Request fields are invalid."},
    503: {"model": ErrorResponse, "description": "The paper library is unavailable."},
}
NOT_FOUND = {404: {"model": ErrorResponse, "description": "The saved paper was not found."}}


@router.post(
    "", status_code=201, response_model=SavedPaper,
    responses={**LIBRARY_ERRORS, 409: {"model": ErrorResponse, "description": "The paper is already saved."}},
)
def save_paper(paper: PaperCreate, library: Library) -> SavedPaper:
    return library.save(paper)


@router.get("", response_model=PaperListResponse, responses=LIBRARY_ERRORS)
def list_saved_papers(library: Library) -> PaperListResponse:
    return PaperListResponse(papers=library.list_papers())


@router.get("/{paper_id}", response_model=PaperDetail, responses={**LIBRARY_ERRORS, **NOT_FOUND})
def get_saved_paper(paper_id: PaperId, library: Library) -> PaperDetail:
    return library.get(paper_id)


@router.delete("/{paper_id}", status_code=204, responses={**LIBRARY_ERRORS, **NOT_FOUND})
def delete_saved_paper(paper_id: PaperId, library: Library) -> Response:
    library.delete(paper_id)
    return Response(status_code=204)
