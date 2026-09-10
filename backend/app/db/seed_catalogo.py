"""Datos de demostracion del Ciclo 2: organizacion y catalogo.

Tarea I2 del acuerdo del ciclo, que la contrapropuesta de Mateo paso a Karen
porque siembra sus tres tablas --- producto, variante_producto e
imagen_producto --- y asi desaparece la costura C3.

Que siembra:

  P2  5 sucursales en las 3 ciudades del Ciclo 1, y 4 proveedores
  P3  categorias jerarquicas, tallas por tipo de prenda, colores,
      2 temporadas con sus colecciones,
      ~60 productos con sus variantes talla x color,
      una imagen principal por producto y el PNG transparente del vestidor
      virtual para las variantes de los productos destacados (supuesto S5)

Es idempotente, igual que el resto del seed: se reconoce por el codigo del
producto y por el nombre de cada maestro, asi que volver a correrlo no duplica
nada. Importa porque se ejecuta contra la base desplegada.

Las imagenes NO son archivos versionados: se generan aqui con Pillow. Meter
sesenta fotos en el repositorio lo engordaria sin necesidad, y ademas las
transparentes tienen que tener transparencia DE VERDAD --- es de lo que depende
el prototipo de realidad aumentada (seccion 6.5, supuesto S5) --- y generarlas
es la forma de garantizarlo en vez de confiar en que el archivo subido este bien.

El inventario NO se siembra aqui: `existencia` y `movimiento_inventario` son
tablas de Mateo y su migracion 0003 todavia no esta en main. Ver `main()`.
"""

import random
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.catalogo.models import (
    Categoria,
    Coleccion,
    Color,
    ImagenProducto,
    Producto,
    Talla,
    Temporada,
    VarianteProducto,
)
from app.modules.catalogo.service import armar_sku
from app.modules.organizacion.models import Ciudad, Proveedor, Sucursal

#: Semilla fija: dos corridas producen exactamente el mismo catalogo. Un seed
#: que cambia en cada ejecucion vuelve imposible reproducir un defecto y hace
#: que dos personas vean numeros distintos en la misma demostracion.
AZAR = random.Random(20260910)

# --- P2 · Organizacion ---------------------------------------------------

SUCURSALES: list[tuple[str, str, str, str, int]] = [
    ("Santa Cruz de la Sierra", "Violet Centro", "Calle Libertad 245", "3-3345678", 4),
    ("Santa Cruz de la Sierra", "Violet Equipetrol", "Av. San Martin 1200", "3-3348899", 6),
    ("Santa Cruz de la Sierra", "Violet Ventura Mall", "Av. Banzer km 8", "3-3421100", 8),
    ("La Paz", "Violet Sopocachi", "Av. 20 de Octubre 2033", "2-2415566", 4),
    ("Cochabamba", "Violet El Prado", "Av. Ballivian 780", "4-4258899", 5),
]

PROVEEDORES: list[tuple[str, str, str, str]] = [
    ("Textiles del Oriente S.R.L.", "1023456789", "Marcela Áñez", "ventas@textilesoriente.bo"),
    ("Confecciones Andinas Ltda.", "2098765432", "Rubén Quispe", "contacto@confandinas.bo"),
    ("Importadora Vestir S.A.", "3011223344", "Lucía Melgar", "compras@vestir.com.bo"),
    ("Denim Bolivia S.R.L.", "4055667788", "Iván Rojas", "info@denimbolivia.bo"),
]

# --- P3 · Maestros del catalogo -----------------------------------------

#: (categoria raiz, subcategorias). La jerarquia importa: el filtro del catalogo
#: y las categorias preferidas del perfil (CU-04) cuelgan de ella.
CATEGORIAS: list[tuple[str, list[str]]] = [
    ("Mujer", ["Blusas", "Vestidos", "Pantalones de mujer", "Abrigos de mujer"]),
    ("Hombre", ["Camisas", "Poleras", "Pantalones de hombre", "Casacas"]),
    ("Accesorios", ["Carteras", "Cinturones"]),
]

