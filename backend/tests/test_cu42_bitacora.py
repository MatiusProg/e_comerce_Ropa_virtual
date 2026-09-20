"""CU-42 · Consultar la bitácora del sistema.

Realiza el **RNF14**: dejar rastro de quién hizo qué y cuándo.

QUÉ HUECO CIERRA
-----------------
El RNF10 ya exigía trazabilidad, pero **solo de existencias**. No había
registro de quién inició sesión, quién cambió un precio, quién desactivó un
producto ni quién abrió una caja. En un sistema con cinco roles y dinero de
por medio, eso es un agujero: cuando algo aparece cambiado, no hay cómo
saber quién lo cambió.

Lo que más importa cubrir
-------------------------
- **Que se escriba sola.** Los asientos los pone un middleware, no una
  llamada en cada servicio: una ruta que nadie instrumenta no dejaría rastro
  y el agujero no se notaría nunca.
- **Que no se llene de lecturas.** Solo lo que cambia algo.
- **Que registre lo que falla**, que es lo que más interesa: el intento de
  sesión con un correo que no existe y el rechazo por falta de permiso.
- **Que nunca guarde una contraseña.** La bitácora se lee desde una pantalla;
  una clave ahí dentro es una filtración con fecha y nombre.
- **Que no se pueda escribir ni borrar a mano.** Una bitácora corregible no
  prueba nada.
- **Que una operación no falle porque la bitácora falle.**
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core import tiempo

BITACORA = "/api/v1/bitacora"
LOGIN = "/api/v1/auth/login"
CATEGORIAS = "/api/v1/catalogo/categorias"


def _sustituir_interprete(monkeypatch) -> None:
    """CU-35 sin salir a internet. Solo importa que la ruta se anote bien."""
    from app.integrations import interprete

    monkeypatch.setattr(interprete, "esta_disponible", lambda: True)
    monkeypatch.setattr(interprete, "interpretar", lambda t, r, h: None)


def _asientos(api: TestClient, cab: dict, **params) -> list[dict]:
    r = api.get(BITACORA, headers=cab, params=params)
    assert r.status_code == 200, r.text
    return r.json()["items"]


# --- Que se escriba sola ----------------------------------------------------


def test_UNA_OPERACION_DEJA_ASIENTO_con_quien_que_y_cuando(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """El asiento sale del middleware, sin que la ruta haga nada.

    Es la razón de que sea un middleware: una ruta nueva que nadie
    instrumenta queda cubierta igual.
    """
    alta = api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "Abrigos", "orden": 0, "activa": True},
    )
    assert alta.status_code == 201, alta.text

    asiento = _asientos(api, cabeceras_admin, entidad="categoria")[0]
    assert asiento["accion"] == "CREAR"
    assert asiento["entidad"] == "categoria"
    assert asiento["metodo"] == "POST"
    assert asiento["exito"] is True
    assert asiento["estado_http"] == 201
    assert asiento["actor"]
    assert asiento["rol"] == "ADMINISTRADOR"


def test_una_LECTURA_no_deja_asiento(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Anotar cada GET serían miles de filas por día — cada pantalla del
    catálogo son varias — y volvería inservible la pantalla que existe justo
    para buscar entre ellas."""
    api.get(CATEGORIAS, headers=cabeceras_admin)

    # No se compara contra la lista vacía: el `login` del propio fixture es
    # un POST y deja su asiento, que es justamente lo que tiene que dejar.
    assert [a for a in _asientos(api, cabeceras_admin) if a["metodo"] == "GET"] == []


def test_la_bitacora_no_se_anota_a_si_misma(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Consultarla no cambia nada, y si se anotara, cada consulta agregaría
    una fila a lo que se está consultando."""
    for _ in range(3):
        api.get(BITACORA, headers=cabeceras_admin)

    assert [a for a in _asientos(api, cabeceras_admin) if "bitacora" in a["ruta"]] == []


def test_el_identificador_del_recurso_sale_de_la_ruta(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Sin esto, «alguien modificó una categoría» no dice cuál."""
    categoria = api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "Blusas", "orden": 0, "activa": True},
    ).json()["id"]

    api.patch(
        f"{CATEGORIAS}/{categoria}", headers=cabeceras_admin, json={"orden": 5}
    )

    asiento = _asientos(api, cabeceras_admin, accion="MODIFICAR")[0]
    assert asiento["entidad"] == "categoria"
    assert asiento["entidad_id"] == str(categoria)


