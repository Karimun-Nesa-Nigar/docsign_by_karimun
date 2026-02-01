from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .database import engine, Base
from .routers import users, documents, signing

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Docsign by Karimun")

# Mount API routers
app.include_router(users.router)
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(signing.router, prefix="/signing", tags=["signing"])

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse('static/index.html')
