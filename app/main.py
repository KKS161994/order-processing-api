"""ASGI entry point for the order-processing API.

Builds the :class:`fastapi.FastAPI` application instance that ``uvicorn`` (or any
other ASGI server) imports as ``app.main:app``. Title and version are pulled
from the :mod:`app.config.settings` singleton so a single source of truth drives
both the OpenAPI schema and the ``/version`` endpoint.

Routers for the actual order-processing endpoints should be attached to ``app``
in this module via ``app.include_router(...)`` as they come online; the two
routes defined directly below are deliberately scoped to operational concerns
(liveness and build identification) only.

Run locally with::

    uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.config.settings import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe.

    Returns a static ``{"status": "OK"}`` payload so orchestration platforms
    (Kubernetes, ECS, Fly, etc.) can confirm the process is up and the ASGI
    event loop is servicing requests. Deliberately does **not** touch the
    database, Redis, or any downstream — those belong in a separate readiness
    probe so a slow dependency never causes a pod restart.
    """
    return {"status": "OK"}


@app.get("/version")
def version() -> dict[str, str]:
    """Identify the running build.

    Surfaces the application name, semver string, and deployment environment so
    operators can confirm which release is live without shelling into the
    container. Useful during rollouts and when debugging environment-specific
    incidents in production.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }