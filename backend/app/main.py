import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.papers import router as papers_router
from app.api.documents import router as documents_router
from app.core.config import get_settings
from app.errors import register_error_handlers
from app.database import initialise_database
from app.services.documents import DocumentStore
from app.services.document_worker import DocumentRunner, worker_lock


def create_app() -> FastAPI:
    settings = get_settings()
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        initialise_database(settings.database_path)
        store = application.state.document_store
        with worker_lock(settings.database_path.with_suffix(".pdf-worker.lock")):
            with worker_lock(settings.database_path.with_suffix(".pdf-job.lock")):
                store.recover_interrupted()
            runner = DocumentRunner(store)
            task = asyncio.create_task(runner.run())
            try:
                yield
            finally:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    application = FastAPI(title="ResearchFlow API", lifespan=lifespan)
    application.state.database_path = settings.database_path
    application.state.pdf_cache_path = settings.pdf_cache_path
    application.state.document_store = DocumentStore(settings.database_path, settings.pdf_cache_path)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.frontend_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )
    register_error_handlers(application)
    application.include_router(papers_router, prefix="/api")
    application.include_router(documents_router, prefix="/api")
    return application


app = create_app()
