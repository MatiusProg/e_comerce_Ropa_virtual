"""CU-40 · Notificar eventos a los usuarios. Realiza el RF11.

Cubre los cuatro hechos de la ficha (docs/03-captura-requisitos.md §3.1), el
despachador de correos y el ámbito de los avisos.

Las pruebas que más importan son las que cubren lo que nada garantiza solo:

- **El aviso de stock bajo sale una vez, al cruzar.** Una prenda en alerta
  recibe decenas de movimientos mientras sigue baja —se vende de a una, se
  reserva, se libera— y avisar en cada uno llenaría la campanita del Encargado
  con el mismo aviso repetido hasta volverla inservible.
- **El despacho es idempotente.** Correrlo dos veces no puede mandar el mismo
  correo dos veces: es el único error que el usuario nota.
- **Un proveedor caído no rompe nada.** El aviso dentro de la aplicación es la
  degradación acordada el 13/09 y tiene que sobrevivir a que el correo falle.
- **Un encargado dado de baja deja de recibir las reservas de su ex sucursal**,
  que es una fuga de información y no un descuido.
- **El aviso ajeno responde 404 y no 403**, la convención del proyecto.
"""

from datetime import date, datetime, time, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.integrations.correo.base import ErrorDeEnvio
from app.modules.inventario.service import cruzo_el_umbral
from app.modules.notificaciones import service
from app.modules.notificaciones.models import Notificacion
from app.modules.organizacion.models import Ciudad, Empleado, Sucursal
from app.modules.seguridad.models import Rol, Usuario

NOTIFICACIONES = "/api/v1/notificaciones"
DESPACHO = "/api/v1/mantenimiento/notificaciones/despacho"
REINTENTO = "/api/v1/mantenimiento/notificaciones/reintento"

BOLIVIA = timezone(timedelta(hours=-4))


# --- Ayudantes -----------------------------------------------------------
#
# Se arma directo en la base y no por la API a proposito: lo que se prueba es a
# QUIEN le llega el aviso, y la cadena de altas por HTTP ---ciudad, sucursal,
# usuario, empleado--- probaria sobre todo el armado.


def _usuario(db, *, correo: str, rol: str = "ENCARGADO") -> Usuario:
    fila_rol = db.scalar(select(Rol).where(Rol.nombre == rol))
    usuario = Usuario(
        correo=correo,
        hash_contrasena=hash_password("Secreta123"),
        nombres="Prueba",
        apellidos=rol.title(),
        rol_id=fila_rol.id,
    )
    db.add(usuario)
    db.flush()
    return usuario


def _sucursal(db, *, nombre: str) -> Sucursal:
    ciudad = db.scalar(select(Ciudad).limit(1))
    sucursal = Sucursal(
        ciudad_id=ciudad.id,
        nombre=nombre,
        direccion="Av. Siempre 1",
        horario_apertura=time(9, 0),
        horario_cierre=time(20, 0),
    )
    db.add(sucursal)
    db.flush()
    return sucursal


def _encargado_de(db, sucursal, *, correo: str, baja: date | None = None) -> Usuario:
    usuario = _usuario(db, correo=correo)
    db.add(
        Empleado(
            usuario_id=usuario.id,
            sucursal_id=sucursal.id,
            documento=correo[:8],
            cargo="ENCARGADO",
            fecha_ingreso=date(2026, 1, 1),
            fecha_baja=baja,
        )
    )
    db.flush()
    return usuario


def _reserva_falsa(sucursal_id: int, *, reserva_id: int = 77):
    """Lo único que `avisar_reserva_en_sucursal` lee de una reserva."""
    return SimpleNamespace(
        id=reserva_id,
        sucursal_id=sucursal_id,
        cliente_id=None,
        franja_fin=datetime.now(BOLIVIA) + timedelta(days=1),
    )


# =====================================================================
# RF11 - la reserva le llega al Encargado de SU sucursal
# =====================================================================


def test_la_reserva_le_llega_al_encargado_de_su_sucursal(db):
    sucursal = _sucursal(db, nombre="Centro")
    encargado = _encargado_de(db, sucursal, correo="centro@vb.bo")

    avisos = service.avisar_reserva_en_sucursal(db, _reserva_falsa(sucursal.id))
    db.commit()

    assert len(avisos) == 1
    assert avisos[0].destinatario_id == encargado.id
    assert avisos[0].tipo == "RESERVA_EN_SUCURSAL"
    assert avisos[0].entidad == "reserva"
    # Nace PENDIENTE porque hay a donde mandarlo. El correo sale despues.
    assert avisos[0].correo_estado == "PENDIENTE"


