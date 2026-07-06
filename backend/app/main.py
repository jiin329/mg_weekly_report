"""FastAPI application for the weekly-report-chat backend.

Wires the REST router (task 4.6) and a global structured-error handler onto the
app, alongside the health check used by the desktop shell. The endpoints
themselves live in ``app.api``; the services behind them are implemented by the
[BE] track tasks (see tasks.md section 4).

Every failing request is rendered as the structured error shape
``{"error": {"code", "message", "details"}}`` (design.md "Error Handling").
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import __version__
from .api import APIError, router
from .error_codes import ErrorCode, build_error_response, http_status_for

app = FastAPI(
    title="weekly-report-chat backend",
    version=__version__,
    description="Local loopback REST API for the weekly-report-chat Desktop_App.",
)


@app.exception_handler(APIError)
async def _handle_api_error(_request: Request, exc: APIError) -> JSONResponse:
    """Render a typed APIError as the structured error response (Req 8.7, 8.8)."""
    body = build_error_response(exc.code, exc.message, exc.details)
    return JSONResponse(
        status_code=http_status_for(exc.code),
        content=body.model_dump(by_alias=True),
    )


@app.exception_handler(RequestValidationError)
async def _handle_validation_error(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Render request-body validation failures in the structured error shape."""
    body = build_error_response(
        ErrorCode.INTERNAL_ERROR,
        "요청 형식이 올바르지 않습니다.",
        details=exc.errors(),
    )
    return JSONResponse(status_code=400, content=body.model_dump(by_alias=True))


@app.exception_handler(Exception)
async def _handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all so internal errors still return the structured shape (Req 8.8)."""
    body = build_error_response(ErrorCode.INTERNAL_ERROR, "내부 오류가 발생했습니다.")
    return JSONResponse(
        status_code=http_status_for(ErrorCode.INTERNAL_ERROR),
        content=body.model_dump(by_alias=True),
    )


app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe used by the desktop shell to confirm the backend started."""
    return {"status": "ok", "version": __version__}
