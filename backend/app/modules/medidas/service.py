"""CU-21 · Decide que talla recomendar y como dibujar cada una.

EL PROBLEMA
-----------
El vestidor escalaba la prenda para que CALZARA el cuerpo, siempre. La XS y la
XXL se veian identicas en pantalla y el cliente elegia talla a ciegas, que es
justo lo que un probador tendria que resolver.

COMO SE RESUELVE
----------------
Con dos numeros que ya estan en la base: lo que mide el cuerpo del cliente y lo
que mide la prenda en cada talla. La razon entre los dos dice cuanto ensanchar
o angostar el dibujo, y de paso cual es la talla que le corresponde.

TODO DEGRADA A LO DE ANTES
---------------------------
Si el cliente no cargo sus medidas, o si el producto no tiene tabla de tallas
---pantalones, carteras---, la respuesta viene con `hay_medidas` o `hay_tabla`
en falso y **sin factores**. La pantalla dibuja como dibujaba siempre. Es a
proposito: una funcionalidad nueva que rompe el vestidor cuando le falta un
dato es peor que no tenerla.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.medidas import repository, tallaje
from app.modules.medidas.schemas import AjusteDeProducto, AjusteDeTalla


def _sin_ajuste(
    producto_id: int, hay_medidas: bool, hay_tabla: bool
) -> AjusteDeProducto:
    return AjusteDeProducto(
        producto_id=producto_id,
        hay_medidas=hay_medidas,
        hay_tabla=hay_tabla,
        tallas=[],
    )


def ajuste_de_producto(
    db: Session, producto_id: int, usuario_id: int
) -> AjusteDeProducto:
    tabla = repository.tabla_de_producto(db, producto_id)
    if not tabla:
        return _sin_ajuste(producto_id, hay_medidas=False, hay_tabla=False)

    cliente = repository.cliente_de_usuario(db, usuario_id)
    medidas = repository.medidas_de(db, cliente.id) if cliente else None
    if medidas is None:
        return _sin_ajuste(producto_id, hay_medidas=False, hay_tabla=True)

    busto_cuerpo = float(medidas.busto_cm)

    # La holgura de diseno de ESTA prenda. Se saca de una talla cualquiera:
    # por como se construye la tabla, la prenda y el cuerpo crecen al mismo
    # paso, asi que da lo mismo en todas.
    diseno = None
    for _, codigo, busto, *_ in tabla:
        diseno = tallaje.holgura_de_diseno(float(busto), codigo)
        if diseno is not None:
            break
    if diseno is None:
        # La tabla tiene tallas fuera de la serie conocida. No se inventa una
        # holgura: se devuelve como si no hubiera tabla.
        return _sin_ajuste(producto_id, hay_medidas=True, hay_tabla=False)

    filas: list[AjusteDeTalla] = []
    for talla_id, codigo, busto, cintura, cadera, largo in tabla:
        filas.append(
            AjusteDeTalla(
                talla_id=talla_id,
                codigo=codigo,
                busto_cm=busto,
                cintura_cm=cintura,
                cadera_cm=cadera,
                largo_cm=largo,
                ajuste=tallaje.clasificar(float(busto), busto_cuerpo, diseno),
                factor_ancho=tallaje.factor_de_ancho(
                    float(busto), busto_cuerpo, diseno
                ),
                # Se llena despues: el largo se mide CONTRA la talla
                # recomendada, que todavia no se sabe cual es.
                factor_largo=1.0,
            )
        )

    # La recomendada es la que menos se aparta de la holgura de diseno.
    #
    # Se busca por el desvio absoluto y no «la primera que entra» porque la
    # primera que entra es siempre la mas chica de las posibles: a un cuerpo
    # de 92 cm le entraria la M y tambien la XL, y recomendar la M por ser la
    # primera de la lista seria correcto por casualidad. Con el desvio, si el
    # cuerpo cae entre dos tallas gana la que de verdad queda mejor.
    ideal = busto_cuerpo + diseno
    recomendada = min(filas, key=lambda f: abs(float(f.busto_cm) - ideal))

    largo_referencia = float(recomendada.largo_cm)
    for fila in filas:
        if largo_referencia > 0:
            fila.factor_largo = max(
                tallaje.FACTOR_MINIMO,
                min(
                    tallaje.FACTOR_MAXIMO,
                    float(fila.largo_cm) / largo_referencia,
                ),
            )

    return AjusteDeProducto(
        producto_id=producto_id,
        hay_medidas=True,
        hay_tabla=True,
        talla_recomendada_id=recomendada.talla_id,
        talla_recomendada=recomendada.codigo,
        tallas=filas,
    )
