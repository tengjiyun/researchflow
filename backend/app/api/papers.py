from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.errors import ApiError
from app.schemas.errors import ErrorResponse
from app.schemas.papers import PaperSearchResponse
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
