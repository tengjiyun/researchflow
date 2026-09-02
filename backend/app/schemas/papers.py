from pydantic import BaseModel, Field


class PaperSearchItem(BaseModel):
    openalex_id: str
    title: str
    authors: list[str]
    publication_year: int | None
    abstract: str | None
    doi: str | None
    venue: str | None
    citation_count: int = Field(ge=0)
    landing_page_url: str | None


class PaperSearchResponse(BaseModel):
    papers: list[PaperSearchItem]
    page: int = Field(ge=1)
    has_more: bool

