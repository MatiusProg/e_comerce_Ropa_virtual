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

import logging
import uuid
from urllib.parse import urlencode

from app.core.config import settings
from app.integrations.pasarela_pago.base import SesionDePago, SolicitudDePago

_log = logging.getLogger("violetboutique.pago")

_SEPARADOR = "-" * 72


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
