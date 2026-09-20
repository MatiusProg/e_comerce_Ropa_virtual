"""Genera el fragmento de datos del 2.3 del Ciclo 3.

Los nombres y los tipos NO se escriben a mano: salen del codigo ---`ast` sobre
los modulos del backend, regex sobre los servicios de Angular--- y de
`information_schema`. Es lo que permite defender el diagrama: cada operacion se
puede abrir en el repositorio.

DIFERENCIA CON EL DEL CICLO 2
------------------------------
Aquel leia los tipos de una base `violetboutique_uml` en el puerto 5433, que
hay que construir aparte. Este lee la **base de pruebas**, que ya existe y que
`alembic upgrade head` deja al dia: es la misma cadena de migraciones, asi que
los tipos son los mismos, y no hay que mantener una segunda base solo para
generar un diagrama.

Se lee `TEST_DATABASE_URL` de `backend/.env.test`. **Solo lectura**: consulta
`information_schema` y nada mas.
"""
import ast
import io
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACK = os.path.join(RAIZ, "backend", "app", "modules")
WEB = os.path.join(RAIZ, "frontend-web", "src", "app", "core", "services")

# --- los modulos del Ciclo 3 -------------------------------------------------
MODULOS = {
    # CU-12 promociones
    "promo_repo": "catalogo/promociones_repository.py",
    "promo_svc": "catalogo/promociones_service.py",
    "promo_rt": "catalogo/promociones_router.py",
    # CU-26 carrito
    "carr_repo": "ventas/carrito_repository.py",
    "carr_svc": "ventas/carrito_service.py",
    "carr_rt": "ventas/carrito_router.py",
    # CU-27 pedido
    "vent_repo": "ventas/repository.py",
    "vent_svc": "ventas/service.py",
    "vent_rt": "ventas/router.py",
    # CU-28 pagos
    "pago_svc": "pagos/service.py",
    "pago_rt": "pagos/router.py",
    # CU-29 historial
    "hist_repo": "ventas/historial_repository.py",
    "hist_svc": "ventas/historial_service.py",
    "hist_rt": "ventas/historial_router.py",
    # CU-30 caja
    "caja_repo": "caja/repository.py",
    "caja_svc": "caja/service.py",
    "caja_rt": "caja/router.py",
    # CU-31 y CU-32 punto de venta
    "pos_repo": "pos/repository.py",
    "pos_svc": "pos/service.py",
    "pos_rt": "pos/router.py",
    "dev_repo": "pos/devolucion_repository.py",
    "dev_svc": "pos/devolucion_service.py",
    "dev_rt": "pos/devolucion_router.py",
    # CU-33 recomendaciones
    "ia_repo": "ia/repository.py",
    "ia_svc": "ia/service.py",
    "ia_rt": "ia/router.py",
    # CU-36 y CU-37 reportes
    "tab_repo": "reportes/tablero_repository.py",
    "tab_svc": "reportes/tablero_service.py",
    "tab_rt": "reportes/tablero_router.py",
    "rep_svc": "reportes/reportes_service.py",
    "rep_rt": "reportes/reportes_router.py",
    # CU-39 abastecimiento
    "abas_repo": "abastecimiento/repository.py",
    "abas_svc": "abastecimiento/service.py",
    "abas_rt": "abastecimiento/router.py",
    # CU-41 seguridad
    "seg_repo": "seguridad/repository.py",
    "seg_svc": "seguridad/service.py",
    # CU-42 bitacora
    "bit_repo": "bitacora/repository.py",
    "bit_svc": "bitacora/service.py",
    "bit_rt": "bitacora/router.py",
    # CU-20 favoritos
    "fav_repo": "catalogo_publico/repository.py",
    "fav_svc": "catalogo_publico/service.py",
    "fav_rt": "catalogo_publico/favoritos_router.py",
    # CU-21 vestidor virtual
    "vest_repo": "vestidor_virtual/repository.py",
    "vest_svc": "vestidor_virtual/service.py",
    "vest_rt": "vestidor_virtual/router.py",
    "med_repo": "medidas/repository.py",
    "med_svc": "medidas/service.py",
    "med_rt": "medidas/router.py",
    # CU-38 catalogo del proveedor
    "prov_svc": "catalogo/proveedor_service.py",
    "prov_rt": "catalogo/proveedor_router.py",
    # CU-41 recuperar contrasena (el router es el de toda la seguridad: se
    # filtra mas abajo con `sel`)
    "seg_rt": "seguridad/router.py",
}

