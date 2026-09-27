from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

FindingType = Literal['research_problem', 'methodology', 'key_finding', 'limitation']
FINDING_TYPES = ('research_problem', 'methodology', 'key_finding', 'limitation')


class AnalysisCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    analysis_version: Literal['full-text-v1'] = 'full-text-v1'


class AnalysisStatus(BaseModel):
    id: int
    document_id: int
    status: Literal['pending', 'processing', 'completed', 'failed']
    analysis_version: str
    service_name: str
    service_model: str
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class AnalysisList(BaseModel):
    analyses: list[AnalysisStatus]
    page: int = Field(ge=1, le=2147483647)
    page_size: int = Field(ge=1, le=100)
    has_more: bool


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class EvidenceCandidate(StrictModel):
    chunk_id: Annotated[int, Field(ge=1, le=9223372036854775807)]
    source_excerpt: Annotated[str, Field(min_length=1, max_length=2000)]

    @field_validator('source_excerpt')
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Evidence must contain text.')
        return value


class Candidate(StrictModel):
    finding_type: FindingType
    content: Annotated[str, Field(min_length=1, max_length=2000)]
    evidence: Annotated[list[EvidenceCandidate], Field(min_length=1, max_length=5)]

    @field_validator('content')
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Findings must contain text.')
        return value


class BatchResponse(StrictModel):
    findings: Annotated[list[Candidate], Field(max_length=20)]


class FindingSummary(BaseModel):
    id: int
    analysis_run_id: int
    finding_type: FindingType
    content: str | None
    support_status: Literal['supported', 'unavailable']
    sequence_number: int
    evidence_count: int


class EvidenceDetail(BaseModel):
    id: int
    chunk_id: int
    section_type: str
    original_heading: str | None
    source_excerpt: str
    start_page: int
    end_page: int
    start_offset: int
    end_offset: int
    is_primary: bool


class FindingDetail(FindingSummary):
    evidence: list[EvidenceDetail]


class FindingList(BaseModel):
    findings: list[FindingSummary]
