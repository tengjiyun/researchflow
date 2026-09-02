from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.papers import router as papers_router
from app.core.config import get_settings
from app.errors import register_error_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="ResearchFlow API")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.frontend_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )
    register_error_handlers(application)
    application.include_router(papers_router, prefix="/api")
    return application


app = create_app()