#: Los adaptadores de servicios externos NO viven en `modules`. Son la
#: realizacion de tres controles ---el interprete de voz de CU-35, el
#: probador de CU-21 y el recomendador de CU-33--- y del canal de aviso.
INTEGRACIONES = {
    "interprete": "interprete/__init__.py",
    "probador": "probador_ia/__init__.py",
    "recomendador": "recomendador/__init__.py",
    "correo": "correo/__init__.py",
    "pasarela": "pasarela_pago/__init__.py",
}

SERVICIOS = [
    "promociones.service.ts", "carrito.service.ts", "pedidos.service.ts",
    "compras.service.ts", "caja.service.ts", "pos.service.ts",
    "devoluciones.service.ts", "tablero.service.ts", "reportes.service.ts",
    "abastecimiento.service.ts",
]

RE_METODO = re.compile(
    r"^  (?!private |constructor|readonly )([a-zA-Z][A-Za-z0-9]*)\(([^)]*)\)\s*:\s*([^{]+?)\s*\{",
    re.M)


def firmas_python(rel, base=None):
    """Las firmas reales del backend, leidas con `ast`.

    Devuelve `{}` si el archivo no existe: los modulos del Ciclo 3 se fueron
    escribiendo en distinto orden y uno que falte no tiene que romper la
    generacion entera --- se nota despues, en las operaciones que no salen.
    """
    ruta = os.path.join(base or BACK, rel)
    if not os.path.exists(ruta):
        print(f"  (aviso) no existe {rel}", file=sys.stderr)
        return {}
    arbol = ast.parse(io.open(ruta, encoding="utf-8").read())
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
    ruta = os.path.join(WEB, archivo)
    if not os.path.exists(ruta):
        print(f"  (aviso) no existe {archivo}", file=sys.stderr)
        return {}
    s = io.open(ruta, encoding="utf-8").read()
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


INTEG = os.path.join(RAIZ, "backend", "app", "integrations")
be = {k: firmas_python(v) for k, v in MODULOS.items()}
be.update({k: firmas_python(v, INTEG) for k, v in INTEGRACIONES.items()})
fe = {a.split(".")[0]: firmas_angular(a) for a in SERVICIOS}

# --- las columnas, desde la base de pruebas ----------------------------------

TABLA_DE = {
    "Promocion": "promocion",
    "Favorito": "favorito",
    "Carrito": "carrito",
    "CarritoDetalle": "carrito_detalle",
    "Venta": "venta",
    "DetalleVenta": "detalle_venta",
    "Pago": "pago",
    "TransaccionPasarela": "transaccion_pasarela",
    "Comprobante": "comprobante",
    "Caja": "caja",
    "TurnoCaja": "turno_caja",
    "Devolucion": "devolucion",
    "DetalleDevolucion": "detalle_devolucion",
    "Recomendacion": "recomendacion",
    "Abastecimiento": "abastecimiento",
    "Bitacora": "bitacora",
    "TokenRecuperacion": "token_recuperacion",
    "MedidaCliente": "medida_cliente",
}

SQL = """
SELECT c.table_name, c.column_name,
  CASE
    WHEN c.column_default LIKE 'nextval' || '%%' AND c.data_type = 'integer' THEN 'SERIAL'
    WHEN c.column_default LIKE 'nextval' || '%%' AND c.data_type = 'bigint'  THEN 'BIGSERIAL'
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
    ELSE upper(c.data_type) END AS tipo
FROM information_schema.columns c
WHERE c.table_schema = 'public' AND c.table_name = ANY(:tablas)
ORDER BY c.table_name, c.ordinal_position
"""

sys.path.insert(0, os.path.join(RAIZ, "backend"))
from sqlalchemy import create_engine, text  # noqa: E402

url = os.environ.get("TEST_DATABASE_URL")
if not url:
    raise SystemExit(
        "Falta TEST_DATABASE_URL. Corre:  set -a && . backend/.env.test && set +a"
    )

cols = {}
motor = create_engine(url)
with motor.connect() as con:
    filas = con.execute(text(SQL), {"tablas": list(TABLA_DE.values())}).all()
for tabla, col, tipo in filas:
    cols.setdefault(tabla, []).append((col, tipo))

