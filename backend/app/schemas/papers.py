from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


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


class PaperCreate(PaperSearchItem):
    openalex_id: Annotated[str, StringConstraints(
        strip_whitespace=True, pattern=r"^https://openalex\.org/W[1-9][0-9]*$"
    )]
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    publication_year: int | None = Field(default=None, strict=True, ge=1, le=9999)
    citation_count: int = Field(default=0, strict=True, ge=0)


class SavedPaper(PaperSearchItem):
    id: int
    created_at: datetime
    updated_at: datetime


class LibraryPaper(BaseModel):
    id: int
    openalex_id: str
    title: str
    publication_year: int | None
    venue: str | None
    document_status: str | None = None
    latest_analysis_status: str | None = None


class PaperListResponse(BaseModel):
    papers: list[LibraryPaper]


class PaperDocumentSummary(BaseModel):
    id: int
    retrieval_status: str
    parsing_status: str


class PaperDetail(PaperSearchItem):
    id: int
    documents: list[PaperDocumentSummary] = Field(default_factory=list)
