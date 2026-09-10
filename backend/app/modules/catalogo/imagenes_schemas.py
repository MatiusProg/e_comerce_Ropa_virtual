"""
P3 - Catalogo / CU-11  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 2
Caso de uso: CU-11 Gestionar imagenes de producto

Regla: NUNCA se expone un modelo SQLAlchemy directamente.

La forma de la tabla esta fijada en la seccion 6.4 de
docs/entregas/ciclo-2/00-organizacion-por-caso-de-uso.md.
"""
from pydantic import BaseModel, ConfigDict, Field


class ImagenOut(BaseModel):
    """Una imagen del producto o de una de sus variantes.

    `ruta` es la ruta relativa dentro del volumen, tal como la guarda la base
    (seccion 6.8). `url` es esa misma ruta ya prefijada con MEDIA_URL: la arma
    el servidor para que la web y la app movil no tengan que saber como se
    monta el volumen ni concatenar nada.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    variante_id: int | None
    ruta: str
    url: str = ""
    es_principal: bool
    es_transparente: bool
    orden: int
    #: Se resuelven en el servidor para poder rotular la miniatura sin que la
    #: interfaz cruce la tabla de variantes.
    variante_sku: str | None = None
    variante_etiqueta: str | None = None


class ImagenEditarIn(BaseModel):
    """Flujos alternativos 3a a 3d: a que variante pertenece y en que orden va.

    El archivo NO se reemplaza desde aqui. Cambiar los bytes conservando la
    misma fila dejaria en el volumen un archivo huerfano y una ruta que ya no
    describe lo que hay: para cambiar la foto se sube otra y se borra esta.

    `variante_id` distingue «no enviado» de «enviado en null» con
    `model_fields_set`: mandarlo en null desasocia la imagen de su variante y la
    convierte en imagen del producto en general.
    """

    variante_id: int | None = None
    orden: int | None = Field(default=None, ge=0, le=32767)


class MarcarPrincipalIn(BaseModel):
    """Flujo alternativo 3b. Solo puede haber una principal por producto."""

    es_principal: bool


class MarcarTransparenteIn(BaseModel):
    """Flujo alternativo 3c: el PNG del vestidor virtual (supuesto S5).

    Marcar exige que la imagen este asociada a una variante y que el archivo
    tenga transparencia de verdad; las dos cosas las verifica el servicio.
    """

    es_transparente: bool


class ReordenarIn(BaseModel):
    """Flujo alternativo 3d: el nuevo orden, de una sola vez.

    Se manda la lista completa de identificadores en el orden deseado en vez de
    un par (imagen, posicion) por vez. Reordenar de a una deja estados
    intermedios con dos imagenes en la misma posicion, y si la conexion se corta
    a la mitad el orden queda a medio aplicar.
    """

    imagenes: list[int] = Field(min_length=1)