#: (tipo de prenda, codigos en orden). El orden es el que decide como se
#: muestran en la ficha: sin el, XL sale antes que S por orden alfabetico.
TALLAS: list[tuple[str, list[str]]] = [
    ("Superior", ["XS", "S", "M", "L", "XL"]),
    ("Inferior", ["36", "38", "40", "42", "44"]),
    ("Unica", ["U"]),
]

COLORES: list[tuple[str, str]] = [
    ("Negro", "#1A1A1A"),
    ("Blanco", "#FAFAFA"),
    ("Malva", "#8E6C88"),
    ("Oro rosa", "#B76E79"),
    ("Azul marino", "#1F3A5F"),
    ("Verde militar", "#4B5320"),
    ("Beige", "#D8C3A5"),
    ("Rojo vino", "#722F37"),
]

TEMPORADAS: list[tuple[str, str, str, list[str]]] = [
    ("Primavera-Verano 2026", "2026-09-01", "2027-02-28", ["Fiesta", "Playa", "Urbano"]),
    ("Otoño-Invierno 2026", "2026-03-01", "2026-08-31", ["Abrigo", "Oficina"]),
]

#: (subcategoria, tipo de prenda, prefijo del codigo, nombres de los modelos,
#:  precio minimo, precio maximo)
#:
#: El prefijo se mantiene corto a proposito: el SKU es CODIGO-TALLA-COLOR y no
#: se trunca, asi que un codigo largo dejaria sin lugar al nombre del color.
MODELOS: list[tuple[str, str, str, list[str], int, int]] = [
    ("Blusas", "Superior", "BLU", [
        "Blusa de seda manga larga", "Blusa cruzada", "Blusa con lazo",
        "Blusa de gasa", "Blusa oversize", "Blusa de encaje", "Blusa sin mangas",
    ], 180, 340),
    ("Vestidos", "Superior", "VES", [
        "Vestido midi plisado", "Vestido camisero", "Vestido de fiesta",
        "Vestido de verano", "Vestido tejido", "Vestido envolvente",
        "Vestido largo de gala",
    ], 320, 690),
    ("Pantalones de mujer", "Inferior", "PMU", [
        "Pantalón palazzo", "Jean skinny", "Pantalón de vestir", "Jean mom fit",
        "Pantalón capri", "Jean wide leg",
    ], 260, 480),
    ("Abrigos de mujer", "Superior", "ABM", [
        "Abrigo de paño", "Trench clásico", "Chaqueta acolchada",
        "Abrigo largo cruzado", "Chaleco de lana",
    ], 520, 980),
    ("Camisas", "Superior", "CAM", [
        "Camisa Oxford manga larga", "Camisa de lino", "Camisa a cuadros",
        "Camisa slim fit", "Camisa denim", "Camisa de vestir blanca",
        "Camisa manga corta",
    ], 220, 420),
    ("Poleras", "Superior", "POL", [
        "Polera básica", "Polera estampada", "Polera de algodón peinado",
        "Polera manga larga", "Polera con cuello", "Polera deportiva",
    ], 110, 220),
    ("Pantalones de hombre", "Inferior", "PHO", [
        "Jean recto", "Pantalón chino", "Pantalón cargo", "Jogger de gabardina",
        "Jean slim", "Pantalón de vestir a medida",
    ], 240, 460),
    ("Casacas", "Superior", "CAS", [
        "Casaca de cuero sintético", "Casaca bomber", "Casaca rompeviento",
        "Casaca de mezclilla", "Parka con capucha",
    ], 480, 890),
    ("Carteras", "Unica", "CAR", [
        "Cartera de mano", "Bolso tote", "Bandolera pequeña",
        "Mochila urbana", "Cartera de fiesta",
    ], 190, 520),
    ("Cinturones", "Unica", "CIN", [
        "Cinturón de cuero", "Cinturón trenzado", "Cinturón de hebilla ancha",
        "Cinturón reversible",
    ], 90, 180),
]

