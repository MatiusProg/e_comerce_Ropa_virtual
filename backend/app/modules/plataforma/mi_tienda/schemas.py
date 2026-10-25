"""
P12 - Plataforma SaaS / CU-12  |  capa: esquemas

2do parcial. Caso de uso: CU-12 Personalizar la tienda de la empresa.
"""
from pydantic import BaseModel, Field, field_validator

#: `#rrggbb`. El selector de color del navegador ya lo manda asi; se pasa a
#: minusculas para que la base guarde una sola forma de cada color.
PATRON_COLOR = r"^#[0-9a-fA-F]{6}$"


class MarcaOut(BaseModel):
    """Lo que ve el administrador en «Mi tienda» (pasos 1.5 y 1.6)."""

    empresa: str
    slug: str
    logo_url: str | None
    color_principal: str | None
    color_secundario: str | None
    #: 1a: si el plan incluye `marca_propia`. Sin ella la pantalla se ve pero
    #: no guarda, y la tienda se muestra con la marca de Violet.
    incluida: bool


class ColoresIn(BaseModel):
    """Paso 1.7: los dos colores. `None` vuelve al color de Violet."""

    color_principal: str | None = Field(default=None, pattern=PATRON_COLOR)
    color_secundario: str | None = Field(default=None, pattern=PATRON_COLOR)

    @field_validator("color_principal", "color_secundario")
    @classmethod
    def _en_minusculas(cls, valor: str | None) -> str | None:
        return valor.lower() if valor else None


class MarcaTiendaOut(BaseModel):
    """1.11: la marca que aplica la tienda en linea. Publica.

    Sin `marca_propia` en el plan salen el logo y los colores en `None`: la
    tienda usa los de Violet.
    """

    empresa: str | None
    logo_url: str | None
    color_principal: str | None
    color_secundario: str | None
