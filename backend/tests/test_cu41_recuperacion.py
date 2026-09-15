"""CU-41 · Recuperar contraseña.

Realiza el **RF39**. El Ciclo 1 dejó que cualquiera se autorregistrara (RF01) y
no dejó ninguna forma de volver a entrar tras olvidar la contraseña, salvo
pedírselo al Administrador — que además tendría que elegirla él, o sea
conocerla.

Es el primer caso de uso que **manda un correo**, así que estrena también la
costura de `app/integrations/correo`. Estas pruebas no dependen de ningún
proveedor: sustituyen la función de envío por un buzón en memoria, que es
además la única forma de leer el token — por diseño, el sistema no lo guarda
en ninguna parte de donde pueda recuperarse.

Lo que más importa cubrir
-------------------------
Casi todo lo que hay acá existe porque **el enlace ES la credencial de la
cuenta mientras vive**. Quien lo tenga entra sin saber la contraseña anterior.

- **Que la respuesta no revele si el correo existe.** El endpoint es público y
  sin token: si distinguiera los casos, sería una forma de averiguar qué
  direcciones están registradas en la tienda, probándolas de a una.
- **Que sirva una sola vez.** Los enlaces quedan en el historial del correo.
- **Que venza.** Un correo puede quedar abierto en una máquina compartida.
- **Que el token no se guarde en claro.** Una lectura de la tabla entregaría el
  acceso a todas las cuentas con un enlace pendiente.
- **Que canjearlo corte las sesiones abiertas.** Si alguien recupera la cuenta
  porque se la tomaron, cambiar la contraseña y dejar vivos los tokens ya
  emitidos no le devuelve el control de nada.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.integrations.correo import Mensaje
from app.modules.seguridad import service
from app.modules.seguridad.models import TokenRecuperacion, Usuario

from .conftest import CLAVE_CLIENTE, CORREO_CLIENTE

SOLICITAR = "/api/v1/auth/recuperacion"
CONFIRMAR = "/api/v1/auth/recuperacion/confirmar"
LOGIN = "/api/v1/auth/login"
YO = "/api/v1/auth/yo"

CLAVE_NUEVA = "Renovada456"


@pytest.fixture
def buzon(monkeypatch) -> list[Mensaje]:
    """Intercepta los correos salientes y los acumula.

    Sustituye `enviar` tal como lo ve el servicio, no el del paquete de
    integración: el servicio lo importó por nombre y parchear el original no
    cambiaría la referencia que ya tiene.
    """
    recibidos: list[Mensaje] = []
    monkeypatch.setattr(service, "enviar", recibidos.append)
    return recibidos


def _token_del_ultimo_correo(buzon: list[Mensaje]) -> str:
    """El token, sacado del enlace del correo.

    Es el único camino que existe para obtenerlo, igual que para el usuario: la
    base guarda su SHA-256 y el servicio no lo devuelve por ningún lado.
    """
    assert buzon, "No salió ningún correo."
    enlace = buzon[-1].cuerpo_texto.split("/recuperar/")[1].split()[0]
    return enlace.strip()


def _pedir_enlace(api: TestClient, correo: str = CORREO_CLIENTE):
    return api.post(SOLICITAR, json={"correo": correo})


def _confirmar(api: TestClient, token: str, clave: str = CLAVE_NUEVA):
    return api.post(
        CONFIRMAR,
        json={
            "token": token,
            "contrasena_nueva": clave,
            "contrasena_repetida": clave,
        },
    )


# --- Flujo principal -----------------------------------------------------

def test_el_cliente_recupera_el_acceso_y_entra_con_la_contrasena_nueva(
    api: TestClient, token_cliente: str, buzon: list[Mensaje]
) -> None:
    """Flujo principal completo, de punta a punta."""
    respuesta = _pedir_enlace(api)
    assert respuesta.status_code == 202, respuesta.text

    assert len(buzon) == 1
    assert buzon[0].destinatario == CORREO_CLIENTE
    assert "/recuperar/" in buzon[0].cuerpo_texto
    assert "/recuperar/" in buzon[0].cuerpo_html

    assert _confirmar(api, _token_del_ultimo_correo(buzon)).status_code == 204

    # La nueva sirve...
    entrada = api.post(
        LOGIN, json={"correo": CORREO_CLIENTE, "contrasena": CLAVE_NUEVA}
    )
    assert entrada.status_code == 200, entrada.text

    # ...y la vieja ya no.
    vieja = api.post(
        LOGIN, json={"correo": CORREO_CLIENTE, "contrasena": CLAVE_CLIENTE}
    )
    assert vieja.status_code == 401


# --- Que no se pueda averiguar quién está registrado ---------------------

def test_la_respuesta_es_identica_exista_o_no_la_cuenta(
    api: TestClient, token_cliente: str, buzon: list[Mensaje]
) -> None:
    """El endpoint no puede servir para descubrir correos registrados.

    Se comparan las dos respuestas enteras, no solo el código: un mensaje
    distinto delataría lo mismo que un 404.
    """
    existe = _pedir_enlace(api, CORREO_CLIENTE)
    no_existe = _pedir_enlace(api, "nadie@violetboutique.bo")

    assert existe.status_code == no_existe.status_code == 202
    assert existe.json() == no_existe.json()

    # Y al inexistente no se le mandó nada.
    assert [m.destinatario for m in buzon] == [CORREO_CLIENTE]


def test_una_cuenta_desactivada_no_recibe_enlace_y_tampoco_se_delata(
    api: TestClient, db, token_cliente: str, buzon: list[Mensaje]
) -> None:
    """Sin enlace: no tendría a dónde entrar. Y sin decirlo, por lo mismo."""
    usuario = db.scalar(select(Usuario).where(Usuario.correo == CORREO_CLIENTE))
    usuario.activo = False
    db.commit()

    respuesta = _pedir_enlace(api)
    assert respuesta.status_code == 202
    assert buzon == []


# --- El enlace es una credencial -----------------------------------------

def test_el_token_no_se_guarda_en_claro(
    api: TestClient, db, token_cliente: str, buzon: list[Mensaje]
) -> None:
    """La base guarda el SHA-256, nunca el token.

    Si se guardara en claro, una lectura de esta tabla entregaría el acceso a
    todas las cuentas con un enlace pendiente.
    """
    import hashlib

    _pedir_enlace(api)
    token = _token_del_ultimo_correo(buzon)

    fila = db.scalar(select(TokenRecuperacion))
    assert fila is not None
    assert fila.hash_token != token
    assert fila.hash_token == hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert len(fila.hash_token) == 64


def test_el_enlace_sirve_una_sola_vez(
    api: TestClient, token_cliente: str, buzon: list[Mensaje]
) -> None:
    """Los enlaces quedan en el historial del correo; el segundo uso no vale."""
    _pedir_enlace(api)
    token = _token_del_ultimo_correo(buzon)

    assert _confirmar(api, token).status_code == 204

    segunda = _confirmar(api, token, "Tercera789")
    assert segunda.status_code == 400

    # Y la contraseña quedó en la del primer canje, no en la del segundo.
    assert (
        api.post(
            LOGIN, json={"correo": CORREO_CLIENTE, "contrasena": CLAVE_NUEVA}
        ).status_code
        == 200
    )


def test_un_enlace_vencido_no_sirve(
    api: TestClient, db, token_cliente: str, buzon: list[Mensaje]
) -> None:
    """Media hora es la vida del enlace; pasada, no vale."""
    _pedir_enlace(api)
    token = _token_del_ultimo_correo(buzon)

    # Se envejece la fila entera, no solo el vencimiento: el CHECK
    # `expira_en > solicitado_en` rechaza —con razón— un token que vence antes
    # de haberse pedido.
    ahora = datetime.now(timezone.utc)
    fila = db.scalar(select(TokenRecuperacion))
    fila.solicitado_en = ahora - timedelta(hours=2)
    fila.expira_en = ahora - timedelta(minutes=90)
    db.commit()

    assert _confirmar(api, token).status_code == 400
    assert (
        api.post(
            LOGIN, json={"correo": CORREO_CLIENTE, "contrasena": CLAVE_CLIENTE}
        ).status_code
        == 200
    )


def test_pedir_el_enlace_de_nuevo_invalida_el_anterior(
    api: TestClient, token_cliente: str, buzon: list[Mensaje]
) -> None:
    """Tiene que quedar uno solo válido: el último.

    Si convivieran, el primer correo —que puede haber llegado a una casilla
    equivocada, que es justamente por lo que alguien pide el enlace de nuevo—
    seguiría sirviendo.
    """
    _pedir_enlace(api)
    primero = _token_del_ultimo_correo(buzon)

    _pedir_enlace(api)
    segundo = _token_del_ultimo_correo(buzon)
    assert primero != segundo

    assert _confirmar(api, primero).status_code == 400
    assert _confirmar(api, segundo).status_code == 204


def test_un_token_inventado_no_sirve(api: TestClient, token_cliente: str) -> None:
    """Y falla igual que uno vencido: sin decir cuál de los dos es."""
    assert _confirmar(api, "x" * 43).status_code == 400


def test_canjear_el_enlace_revoca_las_sesiones_abiertas(
    api: TestClient, cabeceras_cliente: dict[str, str], buzon: list[Mensaje]
) -> None:
    """Es el motivo por el que alguien recupera una cuenta que le tomaron.

    Cambiar la contraseña y dejar vivos los tokens ya emitidos no le devolvería
    el control de nada: el intruso seguiría adentro hasta que su token venciera
    solo.
    """
    assert api.get(YO, headers=cabeceras_cliente).status_code == 200

    _pedir_enlace(api)
    assert _confirmar(api, _token_del_ultimo_correo(buzon)).status_code == 204

    assert api.get(YO, headers=cabeceras_cliente).status_code == 401


def test_la_cuenta_desactivada_despues_de_pedir_el_enlace_no_se_recupera(
    api: TestClient, db, token_cliente: str, buzon: list[Mensaje]
) -> None:
    """403 y no 400: el enlace estaba bien, la cuenta no.

    Recuperar la contraseña no puede ser la forma de revertir una baja hecha
    por CU-03.
    """
    _pedir_enlace(api)
    token = _token_del_ultimo_correo(buzon)

    usuario = db.scalar(select(Usuario).where(Usuario.correo == CORREO_CLIENTE))
    usuario.activo = False
    db.commit()

    assert _confirmar(api, token).status_code == 403

    # El canje se deshizo: el enlace sigue sin usar, porque una baja puede
    # revertirse y quemarlo no habría servido para nada.
    db.expire_all()
    fila = db.scalar(select(TokenRecuperacion))
    assert fila.usado_en is None


# --- Validación de la contraseña nueva -----------------------------------

@pytest.mark.parametrize(
    "nueva, repetida, motivo",
    [
        ("corta1", "corta1", "menos de ocho caracteres"),
        ("solamenteletras", "solamenteletras", "sin ningún dígito"),
        ("12345678", "12345678", "sin ninguna letra"),
        ("Renovada456", "Renovada457", "las dos no coinciden"),
    ],
)
def test_la_contrasena_nueva_cumple_las_mismas_reglas_que_el_registro(
    api: TestClient,
    token_cliente: str,
    buzon: list[Mensaje],
    nueva: str,
    repetida: str,
    motivo: str,
) -> None:
    """Recuperar el acceso no es una puerta de atrás para una clave más débil."""
    _pedir_enlace(api)
    token = _token_del_ultimo_correo(buzon)

    respuesta = api.post(
        CONFIRMAR,
        json={
            "token": token,
            "contrasena_nueva": nueva,
            "contrasena_repetida": repetida,
        },
    )
    assert respuesta.status_code == 422, motivo

    # Y el enlace no se gastó: el rechazo ocurre antes de tocar la base, así
    # que quien se equivocó escribiendo puede reintentar con el mismo correo.
    assert _confirmar(api, token).status_code == 204


def test_el_correo_se_normaliza_a_minusculas(
    api: TestClient, token_cliente: str, buzon: list[Mensaje]
) -> None:
    """Quien se registró en minúsculas y escribe con mayúsculas recibe el enlace.

    Sin esto no recibiría nada y no sabría por qué: la respuesta es la misma
    exista o no la cuenta, así que el sistema no se lo diría nunca.
    """
    assert _pedir_enlace(api, CORREO_CLIENTE.upper()).status_code == 202
    assert len(buzon) == 1
    assert buzon[0].destinatario == CORREO_CLIENTE


# --- La costura de correo -------------------------------------------------
#
# Todo lo de arriba sustituye `enviar`, así que el proveedor de verdad nunca se
# ejecuta. Estas dos pruebas no necesitan base: cubren la costura en sí.

def test_el_proveedor_de_consola_vuelca_el_correo_al_log(caplog) -> None:
    """El enlace tiene que quedar legible en el log, que es de donde se saca.

    Es el único camino que hay en desarrollo para completar el flujo, así que
    si esta plantilla se rompe, CU-41 deja de poder probarse a mano — y el
    fallo sería un texto mal armado, no una excepción.
    """
    import logging

    from app.integrations.correo import enviar

    mensaje = Mensaje(
        destinatario="ana@violetboutique.bo",
        asunto="Recupere el acceso",
        cuerpo_texto="Abra http://localhost:4200/recuperar/ABC123",
        cuerpo_html="<p>Abra el enlace</p>",
    )

    with caplog.at_level(logging.INFO, logger="violetboutique.correo"):
        enviar(mensaje)

    volcado = caplog.text
    assert "ana@violetboutique.bo" in volcado
    assert "Recupere el acceso" in volcado
    assert "/recuperar/ABC123" in volcado


def test_un_proveedor_de_correo_desconocido_falla_en_vez_de_degradar(
    monkeypatch,
) -> None:
    """Degradar en silencio sería peor que fallar.

    El sistema parecería mandar correos que nadie recibe, y en CU-41 eso deja a
    los usuarios sin poder entrar sin que nada avise.
    """
    from app.core.config import settings
    from app.integrations.correo import obtener_proveedor

    monkeypatch.setattr(settings, "CORREO_PROVEEDOR", "un-servicio-que-no-existe")
    obtener_proveedor.cache_clear()
    try:
        with pytest.raises(ValueError, match="no existe"):
            obtener_proveedor()
    finally:
        # El proveedor se memoriza: sin esto, la elección inválida sobreviviría
        # a esta prueba y rompería las que vengan después.
        obtener_proveedor.cache_clear()


def test_un_fallo_del_proveedor_no_delata_que_la_cuenta_existe(
    api: TestClient, db, token_cliente: str, monkeypatch
) -> None:
    """Si el envío falla, la respuesta sigue siendo la misma 202.

    Es el hueco menos evidente de todo el caso de uso. Un fallo del proveedor
    reflejado en la respuesta distinguiría una cuenta que existe —hay a quién
    escribirle, y falló— de una que no —nunca se intentó enviar nada—, que es
    exactamente lo que el resto del caso de uso evita.
    """
    from app.integrations.correo import ErrorDeEnvio

    def _revienta(_mensaje):
        raise ErrorDeEnvio("el proveedor devolvió 503")

    monkeypatch.setattr(service, "enviar", _revienta)

    con_cuenta = _pedir_enlace(api, CORREO_CLIENTE)
    sin_cuenta = _pedir_enlace(api, "nadie@violetboutique.bo")

    assert con_cuenta.status_code == sin_cuenta.status_code == 202
    assert con_cuenta.json() == sin_cuenta.json()

    # El token quedó emitido igual: el envío ocurre después del commit, así que
    # no hay nada que deshacer y un reintento entrega uno nuevo.
    assert db.scalar(select(TokenRecuperacion)) is not None
