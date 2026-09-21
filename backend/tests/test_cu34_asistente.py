"""CU-34 · Conversar con el asistente virtual.

Realiza el **RF25** junto con CU-33 y CU-35. Es el tercero de los tres casos
de uso de P10 y el que el plan dejaba caer primero.

LA DECISIÓN QUE ESTAS PRUEBAS PROTEGEN
----------------------------------------
**El modelo no consulta la base: se le arma el contexto.** El servicio busca
los datos reales —ya filtrados por quien pregunta— y el modelo solo redacta
sobre eso.

Lo natural habría sido darle acceso a la base y dejarlo buscar. Se descartó
por dos razones y cualquiera de las dos alcanza:

1. **Un modelo que puede consultar puede leer lo que no le toca.** Acotarlo
   desde el prompt no es un control de acceso.
2. **Inventa.** Preguntado por una prenda que no existe, describe una
   plausible. En una tienda eso es prometer algo que no se puede vender.

NINGUNA PRUEBA LLAMA AL MODELO DE VERDAD
------------------------------------------
Se sustituye el proveedor, igual que en CU-33 y CU-35. Una prueba que sale a
internet tarda, gasta cuota y falla cuando Gemini tarda de más — y una
prueba que falla por algo que el sistema maneja bien no prueba nada.

Lo que más importa cubrir
-------------------------
- **Que el contexto tenga datos reales y SOLO los de quien pregunta.** Es la
  mitad de seguridad de este caso de uso.
- **Que un código de producto inventado no llegue a la pantalla.**
- **Que sin modelo NO se conteste igual.** Un asistente que responde «no
  entendí» a todo es un cartel que engaña.
- **Que el historial viaje**, porque sin él «¿y en talla M?» no significa
  nada.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core import tiempo
from app.integrations import asistente
from app.integrations.asistente import (
    AsistenteNoConfigurado,
    Contexto,
    ErrorDelAsistente,
    Respuesta,
)

ASISTENTE = "/api/v1/asistente"
DISPONIBLE = f"{ASISTENTE}/disponible"


class _AsistenteFalso:
    """Devuelve lo que la prueba le diga, y recuerda con qué lo llamaron."""

    nombre = "falso"
    disponible = True

    def __init__(self, texto: str = "Hola.", error: Exception | None = None):
        self.texto = texto
        self.error = error
        self.ultimo_contexto: Contexto | None = None
        self.ultimo_historial: list = []
        self.ultima_pregunta = ""

    def responder(self, pregunta, contexto, historial):
        self.ultima_pregunta = pregunta
        self.ultimo_contexto = contexto
        self.ultimo_historial = list(historial)
        if self.error is not None:
            raise self.error
        # Se pasa por el lector de verdad para que la validación de códigos
        # contra el catálogo sea la real y no una simulada.
        from app.integrations.asistente.gemini import _leer

        return _leer(self.texto, contexto)


def _sustituir(monkeypatch, falso: _AsistenteFalso) -> _AsistenteFalso:
    monkeypatch.setattr(asistente, "obtener_proveedor", lambda: falso)
    monkeypatch.setattr(
        asistente, "responder", lambda p, c, h: falso.responder(p, c, h)
    )
    monkeypatch.setattr(asistente, "esta_disponible", lambda: falso.disponible)
    return falso


def _preguntar(api: TestClient, cab: dict, texto: str, historial=None) -> dict:
    r = api.post(
        ASISTENTE,
        headers=cab,
        json={"pregunta": texto, "historial": historial or []},
    )
    assert r.status_code == 200, r.text
    return r.json()


# --- El contexto: datos reales, y solo los propios -------------------------


def test_EL_CONTEXTO_SALE_DE_LA_BASE_no_lo_inventa_el_modelo(
    api: TestClient, cabeceras_cliente: dict[str, str], monkeypatch
) -> None:
    """Es la decisión de fondo del caso de uso.

    El modelo recibe el catálogo ya resuelto —con precio, tallas y si hay
    stock— y no tiene forma de pedir nada más.
    """
    falso = _sustituir(monkeypatch, _AsistenteFalso())
    _preguntar(api, cabeceras_cliente, "¿qué tienen?")

    ctx = falso.ultimo_contexto
    assert ctx is not None
    assert ctx.nombre, "la respuesta se dirige a alguien"
    # Cada línea del catálogo lleva el código, el precio y si hay stock.
    for linea in ctx.catalogo:
        assert linea.startswith("#")
        assert "Bs " in linea
        assert "hay stock" in linea or "AGOTADA" in linea


def test_EL_ASISTENTE_SOLO_VE_LOS_DATOS_DE_QUIEN_PREGUNTA(
    api: TestClient, cabeceras_cliente: dict[str, str], monkeypatch
) -> None:
    """La mitad de seguridad de este caso de uso.

    El filtro por cliente va en el `WHERE` de la consulta, **no en la
    instrucción**: pedirle al modelo que no mire lo ajeno no es un control
    de acceso.
    """
    falso = _sustituir(monkeypatch, _AsistenteFalso())
    _preguntar(api, cabeceras_cliente, "¿ya llegó mi pedido?")

    ctx = falso.ultimo_contexto
    # Un cliente recién creado no tiene pedidos ni reservas: si apareciera
    # algo, sería de otro.
    assert ctx.pedidos == ()
    assert ctx.reservas == ()


def test_el_contexto_trae_las_sucursales_y_la_fecha_de_hoy(
    api: TestClient, cabeceras_cliente: dict[str, str], monkeypatch
) -> None:
    """Sin la fecha, «¿cuándo tengo que ir?» no se puede contestar."""
    falso = _sustituir(monkeypatch, _AsistenteFalso())
    _preguntar(api, cabeceras_cliente, "¿dónde retiro?")

    assert any("Hoy es" in d for d in falso.ultimo_contexto.datos)


# --- Lo que el modelo devuelve no se cree sin comprobar --------------------


def test_UN_PRODUCTO_INVENTADO_NO_LLEGA_A_LA_PANTALLA(
    api: TestClient, cabeceras_cliente: dict[str, str], monkeypatch
) -> None:
    """Lo mismo que hace CU-35 con el tipo de reporte.

    Lo que el modelo devuelve es una propuesta, no un hecho. Un código que
    no está en el catálogo que se le pasó **no existe**, y ofrecerlo como
    enlace llevaría a una ficha vacía.
    """
    _sustituir(
        monkeypatch,
        _AsistenteFalso("Mirá el [#999999] que está buenísimo."),
    )
    cuerpo = _preguntar(api, cabeceras_cliente, "¿qué me recomendás?")

    assert cuerpo["productos"] == []
    # El texto se devuelve igual: recortarlo dejaría una frase a medias.
    assert "999999" in cuerpo["texto"]


@pytest.mark.parametrize(
    "escrito, esperado",
    [
        ("[#7]", [7]),
        # Se le pide `[#7]` y a veces lo resalta. Medido el 20/09 contra
        # Gemini: con un patrón estricto esa respuesta se quedaba **sin
        # prendas enlazables** — el texto nombraba la prenda y la pantalla
        # no la podía ofrecer.
        ("[*#7*]", [7]),
        ("[**#7**]", [7]),
        ("Mirá [#7] y también [#9].", [7, 9]),
        # Repetido: se enlaza una sola vez.
        ("[#7] o [#7]", [7]),
        # Inventado: no está en el catálogo, no llega.
        ("[#999]", []),
        ("sin ningún código", []),
    ],
)
def test_QUE_CODIGOS_SE_RECONOCEN_Y_CUALES_SE_DESCARTAN(escrito, esperado) -> None:
    """Se prueba contra `_leer` y no por HTTP a propósito.

    Depender del catálogo de la base haría que estas comprobaciones se
    saltearan cuando no hay productos sembrados — que es justo lo que
    pasaba, y dejaba sin cubrir el arreglo que motivó la prueba.
    """
    from app.integrations.asistente.gemini import _leer

    contexto = Contexto(
        nombre="Ana",
        catalogo=("#7 Blusa | Blusas | Bs 100 | hay stock",
                  "#9 Falda | Faldas | Bs 200 | hay stock"),
    )
    assert list(_leer(escrito, contexto).productos) == esperado


# --- El historial ----------------------------------------------------------


def test_EL_HISTORIAL_VIAJA_al_proveedor(
    api: TestClient, cabeceras_cliente: dict[str, str], monkeypatch
) -> None:
    """Sin él, «¿y en talla M?» no significa nada — y eso es la mitad de lo
    que hace conversacional a un asistente."""
    falso = _sustituir(monkeypatch, _AsistenteFalso())
    _preguntar(
        api,
        cabeceras_cliente,
        "¿y en talla M?",
        historial=[{"pregunta": "¿qué vestidos hay?", "respuesta": "Tres."}],
    )

    assert falso.ultimo_historial == [("¿qué vestidos hay?", "Tres.")]


def test_el_historial_se_acota(api: TestClient, cabeceras_cliente: dict) -> None:
    """Diez turnos como máximo: el cuerpo de la petición no puede crecer sin
    límite porque la conversación siga."""
    r = api.post(
        ASISTENTE,
        headers=cabeceras_cliente,
        json={
            "pregunta": "hola",
            "historial": [{"pregunta": "a", "respuesta": "b"}] * 11,
        },
    )
    assert r.status_code == 422


# --- Cuando no se puede ----------------------------------------------------


def test_SIN_MODELO_NO_SE_CONTESTA_IGUAL(
    api: TestClient, cabeceras_cliente: dict[str, str], monkeypatch
) -> None:
    """No hay degradación posible, y es una decisión.

    El recomendador de CU-33 degrada a popularidad y está bien: una lista
    ordenada por ventas sigue sirviendo. Acá no hay equivalente — un
    asistente que contesta con frases armadas daría respuestas que parecen
    del sistema y no salen de sus datos.
    """
    _sustituir(
        monkeypatch,
        _AsistenteFalso(error=AsistenteNoConfigurado("sin clave")),
    )
    r = api.post(ASISTENTE, headers=cabeceras_cliente, json={"pregunta": "hola"})
    assert r.status_code == 503
    assert "no está habilitado" in r.json()["detail"]


def test_si_el_servicio_falla_tampoco_se_inventa(
    api: TestClient, cabeceras_cliente: dict[str, str], monkeypatch
) -> None:
    _sustituir(
        monkeypatch,
        _AsistenteFalso(error=ErrorDelAsistente("no contestó")),
    )
    r = api.post(ASISTENTE, headers=cabeceras_cliente, json={"pregunta": "hola"})
    assert r.status_code == 503
    assert "Probá de nuevo" in r.json()["detail"]


def test_la_pantalla_puede_preguntar_si_hay_asistente(
    api: TestClient, cabeceras_cliente: dict[str, str], monkeypatch
) -> None:
    """Se pregunta ANTES de ofrecerlo, igual que el micrófono de CU-35:
    esconder lo que no funciona es mejor que ofrecerlo y fallar al tocarlo."""
    _sustituir(monkeypatch, _AsistenteFalso())
    r = api.get(DISPONIBLE, headers=cabeceras_cliente)
    assert r.status_code == 200
    assert r.json()["disponible"] is True
    assert r.json()["ejemplos"], "sin ejemplos nadie sabe qué preguntar"


# --- Quién puede usarlo ----------------------------------------------------


def test_UN_ADMINISTRADOR_NO_TIENE_ASISTENTE(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Habla de «tus pedidos» y «tus reservas». Un administrador tiene
    usuario pero no perfil de compra: contestarle sería hablar de nadie."""
    r = api.post(ASISTENTE, headers=cabeceras_admin, json={"pregunta": "hola"})
    assert r.status_code == 403


