"""
P2 - Organizacion  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-05 Gestionar ciudades y sucursales
  CU-06 Gestionar empleados
  CU-07 Gestionar proveedores
"""
from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.modules.organizacion.models import Ciudad, Sucursal

# Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna
# validacion de permisos, ningun commit de transaccion compuesta.


def listar_sucursales_activas(db: Session) -> list[Row]:
    """Sucursales operativas con el nombre de su ciudad, ordenadas."""
    return list(
        db.execute(
            select(Sucursal.id, Sucursal.nombre, Ciudad.nombre.label("ciudad"))
            .join(Ciudad, Ciudad.id == Sucursal.ciudad_id)
            .where(Sucursal.activa.is_(True))
            .order_by(Ciudad.nombre, Sucursal.nombre)
        ).all()
    )


# TODO CU-05, CU-06 y CU-07: implementar el resto de las consultas.
