import hashlib
import json
import re

from app.errors import ApiError
from app.schemas.analyses import Candidate

DEFAULT_LIMITS = {
    'batch_characters': 12000, 'input_characters': 200000, 'max_batches': 100,
    'request_timeout': 600, 'run_timeout': 1800, 'max_tokens': 100000,
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


def _locate_excerpt(source: str, excerpt: str) -> tuple[int, int] | None:
    # Each normalised character retains its span in the unchanged source.
    characters, spans = [], []
    for match in re.finditer(r'\s+|\S', source):
        value = match.group()
        characters.append(' ' if value.isspace() else value)
        spans.append(match.span())
    normalised = ''.join(characters)
    quote = re.sub(r'\s+', ' ', excerpt).strip()
    if not quote:
        return None
    start = normalised.find(quote)
    # Check overlapping matches too; an exact spelling does not resolve ambiguity.
    if start < 0 or normalised.find(quote, start + 1) >= 0:
        return None
    return spans[start][0], spans[start + len(quote) - 1][1]


def validate_candidates(candidates: list[Candidate], chunks: list[dict], document_id: int) -> list[dict]:
    sources = {c['id']: c for c in chunks if c['document_id'] == document_id}
    findings = []
    for candidate in candidates:
        evidence, seen = [], set()
        for pair in candidate.evidence:
            chunk = sources.get(pair.chunk_id)
            location = _locate_excerpt(chunk['source_text'], pair.source_excerpt) if chunk else None
            if location is None:
                break
            start, end = location
            key = (pair.chunk_id, start, end)
            if key in seen:
                continue
            seen.add(key)
            evidence.append({
                'chunk_id': pair.chunk_id, 'source_excerpt': chunk['source_text'][start:end],
                'start_page': chunk['start_page'], 'end_page': chunk['end_page'],
                'start_offset': start, 'end_offset': end,
                'is_primary': not evidence,
            })
        else:
            findings.append({'finding_type': candidate.finding_type, 'content': candidate.content,
                             'evidence': evidence})
    return findings
