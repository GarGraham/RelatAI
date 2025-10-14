"""Application entrypoint for the RelatAI FastAPI backend."""

from fastapi import Depends, FastAPI

from relat_ai.api.routes import audit, configuration, datasets, health
from relat_ai.core.config import Settings, get_settings, set_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app_settings = settings or get_settings()
    app = FastAPI(
        title="RelatAI API",
        version="0.1.0",
        debug=app_settings.app_env == "development",
    )

    # Ensure dependency-injected settings return the instance associated with
    # this application rather than the process-global default.
    set_settings(app_settings)
    app.dependency_overrides[get_settings] = lambda: app_settings

    app.include_router(health.router)
    app.include_router(datasets.router)
    app.include_router(configuration.router)
    app.include_router(audit.router)

    @app.get("/config", tags=["system"], summary="Retrieve runtime configuration metadata")
    async def read_config(settings: Settings = Depends(get_settings)) -> dict[str, str]:
        """Expose non-sensitive runtime configuration data for observability."""

        return {
            "environment": settings.app_env,
            "host": settings.app_host,
            "port": str(settings.app_port),
            "max_upload_size_mb": str(settings.max_upload_size_mb),
        }

    return app


app = create_app()
