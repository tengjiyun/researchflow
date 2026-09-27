from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import re

from fastapi import Request

from app.database import connect_database
from app.errors import ApiError
from app.schemas.documents import DocumentStatus, FullTextSource
from app.services.library import paper_not_found
from app.services.pdf_parser import ParsedDocument


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def not_found(kind: str = "document") -> ApiError:
    return ApiError(status_code=404, code=f"{kind}_not_found",
                    message=f"The {kind} was not found.", retryable=False)


def invalid_state() -> ApiError:
    return ApiError(status_code=409, code="invalid_resource_state",
                    message="The document state does not allow this operation.", retryable=False)


class DocumentStore:
    def __init__(self, database_path: Path, cache_path: Path):
        self.database_path = database_path
        self.cache_path = cache_path.resolve()

    def pdf_path(self, document_id: int) -> Path:
        return self.cache_path / f"{int(document_id)}.pdf"

    def get(self, document_id: int) -> DocumentStatus:
        with connect_database(self.database_path) as db:
            row = db.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
            if row is None:
                raise not_found()
            return DocumentStatus(**dict(row))

    def create(self, paper_id: int, source: FullTextSource) -> DocumentStatus:
        timestamp = now()
        with connect_database(self.database_path) as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM papers WHERE id = ?", (paper_id,)).fetchone() is None:
                raise paper_not_found()
            cursor = db.execute("""
                INSERT INTO documents(paper_id, source_url, licence, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?) ON CONFLICT(paper_id, source_url) DO NOTHING
            """, (paper_id, source.source_url, source.licence, timestamp, timestamp))
            if cursor.rowcount == 0:
                raise invalid_state()
            row = db.execute("SELECT * FROM documents WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return DocumentStatus(**dict(row))

    def retry(self, document_id: int) -> DocumentStatus:
        with connect_database(self.database_path) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
            if row is None:
                raise not_found()
            if "failed" not in (row["retrieval_status"], row["parsing_status"]):
                raise invalid_state()
            if db.execute("SELECT 1 FROM analysis_runs WHERE document_id=?", (document_id,)).fetchone():
                raise invalid_state()
            self.pdf_path(document_id).unlink(missing_ok=True)
            self.pdf_path(document_id).with_suffix(".part").unlink(missing_ok=True)
            db.execute("DELETE FROM sections WHERE document_id = ?", (document_id,))
            db.execute("DELETE FROM document_pages WHERE document_id = ?", (document_id,))
            db.execute("""UPDATE documents SET retrieval_status='pending', parsing_status='pending',
                error_code=NULL, error_message=NULL, retrieved_at=NULL, parsed_at=NULL,
                local_file_path=NULL, file_sha256=NULL, file_size_bytes=NULL, page_count=NULL,
                updated_at=? WHERE id=?""", (now(), document_id))
            row = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
            return DocumentStatus(**dict(row))

    def sections(self, document_id: int) -> list[dict]:
        if self.get(document_id).parsing_status != "completed":
            raise invalid_state()
        with connect_database(self.database_path) as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM sections WHERE document_id=? ORDER BY sequence_number", (document_id,))]

    def chunks(self, *, document_id: int | None = None, section_id: int | None = None) -> list[dict]:
        with connect_database(self.database_path) as db:
            if section_id is not None:
                row = db.execute("SELECT document_id FROM sections WHERE id=?", (section_id,)).fetchone()
                if row is None:
                    raise not_found("section")
                document_id = row["document_id"]
            if self.get(document_id).parsing_status != "completed":
                raise invalid_state()
            if section_id is not None:
                rows = db.execute("SELECT * FROM chunks WHERE section_id=? ORDER BY sequence_number", (section_id,))
            else:
                rows = db.execute("SELECT * FROM chunks WHERE document_id=? ORDER BY sequence_number", (document_id,))
            return [dict(row) for row in rows]

    def claim_next(self) -> int | None:
        with connect_database(self.database_path) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT id FROM documents WHERE retrieval_status='pending' ORDER BY id LIMIT 1").fetchone()
            if row is None:
                return None
            db.execute("UPDATE documents SET retrieval_status='processing', updated_at=? WHERE id=?", (now(), row["id"]))
            return row["id"]

    def downloaded(self, document_id: int, size: int, digest: str):
        timestamp = now()
        with connect_database(self.database_path) as db:
            db.execute("""UPDATE documents SET retrieval_status='completed', parsing_status='processing',
                local_file_path=?, file_sha256=?, file_size_bytes=?, retrieved_at=?, updated_at=? WHERE id=?""",
                (str(self.pdf_path(document_id)), digest, size, timestamp, timestamp, document_id))

    def complete(self, document_id: int, parsed: ParsedDocument):
        timestamp = now()
        with connect_database(self.database_path) as db:
            db.execute("BEGIN IMMEDIATE")
            if not parsed.chunks:
                raise ValueError("Parsed documents need at least one text chunk.")
            db.executemany("INSERT INTO document_pages VALUES (?, ?, ?)",
                           [(document_id, index, text) for index, text in enumerate(parsed.pages, start=1)])
            section_ids = {}
            for section in parsed.sections:
                cursor = db.execute("""INSERT INTO sections(document_id, section_type, original_heading,
                    sequence_number, start_page, end_page, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (document_id, section["section_type"], section["original_heading"], section["sequence_number"],
                     section["start_page"], section["end_page"], timestamp))
                section_ids[section["sequence_number"]] = cursor.lastrowid
            for chunk in parsed.chunks:
                db.execute("""INSERT INTO chunks(document_id, section_id, sequence_number, source_text,
                    start_page, end_page, start_character, end_character, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (document_id, section_ids[chunk["section_sequence"]], chunk["sequence_number"],
                     chunk["source_text"], chunk["start_page"], chunk["end_page"],
                     chunk["start_character"], chunk["end_character"], timestamp))
            db.execute("""UPDATE documents SET parsing_status='completed', page_count=?, parsed_at=?,
                updated_at=?, error_code=NULL, error_message=NULL WHERE id=?""",
                (len(parsed.pages), timestamp, timestamp, document_id))

    def fail(self, document_id: int, code: str, message: str):
        with connect_database(self.database_path) as db:
            db.execute("""UPDATE documents SET
                retrieval_status=CASE WHEN retrieval_status='completed' THEN 'completed' ELSE 'failed' END,
                parsing_status='failed', error_code=?, error_message=?, updated_at=?
                WHERE id=? AND parsing_status!='completed'""", (code, message, now(), document_id))
        self.pdf_path(document_id).with_suffix(".part").unlink(missing_ok=True)

    def recover_interrupted(self):
        for temporary in self.cache_path.glob("*.deleting"):
            match = re.fullmatch(r"([1-9][0-9]*)\.(pdf|part)\.deleting", temporary.name)
            if match is None:
                continue
            with connect_database(self.database_path) as db:
                exists = db.execute("SELECT 1 FROM documents WHERE id=?", (int(match[1]),)).fetchone()
            original = temporary.with_suffix("")
            if exists and not original.exists():
                temporary.replace(original)
            else:
                temporary.unlink()
        with connect_database(self.database_path) as db:
            ids = [row[0] for row in db.execute("""SELECT id FROM documents
                WHERE retrieval_status='processing' OR parsing_status='processing'""")]
        for document_id in ids:
            self.fail(document_id, "processing_interrupted", "Document processing stopped. Retry the document.")


def get_document_store(request: Request) -> DocumentStore:
    return request.app.state.document_store
