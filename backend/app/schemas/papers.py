from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator


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
    from_cache: bool = False
    cached_at: datetime | None = None


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


LibraryStatus = Literal['pending', 'processing', 'completed', 'failed', 'not_started']


class LibraryQuery(BaseModel):
    q: str = Field(default='', max_length=200)
    year_from: int | None = Field(default=None, ge=1, le=9999)
    year_to: int | None = Field(default=None, ge=1, le=9999)
    collection_id: int | None = Field(default=None, ge=1, le=9223372036854775807)
    document_status: LibraryStatus | None = None
    analysis_status: LibraryStatus | None = None
    sort_by: Literal['saved_at', 'publication_year', 'title', 'citation_count'] = 'saved_at'
    sort_order: Literal['asc', 'desc'] = 'desc'

    @field_validator('q', mode='before')
    @classmethod
    def strip_query(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode='after')
    def validate_year_range(self) -> Self:
        if self.year_from is not None and self.year_to is not None and self.year_from > self.year_to:
            raise ValueError('year_from must not exceed year_to')
        return self


class PaperDocumentSummary(BaseModel):
    id: int
    retrieval_status: str
    parsing_status: str


class PaperDetail(PaperSearchItem):
    id: int
    documents: list[PaperDocumentSummary] = Field(default_factory=list)
