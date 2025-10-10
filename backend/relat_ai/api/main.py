"""Application entrypoint for the RelatAI FastAPI backend."""

from fastapi import FastAPI

from relat_ai.api.routes import datasets, health
from relat_ai.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app_settings = settings or get_settings()
    app = FastAPI(title="RelatAI API", version="0.1.0", debug=app_settings.app_env == "development")

    app.include_router(health.router)
    app.include_router(datasets.router)

    @app.get("/config", tags=["system"], summary="Retrieve runtime configuration metadata")
    async def read_config() -> dict[str, str]:
        """Expose non-sensitive runtime configuration data for observability."""
        return {
            "environment": app_settings.app_env,
            "host": app_settings.app_host,
            "port": str(app_settings.app_port),
            "max_upload_size_mb": str(app_settings.max_upload_size_mb),
        }

    return app


app = create_app()
