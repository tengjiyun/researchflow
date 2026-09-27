from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3

from fastapi import Request

from app.database import connect_database
from app.errors import ApiError
from app.schemas.papers import LibraryPaper, PaperCreate, PaperDetail, SavedPaper


def paper_not_found() -> ApiError:
    return ApiError(
        status_code=404,
        code="paper_not_found",
        message="The saved paper was not found.",
        retryable=False,
    )


def paper_fields(row: sqlite3.Row) -> dict[str, object]:
    fields = dict(row)
    fields["authors"] = json.loads(fields.pop("authors_json"))
    return fields


class PaperLibrary:
    def __init__(self, database_path: Path, cache_path: Path) -> None:
        self.database_path = database_path
        self.cache_path = cache_path.resolve()

    def save(self, paper: PaperCreate) -> SavedPaper:
        timestamp = datetime.now(timezone.utc).isoformat()
        with connect_database(self.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO papers (
                    openalex_id, title, authors_json, publication_year, abstract,
                    doi, venue, citation_count, landing_page_url, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(openalex_id) DO NOTHING
                """,
                (
                    paper.openalex_id, paper.title,
                    json.dumps(paper.authors, ensure_ascii=False), paper.publication_year,
                    paper.abstract, paper.doi, paper.venue, paper.citation_count,
                    paper.landing_page_url, timestamp, timestamp,
                ),
            )
            if cursor.rowcount == 0:
                raise ApiError(
                    status_code=409,
                    code="paper_already_saved",
                    message="This paper is already saved.",
                    retryable=False,
                )
            row = connection.execute(
                "SELECT * FROM papers WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return SavedPaper(**paper_fields(row))

    def list_papers(self) -> list[LibraryPaper]:
        with connect_database(self.database_path) as connection:
            rows = connection.execute(
                """SELECT p.id, p.openalex_id, p.title, p.publication_year, p.venue,
                    (SELECT CASE WHEN d.retrieval_status='failed' OR d.parsing_status='failed' THEN 'failed'
                        WHEN d.parsing_status='completed' THEN 'completed'
                        WHEN d.retrieval_status='pending' THEN 'pending' ELSE 'processing' END
                     FROM documents d WHERE d.paper_id=p.id ORDER BY d.id DESC LIMIT 1) AS document_status,
                    (SELECT a.status FROM analysis_runs a JOIN documents d ON d.id=a.document_id
                     WHERE d.paper_id=p.id ORDER BY a.id DESC LIMIT 1) AS latest_analysis_status
                    FROM papers p ORDER BY p.id DESC"""
            ).fetchall()
            return [LibraryPaper(**dict(row)) for row in rows]

    def get(self, paper_id: int) -> PaperDetail:
        with connect_database(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM papers WHERE id = ?", (paper_id,)
            ).fetchone()
            if row is None:
                raise paper_not_found()
            documents = [dict(document) for document in connection.execute(
                "SELECT id, retrieval_status, parsing_status FROM documents WHERE paper_id=? ORDER BY id DESC",
                (paper_id,),
            )]
            return PaperDetail(**paper_fields(row), documents=documents)

    def delete(self, paper_id: int) -> None:
        staged = []
        try:
            with connect_database(self.database_path) as connection:
                connection.execute("BEGIN IMMEDIATE")
                active = connection.execute("""SELECT 1 FROM documents WHERE paper_id=? AND
                    (retrieval_status IN ('pending', 'processing') OR parsing_status='processing')""", (paper_id,)).fetchone()
                if active:
                    raise ApiError(status_code=409, code="invalid_resource_state",
                                   message="Wait for document processing to finish before deleting the paper.", retryable=True)
                active_analysis = connection.execute("""SELECT 1 FROM analysis_runs a
                    JOIN documents d ON d.id=a.document_id WHERE d.paper_id=?
                    AND a.status IN ('pending','processing')""", (paper_id,)).fetchone()
                if active_analysis:
                    raise ApiError(status_code=409, code="invalid_resource_state",
                                   message="Wait for analysis to finish before deleting the paper.", retryable=True)
                document_ids = [row[0] for row in connection.execute("SELECT id FROM documents WHERE paper_id=?", (paper_id,))]
                for document_id in document_ids:
                    for suffix in (".pdf", ".part"):
                        original = self.cache_path / f"{document_id}{suffix}"
                        temporary = original.with_suffix(suffix + ".deleting")
                        if original.exists():
                            original.replace(temporary)
                            staged.append((original, temporary))
                cursor = connection.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
                if cursor.rowcount == 0:
                    raise paper_not_found()
        except Exception as exc:
            for original, temporary in reversed(staged):
                temporary.replace(original)
            if isinstance(exc, OSError):
                raise ApiError(status_code=503, code="cache_cleanup_failed",
                               message="The cached PDF could not be removed. Retry later.", retryable=True) from exc
            raise
        for _, temporary in staged:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                logging.getLogger(__name__).warning("Cache cleanup will be retried at startup.")


def get_paper_library(request: Request) -> PaperLibrary:
    return PaperLibrary(request.app.state.database_path, request.app.state.pdf_cache_path)
