"""
Tanda C de la auditoría: las tareas automáticas (app/core/tareas.py).

Lo que importa cubrir:
  - una vuelta recorre las empresas y corre las tareas de cada una;
  - si el otro worker tiene el bloqueo, esta vuelta no hace nada;
  - una tarea que falla no corta las demás;
  - la variable las prende y las apaga.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select, text

from app.core import tareas


def test_una_vuelta_corre_las_tareas_de_cada_empresa(db, fabrica_sesiones) -> None:
    from app.modules.datos.models import Respaldo

    vuelta = tareas.correr_vuelta(fabrica_sesiones)

    assert vuelta.tomada is True
    assert vuelta.empresas >= 1
    assert vuelta.errores == []
    # 1 de plataforma + todas las de cada empresa.
    assert vuelta.hechas == 1 + vuelta.empresas * len(tareas.TAREAS_POR_EMPRESA)
    # Y se notan: la copia automática salió sola.
    db.expire_all()
    assert db.scalar(select(Respaldo).where(Respaldo.tipo == "AUTOMATICA")) is not None

    # Idempotente: la segunda vuelta no crea otra copia.
    tareas.correr_vuelta(fabrica_sesiones)
    db.expire_all()
    copias = db.scalars(select(Respaldo).where(Respaldo.tipo == "AUTOMATICA")).all()
    assert len(copias) == 1


def test_si_el_otro_worker_tiene_el_bloqueo_no_corre(db, fabrica_sesiones) -> None:
    otro = fabrica_sesiones().get_bind().connect()
    try:
        assert otro.scalar(text("SELECT pg_try_advisory_lock(:k)"),
                           {"k": tareas.CLAVE_DEL_BLOQUEO}) is True
        vuelta = tareas.correr_vuelta(fabrica_sesiones)
        assert vuelta.tomada is False
        assert vuelta.hechas == 0
    finally:
        otro.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": tareas.CLAVE_DEL_BLOQUEO})
        otro.close()
    # Liberado, la siguiente sí corre.
    assert tareas.correr_vuelta(fabrica_sesiones).tomada is True


def test_una_tarea_que_falla_no_corta_las_demas(db, fabrica_sesiones, monkeypatch) -> None:
    hechas: list[int] = []

    def rompe(_db, _empresa):
        raise RuntimeError("se cayó el proveedor")

    def anota(_db, empresa):
        hechas.append(empresa)

    monkeypatch.setattr(tareas, "TAREAS_POR_EMPRESA", (("rota", rompe), ("sana", anota)))
    vuelta = tareas.correr_vuelta(fabrica_sesiones)

    assert len(hechas) == vuelta.empresas  # la sana corrió en todas
    assert len(vuelta.errores) == vuelta.empresas
    assert "se cayó el proveedor" in vuelta.errores[0]


@pytest.mark.parametrize("valor, esperado", [
    ("on", True), ("ON", True), ("1", True), ("true", True),
    ("off", False), ("", False), ("no", False),
])
def test_la_variable_las_prende_y_las_apaga(valor, esperado, monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "TAREAS_AUTOMATICAS", valor)
    assert tareas.encendidas() is esperado
