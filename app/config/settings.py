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
    db_host, db_port, db_name, db_user, db_password:
        PostgreSQL connection parameters. Defaults target the local
        ``docker-compose`` postgres service; override via environment variables
        (``DB_HOST`` etc.) or ``.env`` in non-local environments. Treat
        ``db_password`` as a secret — never commit a real value.

    Properties
    ----------
    database_url:
        SQLAlchemy/psycopg-style URL assembled from the ``db_*`` fields. Use
        this when handing a connection string to SQLAlchemy or Alembic rather
        than concatenating fields at the call site.

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

    db_host:str = "localhost"
    db_port:int = 5432
    db_name:str = "order_processing"
    db_user:str = "orderapi"
    db_password:str = "orderapi_dev_password"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
"""Process-wide singleton. Import this rather than calling ``Settings()`` directly."""
