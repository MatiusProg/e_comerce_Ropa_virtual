"""
3ra presentación · CU-41 Gestionar roles y permisos de la empresa (RF-64, RN-22)

EL CATÁLOGO DE PERMISOS ES DEL SISTEMA; LOS ROLES, DE CADA EMPRESA
-----------------------------------------------------------------
Qué se puede permitir lo define el sistema, porque cada permiso tiene que
corresponder a algo que el backend sabe cuidar. Cada empresa arma con ellos
sus propios roles («Vendedor de fin de semana», «Analista») y se los asigna a
su personal. Otra empresa no ve ni usa esos roles (RN-22, y el RLS).

UN ROL PROPIO PARTE DE UN ROL BASE Y LO ACOTA
---------------------------------------------
Todo el sistema protege sus rutas por el rol (`requiere_roles("ENCARGADO")`).
Un rol propio parte de uno de los tres roles del personal (ADMINISTRADOR,
ENCARGADO, CAJERO) y elige cuáles de SUS permisos conserva. Nunca da más de
lo que da su rol base: el rol del token sigue siendo el base y todas las
guardas de siempre siguen valiendo; el rol propio solo puede quitar.

CÓMO SE HACE CUMPLIR: POR LA RUTA, EN UN SOLO LUGAR
--------------------------------------------------
Cada permiso cubre uno o más prefijos de ruta. `get_usuario_actual` busca el
prefijo más largo que coincide con la ruta pedida y, si el usuario tiene un
rol propio y ese permiso no está en su rol, responde 403. Una ruta que no
figura en ningún permiso está **cerrada** para quien tiene un rol propio,
salvo las libres (sesión y avisos propios): agregar una pantalla nueva sin
anotarla acá no abre un hueco, la deja fuera hasta que alguien la anote.

Quien NO tiene un rol propio sigue como siempre, con todo lo de su rol base.

RN-22: UN PERMISO QUE DEPENDE DEL PLAN
--------------------------------------
Algunos permisos son una función del plan (`funcion`). No se pueden poner en
un rol si el plan de la empresa no la incluye, y aunque estuvieran, la ruta
sigue pidiendo la función con `requiere_funcion` (CU-05).
"""
from __future__ import annotations

from dataclasses import dataclass

ADMIN = "ADMINISTRADOR"
ENCARGADO = "ENCARGADO"
CAJERO = "CAJERO"

#: Los roles del personal de los que puede partir un rol propio.
ROLES_BASE = (ADMIN, ENCARGADO, CAJERO)


@dataclass(frozen=True)
class Permiso:
    codigo: str
    nombre: str
    area: str
    #: Los roles base que tienen este permiso. Un rol propio solo puede
    #: conservar los de su rol base.
    roles_base: tuple[str, ...]
    #: Los prefijos de ruta (sin `/api/v1`) que cubre.
    rutas: tuple[str, ...]
    #: La función del plan que hace falta (RN-22), o None.
    funcion: str | None = None
    #: False: no se le puede dar a un rol propio (gestionar roles y usuarios:
    #: el que los tuviera podría darse más permisos a sí mismo).
    asignable: bool = True


_E_A = (ENCARGADO, ADMIN)
_C_E = (CAJERO, ENCARGADO)
_SOLO_A = (ADMIN,)

