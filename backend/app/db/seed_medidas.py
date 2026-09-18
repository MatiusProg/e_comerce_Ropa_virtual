"""Siembra la tabla de tallas de las prendas de torso (CU-21).

DE DONDE SALEN ESTOS NUMEROS  ---  LEER ANTES DE DEFENDERLOS
--------------------------------------------------------------
Es una tabla de DEMOSTRACION, construida el 18/09/2026, y conviene decirlo asi
en la defensa en vez de que lo pregunten.

Se armo con lo que hay publicado:

  - **El cuerpo, de tallaje boliviano.** Nativa Denim (Bolivia) publica cintura
    y cadera por talla: XS 60-65 / 86-92, S 65-70 / 92-98, M 70-75 / 98-104,
    L 75-80 / 104-110, XL 80-85 / 110-116. Se tomaron los puntos medios.
  - **El busto no tiene dato boliviano publicado.** Se derivo manteniendo el
    paso de 5 cm de la serie y la relacion busto ~ cadera - 7, que es la que
    dan las tablas de la region (Blühen: S 80-85, M 85-90, L 95-105).
  - **SHEIN no sirve como referencia fija**, aunque sea de donde viene la
    mayoria de la ropa que se consigue hoy: no publica una tabla unica. Cada
    proveedor sube la suya por producto y dos «L» de la misma tienda pueden
    medir distinto; ademas calza 1 o 2 tallas mas chico que lo estandar. Eso
    es exactamente el motivo por el que `medida_talla` cuelga del PRODUCTO y
    no de la talla sola.

LA HOLGURA ES LO QUE CONVIERTE UN CUERPO EN UNA PRENDA
-------------------------------------------------------
`medida_talla` guarda la PRENDA, no el cuerpo. Una blusa que midiera
exactamente el busto de quien la usa no le entraria. Cuanta holgura lleva
depende de que sea: una blusa de gasa cae suelta, un abrigo tiene que pasar
por encima de la ropa de abajo. Por eso la holgura va por categoria.

Los pantalones NO se siembran. Su tabla es de otra forma --- cintura, cadera y
entrepierna, sin busto --- y el vestidor no los dibuja: el pintor pone una
prenda de torso. Sembrarles un busto inventado seria dato falso para que no
quede una columna vacia. Cuando haga falta, van con su propia tabla.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Categoria, Producto, Talla, VarianteProducto
from app.modules.medidas.models import MedidaTalla
from app.modules.medidas.tallaje import CUERPO_POR_TALLA, ORDEN

# La tabla del CUERPO y el orden de la serie viven en
# `app/modules/medidas/tallaje.py`, porque el servicio que recomienda la talla
# necesita exactamente los mismos numeros. Dos copias se separan.

#: Cuanto mas grande que el cuerpo es la prenda ---(busto, cintura, cadera) en
#: centimetros--- y el largo de hombro a ruedo en la talla M, segun QUE es la
#: prenda. Gana la primera regla cuyo texto aparezca en el nombre de la
#: categoria, sin distinguir mayusculas ni acentos.
#:
#: POR PALABRA Y NO POR NOMBRE EXACTO  ---  ESTO YA FALLO
#: ------------------------------------------------------
#: La primera version indexaba por el nombre completo de la categoria, con las
#: de la base local: «Blusas», «Casacas», «Abrigos de mujer». **En produccion
#: no coincidio ni una**: ahi las categorias se llaman «Blusas y Camisas»,
#: «Chaquetas, Abrigos y Sudaderas», «Tops y Camisetas». El sembrado escribio
#: cero filas y, como saltarse lo desconocido es deliberado, no fallo: la
#: funcionalidad simplemente no hacia nada, en silencio.
#:
#: La leccion es que **el nombre para mostrar de una categoria no es una clave**
#: --- se escribe distinto en cada base y se renombra sin avisar a nadie ---.
#: Lo estable es de que tipo de prenda se trata, y eso se lee de una palabra.
#:
#: El largo crece 2 cm por talla: una XS no es solo mas angosta, tambien es mas
#: corta, y eso es la mitad de lo que se ve en el vestidor al cambiar de talla.
REGLAS_DE_HOLGURA: tuple[tuple[tuple[str, ...], tuple[float, float, float, float]], ...] = (
    # Lo de abrigo va primero: «Chaquetas, Abrigos y Sudaderas» tambien
    # contiene palabras de otras reglas si alguna vez se renombra.
    (("abrigo", "chaqueta", "casaca", "sudadera", "parka", "campera"),
     (18.0, 20.0, 20.0, 72.0)),
    (("vestido", "pieza", "conjunto", "enterizo", "mono"),
     (6.0, 8.0, 8.0, 95.0)),
    (("descanso", "pijama", "bata", "dormir"),
     (14.0, 16.0, 16.0, 70.0)),
    (("blusa", "camisa"), (8.0, 10.0, 10.0, 62.0)),
    (("top", "camiseta", "polera", "playera"), (8.0, 10.0, 10.0, 64.0)),
)

#: Para una categoria de torso que no encaje en ninguna regla.
#:
#: Aca SI se usa un valor por omision, al reves que con la talla del cuerpo, y
#: la diferencia importa. Una talla fuera de la serie conocida no se puede
#: adivinar: inventarla seria decirle al cliente que le queda bien algo que no
#: se midio. La holgura de una prenda de torso, en cambio, cae siempre en un
#: rango estrecho, y usar un valor generico da una respuesta aproximada en vez
#: de ninguna. Es lo que evita que una categoria nueva deje el vestidor mudo.
HOLGURA_POR_OMISION = (10.0, 12.0, 12.0, 66.0)

#: Lo que se le suma al largo por cada talla por encima de la M.
PASO_DE_LARGO = 2.0


def holgura_de(categoria: str) -> tuple[float, float, float, float]:
    """La holgura que le toca a una categoria, por las palabras de su nombre."""
    nombre = categoria.casefold()
    for palabras, holgura in REGLAS_DE_HOLGURA:
        if any(palabra in nombre for palabra in palabras):
            return holgura
    return HOLGURA_POR_OMISION


def sembrar(db: Session) -> int:
    """Escribe una fila por cada (producto, talla) que exista como variante.

    Solo las que existen: sembrar tallas que ningun producto tiene llenaria la
    tabla de filas que nadie consulta y que habria que mantener al alta de cada
    producto.

    Es idempotente --- no vuelve a escribir lo que ya esta ---, porque el seed
    se corre mas de una vez sobre la misma base durante el desarrollo.
    """
    ya_estan = {
        (p, t) for p, t in db.execute(
            select(MedidaTalla.producto_id, MedidaTalla.talla_id)
        ).all()
    }

    # Las combinaciones (producto, talla) que de verdad se venden.
    combinaciones = db.execute(
        select(
            Producto.id,
            Categoria.nombre,
            Talla.id,
            Talla.codigo,
        )
        .join(Categoria, Categoria.id == Producto.categoria_id)
        .join(VarianteProducto, VarianteProducto.producto_id == Producto.id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        # En MAYUSCULAS a proposito, y no `== "Superior"`.
        #
        # La base tiene el mismo tipo escrito de dos formas: el sembrado de
        # catalogo escribe 'Superior' y el alta por la API de CU-08 lo
        # normaliza a 'SUPERIOR'. Comparando exacto, **una talla creada desde
        # el panel se quedaba sin tabla de medidas sin que nada avisara** --- y
        # el sintoma seria «esa prenda no recomienda talla», que no señala la
        # causa por ningun lado. Se descubrio el 18/09 escribiendo la prueba.
        .where(func.upper(Talla.tipo_prenda) == "SUPERIOR")
        .distinct()
    ).all()

    escritas = 0
    for producto_id, categoria, talla_id, codigo in combinaciones:
        if (producto_id, talla_id) in ya_estan:
            continue
        holgura = holgura_de(categoria)
        cuerpo = CUERPO_POR_TALLA.get(codigo)
        # Una talla fuera de la serie conocida se SALTA, no se inventa: sin
        # saber a que cuerpo corresponde, cualquier medida seria un numero
        # dicho al azar y el vestidor recomendaria sobre el. Que falte la fila
        # es visible ---dice que no hay tabla---; un numero inventado no.
        if cuerpo is None:
            continue

        d_busto, d_cintura, d_cadera, largo_m = holgura
        busto, cintura, cadera = cuerpo
        pasos = ORDEN.index(codigo) - ORDEN.index("M")

        db.add(
            MedidaTalla(
                producto_id=producto_id,
                talla_id=talla_id,
                busto_cm=Decimal(str(round(busto + d_busto, 1))),
                cintura_cm=Decimal(str(round(cintura + d_cintura, 1))),
                cadera_cm=Decimal(str(round(cadera + d_cadera, 1))),
                largo_cm=Decimal(str(round(largo_m + pasos * PASO_DE_LARGO, 1))),
            )
        )
        escritas += 1

    db.flush()
    return escritas
