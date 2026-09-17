from typing import Literal

from pydantic import BaseModel, Field

State = Literal["pending", "processing", "completed", "failed"]


class FullTextSource(BaseModel):
    source_url: str
    source_format: Literal["pdf"] = "pdf"
    access_type: Literal["open_access"] = "open_access"
    licence: str | None = None


class SourceList(BaseModel):
    sources: list[FullTextSource]


class DocumentCreate(BaseModel):
    source_url: str = Field(min_length=1, max_length=4096)


class DocumentStatus(FullTextSource):
    id: int
    paper_id: int
    retrieval_status: State
    parsing_status: State
    file_size_bytes: int | None = None
    page_count: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    retrieved_at: str | None = None
    parsed_at: str | None = None
    created_at: str
    updated_at: str


class Section(BaseModel):
    id: int
    document_id: int
    section_type: str
    original_heading: str | None
    sequence_number: int
    start_page: int
    end_page: int


class SectionList(BaseModel):
    sections: list[Section]


class Chunk(BaseModel):
    id: int
    document_id: int
    section_id: int
    sequence_number: int
    source_text: str
    start_page: int
    end_page: int
    start_character: int
    end_character: int


class ChunkList(BaseModel):
    chunks: list[Chunk]
