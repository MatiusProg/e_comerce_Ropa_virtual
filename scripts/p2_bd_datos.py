"""Datos del 3.1 (modelo de dominio) y del 3.5 (diseño de la base de datos) del 2do parcial.

Escribe scripts/ea-p2-bd.datos.json, que dibuja scripts/ea-p2-dominio-bd.ps1.

3.1 MODELO DE DOMINIO (corto, como lo pide la ing): las entidades del dominio sin
atributos, con sus asociaciones nombradas y la multiplicidad. Son las mismas
entidades que usa la robustez (3.2) de CU-01 a CU-20, más Producto y
VarianteProducto, que hacen falta para entender la existencia y la venta. Se
escribe a mano: es el vocabulario del negocio, no el esquema.

3.5 DISEÑO DE LA BASE DE DATOS (completo): todas las tablas del sistema, con
todas sus columnas, su tipo y «PK»/«FK». EL CONTENIDO NO SE TRANSCRIBE A MANO:
sale de information_schema de la base que se le pase (la QA, que está en la
última migración). Las cardinalidades salen de lo que la base obliga
(NOT NULL y UNIQUE de una sola columna), igual que en el 3.3.1 del 1er parcial.
Solo los verbos de cada relación se escriben a mano.

Uso (SOLO LECTURA; nunca contra producción):
    P2_BD_URL=postgresql+psycopg://postgres:...@localhost:5433/violetboutique_qa \
        backend/.venv/Scripts/python.exe scripts/p2_bd_datos.py
"""
import json
import os
import sys

from sqlalchemy import create_engine, text

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
url = os.environ.get("P2_BD_URL")
if not url or "localhost" not in url:
    raise SystemExit("Falta P2_BD_URL, y tiene que ser una base local (localhost).")

# ---------------------------------------------------------------- 3.1 --------
# Columnas de izquierda a derecha; cada una, de arriba hacia abajo.
DOMINIO_COLUMNAS = [
    ["Plan", "Suscripcion", "PagoSimulado", "ConsumoCupo"],
    ["Empresa", "Ciudad", "Rol", "SesionToken"],
    ["ClienteEmpresa", "Sucursal", "Usuario", "AsientoBitacora"],
    ["Cliente", "Empleado", "Caja", "TurnoCaja"],
    ["Reserva", "Existencia", "OperacionOffline", "Venta", "Devolucion"],
    ["Producto", "VarianteProducto", "ImagenProducto"],
    ["PaqueteLocal", "FotoLocal", "OperacionLocal"],
]
# Las que viven en el dispositivo (IndexedDB de la PWA o SQLite del móvil).
DOMINIO_LOCALES = {"PaqueteLocal", "FotoLocal", "OperacionLocal"}
# (A, verbo, B, multiplicidad de A, multiplicidad de B): se lee «A verbo B».
DOMINIO_ASOCIACIONES = [
    ("Plan", "rige", "Suscripcion", "1", "0..*"),
    ("Empresa", "contrata", "Suscripcion", "1", "0..*"),
    ("Suscripcion", "se paga con", "PagoSimulado", "0..1", "0..*"),
    ("Plan", "se cobra en", "PagoSimulado", "1", "0..*"),
    ("Empresa", "consume", "ConsumoCupo", "1", "0..*"),
    ("Empresa", "tiene", "Sucursal", "1", "1..*"),
    ("Ciudad", "aloja", "Sucursal", "1", "0..*"),
    ("Empresa", "da acceso a", "Usuario", "0..1", "0..*"),
    ("Rol", "define", "Usuario", "1", "0..*"),
    ("Usuario", "inicia", "SesionToken", "1", "0..*"),
    ("Usuario", "es", "Empleado", "1", "0..1"),
    ("Sucursal", "emplea a", "Empleado", "0..1", "0..*"),
    ("Usuario", "es", "Cliente", "1", "0..1"),
    ("Cliente", "se registra en", "ClienteEmpresa", "1", "1..*"),
    ("Empresa", "atiende a", "ClienteEmpresa", "1", "0..*"),
    ("Sucursal", "tiene", "Caja", "1", "0..*"),
    ("Caja", "registra", "TurnoCaja", "1", "0..*"),
    ("Usuario", "abre", "TurnoCaja", "1", "0..*"),
    ("TurnoCaja", "registra", "Venta", "0..1", "0..*"),
    ("Cliente", "compra en", "Venta", "0..1", "0..*"),
    ("Venta", "se revierte en", "Devolucion", "1", "0..*"),
    ("TurnoCaja", "registra", "Devolucion", "0..1", "0..*"),
    ("Producto", "se ofrece como", "VarianteProducto", "1", "1..*"),
    ("Producto", "se ilustra con", "ImagenProducto", "1", "0..*"),
    ("VarianteProducto", "se almacena en", "Existencia", "1", "0..*"),
    ("Sucursal", "alberga", "Existencia", "1", "0..*"),
    ("Venta", "vende", "VarianteProducto", "0..*", "1..*"),
    ("Cliente", "realiza", "Reserva", "1", "0..*"),
    ("Sucursal", "atiende", "Reserva", "1", "0..*"),
    ("Reserva", "aparta", "VarianteProducto", "0..*", "1..*"),
    ("Usuario", "sube", "OperacionOffline", "1", "0..*"),
    ("Sucursal", "atiende", "OperacionOffline", "0..1", "0..*"),
    ("TurnoCaja", "imputa", "OperacionOffline", "0..1", "0..*"),
    ("OperacionOffline", "se confirma como", "Venta", "0..1", "0..1"),
    ("OperacionOffline", "se confirma como", "Reserva", "0..1", "0..1"),
    ("Usuario", "descarga", "PaqueteLocal", "1", "0..*"),
    ("PaqueteLocal", "copia", "Existencia", "0..*", "0..*"),
    ("PaqueteLocal", "guarda", "FotoLocal", "1", "0..*"),
    ("Usuario", "registra", "OperacionLocal", "1", "0..*"),
    ("OperacionLocal", "se sube como", "OperacionOffline", "1", "0..1"),
    ("Usuario", "deja", "AsientoBitacora", "0..1", "0..*"),
    ("Empresa", "agrupa", "AsientoBitacora", "0..1", "0..*"),
]

