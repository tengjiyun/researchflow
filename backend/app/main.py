import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.papers import router as papers_router
from app.api.documents import router as documents_router
from app.api.analyses import router as analyses_router
from app.core.config import get_settings
from app.errors import register_error_handlers
from app.database import initialise_database
from app.services.documents import DocumentStore
from app.services.document_worker import DocumentRunner, worker_lock
from app.services.analyses import AnalysisStore
from app.services.analysis_client import AnalysisClient
from app.services.analysis_worker import AnalysisRunner


def create_app() -> FastAPI:
    settings = get_settings()
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        initialise_database(settings.database_path)
        store = application.state.document_store
        with worker_lock(settings.database_path.with_suffix(".pdf-worker.lock")):
            with worker_lock(settings.database_path.with_suffix(".pdf-job.lock")):
                store.recover_interrupted()
            application.state.analysis_store.recover_interrupted()
            runner = DocumentRunner(store)
            analysis_runner = AnalysisRunner(application.state.analysis_store, application.state.analysis_client)
            tasks = [asyncio.create_task(runner.run()), asyncio.create_task(analysis_runner.run())]
            try:
                yield
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    application = FastAPI(title="ResearchFlow API", lifespan=lifespan)
    application.state.database_path = settings.database_path
    application.state.pdf_cache_path = settings.pdf_cache_path
    application.state.document_store = DocumentStore(settings.database_path, settings.pdf_cache_path)
    application.state.analysis_store = AnalysisStore(settings.database_path)
    application.state.analysis_client = AnalysisClient(settings.openrouter_api_key)
    application.state.analysis_model = settings.openrouter_model

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
    application.include_router(analyses_router, prefix="/api")
    return application


app = create_app()
