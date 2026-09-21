"""Genera el fragmento de datos del 3.3.1 del Ciclo 3: EL SISTEMA ENTERO.

A diferencia del Ciclo 2 ---que dibujaba sus ocho tablas nuevas mas las de
apoyo a las que apuntaban---, este lleva **las 43 tablas**. Es el modelo de
datos completo al cerrar el proyecto, y por eso no hay lista de «nuevas» y
«de apoyo»: se leen todas las tablas base del esquema.

EL CONTENIDO NO SE TRANSCRIBE A MANO. Las columnas, sus tipos y los
estereotipos PK/FK salen de `information_schema`; las cardinalidades salen de
lo que la base OBLIGA ---NOT NULL y UNIQUE---, no de la prosa.

DE DONDE SE LEE
---------------
De la **base de pruebas**, que `alembic upgrade head` deja al dia, igual que
gen-ops-2-3-ciclo3.py. El generador del Ciclo 2 usaba una `vb_dominio` en el
puerto 5433 que hay que construir aparte; siendo la misma cadena de
migraciones, los tipos son identicos y no hay por que mantener una segunda
base solo para dibujar.

**Solo lectura**: consulta `information_schema` y nada mas.
"""
import io
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "backend"))

from sqlalchemy import create_engine, text  # noqa: E402

url = os.environ.get("TEST_DATABASE_URL")
if not url:
    raise SystemExit(
        "Falta TEST_DATABASE_URL. Corre:  set -a && . backend/.env.test && set +a"
    )
motor = create_engine(url)

#: `alembic_version` es contabilidad de la herramienta, no del dominio.
EXCLUIR = {"alembic_version"}

TIPO = """CASE
    WHEN c.column_default LIKE 'nextval' || '%' AND c.data_type = 'integer' THEN 'SERIAL'
    WHEN c.column_default LIKE 'nextval' || '%' AND c.data_type = 'bigint'  THEN 'BIGSERIAL'
    WHEN c.data_type = 'character varying' THEN 'VARCHAR(' || c.character_maximum_length || ')'
    WHEN c.data_type = 'numeric' THEN 'NUMERIC(' || c.numeric_precision || ',' || c.numeric_scale || ')'
    WHEN c.data_type = 'timestamp with time zone' THEN 'TIMESTAMPTZ'
    WHEN c.data_type = 'time without time zone' THEN 'TIME'
    WHEN c.data_type = 'integer' THEN 'INTEGER'
    WHEN c.data_type = 'bigint' THEN 'BIGINT'
    WHEN c.data_type = 'smallint' THEN 'SMALLINT'
    WHEN c.data_type = 'boolean' THEN 'BOOLEAN'
    WHEN c.data_type = 'date' THEN 'DATE'
    WHEN c.data_type = 'text' THEN 'TEXT'
    ELSE upper(c.data_type) END"""

with motor.connect() as con:
    tablas = [t for t in con.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name"
    )).scalars().all() if t not in EXCLUIR]

    columnas = {}
    for tabla, col, tipo in con.execute(text(
            "SELECT c.table_name, c.column_name, %s AS tipo "
            "FROM information_schema.columns c "
            "WHERE c.table_schema='public' "
            "ORDER BY c.table_name, c.ordinal_position" % TIPO)).all():
        if tabla in EXCLUIR:
            continue
        columnas.setdefault(tabla, []).append((col, tipo))

    # PK y FK por columna. Una columna puede ser las dos ---la clave compuesta
    # de una tabla puente--- y entonces el estereotipo va 'PK,FK'.
    claves = {}
    for tabla, col, clase in con.execute(text(
            "SELECT tc.table_name, kcu.column_name, tc.constraint_type "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "  ON kcu.constraint_name = tc.constraint_name "
            " AND kcu.table_schema = tc.table_schema "
            "WHERE tc.table_schema='public' "
            "  AND tc.constraint_type IN ('PRIMARY KEY','FOREIGN KEY')")).all():
        claves.setdefault((tabla, col), set()).add(
            "PK" if clase == "PRIMARY KEY" else "FK")

    # EL UNIQUE COMPUESTO NO HACE UNICA A CADA UNA DE SUS COLUMNAS.
    # `variante_producto` tiene UNIQUE(producto_id, talla_id, color_id): leido
    # columna por columna, `producto_id` pareceria unico y el modelo terminaria
    # diciendo que un producto tiene A LO SUMO UNA variante ---exactamente al
    # reves de la decision D1---. Por eso se agrupa por restriccion y se
    # descartan las de mas de una columna. No da error: se detecta leyendo las
    # cardinalidades una por una.
    unicas = set()
    for tabla, columna, cuantas in con.execute(text(
            "SELECT tc.table_name, MIN(kcu.column_name), COUNT(kcu.column_name) "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "  ON kcu.constraint_name = tc.constraint_name "
            "WHERE tc.table_schema='public' AND tc.constraint_type = 'UNIQUE' "
            "GROUP BY tc.table_name, tc.constraint_name")).all():
        if int(cuantas) == 1:
            unicas.add((tabla, columna))

    nulables = {(t, c): (n == "YES") for t, c, n in con.execute(text(
        "SELECT table_name, column_name, is_nullable FROM information_schema.columns "
        "WHERE table_schema='public'")).all()}

    fks = con.execute(text(
        "SELECT ccu.table_name AS destino, tc.table_name AS origen, kcu.column_name "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu "
        "  ON kcu.constraint_name = tc.constraint_name "
        "JOIN information_schema.constraint_column_usage ccu "
        "  ON ccu.constraint_name = tc.constraint_name "
        "WHERE tc.table_schema='public' AND tc.constraint_type = 'FOREIGN KEY' "
        "ORDER BY ccu.table_name, tc.table_name")).all()

