from fastapi import FastAPI

from app.adapters.api.exemplares import exemplares_router
from app.adapters.api.health import router as health_router
from app.adapters.api.obras import obras_router

app = FastAPI(title="Severino SIGB API")

app.include_router(health_router, prefix="/api")
app.include_router(obras_router, prefix="/api")
app.include_router(exemplares_router, prefix="/api")
