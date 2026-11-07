"""Probador SIMULADO: la foto «realista» sin llamar a ningun modelo.

2do parcial, CU-38. Es el proveedor por defecto desde el 07/11/2026.

POR QUE EXISTE
--------------
La generacion de imagenes de Gemini esta detras de facturacion (ver la nota de
`gemini.py`, probado el 18/09: limite CERO en el plan gratuito). Sin esto, el
CU-38 no se podria recorrer entero ni en local ni en la defensa: el boton
estaria escondido y el cupo del plan, que es justamente lo que el caso de uso
regula, nunca se gastaria.

Este proveedor toma la COMPOSICION del CU-37 --- la foto del cliente con la
prenda ya puesta a su escala real --- y la devuelve suavizada, con una franja
que dice que es una vista simulada. No inventa nada: lo que se ve es lo que el
probador calculo con las medidas, que es lo unico que respeta la talla.

POR QUE NO VIOLA EL RIESGO R9
-----------------------------
R9 era «quedarse sin credito antes de la defensa» por un valor por defecto que
llama a un servicio pago. Este no llama a nadie: corre con Pillow, en el mismo
proceso, y no cuesta nada.

LA MARCA NO SE PUEDE QUITAR
---------------------------
Una imagen generada tiene que poder reconocerse como tal. La franja va dentro
de los pixeles y no solo en la cabecera `X-Generada-Por`, porque la cabecera se
pierde en cuanto el cliente guarda o comparte la imagen.
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, UnidentifiedImageError

from app.integrations.probador_ia.base import (
    ErrorDelProbador,
    ResultadoDeProbado,
    SolicitudDeProbado,
)

#: El texto de la franja.
MARCA = "VISTA SIMULADA - sin IA generativa"

#: Lado mayor de la imagen que se devuelve. Una foto de 12 MP del telefono no
#: hace falta para verse en pantalla y pesa diez veces mas.
LADO_MAXIMO = 1280


class ProbadorSimulado:
    """Compone la vista localmente, sin terceros."""

    nombre = "simulado"
    disponible = True

    def probar(self, solicitud: SolicitudDeProbado) -> ResultadoDeProbado:
        try:
            imagen = Image.open(io.BytesIO(solicitud.foto))
            imagen.load()
        except (UnidentifiedImageError, OSError) as e:
            raise ErrorDelProbador("La composición no es una imagen válida.") from e

        imagen = imagen.convert("RGB")
        imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
        # Un retoque leve, para que se distinga de la composicion cruda: suaviza
        # el borde recortado de la prenda y le da algo de color.
        imagen = imagen.filter(ImageFilter.SMOOTH_MORE)
        imagen = ImageEnhance.Color(imagen).enhance(1.08)
        imagen = ImageEnhance.Contrast(imagen).enhance(1.04)

        ancho, alto = imagen.size
        franja = max(22, alto // 18)
        dibujo = ImageDraw.Draw(imagen, "RGBA")
        dibujo.rectangle((0, alto - franja, ancho, alto), fill=(40, 16, 64, 190))
        fuente = _fuente(max(10, int(franja * 0.55)))
        caja = dibujo.textbbox((0, 0), MARCA, font=fuente)
        x = max(4, (ancho - (caja[2] - caja[0])) // 2)
        y = alto - franja + (franja - (caja[3] - caja[1])) // 2 - caja[1]
        dibujo.text((x, y), MARCA, font=fuente, fill=(255, 255, 255, 235))

        salida = io.BytesIO()
        imagen.save(salida, format="PNG", optimize=True)
        return ResultadoDeProbado(
            imagen=salida.getvalue(), tipo_mime="image/png", generada_por=self.nombre
        )


def _fuente(tamano: int):
    """Una fuente TrueType si la hay; si no, la de Pillow (Railway no trae fuentes)."""
    for nombre in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(nombre, tamano)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=tamano)
    except TypeError:  # Pillow viejo
        return ImageFont.load_default()
