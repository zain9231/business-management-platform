from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()

    app = FastAPI(title="Business Management Platform API", version="0.1.0")
    app.state.settings = resolved_settings
    app.include_router(health_router)
    return app
