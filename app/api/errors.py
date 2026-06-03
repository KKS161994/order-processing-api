from datetime import timezone, datetime
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

def _error_response(
        status_code: int,
        code: str,
        message: str,
        details: Any = None,
        request_id: str | None = None,
):
    payload = {
        "error":{
            "status" : status_code,
            "code" : code,
            "message" : message,
            "timestamp" : datetime.now(timezone.utc).isoformat()
        }
    }

    if details is not None:
        payload["error"]["details"] = details
    if request_id is not None:
        payload["error"]["request_id"] = request_id

    return JSONResponse(status_code=status_code,content=payload)


async def http_exception_handler(request: Request, exc: HTTPException)-> JSONResponse:
    code_map = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limited",
        500: "internal_error",
        503: "service_unavailable",
    }

    code = code_map[exc.status_code]

    return _error_response(
        status_code=exc.status_code,
        code= code,
        message=str(exc.detail) if exc.detail else ""
    )

async def request_validation_handler(
        request : Request,
        exc : RequestValidationError
):
    """Convert Pydantic/FastAPI validation errors into a flat, client-friendly shape.

    Each entry from ``exc.errors()`` has a ``loc`` tuple tracing the path from
    the request root to the offending field, e.g. ``("body", "items", 0, "quantity")``.
    The leading ``"body"`` marker is dropped (the caller already knows they sent a body),
    integer list indices are stringified, and the remaining segments are joined with
    ``.`` to produce a dotted path like ``"items.0.quantity"``.

    Example — POST ``{"user_id": "abc", "items": [{"quantity": "two"}]}`` yields::

        [
            {"field": "user_id",          "message": "...", "type": "int_parsing"},
            {"field": "items.0.quantity", "message": "...", "type": "int_parsing"},
        ]
    """
    errors = [
        {
            "field" : ".".join(str(loc) for loc in err["loc"] if loc!= "body"),
            "message" : err["msg"],
            "type" : err["type"]
        } for err in exc.errors()
    ]

    return _error_response(
        status_code=422,
        code = "validation_error",
        message = "validation request failed",
        details={"errors":errors}
    )