def test_el_encargado_de_otra_sucursal_no_se_entera(db):
    centro = _sucursal(db, nombre="Centro")
    norte = _sucursal(db, nombre="Norte")
    _encargado_de(db, centro, correo="centro@vb.bo")
    ajeno = _encargado_de(db, norte, correo="norte@vb.bo")

    service.avisar_reserva_en_sucursal(db, _reserva_falsa(centro.id))
    db.commit()

    assert db.scalars(
        select(Notificacion).where(Notificacion.destinatario_id == ajeno.id)
    ).all() == []


def test_un_encargado_dado_de_baja_no_recibe_las_reservas_de_su_ex_sucursal(db):
    """Su fila de empleado sigue ahí —es historia— pero ya no trabaja ahí.

    Seguirle mandando las reservas del local es una fuga de información, no un
    descuido: se entera de la operación de una tienda en la que ya no está.
    """
    sucursal = _sucursal(db, nombre="Centro")
    _encargado_de(db, sucursal, correo="exjefe@vb.bo", baja=date(2026, 6, 30))

    avisos = service.avisar_reserva_en_sucursal(db, _reserva_falsa(sucursal.id))
    db.commit()

    assert avisos == []


def test_una_sucursal_sin_encargado_no_hace_fallar_la_reserva(db):
    """Es un dato maestro incompleto, no un motivo para que el cliente falle."""
    sucursal = _sucursal(db, nombre="Sin jefe")

    avisos = service.avisar_reserva_en_sucursal(db, _reserva_falsa(sucursal.id))
    db.commit()

    assert avisos == []


def test_una_cuenta_desactivada_no_recibe_avisos(db):
    sucursal = _sucursal(db, nombre="Centro")
    encargado = _encargado_de(db, sucursal, correo="baja@vb.bo")
    encargado.activo = False
    db.flush()

    assert service.avisar_reserva_en_sucursal(db, _reserva_falsa(sucursal.id)) == []


# =====================================================================
# El aviso de stock bajo sale AL CRUZAR, no cada vez que esta bajo
# =====================================================================


@pytest.mark.parametrize(
    ("antes", "ahora", "minimo", "esperado", "por_que"),
    [
        (6, 5, 5, True, "cae justo al umbral: es el cruce"),
        (6, 2, 5, True, "lo atraviesa de un saque"),
        (5, 4, 5, False, "ya estaba en alerta: no vuelve a avisar"),
        (4, 3, 5, False, "sigue bajando dentro de la alerta"),
        (3, 9, 5, False, "se repuso: subir no avisa"),
        (6, 5, 0, False, "stock_minimo 0 significa «sin alerta»"),
        (1, 0, 0, False, "llegar a cero sin umbral tampoco avisa"),
    ],
)
def test_el_umbral_se_cruza_una_sola_vez(antes, ahora, minimo, esperado, por_que):
    assert cruzo_el_umbral(antes=antes, ahora=ahora, stock_minimo=minimo) is esperado, por_que


def test_el_aviso_de_stock_bajo_va_al_encargado_con_las_cantidades(db):
    sucursal = _sucursal(db, nombre="Centro")
    encargado = _encargado_de(db, sucursal, correo="centro@vb.bo")
    existencia = SimpleNamespace(
        id=9, sucursal_id=sucursal.id, cantidad_disponible=2, stock_minimo=5
    )

    avisos = service.avisar_stock_bajo(db, existencia, etiqueta="Blusa seda (BL-01)")
    db.commit()

    assert len(avisos) == 1
    assert avisos[0].destinatario_id == encargado.id
    assert avisos[0].tipo == "STOCK_BAJO"
    assert "Blusa seda (BL-01)" in avisos[0].titulo
    # Las dos cantidades en el cuerpo: sin ellas el aviso no dice cuánto reponer.
    assert "2" in avisos[0].cuerpo and "5" in avisos[0].cuerpo


# =====================================================================
# El despachador de correos
# =====================================================================


def _aviso_para(db, usuario) -> Notificacion:
    return service.notificar(
        db,
        destinatario=usuario,
        tipo="RESERVA_PREPARADA",
        titulo="Su reserva está lista",
        cuerpo="Pase a retirarla.",
        enlace="/mis-reservas/1",
    )


