"""Genera el fragmento de datos del 2.3 del Ciclo 2.

Los nombres y los tipos NO se escriben a mano: salen del codigo (ast sobre los
modulos del backend, regex sobre los servicios de Angular) y de
information_schema de la base construida con las migraciones. Es lo que permite
defender el diagrama: cada operacion se puede abrir en el repositorio.
"""
import ast
import io
import os
import re
import subprocess

BACK = r"D:\UNI\Si2\PRIMER_PARCIAL\backend\app\modules"
WEB = r"D:\UNI\Si2\PRIMER_PARCIAL\frontend-web\src\app\core\services"

MODULOS = {
    "cat_repo": "catalogo/repository.py", "img_repo": "catalogo/imagenes_repository.py",
    "cat_svc": "catalogo/service.py", "img_svc": "catalogo/imagenes_service.py",
    "inv_repo": "inventario/repository.py", "inv_svc": "inventario/service.py",
    "cons_svc": "inventario/consolidado_service.py", "pub_repo": "catalogo_publico/repository.py",
    "pub_svc": "catalogo_publico/service.py", "res_repo": "reservas/repository.py",
    "res_svc": "reservas/service.py", "cat_rt": "catalogo/router.py",
    "img_rt": "catalogo/imagenes_router.py", "inv_rt": "inventario/router.py",
    "cons_rt": "inventario/consolidado_router.py", "pub_rt": "catalogo_publico/router.py",
    "res_rt": "reservas/router.py",
}

SERVICIOS = ["productos.service.ts", "inventario.service.ts", "consolidado.service.ts",
             "tienda.service.ts", "reservas.service.ts"]

RE_METODO = re.compile(
    r"^  (?!private |constructor|readonly )([a-zA-Z][A-Za-z0-9]*)\(([^)]*)\)\s*:\s*([^{]+?)\s*\{",
    re.M)


def firmas_python(rel):
    """Las firmas reales del backend, leidas con `ast`: nombre, parametros con
    su anotacion de tipo y tipo de retorno. Solo funciones de modulo."""
    arbol = ast.parse(io.open(os.path.join(BACK, rel), encoding="utf-8").read())
    out = {}
    for n in arbol.body:
        if not isinstance(n, ast.FunctionDef):
            continue
        params = [(a.arg, ast.unparse(a.annotation) if a.annotation else "")
                  for a in n.args.args]
        out[n.name] = {"p": params, "r": ast.unparse(n.returns) if n.returns else "None"}
    return out


def firmas_angular(archivo):
    """Los metodos publicos de un servicio de Angular, con sus tipos."""
    s = io.open(os.path.join(WEB, archivo), encoding="utf-8").read()
    out = {}
    for m in RE_METODO.finditer(s):
        ps = []
        for trozo in re.split(r",(?![^<>()]*[>)])", m.group(2).strip()):
            trozo = trozo.strip()
            if not trozo:
                continue
            if ":" in trozo:
                nom, tipo = trozo.split(":", 1)
                ps.append([nom.strip().rstrip("?"), tipo.split("=")[0].strip()])
            else:
                ps.append([trozo, ""])
        out[m.group(1)] = {"p": ps, "r": m.group(3).strip()}
    return out


be = {k: firmas_python(v) for k, v in MODULOS.items()}
fe = {a.split(".")[0]: firmas_angular(a) for a in SERVICIOS}

SQL = """SELECT c.table_name || '|' || c.column_name || '|' ||
  CASE
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
    ELSE upper(c.data_type) END
FROM information_schema.columns c
WHERE c.table_schema = 'public'
  AND c.table_name IN ('producto', 'variante_producto', 'imagen_producto', 'existencia',
                       'movimiento_inventario', 'reserva', 'reserva_detalle')
ORDER BY c.table_name, c.ordinal_position"""

salida = subprocess.run(
    [r"C:\Program Files\PostgreSQL\18\bin\psql.exe",
     "postgresql://postgres:291022@localhost:5433/violetboutique_uml", "-At", "-c", SQL],
    capture_output=True, text=True, encoding="utf-8").stdout

cols = {}
for ln in salida.strip().split("\n"):
    if not ln.strip():
        continue
    tabla, col, tipo = ln.split("|")
    cols.setdefault(tabla, []).append((col, tipo))

TABLA_DE = {
    "Producto": "producto", "VarianteProducto": "variante_producto",
    "ImagenProducto": "imagen_producto", "Existencia": "existencia",
    "MovimientoInventario": "movimiento_inventario", "Reserva": "reserva",
    "ReservaDetalle": "reserva_detalle",
}