# --- Lo que falla es lo que más interesa ------------------------------------


def test_UN_INTENTO_DE_SESION_FALLIDO_QUEDA_REGISTRADO_con_el_correo(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Es el asiento más valioso de todos, y el que casi se pierde.

    En un login fallido no hay usuario que resolver, así que el middleware
    no sabe quién fue. El correo intentado lo deja la ruta en
    `request.state`: sin eso, el asiento diría que alguien intentó entrar
    sin decir con qué cuenta, que es el único dato que importa.
    """
    r = api.post(
        LOGIN, json={"correo": "intruso@ejemplo.com", "contrasena": "Loquesea1"}
    )
    assert r.status_code == 401

    asiento = _asientos(api, cabeceras_admin, accion="INTENTO_FALLIDO")[0]
    assert asiento["actor"] == "intruso@ejemplo.com"
    assert asiento["exito"] is False
    assert asiento["usuario_id"] is None


def test_un_rechazo_por_falta_de_permiso_queda_registrado(
    api: TestClient, cabeceras_admin: dict[str, str], cabeceras_cliente: dict
) -> None:
    """Un cliente intentando crear una categoría es exactamente lo que una
    bitácora existe para mostrar."""
    r = api.post(
        CATEGORIAS,
        headers=cabeceras_cliente,
        json={"nombre": "Colada", "orden": 0, "activa": True},
    )
    assert r.status_code == 403

    fallidos = _asientos(api, cabeceras_admin, exito=False)
    assert any(a["accion"] == "CREAR_RECHAZADO" for a in fallidos)


def test_iniciar_sesion_bien_tambien_queda(api: TestClient, cabeceras_admin: dict) -> None:
    asientos = _asientos(api, cabeceras_admin, accion="INICIAR_SESION")
    assert asientos, "el login del propio fixture tiene que estar anotado"
    assert asientos[0]["exito"] is True


# --- Lo que NUNCA puede quedar escrito --------------------------------------


@pytest.mark.parametrize(
    "detalle, esperado",
    [
        ({"contrasena": "Secreta123"}, {"contrasena": "«omitido»"}),
        ({"password": "x"}, {"password": "«omitido»"}),
        ({"correo": "a@b.c"}, {"correo": "a@b.c"}),
        # Anidado: es la forma que tiene el alta de un proveedor con acceso.
        (
            {"acceso": {"correo": "a@b.c", "contrasena": "x"}},
            {"acceso": {"correo": "a@b.c", "contrasena": "«omitido»"}},
        ),
        # En lista: las líneas de un alta masiva.
        (
            {"lineas": [{"clave_api": "x", "cantidad": 2}]},
            {"lineas": [{"clave_api": "«omitido»", "cantidad": 2}]},
        ),
    ],
)
def test_NINGUNA_CREDENCIAL_LLEGA_A_LA_BITACORA(detalle, esperado) -> None:
    """Se filtra en profundidad a propósito.

    Filtrar solo el primer nivel dejaría pasar `{"acceso": {"contrasena":
    ...}}`, que es justo la forma del alta de un proveedor.
    """
    from app.modules.bitacora import service

    assert service.limpiar(detalle) == esperado


def test_la_contrasena_de_un_login_no_queda_ni_en_el_detalle_ni_en_la_ruta(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    api.post(LOGIN, json={"correo": "x@y.z", "contrasena": "NoDebeAparecer1"})

    entero = str(_asientos(api, cabeceras_admin))
    assert "NoDebeAparecer1" not in entero


# --- Inmutable --------------------------------------------------------------


def test_NO_HAY_FORMA_DE_ESCRIBIR_NI_DE_BORRAR_UN_ASIENTO(api: TestClient) -> None:
    """Una bitácora que se puede corregir no prueba nada, y justo quien
    tendría motivo para alterarla es quien tiene el rol para leerla."""
    from app.main import app

    # Se mira el contrato publicado y no `app.routes`: lo que importa no es
    # como esta armado por dentro, es que la API no OFREZCA forma de tocar
    # un asiento. Es ademas lo que ve cualquiera que abra /docs.
    expuestas = {
        ruta: {m.upper() for m in operaciones}
        for ruta, operaciones in app.openapi()["paths"].items()
        if "/bitacora" in ruta
    }
    assert expuestas, "el router tiene que estar montado"
    for ruta, metodos in expuestas.items():
        assert metodos == {"GET"}, f"{ruta} expone {metodos}"


# --- Quién la puede leer ----------------------------------------------------


def test_solo_el_administrador_la_lee(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """Dice a qué hora entra cada empleado, desde dónde y qué toca. En manos
    de un Encargado eso es vigilancia de sus compañeros, no auditoría."""
    assert api.get(BITACORA, headers=cabeceras_cliente).status_code == 403


def test_sin_token_no_hay_bitacora(api: TestClient) -> None:
    assert api.get(BITACORA).status_code == 401


# --- La lectura -------------------------------------------------------------


def test_la_hora_vuelve_EN_HORA_BOLIVIANA(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Se convierte en el servidor y no en la pantalla.

    La web y el móvil formatearían cada uno con la zona del aparato, y un
    teléfono con la hora mal puesta mostraría una bitácora que no coincide
    con la de la computadora de al lado — sobre un registro cuyo único valor
    es que todos vean lo mismo.
    """
    api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "Faldas", "orden": 0, "activa": True},
    )

    from datetime import datetime

    momento = datetime.fromisoformat(_asientos(api, cabeceras_admin)[0]["ocurrido_en"])
    assert momento.utcoffset() == tiempo.BOLIVIA.utcoffset(None)


