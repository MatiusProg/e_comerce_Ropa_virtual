"""Pasarela que no cobra nada: escribe la sesion en el log y la aprueba.

Es el proveedor por defecto y el que permite construir, probar y DEMOSTRAR el
flujo entero de CU-27 y CU-28 sin tener claves de Stripe ni salir a internet.
Es la misma decision que tomo Karen con `correo/consola.py`.

COMO SE USA EN LA DEMOSTRACION
------------------------------
`crear_sesion` devuelve una URL que apunta a la propia web, a la pantalla de
retorno, con el identificador de la sesion adentro. El flujo que ve la persona
es el mismo que con Stripe --- confirmar, ser redirigido, volver --- y lo unico
que cambia es que no hay tarjeta de por medio.

El pago NO queda aprobado por visitar esa URL. Sigue valiendo D5: la venta la
mueve el webhook de CU-28, y para este proveedor el webhook se dispara a mano
con el endpoint de simulacion. Si visitar la URL de retorno alcanzara para
cobrar, la demostracion estaria mostrando un flujo distinto del real, que es
exactamente lo que no queremos ensenar en la defensa.

CUIDADO EN PRODUCCION
---------------------
Si alguien despliega sin configurar PAGO_PROVEEDOR, el sistema aceptaria
pedidos que nadie cobra. Por eso `crear_sesion` avisa con un WARNING cuando
corre en produccion, igual que hace el proveedor de consola del correo.
"""

import hashlib
import hmac
import json
import logging
import uuid
from urllib.parse import urlencode

from app.core.config import settings
from app.integrations.pasarela_pago.base import (
    ErrorDePasarela,
    EventoDePago,
    FirmaInvalida,
    SesionDePago,
    SolicitudDePago,
)

_log = logging.getLogger("violetboutique.pago")

_SEPARADOR = "-" * 72

#: Los dos tipos de evento que el proveedor simulado sabe emitir. Se nombran
#: como los nombraria una pasarela de verdad --- `<recurso>.<que paso>` --- para
#: que el registro de `transaccion_pasarela` se lea igual con cualquiera.
TIPO_APROBADO = "pago.aprobado"
TIPO_RECHAZADO = "pago.rechazado"

#: Los eventos que hablan del resultado de un cobro. Cualquier otro se registra
#: y no mueve nada: ver `EventoDePago.es_de_cobro`.
TIPOS_DE_COBRO = (TIPO_APROBADO, TIPO_RECHAZADO)


class ProveedorSimulado:
    """Abre una sesion de mentira y la deja escrita en el log."""

    nombre = "simulada"
    cobra_de_verdad = False

    def crear_sesion(self, solicitud: SolicitudDePago) -> SesionDePago:
        if settings.es_produccion:
            _log.warning(
                "PAGO_PROVEEDOR=simulada en PRODUCCION: el pedido %s no se va a "
                "cobrar. Ningun dinero cambia de manos.",
                solicitud.referencia,
            )

        # El prefijo imita la forma de un identificador de Stripe a proposito:
        # asi el codigo que lo consume ---y las pruebas--- no dependen de que
        # el identificador tenga una forma particular segun el proveedor.
        id_externo = "sim_" + uuid.uuid4().hex

        total = sum(
            linea.precio_unitario * linea.cantidad for linea in solicitud.lineas
        )

        detalle = "\n".join(
            "  %-40s x%-3d %8s" % (l.descripcion[:40], l.cantidad, l.precio_unitario)
            for l in solicitud.lineas
        )
        _log.info(
            "\n%s\nPAGO SIMULADO (proveedor 'simulada') --- no se cobro nada\n"
            "Pedido:  %s\n"
            "Cliente: %s\n"
            "Sesion:  %s\n%s\n%s\n%s\nTOTAL: %s %s\n%s",
            _SEPARADOR,
            solicitud.referencia,
            solicitud.correo_cliente or "(anonimo)",
            id_externo,
            _SEPARADOR,
            detalle,
            _SEPARADOR,
            solicitud.moneda,
            total,
            _SEPARADOR,
        )

        # Se vuelve a la pantalla de exito con la sesion en la consulta. La
        # pantalla NO da el pago por bueno: pregunta al backend, que responde
        # lo que diga la venta. Ver D5.
        consulta = urlencode(
            {"sesion": id_externo, "pedido": solicitud.referencia, "simulado": "1"}
        )
        return SesionDePago(
            id_externo=id_externo,
            url_redireccion=f"{solicitud.url_exito}?{consulta}",
        )

    # --- CU-28: la notificacion ------------------------------------------

    def interpretar_webhook(self, cuerpo: bytes, firma: str | None) -> EventoDePago:
        """Verifica la firma del evento simulado y lo traduce.

        **El simulado tambien firma, y no es ceremonia.** Si aceptara cualquier
        cuerpo, la demostracion estaria mostrando un flujo distinto del real
        justo en el punto que el proyecto dice cuidar: que el estado del pago lo
        fije alguien que puede demostrar quien es. Con firma, lo unico que
        cambia respecto de Stripe es quien la calcula.

        La firma es un HMAC-SHA256 del cuerpo con `PAGO_WEBHOOK_SECRET`, que es
        el mismo mecanismo que usa Stripe, sin su marca de tiempo. Se compara
        con `compare_digest` y no con `==`: comparar cadenas secreta y recibida
        con el operador normal tarda distinto segun cuantos caracteres
        coinciden, y eso alcanza para adivinarla byte a byte.

        **Sin secreto configurado no se verifica nada**, y se avisa por el log.
        Es lo que permite estrenar el flujo en desarrollo sin inventar una
        clave, y es tambien la razon por la que `es_produccion` pide el secreto
        de verdad.
        """
        secreto = settings.PAGO_WEBHOOK_SECRET.strip()
        if secreto:
            esperada = hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()
            if not firma or not hmac.compare_digest(esperada, firma.strip()):
                raise FirmaInvalida(
                    "La firma no corresponde al cuerpo recibido."
                )
        elif settings.es_produccion:
            # En produccion, un webhook sin secreto es un endpoint que
            # cualquiera puede usar para dar pedidos por pagados.
            raise FirmaInvalida(
                "PAGO_WEBHOOK_SECRET no esta configurado: no se puede verificar."
            )
        else:
            _log.warning(
                "Webhook simulado SIN verificar: PAGO_WEBHOOK_SECRET esta vacio."
            )

        try:
            datos = json.loads(cuerpo.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ErrorDePasarela(f"El cuerpo no es JSON valido: {error}") from error

        if not isinstance(datos, dict):
            raise ErrorDePasarela("El cuerpo tiene que ser un objeto JSON.")

        tipo = str(datos.get("tipo") or "pago.desconocido")
        id_evento = str(datos.get("id_evento") or "")
        if not id_evento:
            # Sin identificador no hay idempotencia posible: dos entregas de la
            # misma notificacion se aplicarian dos veces.
            raise ErrorDePasarela("El evento no trae `id_evento`.")

        return EventoDePago(
            id_evento=id_evento,
            tipo=tipo,
            id_sesion=(str(datos["sesion"]) if datos.get("sesion") else None),
            referencia=(str(datos["pedido"]) if datos.get("pedido") else None),
            aprobado=(tipo == TIPO_APROBADO),
            es_de_cobro=tipo in TIPOS_DE_COBRO,
            carga_util=cuerpo.decode("utf-8", errors="replace"),
        )