# ---------------------------------------------------------------- 3.5 --------
# Cada parte: su título y sus columnas. Un nombre con '~' es una tabla de OTRA
# parte que se dibuja en gris y solo con su clave primaria, para cerrar la FK.
PARTES = [
    ("3.5 Parte 1 - Plataforma, empresas y seguridad", [
        ["plan", "pago_simulado"],
        ["suscripcion", "consumo_cupo"],
        ["empresa", "cliente_empresa", "~cliente"],
        ["usuario", "sesion_token", "token_recuperacion"],
        ["rol", "rol_permiso", "permiso"],
        ["bitacora", "notificacion"],
    ]),
    ("3.5 Parte 2 - Organización y clientes", [
        ["ciudad", "direccion_cliente"],
        ["sucursal", "caja"],
        ["empleado", "~usuario", "proveedor"],
        ["cliente", "medida_cliente"],
        ["cliente_categoria", "~categoria"],
    ]),
    ("3.5 Parte 3 - Catálogo e inventario", [
        ["temporada", "coleccion"],
        ["categoria", "promocion"],
        ["producto", "medida_talla", "favorito"],
        ["talla", "color", "imagen_producto"],
        ["variante_producto", "abastecimiento"],
        ["existencia", "movimiento_inventario"],
        ["~sucursal", "~proveedor", "~usuario", "~cliente", "recomendacion"],
    ]),
    ("3.5 Parte 4 - Ventas, caja, reservas y sin conexión", [
        ["~caja", "turno_caja", "~usuario"],
        ["venta", "pago", "transaccion_pasarela"],
        ["detalle_venta", "comprobante", "devolucion", "detalle_devolucion"],
        ["operacion_offline", "~sucursal", "~direccion_cliente"],
        ["reserva", "reserva_detalle", "~cliente"],
        ["carrito", "carrito_detalle", "~variante_producto"],
    ]),
]

