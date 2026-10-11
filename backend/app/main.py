"""Main FastAPI application entrypoint."""
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.database import init_db
from app.api.routes import files_router, health_router

# Initialize database schema on startup
init_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers under /api
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(files_router, prefix=settings.API_V1_STR)

# Mount sample data for demo loading
sample_dir = Path(__file__).resolve().parent.parent / "sample_data"
sample_dir.mkdir(parents=True, exist_ok=True)
app.mount("/sample_data", StaticFiles(directory=str(sample_dir)), name="sample_data")

# Mount frontend dist (React app) or fallback static dashboard
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
static_dir = Path(__file__).resolve().parent.parent / "static"

if frontend_dist.exists() and (frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", include_in_schema=False)
async def root():
    """Serves the interactive geospatial dashboard (React build or fallback)."""
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        return FileResponse(str(frontend_dist / "index.html"))
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(
        content={
            "message": "Welcome to Aereo Geospatial File Measurement API",
            "docs": "/docs",
            "health": "/api/health"
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global fallback exception handler."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )
