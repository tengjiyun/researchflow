from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from fastapi import Request

from app.database import connect_database
from app.errors import ApiError
from app.schemas.collections import Collection, CollectionWrite
from app.services.library import paper_not_found


def collection_not_found() -> ApiError:
    return ApiError(status_code=404, code='collection_not_found',
                    message='The collection was not found.', retryable=False)


def name_conflict(error: sqlite3.IntegrityError) -> None:
    if error.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE:
        raise ApiError(status_code=409, code='collection_name_conflict',
                       message='A collection with this name already exists.', retryable=False) from error
    raise error


COLLECTION_SELECT = '''SELECT c.id, c.name, c.created_at, c.updated_at,
    (SELECT count(*) FROM paper_collections pc WHERE pc.collection_id=c.id) AS paper_count
    FROM collections c'''


def get_collection(connection: sqlite3.Connection, collection_id: int) -> Collection:
    row = connection.execute(COLLECTION_SELECT + ' WHERE c.id=?', (collection_id,)).fetchone()
    if row is None:
        raise collection_not_found()
    return Collection(**dict(row))


def require_paper(connection: sqlite3.Connection, paper_id: int) -> None:
    if connection.execute('SELECT 1 FROM papers WHERE id=?', (paper_id,)).fetchone() is None:
        raise paper_not_found()


class CollectionStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def create(self, name: str) -> Collection:
        name = CollectionWrite(name=name).name
        timestamp = datetime.now(timezone.utc).isoformat()
        with connect_database(self.database_path) as connection:
            connection.execute('BEGIN IMMEDIATE')
            try:
                cursor = connection.execute('''INSERT INTO collections (name,name_key,created_at,updated_at)
                    VALUES (?,?,?,?)''', (name, name.casefold(), timestamp, timestamp))
            except sqlite3.IntegrityError as error:
                name_conflict(error)
            return get_collection(connection, cursor.lastrowid)

    def list_collections(self, paper_id: int | None = None) -> list[Collection]:
        with connect_database(self.database_path) as connection:
            connection.execute('BEGIN')
            query = COLLECTION_SELECT
            parameters = ()
            if paper_id is not None:
                require_paper(connection, paper_id)
                query += ''' WHERE EXISTS (SELECT 1 FROM paper_collections pc
                    WHERE pc.collection_id=c.id AND pc.paper_id=?)'''
                parameters = (paper_id,)
            rows = connection.execute(query + ' ORDER BY c.name_key, c.id', parameters)
            return [Collection(**dict(row)) for row in rows]

    def rename(self, collection_id: int, name: str) -> Collection:
        name = CollectionWrite(name=name).name
        with connect_database(self.database_path) as connection:
            connection.execute('BEGIN IMMEDIATE')
            get_collection(connection, collection_id)
            try:
                connection.execute('UPDATE collections SET name=?,name_key=?,updated_at=? WHERE id=?',
                                   (name, name.casefold(), datetime.now(timezone.utc).isoformat(), collection_id))
            except sqlite3.IntegrityError as error:
                name_conflict(error)
            return get_collection(connection, collection_id)

    def delete(self, collection_id: int) -> None:
        with connect_database(self.database_path) as connection:
            connection.execute('BEGIN IMMEDIATE')
            if connection.execute('DELETE FROM collections WHERE id=?', (collection_id,)).rowcount == 0:
                raise collection_not_found()

    def add_paper(self, collection_id: int, paper_id: int) -> None:
        with connect_database(self.database_path) as connection:
            connection.execute('BEGIN IMMEDIATE')
            get_collection(connection, collection_id)
            require_paper(connection, paper_id)
            connection.execute('''INSERT INTO paper_collections (paper_id,collection_id,created_at)
                VALUES (?,?,?) ON CONFLICT(paper_id,collection_id) DO NOTHING''',
                (paper_id, collection_id, datetime.now(timezone.utc).isoformat()))

    def remove_paper(self, collection_id: int, paper_id: int) -> None:
        with connect_database(self.database_path) as connection:
            connection.execute('BEGIN IMMEDIATE')
            get_collection(connection, collection_id)
            require_paper(connection, paper_id)
            connection.execute('DELETE FROM paper_collections WHERE paper_id=? AND collection_id=?',
                               (paper_id, collection_id))


def get_collection_store(request: Request) -> CollectionStore:
    return request.app.state.collection_store