# Verbos, escritos a mano porque la base no los tiene. Clave: (destino, origen,
# columna); se lee «DESTINO VERBO ORIGEN». Los del 1er parcial se conservan.
VERBOS = {
    # Plataforma (2do parcial)
    ("plan", "suscripcion", "plan_id"): "RIGE",
    ("plan", "pago_simulado", "plan_id"): "SE_COBRA_EN",
    ("suscripcion", "pago_simulado", "suscripcion_id"): "SE_PAGA_CON",
    ("empresa", "suscripcion", "empresa_id"): "CONTRATA",
    ("empresa", "pago_simulado", "empresa_id"): "PAGA_CON",
    ("empresa", "consumo_cupo", "empresa_id"): "CONSUME",
    ("empresa", "cliente_empresa", "empresa_id"): "ATIENDE_A",
    ("empresa", "usuario", "empresa_id"): "DA_ACCESO_A",
    ("empresa", "bitacora", "empresa_id"): "AUDITA_EN",
    ("empresa", "notificacion", "empresa_id"): "NOTIFICA_EN",
    ("cliente", "cliente_empresa", "cliente_id"): "SE_REGISTRA_EN",
    # Seguridad y usuarios
    ("rol", "usuario", "rol_id"): "DEFINE",
    ("rol", "rol_permiso", "rol_id"): "SE_HABILITA_EN",
    ("permiso", "rol_permiso", "permiso_id"): "SE_OTORGA_EN",
    ("usuario", "sesion_token", "usuario_id"): "INICIA_SESION_EN",
    ("usuario", "token_recuperacion", "usuario_id"): "RECUPERA_CON",
    ("usuario", "cliente", "usuario_id"): "ES",
    ("usuario", "empleado", "usuario_id"): "ES_EMPLEADO",
    ("usuario", "proveedor", "usuario_id"): "PUEDE_SER",
    ("usuario", "bitacora", "usuario_id"): "SE_AUDITA_EN",
    ("usuario", "notificacion", "destinatario_id"): "RECIBE",
    ("usuario", "movimiento_inventario", "usuario_id"): "ORIGINA",
    ("usuario", "turno_caja", "usuario_id"): "ABRE",
    ("usuario", "operacion_offline", "usuario_id"): "SUBE",
    ("usuario", "operacion_offline", "devuelto_por"): "DEVUELVE",
    ("cliente", "direccion_cliente", "cliente_id"): "REGISTRA",
    ("cliente", "cliente_categoria", "cliente_id"): "PREFIERE_EN",
    ("cliente", "medida_cliente", "cliente_id"): "SE_MIDE_EN",
    # Organización
    ("ciudad", "sucursal", "ciudad_id"): "ALOJA",
    ("ciudad", "direccion_cliente", "ciudad_id"): "UBICA",
    ("sucursal", "empleado", "sucursal_id"): "EMPLEA_A",
    ("sucursal", "existencia", "sucursal_id"): "ALBERGA",
    ("sucursal", "reserva", "sucursal_id"): "ATIENDE",
    ("sucursal", "venta", "sucursal_id"): "VENDE_EN",
    ("sucursal", "caja", "sucursal_id"): "TIENE_CAJA",
    ("sucursal", "operacion_offline", "sucursal_id"): "RESPONDE_POR",
    # Catálogo
    ("categoria", "categoria", "categoria_padre_id"): "SE_SUBDIVIDE_EN",
    ("categoria", "producto", "categoria_id"): "CLASIFICA",
    ("categoria", "cliente_categoria", "categoria_id"): "SE_PREFIERE_EN",
    ("categoria", "promocion", "categoria_id"): "AGRUPA_PROMOCION",
    ("proveedor", "producto", "proveedor_id"): "ABASTECE",
    ("proveedor", "movimiento_inventario", "proveedor_id"): "ABASTECE_EN",
    ("proveedor", "abastecimiento", "proveedor_id"): "ANUNCIA_EN",
    ("temporada", "coleccion", "temporada_id"): "CONTIENE",
    ("temporada", "producto", "temporada_id"): "ENMARCA",
    ("temporada", "promocion", "temporada_id"): "ENMARCA_PROMOCION",
    ("coleccion", "producto", "coleccion_id"): "AGRUPA",
    ("talla", "variante_producto", "talla_id"): "DIMENSIONA",
    ("talla", "medida_talla", "talla_id"): "DIMENSIONA_EN",
    ("color", "variante_producto", "color_id"): "TINE",
    ("producto", "variante_producto", "producto_id"): "SE_OFRECE_COMO",
    ("producto", "imagen_producto", "producto_id"): "SE_ILUSTRA_CON",
    ("producto", "medida_talla", "producto_id"): "SE_TABULA_EN",
    ("producto", "promocion", "producto_id"): "SE_PROMOCIONA_EN",
    ("producto", "favorito", "producto_id"): "SE_MARCA_EN",
    ("variante_producto", "imagen_producto", "variante_id"): "SE_MUESTRA_EN",
    ("variante_producto", "existencia", "variante_id"): "SE_ALMACENA_EN",
    ("variante_producto", "reserva_detalle", "variante_id"): "SE_APARTA_EN",
    ("variante_producto", "carrito_detalle", "variante_id"): "SE_AGREGA_EN",
    ("variante_producto", "detalle_venta", "variante_id"): "SE_VENDE_EN",
    ("variante_producto", "detalle_devolucion", "variante_id"): "SE_DEVUELVE_EN",
    ("variante_producto", "abastecimiento", "variante_id"): "SE_REPONE_EN",
    # Inventario
    ("existencia", "movimiento_inventario", "existencia_id"): "SE_EXPLICA_POR",
    # Reservas
    ("cliente", "reserva", "cliente_id"): "REALIZA",
    ("reserva", "reserva_detalle", "reserva_id"): "SE_DETALLA_EN",
    ("reserva", "venta", "reserva_id"): "SE_CONCRETA_EN",
    ("reserva", "operacion_offline", "reserva_id"): "SE_ORIGINA_EN",
    # Ventas y pagos
    ("cliente", "carrito", "cliente_id"): "TIENE",
    ("carrito", "carrito_detalle", "carrito_id"): "SE_DESGLOSA_EN",
    ("cliente", "favorito", "cliente_id"): "MARCA_EN",
    ("cliente", "venta", "cliente_id"): "COMPRA_EN",
    ("cliente", "recomendacion", "cliente_id"): "RECIBE",
    ("direccion_cliente", "venta", "direccion_id"): "ES_DESTINO_DE",
    ("venta", "detalle_venta", "venta_id"): "SE_DETALLA_EN",
    ("venta", "pago", "venta_id"): "SE_SALDA_CON",
    ("pago", "transaccion_pasarela", "pago_id"): "SE_NOTIFICA_EN",
    ("venta", "comprobante", "venta_id"): "SE_ACREDITA_CON",
    ("venta", "operacion_offline", "venta_id"): "SE_ORIGINA_EN",
    # Caja y punto de venta
    ("caja", "turno_caja", "caja_id"): "REGISTRA",
    ("turno_caja", "venta", "turno_caja_id"): "REGISTRA_VENTA",
    ("turno_caja", "devolucion", "turno_caja_id"): "REGISTRA_DEVOLUCION",
    ("venta", "devolucion", "venta_id"): "SE_REVIERTE_EN",
    ("venta", "devolucion", "venta_cambio_id"): "ES_CAMBIO_EN",
    ("devolucion", "detalle_devolucion", "devolucion_id"): "SE_DESGLOSA_EN",
}