def test_sin_token_no_hay_asistente(api: TestClient) -> None:
    assert api.post(ASISTENTE, json={"pregunta": "hola"}).status_code == 401


# --- Validación de la pregunta ---------------------------------------------


@pytest.mark.parametrize("texto", ["", " ", "a"])
def test_una_pregunta_vacia_o_de_una_letra_se_rechaza(
    api: TestClient, cabeceras_cliente: dict[str, str], texto
) -> None:
    r = api.post(ASISTENTE, headers=cabeceras_cliente, json={"pregunta": texto})
    assert r.status_code == 422


def test_una_pregunta_larguisima_se_rechaza(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    r = api.post(
        ASISTENTE, headers=cabeceras_cliente, json={"pregunta": "a" * 501}
    )
    assert r.status_code == 422


# --- Las promociones (el hueco que cerró el 20/09) -------------------------


def test_SIN_PROMOCIONES_SE_DICE_QUE_NO_HAY_no_se_calla() -> None:
    """La ausencia de ofertas ES un dato, y el prompt la nombra.

    `_seccion` omite las secciones vacías, y con las ofertas eso estaba mal:
    sin la línea, el modelo no distingue «hoy no hay ofertas» de «no me
    pasaron las ofertas», y ante la duda manda a preguntar en la tienda —
    que es la respuesta inútil que este caso de uso existe para evitar.
    """
    from app.integrations.asistente.gemini import _ofertas

    texto = _ofertas(())
    assert "PROMOCIONES VIGENTES HOY" in texto
    assert "no hay ninguna" in texto


def test_el_prompt_lleva_las_ofertas_a_la_vista() -> None:
    """Aparte del catálogo, y no es redundancia: «¿qué ofertas hay?» es una
    pregunta por la lista, y recorrer sesenta líneas buscando cuáles tienen
    descuento es justo lo que un modelo hace mal."""
    from app.integrations.asistente.gemini import _INSTRUCCION, _ofertas

    armado = _INSTRUCCION.format(
        nombre="Ana",
        catalogo="#7 Blusa | Bs 100",
        ofertas=_ofertas(("#7 Blusa | Fin de temporada | -20% | de Bs 100 a Bs 80",)),
        tallas="",
        pedidos="",
        reservas="",
        medidas="",
        datos="",
        historial="",
        pregunta="¿qué ofertas hay?",
    )
    assert "Fin de temporada" in armado
    assert "PROMOCIONES VIGENTES HOY" in armado


def test_UNA_PROMOCION_VIGENTE_LLEGA_AL_CONTEXTO(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    monkeypatch,
) -> None:
    """De punta a punta: el Administrador la carga y el asistente la sabe.

    El descuento se pide por la costura de CU-12 y no con una consulta
    propia. Si se recalculara acá, el asistente podría prometer un 20 %
    mientras la vitrina cobra otra cosa — que es peor que no saber de
    ofertas.

    La prenda se siembra acá y no se toma del catálogo que haya: apoyarse en
    lo sembrado dejaba la prueba saltándose sola cuando no había productos,
    que es justo cuando hace falta que corra.
    """
    catalogo = "/api/v1/catalogo"
    categoria = api.post(
        f"{catalogo}/categorias",
        headers=cabeceras_admin,
        json={"nombre": "Abrigos CU-34", "orden": 0, "activa": True},
    )
    assert categoria.status_code == 201, categoria.text

    producto = api.post(
        f"{catalogo}/productos",
        headers=cabeceras_admin,
        json={
            "codigo": "CU34-OFERTA",
            "nombre": "Abrigo de prueba del asistente",
            "categoria_id": categoria.json()["id"],
            "temporada_id": None,
            "precio_base": "500.00",
            "activo": True,
        },
    )
    assert producto.status_code == 201, producto.text
    producto_id = producto.json()["id"]

    talla = api.post(
        f"{catalogo}/tallas",
        headers=cabeceras_admin,
        json={"tipo_prenda": "Superior", "codigo": "U", "orden": 0, "activa": True},
    )
    color = api.post(
        f"{catalogo}/colores",
        headers=cabeceras_admin,
        json={"nombre": "Gris CU-34", "hexadecimal": "#808080", "activo": True},
    )
    generadas = api.post(
        f"{catalogo}/productos/{producto_id}/variantes/generar",
        headers=cabeceras_admin,
        json={"tallas": [talla.json()["id"]], "colores": [color.json()["id"]]},
    )
    assert generadas.status_code == 201, generadas.text

    alta = api.post(
        f"{catalogo}/promociones",
        headers=cabeceras_admin,
        json={
            "nombre": "Liquidación de prueba",
            "alcance": "PRODUCTO",
            "objetivo_id": producto_id,
            "porcentaje": "20.00",
            "desde": tiempo.hoy().isoformat(),
            "hasta": None,
            "activa": True,
        },
    )
    assert alta.status_code in (200, 201), alta.text

    falso = _sustituir(monkeypatch, _AsistenteFalso())
    _preguntar(api, cabeceras_cliente, "¿qué ofertas hay?")
    ctx = falso.ultimo_contexto

    assert any("Liquidación de prueba" in o for o in ctx.ofertas), ctx.ofertas
    # Y también marcada en su línea del catálogo, para que «¿cuánto sale?»
    # conteste el precio que se paga y no el de lista.
    suya = next(l for l in ctx.catalogo if l.startswith(f"#{producto_id} "))
    assert "EN OFERTA -20%" in suya, suya
    assert "Bs 400.00" in suya, suya
