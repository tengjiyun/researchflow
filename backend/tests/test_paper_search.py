from app.schemas.papers import PaperSearchItem, PaperSearchResponse
from app.services.openalex import OpenAlexSearchError


class SuccessfulSearchService:
    async def search_papers(self, *, query: str, page: int) -> PaperSearchResponse:
        assert query == "research evidence"
        assert page == 2
        return PaperSearchResponse(
            papers=[
                PaperSearchItem(
                    openalex_id="https://openalex.org/W123",
                    title="Example Paper",
                    authors=["Author One"],
                    publication_year=2025,
                    abstract="Example abstract.",
                    doi="https://doi.org/10.xxxx/example",
                    venue="Example Journal",
                    citation_count=12,
                    landing_page_url="https://example.org/paper",
                )
            ],
            page=page,
            has_more=False,
        )


class FailedSearchService:
    async def search_papers(self, *, query: str, page: int) -> PaperSearchResponse:
        raise OpenAlexSearchError


def test_search_papers_returns_contract_shape(client, set_search_service) -> None:
    set_search_service(SuccessfulSearchService())

    response = client.get(
        "/api/papers/search",
        params={"q": "  research evidence  ", "page": 2},
    )

    assert response.status_code == 200
    assert response.json() == {
        "papers": [
            {
                "openalex_id": "https://openalex.org/W123",
                "title": "Example Paper",
                "authors": ["Author One"],
                "publication_year": 2025,
                "abstract": "Example abstract.",
                "doi": "https://doi.org/10.xxxx/example",
                "venue": "Example Journal",
                "citation_count": 12,
                "landing_page_url": "https://example.org/paper",
            }
        ],
        "page": 2,
        "has_more": False,
    }


def test_search_papers_rejects_blank_query(client) -> None:
    response = client.get("/api/papers/search", params={"q": "   "})

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_request",
            "message": "Request parameters are invalid.",
            "retryable": False,
        }
    }


def test_search_papers_rejects_invalid_page(client) -> None:
    response = client.get(
        "/api/papers/search",
        params={"q": "research", "page": 0},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_search_papers_maps_external_failure(client, set_search_service) -> None:
    set_search_service(FailedSearchService())

    response = client.get("/api/papers/search", params={"q": "research"})

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "paper_search_failed",
            "message": "The paper search service is unavailable.",
            "retryable": True,
        }
    }


def test_search_papers_exposes_error_shapes_in_api_schema(client) -> None:
    responses = client.get("/openapi.json").json()["paths"][
        "/api/papers/search"
    ]["get"]["responses"]

    assert responses["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }
    assert responses["502"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }


def test_search_papers_allows_local_frontend_origin(client) -> None:
    response = client.options(
        "/api/papers/search",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
