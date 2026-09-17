"""Punto de entrada de la API REST de Violet Boutique.

Monta un router por cada paquete de analisis (ver docs/04-analisis-arquitectura.md).
Los paquetes se activan por ciclo: los del ciclo 1 ya estan montados, los de los
ciclos 2 y 3 se descomentan a medida que se implementan.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.registro import configurar_logging

# --- Ciclo 1 -------------------------------------------------------------
from app.modules.seguridad.router import admin_router as seguridad_admin_router
from app.modules.seguridad.router import perfil_router as seguridad_perfil_router
from app.modules.seguridad.router import router as seguridad_router
from app.modules.organizacion.router import router as organizacion_router
from app.modules.organizacion.router import consulta_router as organizacion_consulta_router
from app.modules.organizacion.empleados.router import router as empleados_router
from app.modules.organizacion.proveedores_router import router as proveedores_router
from app.modules.organizacion.proveedores_router import (
    router_proveedor as proveedores_mi_ficha_router,
)
from app.modules.catalogo.router import router as catalogo_router
from app.modules.catalogo.maestros.router import router as catalogo_maestros_router
from app.modules.catalogo.temporadas_router import router as catalogo_temporadas_router

# --- Ciclo 2 -------------------------------------------------------------
from app.modules.inventario.router import router as inventario_router
from app.modules.inventario.router import (
    operacion_router as inventario_operacion_router,
)
# CU-14 es de Karen y vive en archivos propios dentro del paquete de Mateo,
# con el mismo patron que catalogo/ usa para imagenes_* y temporadas_*.
from app.modules.inventario.consolidado_router import (
    router as inventario_consolidado_router,
)
from app.modules.catalogo_publico.router import router as catalogo_publico_router
from app.modules.reservas.router import router as reservas_router
from app.modules.reservas.router import (
    mantenimiento_router as reservas_mantenimiento_router,
)
from app.modules.reservas.router import (
    sucursal_router as reservas_sucursal_router,
)

# --- Ciclo 3 -------------------------------------------------------------
# CU-38 es de P3 y vive en archivos propios dentro del paquete de catalogo,
# con el mismo patron que imagenes_* y temporadas_*. Router aparte porque la
# guarda de rol es PROVEEDOR y no ADMINISTRADOR.
from app.modules.catalogo.proveedor_router import router as catalogo_proveedor_router
# CU-26 es de Karen y vive en archivos propios dentro del paquete de Mateo,
# con el mismo patron que consolidado_* dentro de inventario/.
from app.modules.ventas.carrito_router import router as carrito_router
from app.modules.ventas.router import router as pedidos_router
from app.modules.ventas.router import router_operacion as pedidos_operacion_router
# CU-36 es de Karen y vive en archivos propios dentro de P11, con el mismo
# patron que consolidado_* y carrito_*. El `router.py` del paquete queda para
# CU-37 (exportar a PDF y Excel), que es el otro caso de uso de P11.
from app.modules.reportes.tablero_router import router as tablero_router
# from app.modules.ventas.router import router as ventas_router
# from app.modules.pagos.router import router as pagos_router
# from app.modules.vestidor_virtual.router import router as vestidor_router
# from app.modules.ia.router import router as ia_router
# from app.modules.reportes.router import router as reportes_router


# Antes de construir la aplicacion: uvicorn deja el logger raiz sin manejador
# y todo lo que escriba la aplicacion por debajo de WARNING se pierde. Ver
# app/core/registro.py --- lo descubrio el proveedor de correo `consola`,
# que no imprimia nada.
configurar_logging()

app = FastAPI(
    title="Violet Boutique API",
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


# --- Imagenes del catalogo (CU-11) ---------------------------------------
# El volumen persistente de MEDIA_ROOT se sirve tal cual, sin pasar por la API
# ni exigir token: las fotos del catalogo son publicas --- las muestran la
# vitrina (CU-17, CU-18) y la app movil --- y hacerlas pasar por un endpoint
# autenticado obligaria a la app a llevar el token en cada miniatura.
#
# La base guarda solo la ruta relativa; el prefijo es este (seccion 6.8).
_MEDIA = Path(settings.MEDIA_ROOT)
_MEDIA.mkdir(parents=True, exist_ok=True)
app.mount(settings.MEDIA_URL, StaticFiles(directory=_MEDIA), name="media")


@app.get("/", tags=["Infraestructura"], include_in_schema=False)
def raiz() -> dict:
    """Punto de entrada. La API no sirve contenido en la raiz.

    Existe para que abrir el dominio en el navegador diga algo util en vez de
    un 404 seco, que se confunde con un despliegue roto.
    """
    return {
        "servicio": "violetboutique-api",
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
        "servicio": "violetboutique-api",
        "version": app.version,
        "entorno": settings.ENTORNO,
    }


API = settings.API_PREFIX

# --- Ciclo 1 -------------------------------------------------------------
app.include_router(seguridad_router, prefix=API)
app.include_router(seguridad_admin_router, prefix=API)
app.include_router(seguridad_perfil_router, prefix=API)
app.include_router(organizacion_router, prefix=API)
app.include_router(organizacion_consulta_router, prefix=API)
app.include_router(empleados_router, prefix=API)
app.include_router(proveedores_router, prefix=API)
app.include_router(proveedores_mi_ficha_router, prefix=API)
app.include_router(catalogo_router, prefix=API)
app.include_router(catalogo_maestros_router, prefix=API)
app.include_router(catalogo_temporadas_router, prefix=API)

# --- Ciclo 2 -------------------------------------------------------------
app.include_router(inventario_router, prefix=API)
app.include_router(inventario_operacion_router, prefix=API)
app.include_router(inventario_consolidado_router, prefix=API)
app.include_router(catalogo_publico_router, prefix=API)
app.include_router(reservas_router, prefix=API)
app.include_router(reservas_sucursal_router, prefix=API)
app.include_router(reservas_mantenimiento_router, prefix=API)

# --- Ciclo 3 -------------------------------------------------------------
app.include_router(catalogo_proveedor_router, prefix=API)
app.include_router(carrito_router, prefix=API)
app.include_router(tablero_router, prefix=API)
# CU-27. Van los dos: `/tienda/pedidos` es del cliente y `/pedidos` es de la
# operacion --- la barrida de vencidos ---, con otro rol. Mismo reparto que
# tienen reservas y su router de mantenimiento.
app.include_router(pedidos_router, prefix=API)
app.include_router(pedidos_operacion_router, prefix=API)
# app.include_router(pagos_router, prefix=API)
# app.include_router(vestidor_router, prefix=API)
# app.include_router(ia_router, prefix=API)
# app.include_router(reportes_router, prefix=API)