# --- los verbos, escritos a mano porque la base no los tiene ----------------
# Se leen DESTINO -> ORIGEN: ('categoria','producto') se lee
# «CATEGORIA CLASIFICA PRODUCTO».
VERBOS = {
    # Seguridad y usuarios
    ("rol", "usuario"): "DEFINE",
    ("rol", "rol_permiso"): "SE_HABILITA_EN",
    ("permiso", "rol_permiso"): "SE_OTORGA_EN",
    ("usuario", "sesion_token"): "INICIA_SESION_EN",
    ("usuario", "token_recuperacion"): "RECUPERA_CON",
    ("usuario", "cliente"): "ES",
    ("usuario", "empleado"): "ES_EMPLEADO",
    ("usuario", "proveedor"): "PUEDE_SER",
    ("usuario", "bitacora"): "SE_AUDITA_EN",
    ("usuario", "movimiento_inventario"): "ORIGINA",
    ("usuario", "turno_caja"): "ABRE",
    ("cliente", "direccion_cliente"): "REGISTRA",
    ("cliente", "cliente_categoria"): "PREFIERE_EN",
    ("cliente", "medida_cliente"): "SE_MIDE_EN",
    # Organizacion
    ("ciudad", "sucursal"): "ALOJA",
    ("ciudad", "direccion_cliente"): "UBICA",
    ("sucursal", "empleado"): "EMPLEA_A",
    ("sucursal", "existencia"): "ALBERGA",
    ("sucursal", "reserva"): "ATIENDE",
    ("sucursal", "venta"): "VENDE_EN",
    ("sucursal", "caja"): "TIENE_CAJA",
    # Catalogo
    ("categoria", "categoria"): "SE_SUBDIVIDE_EN",
    ("categoria", "producto"): "CLASIFICA",
    ("categoria", "cliente_categoria"): "SE_PREFIERE_EN",
    ("categoria", "promocion"): "AGRUPA_PROMOCION",
    ("proveedor", "producto"): "ABASTECE",
    ("proveedor", "movimiento_inventario"): "ABASTECE_EN",
    ("proveedor", "abastecimiento"): "ANUNCIA_EN",
    ("temporada", "coleccion"): "CONTIENE",
    ("temporada", "producto"): "ENMARCA",
    ("temporada", "promocion"): "ENMARCA_PROMOCION",
    ("coleccion", "producto"): "AGRUPA",
    ("talla", "variante_producto"): "DIMENSIONA",
    ("talla", "medida_talla"): "DIMENSIONA_EN",
    ("color", "variante_producto"): "TINE",
    ("producto", "variante_producto"): "SE_OFRECE_COMO",
    ("producto", "imagen_producto"): "SE_ILUSTRA_CON",
    ("producto", "medida_talla"): "SE_TABULA_EN",
    ("producto", "promocion"): "SE_PROMOCIONA_EN",
    ("producto", "favorito"): "SE_MARCA_EN",
    ("variante_producto", "imagen_producto"): "SE_MUESTRA_EN",
    ("variante_producto", "existencia"): "SE_ALMACENA_EN",
    ("variante_producto", "reserva_detalle"): "SE_APARTA_EN",
    ("variante_producto", "carrito_detalle"): "SE_AGREGA_EN",
    ("variante_producto", "detalle_venta"): "SE_VENDE_EN",
    ("variante_producto", "detalle_devolucion"): "SE_DEVUELVE_EN",
    ("variante_producto", "abastecimiento"): "SE_REPONE_EN",
    # Inventario
    ("existencia", "movimiento_inventario"): "SE_EXPLICA_POR",
    # Reservas
    ("cliente", "reserva"): "REALIZA",
    ("reserva", "reserva_detalle"): "SE_DETALLA_EN",
    ("reserva", "venta"): "SE_CONCRETA_EN",
    # Ventas y pagos
    ("cliente", "carrito"): "TIENE",
    ("carrito", "carrito_detalle"): "SE_DESGLOSA_EN",
    ("cliente", "favorito"): "MARCA_EN",
    ("cliente", "venta"): "COMPRA_EN",
    ("direccion_cliente", "venta"): "ES_DESTINO_DE",
    ("venta", "detalle_venta"): "SE_DETALLA_EN",
    ("venta", "pago"): "SE_SALDA_CON",
    ("pago", "transaccion_pasarela"): "SE_NOTIFICA_EN",
    ("venta", "comprobante"): "SE_ACREDITA_CON",
    # Caja y punto de venta
    ("caja", "turno_caja"): "REGISTRA",
    ("turno_caja", "venta"): "REGISTRA_VENTA",
    ("turno_caja", "devolucion"): "REGISTRA_DEVOLUCION",
    ("venta", "devolucion"): "SE_REVIERTE_EN",
    ("devolucion", "detalle_devolucion"): "SE_DESGLOSA_EN",
    # IA
    ("cliente", "recomendacion"): "RECIBE",
}