def test_el_despacho_manda_las_pendientes_y_las_marca_enviadas(db, monkeypatch):
    usuario = _usuario(db, correo="cliente@vb.bo", rol="CLIENTE")
    _aviso_para(db, usuario)
    db.commit()

    enviados = []
    monkeypatch.setattr(service, "enviar", lambda mensaje: enviados.append(mensaje))

    resultado = service.despachar_pendientes(db)

    assert (resultado.intentadas, resultado.enviadas, resultado.fallidas) == (1, 1, 0)
    assert len(enviados) == 1
    assert enviados[0].destinatario == "cliente@vb.bo"
    fila = db.scalar(select(Notificacion))
    assert fila.correo_estado == "ENVIADO"
    assert fila.correo_enviado_en is not None


def test_el_despacho_es_idempotente(db, monkeypatch):
    """Correrlo dos veces no manda el mismo correo dos veces.

    Es lo que hace que se pueda colgar de un planificador sin miedo, igual que
    la expiración de reservas de CU-25.
    """
    usuario = _usuario(db, correo="cliente@vb.bo", rol="CLIENTE")
    _aviso_para(db, usuario)
    db.commit()

    enviados = []
    monkeypatch.setattr(service, "enviar", lambda mensaje: enviados.append(mensaje))

    service.despachar_pendientes(db)
    segunda = service.despachar_pendientes(db)

    assert segunda.intentadas == 0
    assert len(enviados) == 1


def test_un_proveedor_caido_deja_el_aviso_en_pie_y_anota_el_motivo(db, monkeypatch):
    """El aviso dentro de la aplicación es la degradación acordada el 13/09.

    Que el correo falle no puede borrarlo ni hacer fallar la llamada.
    """
    usuario = _usuario(db, correo="cliente@vb.bo", rol="CLIENTE")
    _aviso_para(db, usuario)
    db.commit()

    def _revienta(mensaje):
        raise ErrorDeEnvio("puerto 587 bloqueado")

    monkeypatch.setattr(service, "enviar", _revienta)

    resultado = service.despachar_pendientes(db)

    assert (resultado.enviadas, resultado.fallidas) == (0, 1)
    fila = db.scalar(select(Notificacion))
    assert fila.correo_estado == "FALLIDO"
    assert "587" in fila.correo_error
    # El aviso sigue existiendo y sin leer: la campanita no se entera del fallo.
    assert fila.leida_en is None


def test_un_error_inesperado_del_proveedor_no_corta_la_corrida(db, monkeypatch):
    """Un proveedor mal configurado levanta lo que se le ocurra.

    Si la corrida entera muriera por una fila, las siguientes no saldrían.
    """
    uno = _usuario(db, correo="uno@vb.bo", rol="CLIENTE")
    otro = _usuario(db, correo="otro@vb.bo", rol="CLIENTE")
    _aviso_para(db, uno)
    _aviso_para(db, otro)
    db.commit()

    llamadas = []

    def _a_veces_revienta(mensaje):
        llamadas.append(mensaje.destinatario)
        if mensaje.destinatario == "uno@vb.bo":
            raise RuntimeError("clave vencida")

    monkeypatch.setattr(service, "enviar", _a_veces_revienta)

    resultado = service.despachar_pendientes(db)

    assert (resultado.intentadas, resultado.enviadas, resultado.fallidas) == (2, 1, 1)
    assert len(llamadas) == 2


def test_el_reintento_devuelve_las_fallidas_a_la_cola(db, monkeypatch):
    usuario = _usuario(db, correo="cliente@vb.bo", rol="CLIENTE")
    _aviso_para(db, usuario)
    db.commit()

    monkeypatch.setattr(
        service, "enviar", lambda m: (_ for _ in ()).throw(ErrorDeEnvio("caído"))
    )
    service.despachar_pendientes(db)

    assert service.reintentar_fallidas(db) == 1
    fila = db.scalar(select(Notificacion))
    assert fila.correo_estado == "PENDIENTE"
    assert fila.correo_error is None


def test_un_usuario_sin_direccion_nace_omitido_y_el_despacho_no_lo_persigue(db):
    """OMITIDO no es lo mismo que FALLIDO.

    Mezclarlos haría que el reintento persiguiera para siempre correos que
    nunca hubo que mandar.
    """
    usuario = _usuario(db, correo="cliente@vb.bo", rol="CLIENTE")
    usuario.correo = "   "
    db.flush()

    aviso = _aviso_para(db, usuario)
    db.commit()

    assert aviso.correo_estado == "OMITIDO"
    assert service.despachar_pendientes(db).intentadas == 0


