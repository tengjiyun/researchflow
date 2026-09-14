from datetime import datetime, timezone
import json
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
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

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
                "SELECT id, openalex_id, title, publication_year, venue FROM papers ORDER BY id DESC"
            ).fetchall()
            return [LibraryPaper(**dict(row)) for row in rows]

    def get(self, paper_id: int) -> PaperDetail:
        with connect_database(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM papers WHERE id = ?", (paper_id,)
            ).fetchone()
            if row is None:
                raise paper_not_found()
            return PaperDetail(**paper_fields(row))

    def delete(self, paper_id: int) -> None:
        with connect_database(self.database_path) as connection:
            cursor = connection.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
            if cursor.rowcount == 0:
                raise paper_not_found()


def get_paper_library(request: Request) -> PaperLibrary:
    return PaperLibrary(request.app.state.database_path)
