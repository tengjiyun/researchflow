from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.openalex import get_openalex_service


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def set_search_service() -> Iterator[Callable[[object], None]]:
    def set_service(service: object) -> None:
        app.dependency_overrides[get_openalex_service] = lambda: service

    yield set_service
    app.dependency_overrides.clear()
