"""Genera el fragmento de datos del 3.3.1 del Ciclo 2.

El contenido NO se transcribe a mano: sale de `information_schema` de la base
construida con las migraciones, que es la misma regla que ya seguia el del
Ciclo 1. Emite las columnas con su tipo y su estereotipo PK/FK, y las
relaciones con la cardinalidad que la base realmente obliga.
"""
import io
import subprocess

URL = "postgresql://postgres:291022@localhost:5433/vb_dominio"
PSQL = r"C:\Program Files\PostgreSQL\18\bin\psql.exe"


def consultar(sql):
    salida = subprocess.run([PSQL, URL, "-At", "-F", "|", "-c", sql],
                            capture_output=True, text=True, encoding="utf-8").stdout
    return [ln.split("|") for ln in salida.strip().split("\n") if ln.strip()]


# Las ocho del Ciclo 2, y las del Ciclo 1 a las que apuntan sus claves foraneas:
# sin ellas las relaciones quedarian colgando.
NUEVAS = ["producto", "variante_producto", "imagen_producto", "existencia",
          "movimiento_inventario", "reserva", "reserva_detalle", "cliente_categoria"]
APOYO = ["categoria", "proveedor", "temporada", "coleccion", "talla", "color",
         "sucursal", "cliente", "usuario"]
TABLAS = NUEVAS + APOYO
LISTA = ", ".join("'%s'" % t for t in TABLAS)

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

columnas = {}
for tabla, pos, col, tipo in consultar(
        "SELECT c.table_name, c.ordinal_position, c.column_name, %s "
        "FROM information_schema.columns c "
        "WHERE c.table_schema='public' AND c.table_name IN (%s) "
        "ORDER BY c.table_name, c.ordinal_position" % (TIPO, LISTA)):
    columnas.setdefault(tabla, []).append((col, tipo))

# PK y FK por columna. Una columna puede ser las dos --- la clave compuesta de
# una tabla puente ---, y entonces el estereotipo va 'PK,FK'.
claves = {}
for tabla, col, clase in consultar(
        "SELECT tc.table_name, kcu.column_name, tc.constraint_type "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu "
        "  ON kcu.constraint_name = tc.constraint_name "
        " AND kcu.table_schema = tc.table_schema "
        "WHERE tc.table_schema='public' AND tc.table_name IN (%s) "
        "  AND tc.constraint_type IN ('PRIMARY KEY','FOREIGN KEY')" % LISTA):
    marca = "PK" if clase == "PRIMARY KEY" else "FK"
    claves.setdefault((tabla, col), set()).add(marca)

# Las relaciones, con la cardinalidad que la base obliga: el lado del que
# apunta es 0..* salvo que la columna sea UNIQUE, y 1 o 0..1 segun sea NOT NULL.
# OJO: solo cuenta el UNIQUE de UNA columna. `variante_producto` tiene
# UNIQUE(producto_id, talla_id, color_id) --- compuesto ---, y tomar cada
# columna por separado diria que un producto tiene a lo sumo UNA variante,
# que es exactamente al reves de lo que el modelo afirma. Por eso se agrupa
# por restriccion y se descartan las que tienen mas de una columna.
unicas = set()
for tabla, columna, cuantas in consultar(
        "SELECT tc.table_name, MIN(kcu.column_name), COUNT(kcu.column_name) "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu "
        "  ON kcu.constraint_name = tc.constraint_name "
        "WHERE tc.table_schema='public' AND tc.constraint_type = 'UNIQUE' "
        "  AND tc.table_name IN (%s) "
        "GROUP BY tc.table_name, tc.constraint_name" % LISTA):
    if int(cuantas) == 1:
        unicas.add((tabla, columna))

nulables = {(t, c): (n == "YES") for t, c, n in consultar(
    "SELECT table_name, column_name, is_nullable FROM information_schema.columns "
    "WHERE table_schema='public' AND table_name IN (%s)" % LISTA)}

relaciones = []
for origen, col, destino in consultar(
        "SELECT tc.table_name, kcu.column_name, ccu.table_name "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu "
        "  ON kcu.constraint_name = tc.constraint_name "
        "JOIN information_schema.constraint_column_usage ccu "
        "  ON ccu.constraint_name = tc.constraint_name "
        "WHERE tc.table_schema='public' AND tc.constraint_type = 'FOREIGN KEY' "
        "  AND tc.table_name IN (%s) ORDER BY tc.table_name, kcu.column_name" % LISTA):
    if destino not in TABLAS:
        continue
    # cardinalidad del lado del que apunta
    if (origen, col) in unicas:
        cd = "0..1"
    else:
        cd = "0..*"
    # del lado apuntado
    co = "0..1" if nulables.get((origen, col), True) else "1"
    relaciones.append((destino, origen, col, co, cd))

