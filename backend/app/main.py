"""Punto de entrada de la API REST de FashionStore.

Monta un router por cada paquete de analisis (ver docs/04-analisis-arquitectura.md).
Los paquetes se activan por ciclo: los del ciclo 1 ya estan montados, los de los
ciclos 2 y 3 se descomentan a medida que se implementan.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# --- Ciclo 1 -------------------------------------------------------------
from app.modules.seguridad.router import admin_router as seguridad_admin_router
from app.modules.seguridad.router import perfil_router as seguridad_perfil_router
from app.modules.seguridad.router import router as seguridad_router
from app.modules.organizacion.router import router as organizacion_router
from app.modules.catalogo.router import router as catalogo_router

# --- Ciclo 2 -------------------------------------------------------------
# from app.modules.inventario.router import router as inventario_router
# from app.modules.catalogo_publico.router import router as catalogo_publico_router
# from app.modules.reservas.router import router as reservas_router

# --- Ciclo 3 -------------------------------------------------------------
# from app.modules.ventas.router import router as ventas_router
# from app.modules.pagos.router import router as pagos_router
# from app.modules.vestidor_virtual.router import router as vestidor_router
# from app.modules.ia.router import router as ia_router
# from app.modules.reportes.router import router as reportes_router


app = FastAPI(
    title="FashionStore API",
    description=(
        "Plataforma inteligente de comercio electronico para tienda de ropa "
        "con vestidores virtuales via realidad aumentada. "
        "Examen 1 - Sistemas de Informacion II, S2-2026."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Angular y Flutter consumen exactamente el mismo contrato (RNF07, RNF08).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Infraestructura"], include_in_schema=False)
def raiz() -> dict:
    """Punto de entrada. La API no sirve contenido en la raiz.

    Existe para que abrir el dominio en el navegador diga algo util en vez de
    un 404 seco, que se confunde con un despliegue roto.
    """
    return {
        "servicio": "fashionstore-api",
        "version": app.version,
        "documentacion": "/docs",
        "salud": "/health",
        "api": settings.API_PREFIX,
    }


@app.get("/health", tags=["Infraestructura"])
def health() -> dict:
    """Sonda de salud. La usa Railway para saber si el servicio esta vivo."""
    return {
        "status": "ok",
        "servicio": "fashionstore-api",
        "version": app.version,
        "entorno": settings.ENTORNO,
    }


API = settings.API_PREFIX

# --- Ciclo 1 -------------------------------------------------------------
app.include_router(seguridad_router, prefix=API)
app.include_router(seguridad_admin_router, prefix=API)
app.include_router(seguridad_perfil_router, prefix=API)
app.include_router(organizacion_router, prefix=API)
app.include_router(catalogo_router, prefix=API)

# --- Ciclo 2 -------------------------------------------------------------
# app.include_router(inventario_router, prefix=API)
# app.include_router(catalogo_publico_router, prefix=API)
# app.include_router(reservas_router, prefix=API)

# --- Ciclo 3 -------------------------------------------------------------
# app.include_router(ventas_router, prefix=API)
# app.include_router(pagos_router, prefix=API)
# app.include_router(vestidor_router, prefix=API)
# app.include_router(ia_router, prefix=API)
# app.include_router(reportes_router, prefix=API)
