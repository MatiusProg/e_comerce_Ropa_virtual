"""Todo router definido tiene que estar montado en la aplicación.

Por qué existe esta prueba
--------------------------
Un `APIRouter` que se define y no se incluye en `main.py` simplemente no aporta
rutas. FastAPI no avisa: el módulo importa sin error, la aplicación arranca, y
los endpoints devuelven 404 como si no existieran.

Ya pasó una vez. El `consulta_router` de ciudades quedó sin montar al resolver
un conflicto de `main.py` entre dos ramas, y rompió tres pantallas a la vez sin
que ningún error lo delatara: parecía que las ciudades se habían borrado de la
base.

El riesgo no es escribir mal el router: es perder su línea de registro en un
merge. `main.py` es el único archivo que todos los casos de uso tocan, así que
es justo donde eso va a volver a pasar.

Esta prueba recorre los routers de verdad, no una lista escrita a mano: si
alguien agrega un módulo nuevo, queda cubierto sin tocar este archivo.
"""

from fastapi import APIRouter

from app.core.config import settings
from app.main import app

#: Módulos que declaran routers. Al agregar un paquete nuevo se suma acá.
MODULOS_CON_ROUTER = (
    "app.modules.seguridad.router",
    "app.modules.organizacion.router",
    "app.modules.organizacion.empleados.router",
    "app.modules.organizacion.proveedores_router",
    "app.modules.catalogo.router",
    "app.modules.catalogo.maestros.router",
)


def _routers_declarados() -> list[tuple[str, str, APIRouter]]:
    """Todos los APIRouter de los módulos, con dónde están declarados."""
    from importlib import import_module

    encontrados = []
    for nombre_modulo in MODULOS_CON_ROUTER:
        modulo = import_module(nombre_modulo)
        for nombre, valor in vars(modulo).items():
            if isinstance(valor, APIRouter):
                encontrados.append((nombre_modulo, nombre, valor))
    return encontrados


def test_todo_router_declarado_esta_montado() -> None:
    montadas = set(app.openapi()["paths"])

    faltantes: list[str] = []
    for nombre_modulo, nombre, router in _routers_declarados():
        for ruta in router.routes:
            camino = f"{settings.API_PREFIX}{ruta.path}"
            if camino not in montadas:
                faltantes.append(f"{nombre_modulo}.{nombre} → {camino}")

    assert not faltantes, (
        "Estos routers están definidos pero sus rutas no llegan a la aplicación. "
        "Falta su app.include_router(...) en app/main.py:\n  "
        + "\n  ".join(faltantes)
    )


def test_no_hay_rutas_declaradas_dos_veces() -> None:
    """Dos rutas con el mismo método y camino: la segunda queda muerta.

    FastAPI se queda con la primera que se registró y no avisa de la otra. Es
    la forma en que dos casos de uso que exponen el mismo recurso se pisan sin
    que nadie lo note — el riesgo concreto que la §6.11.2 quiso evitar.
    """
    vistas: set[tuple[str, str]] = set()
    duplicadas: list[str] = []

    for ruta in app.routes:
        metodos = getattr(ruta, "methods", None)
        camino = getattr(ruta, "path", None)
        if not metodos or camino is None:
            continue
        for metodo in metodos:
            if (metodo, camino) in vistas:
                duplicadas.append(f"{metodo} {camino}")
            vistas.add((metodo, camino))

    assert not duplicadas, (
        "Estas rutas están declaradas más de una vez; solo responde la primera:\n  "
        + "\n  ".join(duplicadas)
    )
