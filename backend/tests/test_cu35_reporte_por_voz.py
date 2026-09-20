"""CU-35 · Generar reporte por comando de voz.

El administrador pide un reporte hablando; el sistema interpreta la frase,
consulta los datos y le devuelve el archivo.

LA VOZ NO LLEGA AL SERVIDOR: LLEGA TEXTO
-----------------------------------------
El reconocimiento corre en el navegador (Web Speech API) y en el teléfono
(`speech_to_text`). Los dos son gratuitos y no consumen cuota del modelo;
mandar audio obligaría a un servicio de transcripción de pago y a subir
megabytes por pedido. Por eso este endpoint recibe una cadena.

NINGUNA PRUEBA LLAMA AL MODELO DE VERDAD
-----------------------------------------
Se sustituye el intérprete. Una prueba que sale a internet tarda, gasta cuota
y **falla cuando Gemini tarda de más** — que pasa: el 20/09 se midió entre 7 y
31 segundos con la misma frase. Una prueba que falla por algo que el sistema
maneja bien no prueba nada.

Lo que más importa cubrir
-------------------------
- **Que no se adivine.** Si la frase no encaja, se pide que la repita. Generar
  «lo más parecido» es como el administrador termina mandando por correo el
  reporte equivocado sin haberlo abierto.
- **Que no se confíe en lo que devuelve el modelo.** Un tipo que no existe, un
  formato inventado o un filtro con un valor que ese reporte no admite se
  descartan.
- **Que se diga qué se entendió ANTES de descargar.** Es la única oportunidad
  de notar que interpretó otra cosa.
- **Que la URL que devuelve sirva de verdad.**
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.integrations import interprete
from app.integrations.interprete import ErrorDelInterprete, InterpreteNoConfigurado
from app.integrations.interprete.base import Pedido

VOZ = "/api/v1/reportes/voz"
DISPONIBLE = f"{VOZ}/disponible"


class _InterpreteFalso:
    """Devuelve lo que la prueba le diga, y recuerda con qué lo llamaron."""

    nombre = "falso"
    disponible = True

    def __init__(self, respuesta=None, error: Exception | None = None):
        self.respuesta = respuesta
        self.error = error
        self.ultimos_reportes: list = []
        self.ultimo_texto = ""

    def interpretar(self, texto, reportes, hoy):
        self.ultimo_texto = texto
        self.ultimos_reportes = list(reportes)
        if self.error is not None:
            raise self.error
        return self.respuesta


def _sustituir(monkeypatch, falso: _InterpreteFalso) -> _InterpreteFalso:
    monkeypatch.setattr(interprete, "obtener_proveedor", lambda: falso)
    monkeypatch.setattr(
        interprete, "interpretar", lambda t, r, h: falso.interpretar(t, r, h)
    )
    monkeypatch.setattr(interprete, "esta_disponible", lambda: falso.disponible)
    return falso


# --- Lo que se entiende -----------------------------------------------------


def test_un_pedido_entendido_devuelve_QUE_ENTENDIO_y_la_url(
    api: TestClient, cabeceras_admin: dict[str, str], monkeypatch
) -> None:
    """No devuelve el archivo: devuelve qué entendió y cómo bajarlo.

    Entregar el archivo directo ahorraría un paso y quitaría la única
    oportunidad de notar que el modelo entendió otra cosa.
    """
    _sustituir(
        monkeypatch,
        _InterpreteFalso(
            Pedido(
                tipo="ventas",
                formato="xlsx",
                desde=date(2026, 9, 1),
                hasta=date(2026, 9, 30),
                filtros={"metodo_pago": "EFECTIVO"},
                resumen="Ventas en efectivo de septiembre, en Excel",
            )
        ),
    )

    r = api.post(VOZ, headers=cabeceras_admin, json={"texto": "ventas en efectivo"})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["entendido"] is True
    assert cuerpo["resumen"] == "Ventas en efectivo de septiembre, en Excel"
    assert cuerpo["url"] == (
        "/reportes/ventas.xlsx?desde=2026-09-01&hasta=2026-09-30"
        "&metodo_pago=EFECTIVO"
    )


def test_LA_URL_QUE_DEVUELVE_BAJA_DE_VERDAD(
    api: TestClient, cabeceras_admin: dict[str, str], monkeypatch
) -> None:
    """Sin esto, el caso de uso puede «entender» y no entregar nada."""
    _sustituir(
        monkeypatch,
        _InterpreteFalso(
            Pedido(tipo="inventario", formato="xlsx", filtros={"bajo_minimo": "si"})
        ),
    )
    url = api.post(
        VOZ, headers=cabeceras_admin, json={"texto": "el inventario"}
    ).json()["url"]

    descarga = api.get(f"/api/v1{url}", headers=cabeceras_admin)
    assert descarga.status_code == 200
    assert descarga.content.startswith(b"PK")


def test_al_modelo_se_le_pasan_los_reportes_QUE_EXISTEN(
    api: TestClient, cabeceras_admin: dict[str, str], monkeypatch
) -> None:
    """Salen del mismo diccionario que la descarga.

    Con una lista aparte, el día que se agregue un reporte el intérprete
    seguiría sin conocerlo y diría «no entendí» a un pedido válido.
    """
    falso = _sustituir(monkeypatch, _InterpreteFalso(None))
    api.post(VOZ, headers=cabeceras_admin, json={"texto": "algo"})

    tipos = {r.tipo for r in falso.ultimos_reportes}
    assert {"ventas", "inventario", "movimientos", "reservas"} <= tipos

    # El inventario tiene que ir marcado como sin período: si el modelo no lo
    # sabe, inventa un rango que después se ignora y el resumen miente.
    inventario = next(r for r in falso.ultimos_reportes if r.tipo == "inventario")
    assert inventario.usa_periodo is False

    # Los valores de cada filtro van con su etiqueta: es lo que le permite
    # al modelo traducir «en efectivo» al valor que la consulta espera.
    ventas = next(r for r in falso.ultimos_reportes if r.tipo == "ventas")
    assert ventas.filtros["metodo_pago"]["EFECTIVO"] == "Efectivo"


# --- Lo que NO se entiende --------------------------------------------------


def test_si_no_se_entiende_se_PIDE_QUE_LO_REPITA_con_ejemplos(
    api: TestClient, cabeceras_admin: dict[str, str], monkeypatch
) -> None:
    """Nunca se adivina.

    Generar «lo más parecido» es como el administrador termina mandando por
    correo el reporte equivocado: no lo nota hasta abrirlo.
    """
    _sustituir(monkeypatch, _InterpreteFalso(None))

    cuerpo = api.post(
        VOZ, headers=cabeceras_admin, json={"texto": "hazme un pastel"}
    ).json()
    assert cuerpo["entendido"] is False
    assert cuerpo["url"] is None
    assert cuerpo["ejemplos"], "sin ejemplos, «no entendí» no dice qué sí funciona"


def test_si_el_servicio_falla_tampoco_se_adivina(
    api: TestClient, cabeceras_admin: dict[str, str], monkeypatch
) -> None:
    _sustituir(
        monkeypatch, _InterpreteFalso(error=ErrorDelInterprete("se cayó"))
    )
    cuerpo = api.post(VOZ, headers=cabeceras_admin, json={"texto": "ventas"}).json()
    assert cuerpo["entendido"] is False
    assert cuerpo["url"] is None
    assert "de nuevo" in cuerpo["motivo"].lower()


def test_sin_modelo_configurado_lo_dice_y_ofrece_la_lista(
    api: TestClient, cabeceras_admin: dict[str, str], monkeypatch
) -> None:
    """Acá NO hay degradación posible: sin modelo no se sabe qué se pidió.

    A diferencia del recomendador, que degrada a popularidad y sigue sirviendo
    prendas. Lo honesto es decirlo y mandar a elegir a mano.
    """
    _sustituir(
        monkeypatch, _InterpreteFalso(error=InterpreteNoConfigurado("sin clave"))
    )
    cuerpo = api.post(VOZ, headers=cabeceras_admin, json={"texto": "ventas"}).json()
    assert cuerpo["entendido"] is False
    assert "lista" in cuerpo["motivo"].lower()


def test_la_pantalla_puede_preguntar_si_hay_voz(
    api: TestClient, cabeceras_admin: dict[str, str], monkeypatch
) -> None:
    """Para esconder el micrófono en vez de ofrecerlo y fallar al tocarlo."""
    falso = _InterpreteFalso(None)
    falso.disponible = False
    _sustituir(monkeypatch, falso)
    assert api.get(DISPONIBLE, headers=cabeceras_admin).json() == {
        "disponible": False
    }


# --- Lo que no entra --------------------------------------------------------


@pytest.mark.parametrize("texto", ["", " ", "a"])
def test_un_texto_vacio_o_de_una_letra_lo_rechaza_el_esquema(
    api: TestClient, cabeceras_admin: dict[str, str], texto: str
) -> None:
    assert api.post(VOZ, headers=cabeceras_admin, json={"texto": texto}).status_code == 422


def test_un_texto_larguisimo_se_rechaza(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Un dictado de dos minutos no es un pedido de reporte: es ruido."""
    r = api.post(VOZ, headers=cabeceras_admin, json={"texto": "a" * 600})
    assert r.status_code == 422


