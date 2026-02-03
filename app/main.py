from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .database import engine, Base
from .routers import users, documents, signing
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully!")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
    yield

app = FastAPI(title="Docsign by Karimun", lifespan=lifespan)


# Mount API routers
app.include_router(users.router)
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(signing.router, prefix="/signing", tags=["signing"])

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse('static/index.html')

@app.get("/health")
def health_check():
    """Health check endpoint for debugging"""
    import os
    return {
        "status": "ok",
        "database": "postgres" if os.getenv("DATABASE_URL") else "sqlite",
        "storage": "vercel_blob" if os.getenv("BLOB_READ_WRITE_TOKEN") else "local"
    }