relaciones, faltan = [], []
for destino, origen, col in fks:
    if destino in EXCLUIR or origen in EXCLUIR:
        continue
    verbo = VERBOS.get((destino, origen))
    if not verbo:
        faltan.append("%s -> %s (%s.%s)" % (destino, origen, origen, col))
        continue
    # Del lado del que apunta: 0..1 solo si la columna es UNIQUE de UNA columna.
    cd = "0..1" if (origen, col) in unicas else "0..*"
    # Del lado apuntado: 1 si la columna es NOT NULL, 0..1 si admite nulo.
    co = "0..1" if nulables.get((origen, col), True) else "1"
    relaciones.append((destino, origen, co, cd))

lineas = [
    "# GENERADO por scripts/gen-dominio-3-3-1-ciclo3.py --- NO editar a mano.",
    "# El sistema ENTERO: las 43 tablas. Las columnas, sus tipos y los",
    "# estereotipos PK/FK salen de information_schema de la base de pruebas, que",
    "# `alembic upgrade head` deja al dia. Las cardinalidades salen de lo que la",
    "# base OBLIGA --- NOT NULL y UNIQUE ---, no de la prosa.",
    "",
    "$TABLAS_C3 = @(",
]
for tabla in tablas:
    cols = []
    for col, tipo in columnas.get(tabla, []):
        marcas = claves.get((tabla, col), set())
        k = ",".join(sorted(marcas, reverse=True)) if marcas else None
        cols.append("       @{n='%s'; t='%s'%s}" % (
            col, tipo, ("; k='%s'" % k) if k else ""))
    lineas.append("  @{ n='%s'\n     cols=@(\n%s\n     ) }," % (
        tabla.upper(), ",\n".join(cols)))
lineas[-1] = lineas[-1].rstrip(",")
lineas += [")", "", "$RELACIONES_C3 = @("]
lineas.append(",\n".join(
    "  @{ o='%s'; v='%s'; d='%s'; co='%s'; cd='%s' }" % (
        destino.upper(), VERBOS[(destino, origen)], origen.upper(), co, cd)
    for destino, origen, co, cd in relaciones))
lineas.append(")")

destino_archivo = os.path.join(RAIZ, "scripts", "ea-datos-3-3-1-ciclo3.datos.ps1")
io.open(destino_archivo, "w", encoding="utf-8-sig", newline="").write(
    "\n".join(lineas) + "\n")

print("escrito", destino_archivo)
print("  tablas    :", len(tablas))
print("  columnas  :", sum(len(v) for v in columnas.values()))
print("  relaciones:", len(relaciones), "de", len(fks), "claves foraneas")
if faltan:
    print("\nSIN VERBO (hay que agregarlo a VERBOS):")
    for f in faltan:
        print("  -", f)
    raise SystemExit(1)
print("\nTodas las relaciones tienen su verbo.")
