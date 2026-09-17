from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3


@contextmanager
def connect_database(path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(path, timeout=5.0)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            yield connection
    finally:
        connection.close()


def initialise_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect_database(path) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                openalex_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                authors_json TEXT NOT NULL,
                publication_year INTEGER,
                abstract TEXT,
                doi TEXT,
                venue TEXT,
                citation_count INTEGER NOT NULL DEFAULT 0 CHECK (citation_count >= 0),
                landing_page_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
                source_url TEXT NOT NULL,
                source_format TEXT NOT NULL DEFAULT 'pdf' CHECK (source_format = 'pdf'),
                access_type TEXT NOT NULL DEFAULT 'open_access' CHECK (access_type = 'open_access'),
                licence TEXT,
                local_file_path TEXT,
                file_sha256 TEXT,
                file_size_bytes INTEGER,
                page_count INTEGER,
                retrieval_status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (retrieval_status IN ('pending','processing','completed','failed')),
                parsing_status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (parsing_status IN ('pending','processing','completed','failed')),
                error_code TEXT,
                error_message TEXT,
                retrieved_at TEXT,
                parsed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(paper_id, source_url)
            );
            CREATE TABLE IF NOT EXISTS document_pages (
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                page_number INTEGER NOT NULL CHECK (page_number >= 1),
                source_text TEXT NOT NULL,
                PRIMARY KEY(document_id, page_number)
            );
            CREATE TABLE IF NOT EXISTS sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                section_type TEXT NOT NULL,
                original_heading TEXT,
                sequence_number INTEGER NOT NULL,
                start_page INTEGER NOT NULL CHECK (start_page >= 1),
                end_page INTEGER NOT NULL CHECK (end_page >= start_page),
                created_at TEXT NOT NULL,
                UNIQUE(document_id, sequence_number),
                UNIQUE(id, document_id)
            );
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                section_id INTEGER NOT NULL,
                sequence_number INTEGER NOT NULL,
                source_text TEXT NOT NULL,
                start_page INTEGER NOT NULL,
                end_page INTEGER NOT NULL CHECK (end_page = start_page),
                start_character INTEGER NOT NULL CHECK (start_character >= 0),
                end_character INTEGER NOT NULL CHECK (end_character > start_character),
                created_at TEXT NOT NULL,
                UNIQUE(document_id, sequence_number),
                FOREIGN KEY(section_id, document_id) REFERENCES sections(id, document_id) ON DELETE CASCADE,
                FOREIGN KEY(document_id, start_page) REFERENCES document_pages(document_id, page_number)
            );
            CREATE INDEX IF NOT EXISTS documents_paper ON documents(paper_id, id);
            CREATE INDEX IF NOT EXISTS chunks_section ON chunks(section_id, sequence_number);
        """)