# --- verbos, escritos a mano porque la base no los tiene -------------------
VERBOS = {
    ("categoria", "producto"): "CLASIFICA",
    ("proveedor", "producto"): "ABASTECE",
    ("temporada", "producto"): "ENMARCA",
    ("coleccion", "producto"): "AGRUPA",
    ("producto", "variante_producto"): "SE_OFRECE_COMO",
    ("talla", "variante_producto"): "DIMENSIONA",
    ("color", "variante_producto"): "TINE",
    ("producto", "imagen_producto"): "SE_ILUSTRA_CON",
    ("variante_producto", "imagen_producto"): "SE_MUESTRA_EN",
    ("variante_producto", "existencia"): "SE_ALMACENA_EN",
    ("sucursal", "existencia"): "ALBERGA",
    ("existencia", "movimiento_inventario"): "SE_EXPLICA_POR",
    ("usuario", "movimiento_inventario"): "ORIGINA",
    ("proveedor", "movimiento_inventario"): "ABASTECE_EN",
    ("cliente", "reserva"): "REALIZA",
    ("sucursal", "reserva"): "ATIENDE",
    ("reserva", "reserva_detalle"): "SE_DETALLA_EN",
    ("variante_producto", "reserva_detalle"): "SE_APARTA_EN",
    ("cliente", "cliente_categoria"): "PREFIERE_EN",
    ("categoria", "cliente_categoria"): "SE_PREFIERE_EN",
    ("temporada", "coleccion"): "CONTIENE",
    ("categoria", "categoria"): "SE_SUBDIVIDE_EN",
    ("usuario", "cliente"): "ES",
    ("usuario", "proveedor"): "PUEDE_SER",
    ("ciudad", "sucursal"): "ALOJA",
}

lineas = [
    "# GENERADO por scripts/gen-dominio-3-3-1.py --- NO editar a mano.",
    "# Las columnas, sus tipos y los estereotipos PK/FK salen de information_schema",
    "# de la base construida con las migraciones. Las cardinalidades salen de lo",
    "# que la base OBLIGA --- NOT NULL y UNIQUE ---, no de la prosa.",
    "",
    "$TABLAS_C2 = @(",
]
faltan = []
for tabla in TABLAS:
    cols = []
    for col, tipo in columnas.get(tabla, []):
        marcas = claves.get((tabla, col), set())
        k = ",".join(sorted(marcas, reverse=True)) if marcas else None
        if k:
            cols.append("       @{n='%s'; t='%s'; k='%s'}" % (col, tipo, k))
        else:
            cols.append("       @{n='%s'; t='%s'}" % (col, tipo))
    lineas.append("  @{ n='%s'; nuevo=$%s\n     cols=@(\n%s\n     ) }," % (
        tabla.upper(), "true" if tabla in NUEVAS else "false", ",\n".join(cols)))
lineas[-1] = lineas[-1].rstrip(",")
lineas.append(")")
lineas.append("")
lineas.append("$RELACIONES_C2 = @(")
filas = []
for destino, origen, col, co, cd in relaciones:
    verbo = VERBOS.get((destino, origen))
    if not verbo:
        faltan.append("%s -> %s (%s)" % (destino, origen, col))
        continue
    filas.append("  @{ o='%s'; v='%s'; d='%s'; co='%s'; cd='%s' }" % (
        destino.upper(), verbo, origen.upper(), co, cd))
lineas.append(",\n".join(filas))
lineas.append(")")

io.open(r"D:\UNI\Si2\PRIMER_PARCIAL\scripts\ea-datos-3-3-1-ciclo2.datos.ps1", "w",
        encoding="utf-8-sig", newline="").write("\n".join(lineas) + "\n")

print("tablas:", len(TABLAS), "(%d nuevas + %d de apoyo)" % (len(NUEVAS), len(APOYO)))
print("columnas:", sum(len(v) for v in columnas.values()))
print("relaciones:", len(filas))
if faltan:
    print("\nSIN VERBO (hay que agregarlo a VERBOS):")
    for f in faltan:
        print("  -", f)
else:
    print("\nTodas las relaciones tienen su verbo.")
