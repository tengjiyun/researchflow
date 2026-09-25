import hashlib
import json

from app.errors import ApiError
from app.schemas.analyses import Candidate

DEFAULT_LIMITS = {
    'batch_characters': 12000, 'input_characters': 200000, 'max_batches': 100,
    'request_timeout': 60, 'run_timeout': 900, 'max_tokens': 4096,
}


def analysis_error(code: str, message: str, status: int = 409, retryable: bool = False) -> ApiError:
    return ApiError(status_code=status, code=code, message=message, retryable=retryable)


def input_digest(chunks: list[dict]) -> str:
    value = json.dumps([[c['id'], c['source_text']] for c in chunks],
                       ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(value).hexdigest()


def make_batches(chunks: list[dict], limits: dict | None = None) -> list[list[dict]]:
    limits = limits or DEFAULT_LIMITS
    if not chunks:
        raise analysis_error('invalid_resource_state', 'The document has no parsed chunks.')
    batches, batch, size = [], [], 0
    total = sum(len(c['source_text']) for c in chunks)
    if total > limits['input_characters']:
        raise analysis_error('analysis_input_limit', 'The full text exceeds the analysis input limit.', 422)
    for chunk in chunks:
        length = len(chunk['source_text'])
        if length > limits['batch_characters']:
            raise analysis_error('analysis_input_limit', 'A source chunk exceeds the batch limit.', 422)
        if batch and size + length > limits['batch_characters']:
            batches.append(batch)
            batch, size = [], 0
        batch.append(chunk)
        size += length
    if batch:
        batches.append(batch)
    if len(batches) > limits['max_batches']:
        raise analysis_error('analysis_input_limit', 'The full text needs too many analysis batches.', 422)
    return batches


def validate_candidates(candidates: list[Candidate], chunks: list[dict], document_id: int) -> list[dict]:
    sources = {c['id']: c for c in chunks if c['document_id'] == document_id}
    findings = []
    for candidate in candidates:
        evidence, seen = [], set()
        for pair in candidate.evidence:
            chunk = sources.get(pair.chunk_id)
            start = chunk['source_text'].find(pair.source_excerpt) if chunk else -1
            if start < 0:
                break
            key = (pair.chunk_id, pair.source_excerpt)
            if key in seen:
                continue
            seen.add(key)
            evidence.append({
                'chunk_id': pair.chunk_id, 'source_excerpt': pair.source_excerpt,
                'start_page': chunk['start_page'], 'end_page': chunk['end_page'],
                'start_offset': start, 'end_offset': start + len(pair.source_excerpt),
                'is_primary': not evidence,
            })
        else:
            findings.append({'finding_type': candidate.finding_type, 'content': candidate.content,
                             'evidence': evidence})
    return findings