faltan = [t for t in TABLA_DE.values() if t not in cols]
if faltan:
    print(f"  (aviso) sin columnas en la base: {', '.join(faltan)}", file=sys.stderr)

# --- entidades -> funciones del repository que consultan ESA tabla ------------
OPS = {
    "Promocion": [("promo_repo", n) for n in (
        "descuentos_de_variantes", "descuentos_de_productos", "listar", "obtener",
        "entidad", "existe_nombre", "agregar")],
    "Favorito": [("fav_repo", n) for n in (
        "listar_favoritos", "ids_de_favoritos", "es_favorito", "agregar_favorito",
        "quitar_favorito", "contar_favoritos")],
    "Carrito": [("carr_repo", n) for n in (
        "obtener_carrito", "agregar_carrito", "vaciar")],
    "CarritoDetalle": [("carr_repo", n) for n in (
        "lineas_resueltas", "obtener_linea", "agregar_linea", "eliminar_linea",
        "stock_de_variantes", "imagen_principal")],
    "Venta": [("vent_repo", n) for n in (
        "obtener_pedido", "obtener_venta_entidad", "agregar_venta", "existe_codigo",
        "pedido_pendiente_de", "listar_pendientes_vencidos", "bloquear_cliente",
        "stock_por_sucursal")]
        + [("pos_repo", n) for n in ("agregar_venta_presencial", "venta_de_sucursal")],
    "DetalleVenta": [("vent_repo", n) for n in (
        "agregar_detalle", "lineas_de_pedido", "detalles_de")]
        + [("pos_repo", "lineas_llevadas")],
    "Pago": [("pago_svc", n) for n in ("iniciar_cobro", "confirmar_pago", "cobra_de_verdad")],
    "TransaccionPasarela": [("pago_svc", "fabricar_notificacion_simulada")],
    "Comprobante": [("hist_repo", n) for n in (
        "obtener_comprobante", "agregar_comprobante", "listar_compras", "contar_compras")],
    "Caja": [("caja_repo", n) for n in (
        "caja_por_id", "cajas_de_sucursal", "bloquear_caja", "sucursal_activa")],
    "TurnoCaja": [("caja_repo", n) for n in (
        "turno_abierto_de_caja", "turno_abierto_de_usuario", "turno_por_id", "abrir",
        "efectivo_cobrado", "devoluciones_del_turno", "ventas_del_turno")],
    "Devolucion": [("dev_repo", n) for n in (
        "venta_devolvible", "ya_devuelto", "bloquear_venta", "agregar_devolucion")],
    "DetalleDevolucion": [("dev_repo", n) for n in ("lineas_vendidas", "agregar_detalle")],
    "Recomendacion": [("ia_repo", n) for n in (
        "guardada", "guardar", "invalidar", "candidatas", "categorias_preferidas",
        "prendas_conocidas")],
    "Abastecimiento": [("abas_repo", n) for n in (
        "mios", "variantes_del_proveedor", "crear", "vigente", "por_id",
        "pendientes_de_recibir", "para_recibir")],
    "Bitacora": [("bit_repo", n) for n in (
        "agregar", "listar", "contar", "acciones", "roles", "entidades")],
    "TokenRecuperacion": [("seg_repo", n) for n in (
        "agregar_token_recuperacion", "canjear_token_de_recuperacion",
        "invalidar_tokens_de_recuperacion")],
    "MedidaCliente": [("med_repo", n) for n in (
        "medidas_de", "guardar_medidas", "tabla_de_producto")],
    # Notificacion NO figura: CU-40 todavia no esta construido y no hay tabla
    # `notificacion` en la cadena de migraciones. Se dibuja sin columnas ni
    # operaciones a proposito ---es lo que la deja visible como pendiente en
    # vez de inventarle un esquema que despues no coincide.
}

