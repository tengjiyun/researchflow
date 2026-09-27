import json
from pathlib import Path
import sqlite3

from fastapi import Request

from app.database import connect_database
from app.schemas.analyses import AnalysisList, AnalysisStatus, Candidate, FINDING_TYPES
from app.services.analysis_evidence import (
    DEFAULT_LIMITS, analysis_error, input_digest, make_batches, validate_candidates,
)
from app.services.documents import now


class AnalysisStore:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    @staticmethod
    def _row(db: sqlite3.Connection, run_id: int) -> sqlite3.Row:
        row = db.execute('SELECT * FROM analysis_runs WHERE id=?', (run_id,)).fetchone()
        if row is None:
            raise analysis_error('analysis_not_found', 'The analysis was not found.', 404)
        return row

    @staticmethod
    def _source(db: sqlite3.Connection, document_id: int) -> tuple[dict, list[dict]]:
        doc = db.execute('SELECT * FROM documents WHERE id=?', (document_id,)).fetchone()
        if doc is None:
            raise analysis_error('document_not_found', 'The document was not found.', 404)
        if doc['parsing_status'] != 'completed' or doc['retrieval_status'] != 'completed':
            raise analysis_error('invalid_resource_state', 'The document must finish parsing first.')
        chunks = [dict(row) for row in db.execute('''SELECT c.*, s.section_type, s.original_heading
            FROM chunks c JOIN sections s ON s.id=c.section_id
            WHERE c.document_id=? ORDER BY c.sequence_number''', (document_id,))]
        return dict(doc), chunks

    @staticmethod
    def _no_active(db: sqlite3.Connection, document_id: int):
        if db.execute("SELECT 1 FROM analysis_runs WHERE document_id=? AND status IN ('pending','processing')",
                      (document_id,)).fetchone():
            raise analysis_error('invalid_resource_state', 'This document already has an active analysis.')

    def get(self, run_id: int) -> AnalysisStatus:
        with connect_database(self.database_path) as db:
            return AnalysisStatus(**dict(self._row(db, run_id)))

    def list_for_document(self, document_id: int, *, page: int = 1, page_size: int = 20) -> AnalysisList:
        with connect_database(self.database_path) as db:
            db.execute('BEGIN')
            if db.execute('SELECT 1 FROM documents WHERE id=?', (document_id,)).fetchone() is None:
                raise analysis_error('document_not_found', 'The document was not found.', 404)
            rows = db.execute('''SELECT * FROM analysis_runs WHERE document_id=?
                ORDER BY id DESC LIMIT ? OFFSET ?''',
                (document_id, page_size + 1, (page - 1) * page_size)).fetchall()
            return AnalysisList(
                analyses=[AnalysisStatus(**dict(row)) for row in rows[:page_size]],
                page=page, page_size=page_size, has_more=len(rows) > page_size,
            )

    def create(self, document_id: int, model: str) -> AnalysisStatus:
        with connect_database(self.database_path) as db:
            db.execute('BEGIN IMMEDIATE')
            doc, chunks = self._source(db, document_id)
            make_batches(chunks)
            self._no_active(db, document_id)
            settings = {**DEFAULT_LIMITS, 'file_sha256': doc['file_sha256'],
                        'chunk_ids': [c['id'] for c in chunks], 'input_digest': input_digest(chunks)}
            cursor = db.execute('''INSERT INTO analysis_runs(document_id, status, analysis_version,
                service_name, service_model, settings_json, created_at)
                VALUES (?, 'pending', 'full-text-v1', 'OpenRouter', ?, ?, ?)''',
                (document_id, model, json.dumps(settings), now()))
            return AnalysisStatus(**dict(self._row(db, cursor.lastrowid)))

    def _input(self, db: sqlite3.Connection, row: sqlite3.Row) -> tuple[list[dict], dict]:
        doc, chunks = self._source(db, row['document_id'])
        settings = json.loads(row['settings_json'])
        if (doc['file_sha256'] != settings['file_sha256']
                or input_digest(chunks) != settings['input_digest']
                or [c['id'] for c in chunks] != settings['chunk_ids']):
            raise analysis_error('analysis_source_changed', 'The source changed. Start a new analysis.')
        make_batches(chunks, settings)
        return chunks, settings

    def input(self, run_id: int) -> tuple[AnalysisStatus, list[dict], dict]:
        with connect_database(self.database_path) as db:
            db.execute('BEGIN')
            row = self._row(db, run_id)
            chunks, settings = self._input(db, row)
            return AnalysisStatus(**dict(row)), chunks, settings

    def retry(self, run_id: int) -> AnalysisStatus:
        with connect_database(self.database_path) as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, run_id)
            if row['status'] != 'failed':
                raise analysis_error('invalid_resource_state', 'Only a failed analysis can be retried.')
            self._no_active(db, row['document_id'])
            self._input(db, row)
            db.execute('DELETE FROM findings WHERE analysis_run_id=?', (run_id,))
            db.execute("""UPDATE analysis_runs SET status='pending', error_code=NULL, error_message=NULL,
                started_at=NULL, completed_at=NULL WHERE id=?""", (run_id,))
            return AnalysisStatus(**dict(self._row(db, run_id)))

    def claim_next(self) -> int | None:
        with connect_database(self.database_path) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT id FROM analysis_runs WHERE status='pending' ORDER BY id LIMIT 1").fetchone()
            if row is None:
                return None
            db.execute("UPDATE analysis_runs SET status='processing', started_at=? WHERE id=?", (now(), row['id']))
            return row['id']

    def complete(self, run_id: int, findings: list[dict], candidate_count: int):
        with connect_database(self.database_path) as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, run_id)
            if row['status'] != 'processing':
                raise analysis_error('invalid_resource_state', 'The analysis is not processing.')
            chunks, _ = self._input(db, row)
            if candidate_count and not findings:
                raise analysis_error('evidence_missing', 'No candidates have valid source evidence.', retryable=True)
            checked = []
            for finding in findings:
                candidate = Candidate(finding_type=finding['finding_type'], content=finding['content'],
                    evidence=[{'chunk_id': e['chunk_id'], 'source_excerpt': e['source_excerpt']}
                              for e in finding['evidence']])
                rebound = validate_candidates([candidate], chunks, row['document_id'])
                if not rebound or rebound[0] != finding:
                    raise analysis_error('analysis_source_changed', 'Source evidence changed before storage.')
                if finding not in checked:
                    checked.append(finding)
            timestamp = now()
            for category in FINDING_TYPES:
                group = [f for f in checked if f['finding_type'] == category]
                for sequence, finding in enumerate(group or [None], start=1):
                    cursor = db.execute('''INSERT INTO findings(analysis_run_id, finding_type, content,
                        support_status, sequence_number, created_at) VALUES (?, ?, ?, ?, ?, ?)''',
                        (run_id, category, finding['content'] if finding else None,
                         'supported' if finding else 'unavailable', sequence, timestamp))
                    for evidence in finding['evidence'] if finding else []:
                        db.execute('''INSERT INTO evidence(finding_id, chunk_id, source_excerpt, start_page,
                            end_page, start_offset, end_offset, is_primary, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (cursor.lastrowid, evidence['chunk_id'], evidence['source_excerpt'],
                             evidence['start_page'], evidence['end_page'], evidence['start_offset'],
                             evidence['end_offset'], int(evidence['is_primary']), timestamp))
            db.execute("UPDATE analysis_runs SET status='completed', completed_at=? WHERE id=?", (timestamp, run_id))

    def fail(self, run_id: int, code: str, message: str):
        with connect_database(self.database_path) as db:
            db.execute("""UPDATE analysis_runs SET status='failed', error_code=?, error_message=?, completed_at=NULL
                WHERE id=? AND status IN ('pending','processing')""", (code, message, run_id))

    def recover_interrupted(self):
        with connect_database(self.database_path) as db:
            db.execute("""UPDATE analysis_runs SET status='failed', error_code='analysis_interrupted',
                error_message='Analysis stopped. Retry the analysis.', completed_at=NULL WHERE status='processing'""")

    def findings(self, run_id: int, finding_type: str | None = None) -> list[dict]:
        with connect_database(self.database_path) as db:
            db.execute('BEGIN')
            if self._row(db, run_id)['status'] != 'completed':
                raise analysis_error('invalid_resource_state', 'Analysis results are not ready.')
            rows = [dict(row) for row in db.execute('''SELECT f.*,
                (SELECT count(*) FROM evidence e WHERE e.finding_id=f.id) AS evidence_count
                FROM findings f WHERE analysis_run_id=? AND support_status!='rejected'
                AND (? IS NULL OR finding_type=?)''', (run_id, finding_type, finding_type))]
            return sorted(rows, key=lambda f: (FINDING_TYPES.index(f['finding_type']), f['sequence_number']))

    def finding(self, finding_id: int) -> dict:
        with connect_database(self.database_path) as db:
            db.execute('BEGIN')
            row = db.execute('''SELECT f.* FROM findings f JOIN analysis_runs a ON a.id=f.analysis_run_id
                WHERE f.id=? AND a.status='completed' AND f.support_status!='rejected' ''', (finding_id,)).fetchone()
            if row is None:
                raise analysis_error('finding_not_found', 'The finding was not found.', 404)
            evidence = [dict(e) for e in db.execute('''SELECT e.*, s.section_type, s.original_heading
                FROM evidence e JOIN chunks c ON c.id=e.chunk_id JOIN sections s ON s.id=c.section_id
                WHERE e.finding_id=? ORDER BY e.is_primary DESC, e.id''', (finding_id,))]
            for item in evidence:
                item['is_primary'] = bool(item['is_primary'])
            return {**dict(row), 'evidence': evidence, 'evidence_count': len(evidence)}


def get_analysis_store(request: Request) -> AnalysisStore:
    return request.app.state.analysis_store