TIPO = """CASE
    WHEN c.column_default LIKE 'nextval' || '%' AND c.data_type = 'integer' THEN 'SERIAL'
    WHEN c.column_default LIKE 'nextval' || '%' AND c.data_type = 'bigint'  THEN 'BIGSERIAL'
    WHEN c.data_type = 'character varying' THEN 'VARCHAR(' || c.character_maximum_length || ')'
    WHEN c.data_type = 'character' THEN 'CHAR(' || c.character_maximum_length || ')'
    WHEN c.data_type = 'numeric' THEN 'NUMERIC(' || c.numeric_precision || ',' || c.numeric_scale || ')'
    WHEN c.data_type = 'timestamp with time zone' THEN 'TIMESTAMPTZ'
    WHEN c.data_type = 'timestamp without time zone' THEN 'TIMESTAMP'
    WHEN c.data_type = 'time without time zone' THEN 'TIME'
    WHEN c.data_type = 'integer' THEN 'INTEGER'
    WHEN c.data_type = 'bigint' THEN 'BIGINT'
    WHEN c.data_type = 'smallint' THEN 'SMALLINT'
    WHEN c.data_type = 'boolean' THEN 'BOOLEAN'
    WHEN c.data_type = 'date' THEN 'DATE'
    WHEN c.data_type = 'text' THEN 'TEXT'
    WHEN c.data_type = 'USER-DEFINED' THEN upper(c.udt_name)
    ELSE upper(c.data_type) END"""

