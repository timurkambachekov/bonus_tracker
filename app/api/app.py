from fastapi import FastAPI

from app.api.routes import router


def create_app() -> FastAPI:
    application = FastAPI(
        title="bonus_tracker",
        description="API for player data, season stats, contracts, and bonuses.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    application.include_router(router)
    return application


app = create_app()