# --- controladores -> funciones del service ----------------------------------
CTRL = {
    "GestorPromociones": [("promo_svc", n) for n in (
        "descuentos_por_variante", "descuentos_por_producto", "a_contrato",
        "listar", "obtener", "crear", "editar", "cambiar_estado")],
    "GestorCarrito": [("carr_svc", n) for n in (
        "ver_carrito", "agregar", "cambiar_cantidad", "quitar", "vaciar")],
    "GestorPedidos": [("vent_svc", n) for n in (
        "opciones_de_pedido", "crear_pedido", "ver_pedido", "cancelar_pedido",
        "expirar_pedidos_vencidos")],
    "GestorPagos": [("pago_svc", n) for n in (
        "iniciar_cobro", "confirmar_pago", "cobra_de_verdad",
        "fabricar_notificacion_simulada")],
    "GestorHistorial": [("hist_svc", n) for n in (
        "listar_compras", "asegurar_comprobante", "comprobante_en_pdf")],
    "GestorCaja": [("caja_svc", n) for n in (
        "cajas_disponibles", "mi_turno", "abrir", "cerrar")],
    "GestorMostrador": [("pos_svc", n) for n in (
        "mostrador_de", "buscar_prendas", "reservas_por_cobrar", "ver_reserva",
        "registrar_venta", "ver_venta", "comprobante_en_pdf")],
    "GestorDevoluciones": [("dev_svc", n) for n in ("buscar_venta", "registrar")],
    "GestorRecomendaciones": [("ia_svc", n) for n in ("recomendaciones", "invalidar")],
    "GestorTablero": [("tab_svc", n) for n in ("consultar",)],
    "GestorReportes": [("rep_svc", n) for n in (
        "opciones_de", "generar", "catalogo_para_el_interprete")],
    "GestorAbastecimiento": [("abas_svc", n) for n in (
        "mis_anuncios", "mis_variantes", "anunciar", "cancelar", "avisos_de_ingreso",
        "recibir", "variante_del_aviso")],
    "GestorBitacora": [("bit_svc", n) for n in ("registrar", "listar", "opciones")],
    "GestorRecuperacion": [("seg_svc", n) for n in (
        "solicitar_recuperacion", "confirmar_recuperacion")],
    "GestorFavoritos": [("fav_svc", n) for n in (
        "listar_favoritos", "ids_de_favoritos", "marcar_favorito",
        "desmarcar_favorito")],
    "GestorVestidor": [("vest_svc", n) for n in ("estado", "probar")]
        + [("med_svc", "ajuste_de_producto")]
        + [("probador", n) for n in ("esta_disponible", "probar")],
    "GestorCatalogoProveedor": [("prov_svc", n) for n in (
        "listas_del_formulario", "listar_mis_productos", "obtener_mi_producto",
        "registrar_mi_producto", "editar_mi_producto",
        "cambiar_estado_de_mi_producto", "generar_variantes_de_mi_producto")],
    "GestorReportePorVoz": [("interprete", n) for n in (
        "esta_disponible", "interpretar", "obtener_proveedor")],
    # GestorAsistente (CU-34) y GestorNotificaciones (CU-40) no figuran: no
    # hay codigo que leer. Se dibujan vacios, que es la verdad del modelo.
}

# --- fronteras -> el servicio de Angular y el endpoint del router -------------
FRONT = {
    "PantallaPromociones": {"web": ("promociones", None), "rt": "promo_rt"},
    "PantallaCarrito": {"web": ("carrito", None), "rt": "carr_rt"},
    "PantallaCheckout": {"web": ("pedidos", None), "rt": "vent_rt"},
    "WebhookPasarela": {"web": None, "rt": "pago_rt"},
    "PantallaCompras": {"web": ("compras", None), "rt": "hist_rt"},
    "PantallaTurno": {"web": ("caja", None), "rt": "caja_rt"},
    "PantallaVenta": {"web": ("pos", None), "rt": "pos_rt"},
    "PantallaDevolucion": {"web": ("devoluciones", None), "rt": "dev_rt"},
    "PantallaParaVos": {"web": None, "rt": "ia_rt"},
    "PantallaTablero": {"web": ("tablero", None), "rt": "tab_rt"},
    "PantallaReportes": {"web": ("reportes", None), "rt": "rep_rt",
                         "sel": ("catalogo_de_reportes", "descargar")},
    "PantallaAbastecimiento": {"web": ("abastecimiento", None), "rt": "abas_rt"},
    "PantallaBitacora": {"web": None, "rt": "bit_rt"},
    "PantallaFavoritos": {"web": None, "rt": "fav_rt"},
    "PantallaVestidor": {"web": None, "rt": "med_rt"},
    "PantallaMisProductos": {"web": ("proveedor", None), "rt": "prov_rt"},
    # El router de reportes sirve a DOS casos de uso. Se parte con `sel` para
    # que cada frontera muestre solo sus endpoints: si no, CU-35 y CU-37
    # aparecen con la misma lista y el diagrama deja de decir nada.
    "PantallaReportePorVoz": {"web": ("dictado", None), "rt": "rep_rt",
                              "sel": ("hay_pedido_por_voz", "pedir_por_voz")},
    # Lo mismo con el de seguridad, que atiende todo el Ciclo 1: de los 20
    # endpoints solo dos son de CU-41.
    "PantallaRecuperacion": {"web": ("auth", None), "rt": "seg_rt",
                             "sel": ("solicitar_recuperacion", "confirmar_recuperacion")},
    "CanalDeAviso": {"web": None, "rt": "correo"},
    # PantallaAsistente (CU-34) queda fuera por la misma razon que
    # GestorAsistente: todavia no existe.
}


