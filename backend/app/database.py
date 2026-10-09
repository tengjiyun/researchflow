from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3


DOCUMENT_TABLE = """
    CREATE TABLE IF NOT EXISTS {table} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
        source_kind TEXT NOT NULL DEFAULT 'download' CHECK (source_kind IN ('download','upload')),
        original_filename TEXT,
        source_url TEXT,
        source_format TEXT NOT NULL DEFAULT 'pdf' CHECK (source_format = 'pdf'),
        access_type TEXT NOT NULL DEFAULT 'open_access' CHECK (access_type IN ('open_access','unknown')),
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
        CHECK ((source_kind='download' AND source_url IS NOT NULL AND access_type='open_access')
            OR (source_kind='upload' AND source_url IS NULL AND access_type='unknown')),
        UNIQUE(paper_id, source_url)
    )
"""


def migrate_documents(connection: sqlite3.Connection) -> None:
    columns = [row['name'] for row in connection.execute('PRAGMA table_info(documents)')]
    if 'source_kind' in columns:
        return
    connection.execute('PRAGMA foreign_keys = OFF')
    try:
        connection.execute('BEGIN IMMEDIATE')
        sequence = connection.execute("SELECT seq FROM sqlite_sequence WHERE name='documents'").fetchone()
        connection.execute(DOCUMENT_TABLE.format(table='documents_new'))
        names = ', '.join(columns)
        connection.execute(f'INSERT INTO documents_new ({names}) SELECT {names} FROM documents')
        connection.execute('DROP TABLE documents')
        connection.execute('ALTER TABLE documents_new RENAME TO documents')
        if sequence is not None:
            connection.execute("DELETE FROM sqlite_sequence WHERE name='documents'")
            connection.execute("INSERT INTO sqlite_sequence(name, seq) VALUES ('documents', ?)", (sequence[0],))
        connection.execute('CREATE INDEX documents_paper ON documents(paper_id, id)')
        if connection.execute('PRAGMA foreign_key_check').fetchone() is not None:
            raise sqlite3.IntegrityError('Document migration failed the foreign key check.')
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute('PRAGMA foreign_keys = ON')


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
        connection.execute(DOCUMENT_TABLE.format(table='documents'))
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS search_cache (
                cache_key TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                cached_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                name_key TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS paper_collections (
                paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
                collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                PRIMARY KEY (paper_id, collection_id)
            );
            CREATE INDEX IF NOT EXISTS paper_collections_collection ON paper_collections(collection_id);
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
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                status TEXT NOT NULL CHECK (status IN ('pending','processing','completed','failed')),
                analysis_version TEXT NOT NULL CHECK (analysis_version='full-text-v1'),
                service_name TEXT NOT NULL,
                service_model TEXT NOT NULL,
                settings_json TEXT NOT NULL,
                error_code TEXT,
                error_message TEXT,
                started_at TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS analysis_active_document ON analysis_runs(document_id)
                WHERE status IN ('pending','processing');
            CREATE INDEX IF NOT EXISTS analysis_queue ON analysis_runs(status, id);
            CREATE INDEX IF NOT EXISTS analysis_document_history ON analysis_runs(document_id, id);
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_run_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
                finding_type TEXT NOT NULL CHECK (finding_type IN
                    ('research_problem','methodology','key_finding','limitation')),
                content TEXT,
                support_status TEXT NOT NULL CHECK (support_status IN ('supported','unavailable','rejected')),
                sequence_number INTEGER NOT NULL CHECK (sequence_number >= 1),
                created_at TEXT NOT NULL,
                CHECK ((support_status='supported' AND content IS NOT NULL AND length(trim(content))>0)
                    OR (support_status='unavailable' AND content IS NULL) OR support_status='rejected'),
                UNIQUE(analysis_run_id, finding_type, sequence_number)
            );
            CREATE TABLE IF NOT EXISTS evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                finding_id INTEGER NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
                chunk_id INTEGER NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
                source_excerpt TEXT NOT NULL CHECK (length(source_excerpt)>0),
                start_page INTEGER NOT NULL CHECK (start_page >= 1),
                end_page INTEGER NOT NULL CHECK (end_page=start_page),
                start_offset INTEGER NOT NULL CHECK (start_offset >= 0),
                end_offset INTEGER NOT NULL CHECK (end_offset > start_offset),
                is_primary INTEGER NOT NULL CHECK (is_primary IN (0,1)),
                created_at TEXT NOT NULL,
                UNIQUE(finding_id, chunk_id, start_offset, end_offset)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS evidence_primary ON evidence(finding_id) WHERE is_primary=1;
        """)
        migrate_documents(connection)