# =====================================================================
# Los endpoints
# =====================================================================


def test_la_campanita_cuenta_todas_las_no_leidas_y_no_las_de_la_pagina(
    api, db, cabeceras_cliente
):
    usuario = db.scalar(select(Usuario).where(Usuario.correo == "ana.cliente@violetboutique.bo"))
    for _ in range(3):
        _aviso_para(db, usuario)
    db.commit()

    pagina = api.get(
        NOTIFICACIONES, headers=cabeceras_cliente, params={"tamano": 1}
    ).json()

    assert len(pagina["items"]) == 1
    assert pagina["total"] == 3
    # El número de la campanita no puede cambiar al pasar de hoja.
    assert pagina["no_leidas"] == 3
    assert api.get(f"{NOTIFICACIONES}/resumen", headers=cabeceras_cliente).json() == {
        "no_leidas": 3
    }


def test_un_aviso_ajeno_responde_404_y_no_403(api, db, cabeceras_cliente):
    """Un 403 confirmaría que ese número corresponde a un aviso real de otro.

    Es la convención del proyecto, la misma de CU-02, CU-38 y CU-41.
    """
    otro = _usuario(db, correo="ajeno@vb.bo", rol="CLIENTE")
    ajeno = _aviso_para(db, otro)
    db.commit()

    respuesta = api.post(
        f"{NOTIFICACIONES}/{ajeno.id}/leer", headers=cabeceras_cliente
    )

    assert respuesta.status_code == 404


def test_marcar_leida_no_mueve_la_fecha_de_una_ya_leida(api, db, cabeceras_cliente):
    """Cuándo se enteró es un dato histórico, no un contador de clics."""
    usuario = db.scalar(select(Usuario).where(Usuario.correo == "ana.cliente@violetboutique.bo"))
    aviso = _aviso_para(db, usuario)
    db.commit()

    assert api.post(f"{NOTIFICACIONES}/{aviso.id}/leer", headers=cabeceras_cliente).status_code == 204
    db.expire_all()
    primera = db.get(Notificacion, aviso.id).leida_en

    assert api.post(f"{NOTIFICACIONES}/{aviso.id}/leer", headers=cabeceras_cliente).status_code == 204
    db.expire_all()

    assert db.get(Notificacion, aviso.id).leida_en == primera


def test_leer_todas_deja_la_campanita_en_cero(api, db, cabeceras_cliente):
    usuario = db.scalar(select(Usuario).where(Usuario.correo == "ana.cliente@violetboutique.bo"))
    for _ in range(2):
        _aviso_para(db, usuario)
    db.commit()

    assert api.post(f"{NOTIFICACIONES}/leer-todas", headers=cabeceras_cliente).json() == {
        "marcadas": 2
    }
    assert api.get(f"{NOTIFICACIONES}/resumen", headers=cabeceras_cliente).json() == {
        "no_leidas": 0
    }


def test_solo_no_leidas_filtra_de_verdad(api, db, cabeceras_cliente):
    usuario = db.scalar(select(Usuario).where(Usuario.correo == "ana.cliente@violetboutique.bo"))
    leida = _aviso_para(db, usuario)
    _aviso_para(db, usuario)
    db.commit()
    api.post(f"{NOTIFICACIONES}/{leida.id}/leer", headers=cabeceras_cliente)

    pagina = api.get(
        NOTIFICACIONES, headers=cabeceras_cliente, params={"solo_no_leidas": True}
    ).json()

    assert pagina["total"] == 1
    assert pagina["items"][0]["id"] != leida.id


def test_el_despacho_es_solo_del_administrador(api, cabeceras_cliente):
    assert api.post(DESPACHO, headers=cabeceras_cliente).status_code == 403
    assert api.post(REINTENTO, headers=cabeceras_cliente).status_code == 403


def test_el_despacho_sin_token_no_pasa(api):
    assert api.post(DESPACHO).status_code == 401


def test_no_existe_forma_de_crearse_un_aviso_por_la_api(api, cabeceras_cliente):
    """El actor de CU-40 es el Sistema.

    Un `POST /notificaciones` convertiría a cualquier usuario con sesión en el
    iniciador del caso de uso, y le permitiría mandarle avisos a otro.
    """
    respuesta = api.post(
        NOTIFICACIONES,
        headers=cabeceras_cliente,
        json={"tipo": "PEDIDO_PAGADO", "titulo": "x", "cuerpo": "y"},
    )

    assert respuesta.status_code == 405
