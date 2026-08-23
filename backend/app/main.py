from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    # Required fields are sourced from the process environment at runtime; mypy has no
    # visibility into BaseSettings' env-var loading and treats them as missing constructor args.
    resolved_settings = settings or Settings()  # type: ignore[call-arg]

    app = FastAPI(title="Business Management Platform API", version="0.1.0")
    app.state.settings = resolved_settings
    app.include_router(health_router)
    return app
