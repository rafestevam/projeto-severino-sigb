from fastapi import FastAPI

from app.adapters.api.health import router as health_router

app = FastAPI(title="Severino SIGB API")

app.include_router(health_router, prefix="/api")
