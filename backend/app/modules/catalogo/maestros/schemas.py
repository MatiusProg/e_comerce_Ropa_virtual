"""
P3 - Catalogo / CU-08  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 1
Caso de uso: CU-08 Gestionar categorias, tallas y colores
"""
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.
#
# Las longitudes maximas replican el esquema fisico de
# docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md seccion 3.3.2.

#: Formato del color, identico al CHECK ck_color_hex de la base. Validarlo aqui
#: devuelve un 422 que nombra el campo, en vez de un error de PostgreSQL.
_HEXADECIMAL = re.compile(r"^#[0-9A-Fa-f]{6}$")


# --- Categorias (flujo principal) ----------------------------------------

class CategoriaOut(BaseModel):
    """Un nodo del arbol de categorias (paso 2).

    `subcategorias` viene poblado: el arbol se arma en el servidor y no en la
    interfaz, para que las dos formas de mostrarlo -- web y movil -- reciban ya
    resuelta la jerarquia.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    categoria_padre_id: int | None
    nombre: str
    orden: int
    activa: bool
    #: Cuantas subcategorias cuelgan directamente. Viaja porque la excepcion E3
    #: impide eliminar una categoria que las tenga, y conviene decirlo antes de
    #: que lo intenten.
    subcategorias: list["CategoriaOut"] = []


class CategoriaCrearIn(BaseModel):
    """Alta de una categoria (pasos 4 y 5)."""

    nombre: str = Field(min_length=1, max_length=60)
    categoria_padre_id: int | None = None
    orden: int = Field(default=0, ge=0, le=32767)
    activa: bool = True

    @field_validator("nombre")
    @classmethod
    def _nombre_limpio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("El nombre no puede quedar vacío.")
        return valor


class CategoriaEditarIn(BaseModel):
    """Edicion de una categoria (flujo alternativo 3a).

    `categoria_padre_id` es el campo delicado: moverla de lugar puede formar un
    ciclo, que es la excepcion E2. Se distingue «no enviado» de «enviado como
    null» con `model_fields_set`, porque enviarlo en null significa convertirla
    en categoria raiz.
    """

    nombre: str | None = Field(default=None, min_length=1, max_length=60)
    categoria_padre_id: int | None = None
    orden: int | None = Field(default=None, ge=0, le=32767)

    @field_validator("nombre")
    @classmethod
    def _nombre_limpio(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


# --- Tallas (flujo alternativo 1a) ---------------------------------------

class TallaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo_prenda: str
    codigo: str
    orden: int
    activa: bool


class TallaCrearIn(BaseModel):
    """Alta de una talla.

    El orden importa: es el que decide como se muestran en la ficha de
    producto. Sin el, XL aparece antes que S por orden alfabetico.
    """

    tipo_prenda: str = Field(min_length=1, max_length=30)
    codigo: str = Field(min_length=1, max_length=10)
    orden: int = Field(default=0, ge=0, le=32767)
    activa: bool = True

    @field_validator("tipo_prenda")
    @classmethod
    def _tipo_normalizado(cls, valor: str) -> str:
        """Normaliza el tipo de prenda a mayusculas.

        Es texto libre y agrupa el catalogo de tallas. Sin normalizar,
        'Superior' y 'superior' serian dos grupos distintos, y la restriccion
        uq_talla_tipo_codigo dejaria pasar 'M' repetida en cada uno.
        """
        valor = valor.strip().upper()
        if not valor:
            raise ValueError("El tipo de prenda no puede quedar vacío.")
        return valor

    @field_validator("codigo")
    @classmethod
    def _codigo_normalizado(cls, valor: str) -> str:
        valor = valor.strip().upper()
        if not valor:
            raise ValueError("El código no puede quedar vacío.")
        return valor


class TallaEditarIn(BaseModel):
    tipo_prenda: str | None = Field(default=None, min_length=1, max_length=30)
    codigo: str | None = Field(default=None, min_length=1, max_length=10)
    orden: int | None = Field(default=None, ge=0, le=32767)

    @field_validator("tipo_prenda", "codigo")
    @classmethod
    def _normalizado(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip().upper() or None


# --- Colores (flujo alternativo 1b) --------------------------------------

class ColorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    hexadecimal: str
    activo: bool


class ColorCrearIn(BaseModel):
    """Alta de un color. El hexadecimal es el que pinta la muestra."""

    nombre: str = Field(min_length=1, max_length=40)
    hexadecimal: str = Field(min_length=7, max_length=7)
    activo: bool = True

    @field_validator("nombre")
    @classmethod
    def _nombre_limpio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("El nombre no puede quedar vacío.")
        return valor

    @field_validator("hexadecimal")
    @classmethod
    def _hexadecimal_valido(cls, valor: str) -> str:
        """Normaliza a mayusculas y exige el formato del CHECK de la base.

        Se guarda en un solo formato para que dos filas no describan el mismo
        color con '#ff0000' y '#FF0000' y la restriccion de nombre unico sea lo
        unico que los distinga.
        """
        valor = valor.strip().upper()
        if not _HEXADECIMAL.match(valor):
            raise ValueError("El color debe tener el formato #RRGGBB, por ejemplo #C9A227.")
        return valor


class ColorEditarIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=40)
    hexadecimal: str | None = Field(default=None, min_length=7, max_length=7)

    @field_validator("nombre")
    @classmethod
    def _nombre_limpio(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None

    @field_validator("hexadecimal")
    @classmethod
    def _hexadecimal_valido(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor = valor.strip().upper()
        if not _HEXADECIMAL.match(valor):
            raise ValueError("El color debe tener el formato #RRGGBB, por ejemplo #C9A227.")
        return valor


# --- Comun ---------------------------------------------------------------

class CambioEstadoIn(BaseModel):
    """Activacion o desactivacion (flujo alternativo 3b).

    Sirve para las tres entidades: el flujo es el mismo y el campo tambien.
    """

    activo: bool