def ps_lista_ops(pares):
    """Las operaciones que EXISTEN, en la forma que espera PowerShell."""
    trozos = []
    for mod, nom in pares:
        f = be.get(mod, {}).get(nom)
        if not f:
            print(f"  (aviso) no existe {mod}.{nom}", file=sys.stderr)
            continue
        ps = "; ".join(
            "@{n='%s';t='%s'}" % (p, t.replace("'", "")) for p, t in f["p"]
        )
        trozos.append(
            "    @{n='%s'; r='%s'; p=@(%s)}" % (nom, f["r"].replace("'", ""), ps)
        )
    return trozos


salida = [
    "# GENERADO por scripts/gen-ops-2-3-ciclo3.py --- NO editar a mano.",
    "# Los nombres y los tipos salen del codigo (ast sobre el backend, regex sobre",
    "# los servicios de Angular) y de information_schema de la base de pruebas, que",
    "# `alembic upgrade head` deja al dia. Es lo que permite defender el diagrama:",
    "# cada operacion se puede abrir en el repositorio.",
    "",
    "$ATTRS = @{",
]
for clase, tabla in TABLA_DE.items():
    if tabla not in cols:
        continue
    attrs = "; ".join("@{n='%s';t='%s'}" % (c, t) for c, t in cols[tabla])
    salida.append("  '%s' = @(%s)" % (clase, attrs))
salida.append("}")
salida.append("")

salida.append("$OPS = @{")
for clase, pares in OPS.items():
    trozos = ps_lista_ops(pares)
    if not trozos:
        continue
    salida.append("  '%s' = @(" % clase)
    salida.append(",\n".join(trozos))
    salida.append("  )")
salida.append("}")
salida.append("")

salida.append("$CTRL = @{")
for clase, pares in CTRL.items():
    trozos = ps_lista_ops(pares)
    if not trozos:
        continue
    salida.append("  '%s' = @(" % clase)
    salida.append(",\n".join(trozos))
    salida.append("  )")
salida.append("}")
salida.append("")

# Fronteras: los metodos del servicio de Angular, y los endpoints del router.
salida.append("$FRONT = @{")
for clase, d in FRONT.items():
    trozos = []
    if d["web"]:
        svc = d["web"][0]
        for nom, f in fe.get(svc, {}).items():
            ps = "; ".join(
                "@{n='%s';t='%s'}" % (p, t.replace("'", "")) for p, t in f["p"]
            )
            trozos.append(
                "    @{n='%s'; r='%s'; p=@(%s)}" % (nom, f["r"].replace("'", ""), ps)
            )
    sel = d.get("sel")
    for nom, f in be.get(d["rt"], {}).items():
        if nom.startswith("_"):
            continue
        if sel and nom not in sel:
            continue
        ps = "; ".join(
            "@{n='%s';t='%s'}" % (p, t.replace("'", "")) for p, t in f["p"]
        )
        trozos.append(
            "    @{n='%s'; r='%s'; p=@(%s)}" % (nom, f["r"].replace("'", ""), ps)
        )
    if not trozos:
        continue
    salida.append("  '%s' = @(" % clase)
    salida.append(",\n".join(trozos))
    salida.append("  )")
salida.append("}")

destino = os.path.join(RAIZ, "scripts", "ea-clases-2-3-ciclo3.datos.ps1")
io.open(destino, "w", encoding="utf-8-sig").write("\n".join(salida) + "\n")
print(f"escrito {destino}")
print(f"  entidades con columnas : {sum(1 for t in TABLA_DE.values() if t in cols)}")
print(f"  entidades con ops      : {sum(1 for c, p in OPS.items() if ps_lista_ops(p))}")
print(f"  controladores          : {sum(1 for c, p in CTRL.items() if ps_lista_ops(p))}")
