from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    frontend_origins: tuple[str, ...]
    openalex_api_key: str | None
    openalex_base_url: str
    database_path: Path
    pdf_cache_path: Path


@lru_cache
def get_settings() -> Settings:
    origins_value = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    origins = tuple(
        dict.fromkeys(
            origin.strip() for origin in origins_value.split(",") if origin.strip()
        )
    )

    return Settings(
        frontend_origins=origins,
        openalex_api_key=os.getenv("OPENALEX_API_KEY") or None,
        openalex_base_url=os.getenv(
            "OPENALEX_BASE_URL",
            "https://api.openalex.org",
        ),
        database_path=BACKEND_DIRECTORY / Path(
            os.getenv("DATABASE_PATH") or "data/researchflow.sqlite3"
        ),
        pdf_cache_path=BACKEND_DIRECTORY / Path(
            os.getenv("PDF_CACHE_PATH") or "data/pdfs"
        ),
    )