def test_vienen_del_mas_reciente_al_mas_viejo(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Una bitácora se abre para ver qué acaba de pasar."""
    for nombre in ("Uno", "Dos", "Tres"):
        api.post(
            CATEGORIAS,
            headers=cabeceras_admin,
            json={"nombre": nombre, "orden": 0, "activa": True},
        )

    fechas = [a["ocurrido_en"] for a in _asientos(api, cabeceras_admin)]
    assert fechas == sorted(fechas, reverse=True)


def test_se_pagina(api: TestClient, cabeceras_admin: dict[str, str]) -> None:
    """Son miles de filas al mes; devolverlas enteras tumba la pantalla."""
    for i in range(5):
        api.post(
            CATEGORIAS,
            headers=cabeceras_admin,
            json={"nombre": f"C{i}", "orden": 0, "activa": True},
        )

    r = api.get(BITACORA, headers=cabeceras_admin, params={"tamano": 2}).json()
    assert len(r["items"]) == 2
    assert r["total"] >= 5
    assert r["pagina"] == 1


def test_los_filtros_se_arman_con_lo_que_REALMENTE_hay(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Con una lista escrita en el código, el filtro ofrecería acciones que
    no dan ningún resultado y escondería las que sí."""
    api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "Shorts", "orden": 0, "activa": True},
    )

    r = api.get(f"{BITACORA}/opciones", headers=cabeceras_admin)
    assert r.status_code == 200, r.text
    assert "CREAR" in r.json()["acciones"]
    assert "categoria" in r.json()["entidades"]


def test_una_fecha_inicial_posterior_a_la_final_se_rechaza(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    r = api.get(
        BITACORA,
        headers=cabeceras_admin,
        params={"desde": "2026-09-30", "hasta": "2026-09-01"},
    )
    assert r.status_code == 422


# --- Que no pueda tumbar nada -----------------------------------------------


def test_SI_LA_BITACORA_FALLA_LA_OPERACION_SIGUE(
    api: TestClient, cabeceras_admin: dict[str, str], monkeypatch
) -> None:
    """Es la regla que define el módulo.

    Una tienda que no puede vender porque no puede anotar que vendió está
    peor que una que vende sin anotar.
    """
    from app.modules.bitacora import repository

    def _explotar(*_args, **_kwargs):
        raise RuntimeError("la tabla no existe")

    monkeypatch.setattr(repository, "agregar", _explotar)

    alta = api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "Sobretodos", "orden": 0, "activa": True},
    )
    assert alta.status_code == 201, alta.text


