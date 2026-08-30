"""
FastAPI application entrypoint.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api import health, recommendations, routes, insights
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Transit SIH Backend",
    description="Smart India Hackathon transit recommendation backend (MVP).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(routes.router, prefix="/api")
app.include_router(insights.router, prefix="/api")


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": str(exc)},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "request_error", "detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": "An unexpected error occurred."},
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Transit SIH backend is running. See /docs for API docs."}
