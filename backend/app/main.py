"""
FastAPI application entrypoint for TransitAI Backend.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api import gov, health, recommendations, routes
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="TransitAI — Smart Public Transport Intelligence Backend",
    description="SIH 2026 Transit Intelligence, GTFS Multi-Modal Journey Engine & ML Predictions.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local dev & demo convenience
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(routes.router, prefix="/api")
app.include_router(gov.router, prefix="/api")


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
        content={"error": "internal_error", "detail": f"An unexpected error occurred: {str(exc)}"},
    )


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "TransitAI Backend",
        "version": "1.0.0",
        "docs_url": "/docs",
        "status": "online",
    }
