import asyncio

import httpx
import pytest

from app.services.openalex import OpenAlexSearchError, OpenAlexService


def test_openalex_search_maps_requested_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["search"] == "evidence synthesis"
        assert request.url.params["page"] == "2"
        assert request.url.params["per_page"] == "25"
        assert "abstract_inverted_index" in request.url.params["select"]
        return httpx.Response(
            200,
            json={
                "meta": {"count": 60},
                "results": [
                    {
                        "id": "https://openalex.org/W123",
                        "display_name": "Example Paper",
                        "authorships": [
                            {"author": {"display_name": "Author One"}}
                        ],
                        "publication_year": 2025,
                        "abstract_inverted_index": {
                            "Useful": [1],
                            "Evidence": [0],
                        },
                        "doi": "https://doi.org/10.xxxx/example",
                        "primary_location": {
                            "landing_page_url": "https://example.org/paper",
                            "source": {"display_name": "Example Journal"},
                        },
                        "cited_by_count": 12,
                    }
                ],
            },
        )

    async def run_search():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://api.openalex.org",
        ) as http_client:
            return await OpenAlexService(http_client).search_papers(
                query="evidence synthesis",
                page=2,
            )

    result = asyncio.run(run_search())

    assert result.page == 2
    assert result.has_more is True
    assert len(result.papers) == 1
    paper = result.papers[0]
    assert paper.openalex_id == "https://openalex.org/W123"
    assert paper.authors == ["Author One"]
    assert paper.abstract == "Evidence Useful"
    assert paper.venue == "Example Journal"


def test_openalex_search_rejects_invalid_response_shape() -> None:
    async def run_search():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"results": None})
            ),
            base_url="https://api.openalex.org",
        ) as http_client:
            return await OpenAlexService(http_client).search_papers(
                query="test",
                page=1,
            )

    with pytest.raises(OpenAlexSearchError):
        asyncio.run(run_search())

