from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapters.api.admin import admin_router
from app.adapters.api.emprestimos import emprestimos_router
from app.adapters.api.exemplares import exemplares_router
from app.adapters.api.health import router as health_router
from app.adapters.api.inventario import inventario_router
from app.adapters.api.leitores import leitores_router
from app.adapters.api.obras import obras_router
from app.adapters.api.relatorios import relatorios_router
from app.adapters.api.reservas import reservas_router
from app.infrastructure.scheduler import scheduler, setup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_scheduler()
    scheduler.start()
    try:
        yield
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


app = FastAPI(title="Severino SIGB API", lifespan=lifespan)

app.include_router(health_router, prefix="/api")
app.include_router(obras_router, prefix="/api")
app.include_router(exemplares_router, prefix="/api")
app.include_router(emprestimos_router, prefix="/api")
app.include_router(reservas_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(inventario_router, prefix="/api")
app.include_router(relatorios_router, prefix="/api")
app.include_router(leitores_router, prefix="/api")