# Entidades -> funciones del repository que consultan ESA tabla.
# Controladores -> funciones del service.
OPS = {
    "Producto": [("cat_repo", n) for n in (
        "contar_productos", "listar_productos", "obtener_producto", "existe_codigo",
        "agregar_producto", "eliminar_producto", "conteo_de_variantes",
        "conteo_de_imagenes", "nombre_de_categoria")],
    "VarianteProducto": [("cat_repo", n) for n in (
        "obtener_variante", "combinaciones_existentes", "agregar_variante",
        "eliminar_variante", "codigos_de_talla", "nombres_de_color")]
        + [("pub_repo", n) for n in (
        "variante_ofrecible", "rango_de_precios", "colores_por_producto",
        "variantes_con_vestidor")],
    "ImagenProducto": [("img_repo", n) for n in (
        "listar_de_producto", "obtener", "variante_de_producto", "principal_de",
        "transparente_de_variante", "siguiente_orden", "contar_de_producto",
        "agregar", "eliminar")],
    "Existencia": [("inv_repo", n) for n in (
        "obtener_existencia", "obtener_existencia_con_detalle", "obtener_existencia_por_id",
        "agregar_existencia", "listar_alertas", "disponibilidad_por_sucursal",
        "inventario_consolidado")],
    "MovimientoInventario": [("inv_repo", n) for n in (
        "agregar_movimiento", "obtener_movimiento", "contar_movimientos",
        "listar_movimientos", "contar_ingresos", "listar_ingresos", "lineas_de_ingreso")],
    "Reserva": [("res_repo", n) for n in (
        "obtener_reserva", "obtener_reserva_entidad", "contar_reservas_solapadas",
        "listar_vencidas", "agregar_reserva", "contar_reservas", "listar_reservas",
        "obtener_cliente_de_usuario", "obtener_sucursal")],
    "ReservaDetalle": [("res_repo", n) for n in (
        "agregar_detalle", "detalles_de", "listar_detalles", "listar_variantes")],

    "GestorProductos": [("cat_svc", n) for n in (
        "listar_productos", "obtener_producto", "crear_producto", "editar_producto",
        "cambiar_estado_producto", "eliminar_producto", "generar_variantes",
        "crear_variante", "editar_variante", "eliminar_variante", "armar_sku",
        "_validar_maestros", "_resolver_temporada", "_precio_de", "_viola")],
    "GestorImagenes": [("img_svc", n) for n in (
        "listar", "obtener", "subir", "editar", "marcar_principal", "marcar_transparente",
        "reordenar", "eliminar", "_asegurar_producto", "_asegurar_variante",
        "_archivo_tiene_transparencia")],
    "GestorInventario": [("inv_svc", n) for n in (
        "registrar_ingreso", "listar_ingresos", "detalle_de_ingreso", "registrar_ajuste",
        "registrar_transferencia", "listar_movimientos", "existencia_por_id",
        "fijar_stock_minimo", "alertas_de_stock", "apartar_para_reserva",
        "liberar_de_reserva", "descontar_por_venta", "disponibilidad_por_sucursal",
        "inventario_consolidado", "_aplicar_movimiento", "_existencia_o_crearla",
        "_sucursal_activa", "_variantes_validas")],
    "GestorConsolidado": [("cons_svc", n) for n in ("consultar", "_estado", "_agrupar", "_ordenar")],
    "GestorVitrina": [("pub_svc", n) for n in (
        "listar_productos", "obtener_ficha", "disponibilidad_de_variante",
        "obtener_filtros", "_ordenadas", "_variante", "_opciones")],
    "GestorReservas": [("res_svc", n) for n in (
        "crear_reserva", "cancelar_reserva", "preparar_reserva", "atender_reserva",
        "listar_reservas_de_sucursal", "obtener_reserva_de_sucursal",
        "expirar_reservas_vencidas", "obtener_reserva_de_cliente", "listar_mis_reservas",
        "_validar_franja", "_armar_reserva", "_reserva_de_la_sucursal", "_ahora")],
}