# --- Lo que se agregó el 20/09: llevarse datos también deja rastro ---------
#
# La primera versión solo anotaba lo que CAMBIA algo, y en producción el
# resultado fue elocuente: de 28 asientos, 24 eran entrar y salir. Bajar el
# reporte de ventas de un mes ---que es sacar información del sistema a un
# archivo que después vive fuera--- no dejaba ningún rastro.


def test_BAJAR_UN_REPORTE_DEJA_ASIENTO_aunque_sea_una_lectura(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """«Leer» y «llevarse» no son lo mismo.

    Es la excepción a la regla de que un GET no se anota, y es justo lo que
    una auditoría quiere saber.
    """
    r = api.get(
        "/api/v1/reportes/ventas.xlsx",
        headers=cabeceras_admin,
        params={"desde": "2026-09-01", "hasta": "2026-09-30"},
    )
    assert r.status_code == 200, r.text

    asiento = _asientos(api, cabeceras_admin, accion="EXPORTAR")[0]
    assert asiento["entidad"] == "reporte de ventas"
    assert asiento["entidad_id"] == "xlsx"
    assert asiento["exito"] is True


def test_el_asiento_de_una_exportacion_dice_CON_QUE_FILTROS(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Sin esto, el asiento dice que alguien se llevó «el reporte de ventas»
    sin decir de qué período. Media auditoría."""
    api.get(
        "/api/v1/reportes/ventas.xlsx",
        headers=cabeceras_admin,
        params={"desde": "2026-09-01", "hasta": "2026-09-30", "canal": "DIGITAL"},
    )

    detalle = _asientos(api, cabeceras_admin, accion="EXPORTAR")[0]["detalle"]
    assert detalle["parametros"]["desde"] == "2026-09-01"
    assert detalle["parametros"]["canal"] == "DIGITAL"


def test_una_lectura_comun_sigue_SIN_dejar_asiento(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """La regla general no cambió: solo las exportaciones son la excepción.

    El tablero entra acá a propósito: se mira en pantalla, no genera archivo,
    y en el teléfono se refresca tirando hacia abajo — anotarlo llenaría la
    bitácora de ruido que nadie pidió.
    """
    api.get("/api/v1/reportes/catalogo", headers=cabeceras_admin)
    api.get("/api/v1/reportes/tablero", headers=cabeceras_admin)

    assert [
        a for a in _asientos(api, cabeceras_admin) if a["metodo"] == "GET"
    ] == []


def test_el_pedido_por_voz_no_se_anota_como_CREAR(
    api: TestClient, cabeceras_admin: dict[str, str], monkeypatch
) -> None:
    """`POST /reportes/voz` no crea nada: le pide a un modelo que interprete.

    Anotarlo como «Crear» obliga a quien lee la bitácora a abrir la ruta para
    entender qué pasó.
    """
    _sustituir_interprete(monkeypatch)
    api.post(
        "/api/v1/reportes/voz",
        headers=cabeceras_admin,
        json={"texto": "las ventas de este mes"},
    )

    acciones = {a["accion"] for a in _asientos(api, cabeceras_admin)}
    assert "PEDIR_REPORTE_POR_VOZ" in acciones
    assert "CREAR" not in acciones


def test_el_webhook_de_la_pasarela_NO_se_anota(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Llega miles de veces con reintentos y no lo hace una persona; su
    rastro propio está en `pago`.

    Estaba excluido desde el principio y **la exclusión no funcionaba**: la
    lista decía `/webhooks/` y la ruta real es `/pagos/webhook`. En
    producción se coló un asiento antes de que se notara.
    """
    api.post("/api/v1/pagos/webhook", json={"cualquier": "cosa"})

    assert [
        a for a in _asientos(api, cabeceras_admin) if "webhook" in a["ruta"]
    ] == []


# --- El filtro por rol ------------------------------------------------------


def test_SE_PUEDE_MIRAR_SOLO_LO_QUE_HICIERON_LOS_EMPLEADOS(
    api: TestClient, cabeceras_admin: dict[str, str], cabeceras_cliente: dict
) -> None:
    """«Qué hicieron los empleados» es la pregunta que se hace de verdad.

    Se anota a todos ---cancelar una reserva también es auditable--- pero
    tiene que poder mirarse solo lo interno sin leer la lista entera.
    """
    api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "Botas", "orden": 0, "activa": True},
    )
    api.post(
        CATEGORIAS,
        headers=cabeceras_cliente,
        json={"nombre": "Colada", "orden": 0, "activa": True},
    )

    empleados = _asientos(api, cabeceras_admin, rol="EMPLEADOS")
    assert empleados, "el alta del administrador tiene que estar"
    assert all(
        a["rol"] in ("ADMINISTRADOR", "ENCARGADO", "CAJERO") for a in empleados
    )

    # Y el cliente sigue registrado: se filtra, no se descarta.
    clientes = _asientos(api, cabeceras_admin, rol="CLIENTE")
    assert clientes


