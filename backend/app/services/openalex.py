from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas.papers import PaperSearchItem, PaperSearchResponse

RESULTS_PER_PAGE = 25
SELECTED_FIELDS = ",".join(
    (
        "id",
        "display_name",
        "authorships",
        "publication_year",
        "abstract_inverted_index",
        "doi",
        "primary_location",
        "cited_by_count",
    )
)


class OpenAlexSearchError(Exception):
    pass


class OpenAlexService:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def search_papers(self, *, query: str, page: int) -> PaperSearchResponse:
        try:
            response = await self.client.get(
                "/works",
                params={
                    "search": query,
                    "page": page,
                    "per_page": RESULTS_PER_PAGE,
                    "select": SELECTED_FIELDS,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OpenAlexSearchError from exc

        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise OpenAlexSearchError

        papers = [normalise_work(work) for work in payload["results"]]
        count = _result_count(payload.get("meta"))
        has_more = (
            page * RESULTS_PER_PAGE < count
            if count is not None
            else len(papers) == RESULTS_PER_PAGE
        )

        return PaperSearchResponse(papers=papers, page=page, has_more=has_more)


async def get_openalex_service() -> AsyncIterator[OpenAlexService]:
    settings = get_settings()
    headers = {"Accept": "application/json"}
    if settings.openalex_api_key:
        headers["Authorization"] = f"Bearer {settings.openalex_api_key}"

    async with httpx.AsyncClient(
        base_url=settings.openalex_base_url,
        headers=headers,
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        yield OpenAlexService(client)


def normalise_work(work: Any) -> PaperSearchItem:
    if not isinstance(work, dict):
        raise OpenAlexSearchError

    openalex_id = work.get("id")
    title = work.get("display_name")
    if not isinstance(openalex_id, str) or not isinstance(title, str):
        raise OpenAlexSearchError

    primary_location = _mapping_or_empty(work.get("primary_location"))
    source = _mapping_or_empty(primary_location.get("source"))

    return PaperSearchItem(
        openalex_id=openalex_id,
        title=title,
        authors=_author_names(work.get("authorships")),
        publication_year=_optional_int(work.get("publication_year")),
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        doi=_optional_str(work.get("doi")),
        venue=_optional_str(source.get("display_name")),
        citation_count=max(_optional_int(work.get("cited_by_count")) or 0, 0),
        landing_page_url=(
            _optional_str(primary_location.get("landing_page_url"))
            or _optional_str(work.get("doi"))
        ),
    )


def reconstruct_abstract(value: Any) -> str | None:
    if not isinstance(value, dict) or not value:
        return None

    positioned_words: list[tuple[int, str]] = []
    for word, positions in value.items():
        if not isinstance(word, str) or not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int) and position >= 0:
                positioned_words.append((position, word))

    if not positioned_words:
        return None

    positioned_words.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positioned_words)


def _author_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    names: list[str] = []
    for authorship in value:
        author = _mapping_or_empty(_mapping_or_empty(authorship).get("author"))
        name = _optional_str(author.get("display_name"))
        if name:
            names.append(name)
    return names


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _result_count(value: Any) -> int | None:
    count = _mapping_or_empty(value).get("count")
    return _optional_int(count)

