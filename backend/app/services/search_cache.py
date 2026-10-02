from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import sqlite3

from fastapi import Request

from app.core.config import get_settings
from app.database import connect_database
from app.schemas.papers import PaperSearchResponse
from app.services.openalex import RESULTS_PER_PAGE


class SearchCache:
    def __init__(self, database_path: Path, base_url: str) -> None:
        self.database_path = database_path
        self.base_url = base_url.rstrip('/')

    def key(self, query: str, page: int) -> str:
        return json.dumps(['openalex-search-v1', self.base_url, query.strip(), page, RESULTS_PER_PAGE])

    def save(self, query: str, page: int, result: PaperSearchResponse) -> datetime | None:
        timestamp = datetime.now(timezone.utc)
        try:
            with connect_database(self.database_path) as connection:
                connection.execute('''INSERT INTO search_cache (cache_key,response_json,cached_at)
                    VALUES (?,?,?) ON CONFLICT(cache_key) DO UPDATE SET
                    response_json=excluded.response_json, cached_at=excluded.cached_at''',
                    (self.key(query, page), result.model_dump_json(exclude={'from_cache', 'cached_at'}),
                     timestamp.isoformat()))
        except sqlite3.Error:
            logging.getLogger(__name__).warning('Search cache could not be saved.')
            return None
        return timestamp

    def load(self, query: str, page: int) -> PaperSearchResponse | None:
        try:
            with connect_database(self.database_path) as connection:
                row = connection.execute('SELECT response_json,cached_at FROM search_cache WHERE cache_key=?',
                                         (self.key(query, page),)).fetchone()
            if row is None:
                return None
            timestamp = datetime.fromisoformat(row['cached_at'])
            if timestamp.tzinfo is None or not timedelta(0) <= datetime.now(timezone.utc) - timestamp <= timedelta(days=7):
                return None
            result = PaperSearchResponse.model_validate_json(row['response_json'])
            if result.page != page:
                return None
            return result.model_copy(update={'from_cache': True, 'cached_at': timestamp})
        except (sqlite3.Error, ValueError):
            logging.getLogger(__name__).warning('Search cache could not be read.')
            return None


def get_search_cache(request: Request) -> SearchCache:
    return SearchCache(request.app.state.database_path, get_settings().openalex_base_url)
