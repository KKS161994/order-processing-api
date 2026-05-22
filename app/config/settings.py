from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from the environment and ``.env``.

    Centralises every runtime knob the order-processing API needs so the rest of
    the codebase never has to read ``os.environ`` directly. Each attribute below
    is a typed field; pydantic-settings populates it from (in order of
    precedence) a real environment variable, the ``.env`` file at the repo root,
    or the default declared here. Names are matched case-insensitively, so the
    shell variable ``ENVIRONMENT`` maps to the ``environment`` field.

    Fields
    ------
    app_name:
        Human-readable service name, surfaced in logs and the OpenAPI schema.
    app_version:
        Semver string for the running build; bump on each release.
    environment:
        Deployment target — ``development``, ``staging``, or ``production``.
        Used to gate debug behaviour and pick environment-specific defaults.

    Usage
    -----
    Import the module-level ``settings`` singleton — do not construct
    ``Settings()`` yourself, otherwise the ``.env`` file is re-parsed on every
    call and you lose a single source of truth::

        from app.config.settings import settings

        if settings.environment == "production":
            ...

    In FastAPI handlers, prefer dependency injection so tests can swap the
    config via ``app.dependency_overrides``::

        from fastapi import Depends
        from app.config.settings import Settings, settings

        def get_settings() -> Settings:
            return settings

        @router.get("/health")
        def health(cfg: Settings = Depends(get_settings)):
            return {"env": cfg.environment, "version": cfg.app_version}
    """

    app_name: str = "order-processing-api"
    app_version: str = "0.1.0"
    environment: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
"""Process-wide singleton. Import this rather than calling ``Settings()`` directly."""