motor = create_engine(url)
with motor.connect() as con:
    con.execute(text("SET TRANSACTION READ ONLY"))
    tablas = [t for t in con.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY 1"
    )).scalars().all() if t != "alembic_version"]
    columnas = {}
    for tabla, col, tipo, nulo in con.execute(text(
            "SELECT c.table_name, c.column_name, %s, c.is_nullable FROM information_schema.columns c "
            "WHERE c.table_schema='public' ORDER BY c.table_name, c.ordinal_position" % TIPO)).all():
        columnas.setdefault(tabla, []).append((col, tipo, nulo == "YES"))
    claves = {}
    for tabla, col, clase in con.execute(text(
            "SELECT tc.table_name, kcu.column_name, tc.constraint_type "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu ON kcu.constraint_name = tc.constraint_name "
            " AND kcu.table_schema = tc.table_schema "
            "WHERE tc.table_schema='public' AND tc.constraint_type IN ('PRIMARY KEY','FOREIGN KEY')")).all():
        claves.setdefault((tabla, col), set()).add("PK" if clase == "PRIMARY KEY" else "FK")
    # El UNIQUE compuesto no hace única a cada columna (guía, 7.9).
    unicas = {(t, c) for t, c, n in con.execute(text(
        "SELECT tc.table_name, MIN(kcu.column_name), COUNT(kcu.column_name) "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu ON kcu.constraint_name = tc.constraint_name "
        "WHERE tc.table_schema='public' AND tc.constraint_type = 'UNIQUE' "
        "GROUP BY tc.table_name, tc.constraint_name")).all() if int(n) == 1}
    fks = con.execute(text(
        "SELECT ccu.table_name, tc.table_name, kcu.column_name "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu ON kcu.constraint_name = tc.constraint_name "
        "JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name "
        "WHERE tc.table_schema='public' AND tc.constraint_type = 'FOREIGN KEY' ORDER BY 1, 2, 3")).all()
    rls = set(con.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' AND rowsecurity")).scalars().all())

# Cada tabla en una sola parte, y todas en alguna.
duenia = {}
for titulo, cols in PARTES:
    for col in cols:
        for t in col:
            if not t.startswith("~"):
                assert t not in duenia, f"{t} está en dos partes"
                duenia[t] = titulo
faltan = set(tablas) - set(duenia)
if faltan:
    raise SystemExit(f"Tablas sin parte: {sorted(faltan)}")

tabla_json = {}
for t in tablas:
    nulos = {c: n for c, _, n in columnas[t]}
    tabla_json[t] = {
        "nombre": t.upper(),
        "rls": t in rls,
        "columnas": [{"n": c, "t": tipo, "k": ",".join(sorted(claves.get((t, c), set()), reverse=True)),
                      "nulo": n} for c, tipo, n in columnas[t]],
    }

relaciones, sin_verbo = [], []
for destino, origen, col in fks:
    verbo = VERBOS.get((destino, origen, col))
    if destino == "empresa" and not verbo:
        verbo = "AGRUPA"   # las del tenant: solo se dibujan en la parte 1
    if not verbo:
        sin_verbo.append(f"{destino} <- {origen}.{col}")
        continue
    relaciones.append({
        "destino": destino, "origen": origen, "columna": col, "verbo": verbo,
        # Del lado apuntado: 1 si la columna es NOT NULL, 0..1 si admite nulo.
        "card_destino": "0..1" if dict((c, n) for c, _, n in columnas[origen])[col] else "1",
        # Del lado que apunta: 0..1 si la columna es UNIQUE sola, 0..* si no.
        "card_origen": "0..1" if (origen, col) in unicas else "0..*",
    })
if sin_verbo:
    raise SystemExit("Sin verbo:\n  " + "\n  ".join(sin_verbo))

# La asociación del dominio tiene que unir clases que estén en el diagrama.
clases = {c for col in DOMINIO_COLUMNAS for c in col}
for a, _, b, _, _ in DOMINIO_ASOCIACIONES:
    assert a in clases and b in clases, (a, b)


# ---------------------------------------------------------- disposición --
# Los tamaños y las posiciones se calculan acá (p2_bd_layout.py) y el .ps1
# solo pone cada caja donde dice el JSON.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p2_bd_layout import maquetar_mejor  # noqa: E402


def tam_tabla(t, solo_pk):
    cols = [c for c in tabla_json[t]["columnas"] if not solo_pk or "PK" in c["k"]]
    largo = max([len(t) + 8] + [len(c["n"]) + len(c["t"]) + 6 for c in cols])
    # EA agrega una línea por cada grupo de estereotipo («PK», «FK», sin estereotipo).
    grupos = len({c["k"] for c in cols})
    return (max(150, int(largo * 6.8)), 46 + (len(cols) + grupos) * 15)


def relaciones_de_la_parte(propias, presentes):
    """Las que se dibujan: al menos un extremo propio; las de EMPRESA, solo entre propias."""
    out = []
    for r in relaciones:
        d, o = r["destino"], r["origen"]
        if d not in presentes or o not in presentes:
            continue
        if d not in propias and o not in propias:
            continue
        if d == "empresa" and not (d in propias and o in propias):
            continue
        out.append(r)
    return out


tam_dom = {c: (170, 60) for col in DOMINIO_COLUMNAS for c in col}
pos_dom, costo_dom = maquetar_mejor(tam_dom, [(a, b) for a, _, b, _, _ in DOMINIO_ASOCIACIONES],
                              n_columnas=len(DOMINIO_COLUMNAS) + 1, max_por_columna=5,
                              iteraciones=15000, inicial=DOMINIO_COLUMNAS,
                              semillas=range(1, 13))
print("  dominio: costo de la disposición", round(costo_dom, 1))

partes_json = []
for titulo, cols in PARTES:
    propias = {t for col in cols for t in col if not t.startswith("~")}
    presentes = {t.lstrip("~") for col in cols for t in col}
    tam = {t: tam_tabla(t, t not in propias) for t in presentes}
    rels = relaciones_de_la_parte(propias, presentes)
    pos, c = maquetar_mejor(tam, [(r["destino"], r["origen"]) for r in rels],
                      n_columnas=len(cols) + 1, max_por_columna=4, iteraciones=8000,
                      inicial=[[t.lstrip("~") for t in col] for col in cols])
    print(f"  {titulo}: costo de la disposición {round(c, 1)}")
    partes_json.append({"titulo": titulo, "propias": sorted(propias), "posiciones": pos,
                        "relaciones": [[r["destino"], r["origen"], r["columna"]] for r in rels]})

salida = {
    "_generado_por": "scripts/p2_bd_datos.py — no editar a mano",
    "dominio": {"locales": sorted(DOMINIO_LOCALES), "posiciones": pos_dom,
                "asociaciones": [list(x) for x in DOMINIO_ASOCIACIONES]},
    "partes": partes_json,
    "tablas": tabla_json,
    "relaciones": relaciones,
}
ruta = os.path.join(RAIZ, "scripts", "ea-p2-bd.datos.json")
with open(ruta, "w", encoding="utf-8") as f:
    json.dump(salida, f, ensure_ascii=False, indent=1)
print("escrito", ruta)
print("  tablas:", len(tablas), "columnas:", sum(len(v) for v in columnas.values()),
      "relaciones:", len(relaciones), "con RLS:", len(rls))
print("  dominio:", len(clases), "clases,", len(DOMINIO_ASOCIACIONES), "asociaciones")