# Fronteras -> el componente del frontend Y el endpoint del router.
FRONT = {
    "PantallaProductos": (
        ("productos", ["listar", "obtener", "crear", "editar", "cambiarEstado", "eliminar",
                       "generarVariantes", "crearVariante", "editarVariante", "eliminarVariante"]),
        ("cat_rt", ["listar_productos", "crear_producto", "obtener_producto", "editar_producto",
                    "cambiar_estado_producto", "eliminar_producto", "generar_variantes",
                    "crear_variante", "editar_variante", "eliminar_variante"])),
    "PantallaImagenes": (
        ("productos", ["listarImagenes", "subirImagen", "editarImagen", "marcarPrincipal",
                       "marcarTransparente", "reordenarImagenes", "eliminarImagen", "urlDeImagen"]),
        ("img_rt", ["listar", "editar", "marcar_principal", "marcar_transparente",
                    "reordenar", "eliminar"])),
    "PantallaInventario": (
        ("inventario", ["registrarIngreso", "listarIngresos", "detalleDeIngreso",
                        "listarExistencias", "listarMovimientos", "tiposManuales",
                        "registrarAjuste", "registrarTransferencia"]),
        ("inv_rt", ["registrar_ingreso", "listar_ingresos", "detalle_de_ingreso",
                    "listar_existencias", "listar_movimientos", "listar_tipos_manuales",
                    "registrar_ajuste", "registrar_transferencia"])),
    "PantallaConsolidado": (
        ("consolidado", ["consultar"]), ("cons_rt", ["consultar_consolidado"])),
    "PantallaDisponibilidad": (
        ("inventario", ["listarAlertas", "fijarStockMinimo", "listarExistencias", "registrarAjuste"]),
        ("inv_rt", ["listar_alertas", "fijar_stock_minimo", "listar_existencias"])),
    "PantallaCatalogo": (
        ("tienda", ["listar", "obtenerFiltros", "urlDeImagen"]),
        ("pub_rt", ["listar_productos", "obtener_filtros"])),
    "PantallaFichaProducto": (
        ("tienda", ["obtenerFicha", "obtenerDisponibilidad", "urlDeImagen"]),
        ("pub_rt", ["obtener_ficha", "disponibilidad_de_variante"])),
    "PantallaReservas": (
        ("reservas", ["crear", "misReservas", "obtener", "cancelar"]),
        ("res_rt", ["crear_reserva", "listar_mis_reservas", "obtener_reserva", "cancelar_reserva"])),
    "PantallaReservasSucursal": (
        ("reservas", ["deMiSucursal", "obtenerDeSucursal", "preparar", "atender"]),
        ("res_rt", ["listar_reservas_de_sucursal", "obtener_reserva_de_sucursal",
                    "preparar_reserva", "atender_reserva"])),
    "PlanificadorTareas": (
        ("reservas", ["expirarVencidas"]), ("res_rt", ["expirar_reservas_vencidas"])),
}


def ps_op(nombre, firma):
    ps = "; ".join("@{n='%s';t='%s'}" % (n, t.replace("'", "")) for n, t in firma["p"])
    return "    @{n='%s'; r='%s'; p=@(%s)}" % (nombre, firma["r"].replace("'", ""), ps)


faltan = []
lineas = [
    "# GENERADO por scripts/gen-ops-2-3.py --- NO editar a mano.",
    "# Los nombres y los tipos salen del codigo (ast sobre el backend, regex sobre los",
    "# servicios de Angular) y de information_schema de la base construida con las",
    "# migraciones. Es lo que permite defender el diagrama: cada operacion se puede",
    "# abrir en el repositorio.",
    "",
    "$ATTRS = @{",
]
for clase, tabla in TABLA_DE.items():
    attrs = "; ".join("@{n='%s';t='%s'}" % (c, t) for c, t in cols[tabla])
    lineas.append("  '%s' = @(%s)" % (clase, attrs))
lineas += ["}", "", "$OPS = @{"]

for clase, refs in OPS.items():
    ops = []
    for mod, fn in refs:
        if fn not in be[mod]:
            faltan.append("%s: %s.%s" % (clase, mod, fn))
            continue
        ops.append(ps_op(fn, be[mod][fn]))
    lineas.append("  '%s' = @(\n%s\n  )" % (clase, ",\n".join(ops)))

for clase, ((svc, ms), (rt, rs)) in FRONT.items():
    ops = []
    for m in ms:
        if m not in fe[svc]:
            faltan.append("%s: %s.%s" % (clase, svc, m))
            continue
        ops.append(ps_op(m, fe[svc][m]))
    for m in rs:
        if m not in be[rt]:
            faltan.append("%s: %s.%s" % (clase, rt, m))
            continue
        ops.append(ps_op(m, be[rt][m]))
    lineas.append("  '%s' = @(\n%s\n  )" % (clase, ",\n".join(ops)))
lineas.append("}")

destino = r"D:\UNI\Si2\PRIMER_PARCIAL\scripts\ea-clases-2-3-ciclo2.datos.ps1"
io.open(destino, "w", encoding="utf-8-sig", newline="").write("\n".join(lineas) + "\n")

total = sum(len(v) for v in OPS.values()) + sum(len(a) + len(b) for (_, a), (_, b) in FRONT.values())
print("clases con atributos :", len(TABLA_DE))
print("clases con operaciones:", len(OPS) + len(FRONT))
print("operaciones escritas :", total - len(faltan))
if faltan:
    print("\nNO ENCONTRADAS en el codigo (hay que corregir el mapeo):")
    for f in faltan:
        print("  -", f)
else:
    print("\nTodas las funciones referenciadas existen en el codigo.")
