"""
P3 - Catalogo / CU-38  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 3
Caso de uso: CU-38 Registrar productos del proveedor  (RF37)

Archivos propios ---`proveedor_service.py` y `proveedor_router.py` junto a
este--- con el mismo patron que `imagenes_*` y `temporadas_*` usan dentro de
este paquete. No cuelgan del router de CU-10 porque la guarda de rol es otra:
alli manda el Administrador y aqui el Proveedor.

POR QUE ESTOS ESQUEMAS Y NO LOS DE CU-10
----------------------------------------
Son casi los mismos menos dos campos, y esos dos campos son todo el caso de uso:

  - **`proveedor_id` no existe aqui.** No es que se ignore si llega: no esta en
    el esquema, asi que el contrato dice que no se manda. El ambito sale del
    token y de ningun otro lado --- ver `proveedor_service.py`.
  - **`activo` tampoco.** Un producto que registra el Proveedor nace inactivo y
    solo el Administrador lo publica, por CU-10.

Reutilizar `ProductoCrearIn` con esos campos adentro habria dejado dos lugares
donde un descuido abre el mismo agujero: el que valida y el que ignora.
"""
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.modules.catalogo.maestros.schemas import CategoriaOut, ColorOut, TallaOut
from app.modules.catalogo.schemas import _limpiar, _PRECIO_MAXIMO
from app.modules.catalogo.temporadas_schemas import ColeccionOut, TemporadaOut


class MiProductoCrearIn(BaseModel):
    """Alta de un producto por parte de su proveedor (pasos 4 y 5).

    `codigo` sigue siendo del Proveedor y no se genera solo: es el que usa en su
    propia nomenclatura, y es lo que permite reconocer la prenda cuando llega el
    remito. El UNIQUE es de toda la tabla, asi que dos proveedores no pueden
    repetirlo --- ver la excepcion E1.
    """

    codigo: str = Field(min_length=1, max_length=30)
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str | None = Field(default=None, max_length=500)
    categoria_id: int
    temporada_id: int | None = None
    coleccion_id: int | None = None
    precio_base: Decimal = Field(gt=0, le=_PRECIO_MAXIMO)

    @field_validator("codigo")
    @classmethod
    def _codigo_limpio(cls, valor: str) -> str:
        # En mayusculas, igual que CU-10: el UNIQUE de PostgreSQL distingue
        # mayusculas y si no, "cam-001" y "CAM-001" entrarian los dos.
        return _limpiar(valor).upper()

    @field_validator("nombre")
    @classmethod
    def _nombre_limpio(cls, valor: str) -> str:
        return _limpiar(valor)

    @field_validator("descripcion")
    @classmethod
    def _descripcion_limpia(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


class MiProductoEditarIn(BaseModel):
    """Edicion de un producto propio (flujo alternativo 3a).

    Todo opcional: se envia solo lo que cambia. Para temporada y coleccion se
    distingue «no enviado» de «enviado en null» con `model_fields_set`, porque
    mandarlas en null significa sacar el producto de la temporada o de la
    coleccion, que es una operacion legitima --- misma regla que CU-10.

    `categoria_id` SI se puede cambiar; `proveedor_id` no esta.
    """

    codigo: str | None = Field(default=None, min_length=1, max_length=30)
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    descripcion: str | None = Field(default=None, max_length=500)
    categoria_id: int | None = None
    temporada_id: int | None = None
    coleccion_id: int | None = None
    precio_base: Decimal | None = Field(default=None, gt=0, le=_PRECIO_MAXIMO)

    @field_validator("codigo")
    @classmethod
    def _codigo_limpio(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return _limpiar(valor).upper()

    @field_validator("nombre")
    @classmethod
    def _nombre_limpio(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return _limpiar(valor)

    @field_validator("descripcion")
    @classmethod
    def _descripcion_limpia(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


class ListasDelFormularioOut(BaseModel):
    """Los maestros que el formulario del Proveedor necesita para sus selectores.

    POR QUE EXISTE ESTE ENDPOINT Y NO SE REUSAN LOS DE CU-08
    --------------------------------------------------------
    Los routers de maestros ---categorias, tallas, colores--- y el de temporadas
    exigen rol **ADMINISTRADOR** a nivel de router, y ademas de leer permiten
    crear, editar y borrar. Aflojar esa guarda para que el Proveedor pueda
    llenar un selector le daria de paso permiso para crear categorias: la
    dependencia se declara una sola vez para todo el router, que es
    justamente lo que lo hace seguro.

    Tampoco sirve `GET /tienda/filtros`, de CU-17: ese devuelve solo lo que hoy
    se ofrece --- activo y con existencia ---, y un formulario de alta necesita
    el maestro completo, incluso una temporada que todavia no tiene un solo
    producto.

    Asi que el Proveedor recibe SU PROPIA vista, de solo lectura y sin ningun
    verbo de escritura, dentro de su router. Lo que se expone son los maestros
    activos, que es lo unico que se puede elegir en un alta.
    """

    categorias: list[CategoriaOut]
    tallas: list[TallaOut]
    colores: list[ColorOut]
    temporadas: list[TemporadaOut]
    colecciones: list[ColeccionOut]
