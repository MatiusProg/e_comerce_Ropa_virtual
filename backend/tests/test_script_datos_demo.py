"""
El script de datos de demostración para la analítica (scripts/datos_demo_analitica.py).

Lo que importa
- Con los datos cargados, los tres entrenamientos funcionan: demanda,
  segmentos y anomalías (que sin ellos responde 409).
- El turno con el faltante sembrado sale marcado y la explicación nombra el
  arqueo.
- No se puede cargar dos veces, y `borrar` deja la base como estaba.
"""
from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.modules.seguridad.models import Cliente, Usuario
from app.modules.ventas.models import Caja, DetalleVenta, Devolucion, TurnoCaja, Venta
from scripts import datos_demo_analitica as demo
from tests.test_cu36_tablero import CATEGORIAS, COLORES, PRODUCTOS, TALLAS, _crear_sucursal

API = "/api/v1/analitica"


def _catalogo(api, admin) -> None:
    """Dos sucursales y seis productos con dos variantes cada uno."""
    _crear_sucursal(api, admin, nombre="Centro")
    _crear_sucursal(api, admin, nombre="Norte")
    categoria = api.post(CATEGORIAS, headers=admin,
                         json={"nombre": "Blusas", "orden": 0, "activa": True}).json()["id"]
    tallas = [
        api.post(TALLAS, headers=admin, json={"tipo_prenda": "Superior", "codigo": c,
                                              "orden": i, "activa": True}).json()["id"]
        for i, c in enumerate(("S", "M"))
    ]
    color = api.post(COLORES, headers=admin, json={"nombre": "Marfil", "hexadecimal": "#F5F0E6",
                                                   "activo": True}).json()["id"]
    for i in range(6):
        producto = api.post(PRODUCTOS, headers=admin, json={
            "codigo": f"DEM-{i:03d}", "nombre": f"Prenda {i}", "categoria_id": categoria,
            "precio_base": f"{120 + i * 60}.00", "activo": True,
        })
        assert producto.status_code == 201, producto.text
        r = api.post(f"{PRODUCTOS}/{producto.json()['id']}/variantes/generar", headers=admin,
                     json={"tallas": tallas, "colores": [color]})
        assert r.status_code == 201, r.text


def _cuentas(db) -> dict[str, int]:
    return {
        "venta": db.scalar(select(func.count(Venta.id))),
        "detalle_venta": db.scalar(select(func.count(DetalleVenta.id))),
        "devolucion": db.scalar(select(func.count(Devolucion.id))),
        "turno": db.scalar(select(func.count(TurnoCaja.id))),
        "caja": db.scalar(select(func.count(Caja.id))),
        "cliente": db.scalar(select(func.count(Cliente.id))),
        "usuario": db.scalar(select(func.count(Usuario.id))),
    }


def test_con_los_datos_demo_entrenan_los_tres_modelos_y_sale_el_faltante(
    api, db, cabeceras_admin
) -> None:
    _catalogo(api, cabeceras_admin)
    antes = _cuentas(db)

    # Sin datos, las anomalías no tienen con qué.
    assert api.post(f"{API}/anomalias", headers=cabeceras_admin).status_code == 409

    resumen = demo.sembrar(db, semanas=12, semilla=42)
    db.commit()
    assert resumen.turnos >= 40
    assert resumen.devoluciones >= 25
    assert resumen.clientes == demo.CLIENTES_DEMO
    assert set(resumen.turnos_raros) == {
        "faltante_arqueo", "muchas_devoluciones", "madrugada_15h", "devolucion_de_valor"}

    # Demanda y segmentos.
    r = api.post(f"{API}/entrenamientos", headers=cabeceras_admin)
    assert r.status_code == 201, r.text
    assert r.json()["entrenado"] is True
    clientes = api.get(f"{API}/clientes", headers=cabeceras_admin).json()
    demo_ids = {c.id for c in db.scalars(select(Cliente).join(Usuario).where(
        Usuario.correo.like(f"%@{demo.DOMINIO_CLIENTES}")))}
    segmentos = {c["segmento"] for c in clientes if c["cliente_id"] in demo_ids}
    assert len(segmentos) >= 2, segmentos

    # Anomalías: el faltante sembrado sale marcado y la explicación nombra el arqueo.
    r = api.post(f"{API}/anomalias", headers=cabeceras_admin)
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    marcadas = {m["id"]: m for m in cuerpo["turnos"]["marcadas"]}
    faltante = resumen.turnos_raros["faltante_arqueo"]
    assert faltante in marcadas, (resumen.turnos_raros, list(marcadas))
    assert "arqueo" in marcadas[faltante]["explicacion"].lower()
    assert cuerpo["devoluciones"]["suficientes"] is True

    # No se carga dos veces.
    with pytest.raises(demo.ErrorDatosDemo):
        demo.sembrar(db, semanas=12, semilla=42)
    db.rollback()

    # Borrar deja todo como estaba.
    cuenta = demo.borrar(db)
    db.commit()
    assert cuenta["venta"] == resumen.ventas
    assert cuenta["devolucion"] == resumen.devoluciones
    assert cuenta["turno_caja"] == resumen.turnos
    assert _cuentas(db) == antes
    assert not demo.hay_datos_demo(db)


def test_sin_sucursales_ni_productos_avisa_sin_romper(db, cabeceras_admin) -> None:
    with pytest.raises(demo.ErrorDatosDemo):
        demo.sembrar(db, semanas=12)
    db.rollback()