CATALOGO: tuple[Permiso, ...] = (
    # --- Sucursal --------------------------------------------------------
    Permiso("reservas.atender", "Atender reservas", "Sucursal", _E_A, ("/sucursal/reservas",)),
    Permiso("pedidos_web.atender", "Entregar pedidos web y atender devoluciones web", "Sucursal",
            _E_A, ("/sucursal/pedidos", "/sucursal/solicitudes-devolucion")),
    Permiso("inventario.gestionar", "Gestionar el inventario", "Sucursal", _E_A, ("/inventario",)),
    Permiso("traspasos.gestionar", "Pedir y atender traspasos", "Sucursal", _E_A, ("/traspasos",)),
    Permiso("offline.operar", "Trabajar sin conexión y atender rechazadas", "Sucursal",
            (CAJERO, ENCARGADO, ADMIN), ("/offline",)),
    # --- Caja ------------------------------------------------------------
    Permiso("caja.operar", "Abrir y cerrar caja", "Caja", _C_E, ("/caja",)),
    Permiso("ventas.registrar", "Vender en el mostrador", "Caja", _C_E, ("/pos",)),
    Permiso("devoluciones.registrar", "Registrar cambios y devoluciones en caja", "Caja",
            (CAJERO, ENCARGADO, ADMIN), ("/pos/devoluciones", "/pos/notas-devolucion")),
    # --- Reportes ----------------------------------------------------------
    Permiso("reportes.ver", "Generar reportes", "Reportes", _E_A, ("/reportes",)),
    Permiso("reportes_ia.usar", "Reportes con IA por texto o voz", "Reportes", _E_A,
            ("/reportes/voz",), funcion="reportes_ia"),
    Permiso("tablero.ver", "Ver el tablero de indicadores", "Reportes", _SOLO_A,
            ("/reportes/tablero",)),
    Permiso("bitacora.ver", "Ver la bitácora", "Reportes", _SOLO_A, ("/bitacora",)),
    # --- Administración ------------------------------------------------------
    Permiso("catalogo.gestionar", "Gestionar el catálogo", "Administración", _SOLO_A,
            ("/catalogo",)),
    Permiso("ofertas.gestionar", "Gestionar ofertas, promociones y mayoristas",
            "Administración", _SOLO_A, ("/ofertas", "/catalogo/promociones")),
    Permiso("traspasos.sugeridos", "Ver los traspasos sugeridos", "Administración", _SOLO_A,
            ("/traspasos/sugeridos",), funcion="traspasos_sugeridos"),
    Permiso("organizacion.gestionar", "Gestionar sucursales, empleados y proveedores",
            "Administración", _SOLO_A, ("/organizacion",)),
    Permiso("pedidos.gestionar", "Ver los pedidos de la tienda en línea", "Administración",
            _SOLO_A, ("/pedidos",)),
    Permiso("mi_tienda.gestionar", "Personalizar la tienda (logo y colores)", "Administración",
            _SOLO_A, ("/plataforma/mi-tienda",), funcion="marca_propia"),
    Permiso("mi_plan.ver", "Ver el plan y su consumo", "Administración", _SOLO_A,
            ("/plataforma/mi-plan",)),
    Permiso("datos.exportar", "Exportar todos los datos a Excel o CSV", "Administración",
            _SOLO_A, ("/exportacion",), funcion="exportar_datos"),
    Permiso("mantenimiento.ejecutar", "Disparar las tareas de mantenimiento", "Administración",
            _SOLO_A, ("/mantenimiento",)),
    # --- No asignables -------------------------------------------------------
    Permiso("usuarios.gestionar", "Gestionar usuarios", "Administración", _SOLO_A,
            ("/usuarios",), asignable=False),
    Permiso("roles.gestionar", "Gestionar roles y permisos", "Administración", _SOLO_A,
            ("/roles",), asignable=False),
    # RN-19: solo el administrador restaura.
    Permiso("respaldos.gestionar", "Copias de seguridad y restauración", "Administración",
            _SOLO_A, ("/respaldos",), asignable=False),
)

POR_CODIGO: dict[str, Permiso] = {p.codigo: p for p in CATALOGO}

#: Lo que cualquiera con sesión puede hacer aunque su rol propio no lo nombre:
#: su sesión, sus avisos y la vitrina pública.
RUTAS_LIBRES = ("/auth", "/notificaciones", "/tienda")

#: Consultas de apoyo: las listas que las pantallas usan para llenar sus
#: desplegables (sucursales, productos, temporadas...). Solo LECTURA (GET).
#: Sin esto, un rol propio parcial —un «Analista» con reportes y nada más—
#: abría la pantalla de reportes y el selector de sucursal fallaba en
#: silencio con 403. El rol base sigue mandando: estas rutas conservan su
#: `requiere_roles`, así que un cajero no ve más que antes. Ninguna devuelve
#: algo que no se vea ya en la vitrina pública o en el propio reporte.
CONSULTAS_DE_APOYO = (
    "/organizacion/sucursales",
    "/organizacion/ciudades",
    "/catalogo/productos",
    "/catalogo/categorias",
    "/catalogo/temporadas",
    "/catalogo/colecciones",
    "/catalogo/tallas",
    "/catalogo/colores",
)

PREFIJO_API = "/api/v1"


def _coincide(ruta: str, prefijo: str) -> bool:
    return ruta == prefijo or ruta.startswith(prefijo + "/") or ruta.startswith(prefijo + ".")


def permiso_de_ruta(ruta: str) -> str | None:
    """El permiso que cubre la ruta: el de prefijo más largo, o None."""
    if ruta.startswith(PREFIJO_API):
        ruta = ruta[len(PREFIJO_API):]
    mejor: tuple[int, str] | None = None
    for permiso in CATALOGO:
        for prefijo in permiso.rutas:
            if _coincide(ruta, prefijo) and (mejor is None or len(prefijo) > mejor[0]):
                mejor = (len(prefijo), permiso.codigo)
    return mejor[1] if mejor else None


def es_libre(ruta: str) -> bool:
    if ruta.startswith(PREFIJO_API):
        ruta = ruta[len(PREFIJO_API):]
    return any(_coincide(ruta, p) for p in RUTAS_LIBRES)


def asignables_para(rol_base: str) -> list[Permiso]:
    return [p for p in CATALOGO if p.asignable and rol_base in p.roles_base]


def es_consulta_de_apoyo(metodo: str, ruta: str) -> bool:
    if metodo not in ("GET", "HEAD"):
        return False
    if ruta.startswith(PREFIJO_API):
        ruta = ruta[len(PREFIJO_API):]
    return any(_coincide(ruta, p) for p in CONSULTAS_DE_APOYO)