#: Cuantos productos de cada categoria llevan el PNG transparente del vestidor.
#: Son prendas de torso: el prototipo calcula hombros y caderas, asi que una
#: cartera o un cinturon no tienen nada que superponer.
CATEGORIAS_CON_VESTIDOR = {"Blusas", "Vestidos", "Camisas", "Poleras", "Casacas"}


# --- Generacion de imagenes ---------------------------------------------

def _png_de_producto(color_hex: str, etiqueta: str) -> bytes:
    """La foto de catalogo: un rectangulo con el color de la prenda.

    No pretende parecer una fotografia. Sirve para que la vitrina, la ficha y la
    galeria tengan algo que dibujar y para que se vea de un vistazo que cada
    variante es de un color distinto.
    """
    imagen = Image.new("RGB", (600, 750), "#F5F1F4")
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rectangle([80, 90, 520, 660], fill=color_hex)
    dibujo.text((80, 690), etiqueta[:44], fill="#3A2E38")
    buffer = BytesIO()
    imagen.save(buffer, format="JPEG", quality=82)
    return buffer.getvalue()


def _png_transparente_de_variante(color_hex: str) -> bytes:
    """La silueta recortada que consume el vestidor virtual (supuesto S5).

    Tiene transparencia DE VERDAD: el fondo queda en alfa 0 y solo la silueta
    es opaca. Es exactamente lo que CU-11 exige para poder marcarla, y lo que el
    prototipo de realidad aumentada necesita para no superponer un rectangulo
    sobre el torso.
    """
    imagen = Image.new("RGBA", (600, 750), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    # Un torso muy esquematico: tronco mas dos mangas.
    dibujo.polygon(
        [(190, 150), (410, 150), (455, 250), (410, 285), (410, 640),
         (190, 640), (190, 285), (145, 250)],
        fill=color_hex,
    )
    buffer = BytesIO()
    imagen.save(buffer, format="PNG")
    return buffer.getvalue()


def _escribir(contenido: bytes, producto_id: int, nombre: str) -> str:
    """Escribe en el volumen y devuelve la ruta relativa que va a la base.

    Se usa un nombre deterministico --- y no el aleatorio de CU-11 --- para que
    volver a correr el seed sobrescriba el mismo archivo en vez de dejar una
    copia nueva por corrida.
    """
    relativa = Path("productos") / str(producto_id) / nombre
    destino = Path(settings.MEDIA_ROOT) / relativa
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return relativa.as_posix()


# --- Siembra -------------------------------------------------------------

def _sucursales(db: Session) -> None:
    ciudades = {c.nombre: c.id for c in db.scalars(select(Ciudad))}
    existentes = {s.nombre for s in db.scalars(select(Sucursal))}
    from datetime import time

    for ciudad, nombre, direccion, telefono, vestidores in SUCURSALES:
        if nombre in existentes or ciudad not in ciudades:
            continue
        db.add(
            Sucursal(
                ciudad_id=ciudades[ciudad],
                nombre=nombre,
                direccion=direccion,
                telefono=telefono,
                horario_apertura=time(9, 0),
                horario_cierre=time(21, 0),
                capacidad_vestidores=vestidores,
            )
        )
        print(f"  + sucursal {nombre}")
    db.flush()


def _proveedores(db: Session) -> list[int]:
    existentes = {p.razon_social: p for p in db.scalars(select(Proveedor))}
    for razon, nit, contacto, correo in PROVEEDORES:
        if razon in existentes:
            continue
        proveedor = Proveedor(
            razon_social=razon,
            identificacion_tributaria=nit,
            contacto=contacto,
            correo=correo,
        )
        db.add(proveedor)
        existentes[razon] = proveedor
        print(f"  + proveedor {razon}")
    db.flush()
    return [p.id for p in existentes.values()]


def _maestros(db: Session) -> tuple[dict[str, int], dict[str, list[Talla]], list[Color]]:
    # Categorias, con su jerarquia.
    por_nombre = {c.nombre: c for c in db.scalars(select(Categoria))}
    for orden, (raiz, hijas) in enumerate(CATEGORIAS):
        if raiz not in por_nombre:
            padre = Categoria(nombre=raiz, orden=orden)
            db.add(padre)
            por_nombre[raiz] = padre
            print(f"  + categoria {raiz}")
        db.flush()
        for posicion, hija in enumerate(hijas):
            if hija not in por_nombre:
                nodo = Categoria(
                    nombre=hija, categoria_padre_id=por_nombre[raiz].id, orden=posicion
                )
                db.add(nodo)
                por_nombre[hija] = nodo
                print(f"  + categoria {raiz} / {hija}")
    db.flush()

    # Tallas, agrupadas por tipo de prenda.
    existentes = {(t.tipo_prenda, t.codigo): t for t in db.scalars(select(Talla))}
    for tipo, codigos in TALLAS:
        for orden, codigo in enumerate(codigos):
            if (tipo, codigo) not in existentes:
                talla = Talla(tipo_prenda=tipo, codigo=codigo, orden=orden)
                db.add(talla)
                existentes[(tipo, codigo)] = talla
    db.flush()
    por_tipo: dict[str, list[Talla]] = {}
    for (tipo, _), talla in existentes.items():
        por_tipo.setdefault(tipo, []).append(talla)
    for lista in por_tipo.values():
        lista.sort(key=lambda t: t.orden)

    # Colores.
    colores = {c.nombre: c for c in db.scalars(select(Color))}
    for nombre, hexadecimal in COLORES:
        if nombre not in colores:
            color = Color(nombre=nombre, hexadecimal=hexadecimal)
            db.add(color)
            colores[nombre] = color
    db.flush()

    return (
        {n: c.id for n, c in por_nombre.items()},
        por_tipo,
        [colores[n] for n, _ in COLORES],
    )


def _temporadas(db: Session) -> list[int]:
    from datetime import date

    existentes = {t.nombre: t for t in db.scalars(select(Temporada))}
    colecciones_ids: list[int] = []
    for nombre, desde, hasta, colecciones in TEMPORADAS:
        if nombre not in existentes:
            temporada = Temporada(
                nombre=nombre,
                fecha_inicio=date.fromisoformat(desde),
                fecha_fin=date.fromisoformat(hasta),
            )
            db.add(temporada)
            existentes[nombre] = temporada
            print(f"  + temporada {nombre}")
        db.flush()
        ya = {
            c.nombre
            for c in db.scalars(
                select(Coleccion).where(Coleccion.temporada_id == existentes[nombre].id)
            )
        }
        for titulo in colecciones:
            if titulo in ya:
                continue
            coleccion = Coleccion(temporada_id=existentes[nombre].id, nombre=titulo)
            db.add(coleccion)
        db.flush()

    colecciones_ids = [c.id for c in db.scalars(select(Coleccion))]
    return colecciones_ids


def _productos(
    db: Session,
    categorias: dict[str, int],
    tallas: dict[str, list[Talla]],
    colores: list[Color],
    proveedores: list[int],
    colecciones: list[int],
) -> int:
    """Los ~60 productos con sus variantes. Devuelve cuantos creo."""
    ya_estan = {p.codigo for p in db.scalars(select(Producto))}
    creados = 0

    for subcategoria, tipo_prenda, prefijo, modelos, minimo, maximo in MODELOS:
        categoria_id = categorias.get(subcategoria)
        if categoria_id is None:
            continue
        for indice, nombre in enumerate(modelos, start=1):
            codigo = f"{prefijo}-{indice:03d}"
            if codigo in ya_estan:
                continue

            coleccion_id = AZAR.choice(colecciones) if colecciones else None
            # La temporada NO se pasa: el servicio la completa a partir de la
            # coleccion. Es la regla de la seccion 6.4, decision 2, y sembrar
            # las dos a mano seria la forma mas facil de contradecirlas.
            coleccion = db.get(Coleccion, coleccion_id) if coleccion_id else None

            producto = Producto(
                codigo=codigo,
                nombre=nombre,
                descripcion=f"{nombre}. Confeccion nacional, linea {subcategoria.lower()}.",
                categoria_id=categoria_id,
                proveedor_id=AZAR.choice(proveedores) if proveedores else None,
                temporada_id=coleccion.temporada_id if coleccion else None,
                coleccion_id=coleccion_id,
                precio_base=Decimal(AZAR.randrange(minimo, maximo, 10)),
            )
            db.add(producto)
            db.flush()
            creados += 1

            # Variantes: todas las tallas del tipo, por dos o tres colores.
            paleta = AZAR.sample(colores, k=AZAR.choice([2, 3]))
            for talla in tallas.get(tipo_prenda, []):
                for color in paleta:
                    db.add(
                        VarianteProducto(
                            producto_id=producto.id,
                            talla_id=talla.id,
                            color_id=color.id,
                            sku=armar_sku(codigo, talla.codigo, color.nombre),
                            precio=producto.precio_base,
                        )
                    )
            db.flush()

            _imagenes_de(db, producto, subcategoria, paleta)

    return creados


def _imagenes_de(
    db: Session, producto: Producto, subcategoria: str, paleta: list[Color]
) -> None:
    """Una imagen principal del producto y, si corresponde, los PNG del vestidor.

    El transparente va por VARIANTE, no por producto: el indice parcial
    uq_imagen_transparente_variante admite uno solo por variante, y el vestidor
    superpone la prenda de una combinacion concreta de talla y color.
    """
    principal = _escribir(
        _png_de_producto(paleta[0].hexadecimal, producto.nombre),
        producto.id,
        "principal.jpg",
    )
    db.add(
        ImagenProducto(
            producto_id=producto.id,
            ruta=principal,
            es_principal=True,
            orden=0,
        )
    )

    if subcategoria not in CATEGORIAS_CON_VESTIDOR:
        return

    # Una variante por color de la paleta, en la talla intermedia: alcanza para
    # que el prototipo tenga con que probar y no llena el volumen de PNG.
    variantes = list(
        db.scalars(
            select(VarianteProducto).where(VarianteProducto.producto_id == producto.id)
        )
    )
    if not variantes:
        return
    por_color: dict[int, VarianteProducto] = {}
    for variante in variantes:
        por_color.setdefault(variante.color_id, variante)

    for orden, (color_id, variante) in enumerate(por_color.items(), start=1):
        color = db.get(Color, color_id)
        ruta = _escribir(
            _png_transparente_de_variante(color.hexadecimal),
            producto.id,
            f"vestidor-{variante.id}.png",
        )
        db.add(
            ImagenProducto(
                producto_id=producto.id,
                variante_id=variante.id,
                ruta=ruta,
                es_principal=False,
                es_transparente=True,
                orden=orden,
            )
        )


def sembrar(db: Session) -> None:
    """Siembra la organizacion y el catalogo del Ciclo 2."""
    print("Sembrando organizacion y catalogo del Ciclo 2...")
    _sucursales(db)
    proveedores = _proveedores(db)
    categorias, tallas, colores = _maestros(db)
    colecciones = _temporadas(db)
    creados = _productos(db, categorias, tallas, colores, proveedores, colecciones)

    total_productos = db.scalar(select(Producto.id).order_by(Producto.id.desc()))
    print(f"  productos nuevos: {creados}")
    if total_productos is None:
        print("  ! no se sembro ningun producto")
    print(
        "  ! el inventario NO se siembra aqui: `existencia` y "
        "`movimiento_inventario` son de Mateo (migracion 0003) y todavia no "
        "estan en main. Cuando lo esten, se agrega su bloque."
    )
