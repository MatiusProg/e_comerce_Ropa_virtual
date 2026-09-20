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

    # La sucursal NO se le ofrece: sus valores son ids y nadie dice
    # «sucursal 3» hablando.
    ventas = next(r for r in falso.ultimos_reportes if r.tipo == "ventas")
    assert "sucursal_id" not in ventas.filtros
    assert "metodo_pago" in ventas.filtros


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