def test_los_roles_del_filtro_salen_de_la_tabla(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Hace falta una operación antes: **el login se anota sin rol.**

    En ese momento todavía no hay token resuelto —se está pidiendo uno— así
    que el asiento sale con `rol` nulo. Los roles del filtro salen de las
    operaciones, no de las entradas.
    """
    api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "Sombreros", "orden": 0, "activa": True},
    )

    r = api.get(f"{BITACORA}/opciones", headers=cabeceras_admin)
    assert r.status_code == 200, r.text
    assert "ADMINISTRADOR" in r.json()["roles"]


def test_EL_INICIO_DE_SESION_QUEDA_CON_SU_ROL(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Sin esto el asiento de una entrada sale sin rol y sin usuario.

    En el momento del login todavía no hay token que resolver, así que el
    middleware no sabe quién es: lo tiene que decir la ruta, que sí lo sabe
    apenas se validan las credenciales.

    Tiene dos consecuencias feas y una de ellas es de fondo: la fila se ve
    distinta de todas las demás, y **filtrar por «solo empleados» dejaba
    fuera justamente sus entradas al sistema** — que es de lo primero que
    se quiere auditar.
    """
    entrada = _asientos(api, cabeceras_admin, accion="INICIAR_SESION")[0]
    assert entrada["rol"] == "ADMINISTRADOR"
    assert entrada["usuario_id"] is not None

    # Y por lo tanto entra en el filtro de empleados.
    empleados = _asientos(api, cabeceras_admin, rol="EMPLEADOS")
    assert any(a["accion"] == "INICIAR_SESION" for a in empleados)


def test_un_intento_fallido_sigue_SIN_rol(api: TestClient, cabeceras_admin: dict) -> None:
    """Y está bien: no hay usuario que resolver.

    Lo que sí lleva es el correo intentado, que es el único dato que
    importa de un intento fallido.
    """
    api.post(LOGIN, json={"correo": "nadie@ejemplo.com", "contrasena": "Loquesea1"})

    fallido = _asientos(api, cabeceras_admin, accion="INTENTO_FALLIDO")[0]
    assert fallido["rol"] is None
    assert fallido["usuario_id"] is None
    assert fallido["actor"] == "nadie@ejemplo.com"


def test_UN_LOGIN_DEJA_UN_SOLO_ASIENTO(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Se revisó porque parecía que dejaba dos.

    No los deja: lo que se ve son DOS acciones distintas y las dos reales
    —cerrar la sesión anterior y abrir una nueva—, que al cambiar de cuenta
    quedan una al lado de la otra. Se comprobó también contra producción:
    cero asientos duplicados en la tabla.
    """
    api.post(LOGIN, json={"correo": "nadie@ejemplo.com", "contrasena": "Mala12345"})

    entradas = [
        a
        for a in _asientos(api, cabeceras_admin)
        if a["ruta"].endswith("/auth/login") and a["actor"] == "nadie@ejemplo.com"
    ]
    assert len(entradas) == 1