# --- Quién puede ------------------------------------------------------------


def test_un_cliente_no_pide_reportes_por_voz(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    assert api.post(VOZ, headers=cabeceras_cliente, json={"texto": "ventas"}).status_code == 403


def test_sin_token(api: TestClient) -> None:
    assert api.post(VOZ, json={"texto": "ventas"}).status_code == 401


# --- Los filtros que salen de la base ---------------------------------------
#
# Hasta el 20/09 el catalogo que se le pasaba al modelo salteaba la sucursal
# ---a proposito--- y, de arrastre, el proveedor y la temporada, porque los
# tres traen la tupla de opciones vacia y se resuelven contra la base. El
# resultado era que «las compras del proveedor Shein» bajaba las compras de
# TODOS los proveedores sin decir nada. Un filtro dicho y no aplicado es peor
# que uno no ofrecido: el numero se lee como si estuviera filtrado.


def _crear_sucursal(
    api: TestClient, admin: dict[str, str], nombre: str, *, activa: bool = True
) -> int:
    r = api.post(
        "/api/v1/organizacion/sucursales",
        headers=admin,
        json={
            "ciudad_id": 1,
            "nombre": nombre,
            "direccion": f"Avenida {nombre} 100",
            "telefono": None,
            "horario_apertura": "09:00",
            "horario_cierre": "20:00",
            "capacidad_vestidores": 2,
            "activa": activa,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _crear_proveedor(
    api: TestClient, admin: dict[str, str], razon: str, nit: str
) -> int:
    r = api.post(
        "/api/v1/organizacion/proveedores",
        headers=admin,
        json={
            "razon_social": razon,
            "identificacion_tributaria": nit,
            "activo": True,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_AL_MODELO_SE_LE_DAN_LOS_NOMBRES_no_solo_los_identificadores(
    api: TestClient, cabeceras_admin: dict[str, str], monkeypatch
) -> None:
    """Sin el par `id -> nombre`, un filtro hablado es inalcanzable.

    Nadie dice «sucursal 3» ni «proveedor 7»: dice «la sucursal Centro» y «de
    Shein». Lo que la consulta necesita, en cambio, es el identificador. El
    puente entre las dos cosas es esta correspondencia, y va en el catalogo
    porque el modelo no puede consultarla por su cuenta.
    """
    centro = _crear_sucursal(api, cabeceras_admin, "Centro")
    shein = _crear_proveedor(api, cabeceras_admin, "Shein", "9001234567")

    falso = _sustituir(monkeypatch, _InterpreteFalso(None))
    api.post(VOZ, headers=cabeceras_admin, json={"texto": "algo"})

    ventas = next(r for r in falso.ultimos_reportes if r.tipo == "ventas")
    assert ventas.filtros["sucursal_id"][str(centro)] == "Centro"

    compras = next(r for r in falso.ultimos_reportes if r.tipo == "compras")
    assert compras.filtros["proveedor_id"][str(shein)] == "Shein"


def test_una_sucursal_dada_de_baja_NO_se_le_ofrece_al_modelo(
    api: TestClient, cabeceras_admin: dict[str, str], monkeypatch
) -> None:
    """El catalogo se arma en cada pedido, no una vez al arrancar.

    Es lo que hace que el intérprete siga al negocio: una sucursal que abrio
    ayer se puede pedir hoy hablando, y una que cerro deja de ofrecerse sin
    que nadie toque el codigo.
    """
    viva = _crear_sucursal(api, cabeceras_admin, "Centro")
    cerrada = _crear_sucursal(
        api, cabeceras_admin, "Sucursal Que Cierra", activa=False
    )

    falso = _sustituir(monkeypatch, _InterpreteFalso(None))
    api.post(VOZ, headers=cabeceras_admin, json={"texto": "algo"})

    ventas = next(r for r in falso.ultimos_reportes if r.tipo == "ventas")
    assert str(viva) in ventas.filtros["sucursal_id"]
    assert str(cerrada) not in ventas.filtros["sucursal_id"]


def test_al_encargado_no_se_le_ofrece_ELEGIR_sucursal_hablando(
    api: TestClient, cabeceras_admin: dict[str, str], monkeypatch
) -> None:
    """Se le fuerza la suya, asi que aceptarsela seria prometerle una
    eleccion que despues se ignora en silencio."""
    from datetime import timedelta

    sucursal = _crear_sucursal(api, cabeceras_admin, "Centro")
    correo = "encargado.voz@violetboutique.bo"
    clave = "Encargado12"
    alta = api.post(
        "/api/v1/organizacion/empleados",
        headers=cabeceras_admin,
        json={
            "nombres": "Encargada",
            "apellidos": "De Turno",
            "correo": correo,
            "contrasena": clave,
            "documento": "5544338",
            "telefono": "70000001",
            "cargo": "ENCARGADO",
            "sucursal_id": sucursal,
            "fecha_ingreso": (date.today() - timedelta(days=30)).isoformat(),
        },
    )
    assert alta.status_code == 201, alta.text
    entrada = api.post(
        "/api/v1/auth/login", json={"correo": correo, "contrasena": clave}
    )
    assert entrada.status_code == 200, entrada.text
    cabeceras = {"Authorization": f"Bearer {entrada.json()['access_token']}"}

    falso = _sustituir(monkeypatch, _InterpreteFalso(None))
    api.post(VOZ, headers=cabeceras, json={"texto": "algo"})

    for reporte in falso.ultimos_reportes:
        assert "sucursal_id" not in reporte.filtros


def test_EL_FILTRO_HABLADO_LLEGA_A_LA_URL(
    api: TestClient, cabeceras_admin: dict[str, str], monkeypatch
) -> None:
    """La prueba de punta a punta de lo que fallaba.

    Se dijo «las compras de la sucursal Centro, proveedor Shein»; los dos
    filtros tienen que viajar en la URL. Antes viajaba ninguno y el archivo
    salia con todo.
    """
    centro = _crear_sucursal(api, cabeceras_admin, "Centro")
    shein = _crear_proveedor(api, cabeceras_admin, "Shein", "9001234567")

    _sustituir(
        monkeypatch,
        _InterpreteFalso(
            Pedido(
                tipo="compras",
                formato="pdf",
                filtros={
                    "sucursal_id": str(centro),
                    "proveedor_id": str(shein),
                },
                resumen="Compras a Shein en la sucursal Centro, en PDF",
            )
        ),
    )
    cuerpo = api.post(
        VOZ,
        headers=cabeceras_admin,
        json={"texto": "compras de la sucursal centro, proveedor shein en pdf"},
    ).json()

    assert f"sucursal_id={centro}" in cuerpo["url"]
    assert f"proveedor_id={shein}" in cuerpo["url"]

    descarga = api.get(f"/api/v1{cuerpo['url']}", headers=cabeceras_admin)
    assert descarga.status_code == 200, descarga.text
    assert descarga.content.startswith(b"%PDF")
