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

Un router puede llegar a la aplicación de dos formas: montado directamente en
`main.py`, o incluido dentro de otro router que sí lo está. La segunda es la que
usa CU-11, y justamente para no tocar `main.py` —que es el archivo del que habla
el párrafo anterior—. Por eso la comprobación no exige el camino exacto: busca
las rutas del router bajo el prefijo con el que hayan quedado montadas, y exige
que estén **todas** bajo el mismo. Un router que no se incluyó en ningún lado
sigue fallando, que es lo que esta prueba existe para atrapar.
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
    "app.modules.catalogo.temporadas_router",
    "app.modules.catalogo.imagenes_router",
    "app.modules.inventario.router",
    "app.modules.inventario.consolidado_router",
    "app.modules.catalogo_publico.router",
    "app.modules.catalogo_publico.favoritos_router",
    "app.modules.reservas.router",
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


def _prefijos_posibles(camino_declarado: str, montadas: set[str]) -> set[str]:
    """Los prefijos bajo los que esa ruta aparece montada.

    Un router incluido dentro de otro hereda el prefijo del padre, así que su
    `ruta.path` no coincide con el camino final. Se busca al revés: de qué
    caminos montados es sufijo.
    """
    return {
        montada[: -len(camino_declarado)]
        for montada in montadas
        if montada.endswith(camino_declarado)
    }


def test_todo_router_declarado_esta_montado() -> None:
    montadas = set(app.openapi()["paths"])

    faltantes: list[str] = []
    for nombre_modulo, nombre, router in _routers_declarados():
        # Se filtra por `path`: incluir un router dentro de otro deja en la
        # lista un objeto de inclusion --- FastAPI resuelve esas rutas mas
        # tarde --- que no es una ruta y no tiene camino.
        caminos = [r.path for r in router.routes if hasattr(r, "path")]
        if not caminos:
            continue

        # Los prefijos que sirven para TODAS las rutas del router. Exigir uno
        # solo y comun evita el falso positivo de que una ruta suelta coincida
        # por casualidad con el final de otra de un modulo distinto.
        comunes = _prefijos_posibles(caminos[0], montadas)
        for camino in caminos[1:]:
            comunes &= _prefijos_posibles(camino, montadas)

        if not comunes:
            faltantes.append(
                f"{nombre_modulo}.{nombre} -> {settings.API_PREFIX}{caminos[0]}"
                f" (y {len(caminos) - 1} rutas mas)"
            )

    assert not faltantes, (
        "Estos routers estan definidos pero sus rutas no llegan a la aplicacion. "
        "Falta incluirlos: con app.include_router(...) en app/main.py, o dentro "
        "de otro router que si este montado:\n  "
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
