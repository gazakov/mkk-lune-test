from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.endpoints import router as api_router
from app.db.init_db import init_db
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Directory API for Organizations, Buildings, and Activities",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
def health_check():
        return {"status": "ok"}
