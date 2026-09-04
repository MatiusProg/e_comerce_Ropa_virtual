"""Carga de datos iniciales.

Ciclo 1: los cinco roles del sistema, el usuario Administrador y las ciudades
donde opera la cadena. Es el minimo para que alguien pueda iniciar sesion en el
sistema recien desplegado y empezar a dar de alta sucursales, que es el criterio
de cierre del ciclo.

Ciclo 2: se amplia con proveedores, catalogo, variantes e inventario.

Es idempotente: se puede correr las veces que haga falta sin duplicar nada, lo
que importa porque se ejecuta contra la base desplegada.

Uso:
    python -m app.db.seed

La contrasena inicial del administrador se toma de ADMIN_PASSWORD. Si no esta
definida, el seed no crea el usuario: nunca se versiona ni se inventa una
contrasena por defecto para un entorno desplegado.
"""

import os
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.modules.organizacion.models import Ciudad
from app.modules.seguridad.models import Rol, Usuario

ROLES: list[tuple[str, str]] = [
    ("ADMINISTRADOR", "Acceso completo: usuarios, organizacion, catalogo, inventario y reportes"),
    ("CLIENTE", "Consulta el catalogo, reserva prendas y compra"),
    ("ENCARGADO", "Responsable operativo de una sucursal"),
    ("CAJERO", "Opera el punto de venta de una sucursal"),
    ("PROVEEDOR", "Consulta la informacion de sus propios productos"),
]

CIUDADES: list[tuple[str, str]] = [
    ("Santa Cruz de la Sierra", "Santa Cruz"),
    ("La Paz", "La Paz"),
    ("Cochabamba", "Cochabamba"),
]


def _sembrar_roles(db: Session) -> dict[str, Rol]:
    existentes = {r.nombre: r for r in db.scalars(select(Rol)).all()}
    for nombre, descripcion in ROLES:
        if nombre not in existentes:
            rol = Rol(nombre=nombre, descripcion=descripcion)
            db.add(rol)
            existentes[nombre] = rol
            print(f"  + rol {nombre}")
    db.flush()
    return existentes


def _sembrar_ciudades(db: Session) -> None:
    existentes = {c.nombre for c in db.scalars(select(Ciudad)).all()}
    for nombre, departamento in CIUDADES:
        if nombre not in existentes:
            db.add(Ciudad(nombre=nombre, departamento=departamento))
            print(f"  + ciudad {nombre}")


def _sembrar_administrador(db: Session, roles: dict[str, Rol]) -> None:
    correo = os.getenv("ADMIN_EMAIL", "admin@fashionstore.bo")
    password = os.getenv("ADMIN_PASSWORD")

    if db.scalar(select(Usuario).where(Usuario.correo == correo)):
        print(f"  = administrador {correo} ya existe")
        return

    if not password:
        print(
            "  ! ADMIN_PASSWORD no esta definida: no se crea el administrador.\n"
            "    Definirla y volver a ejecutar el seed."
        )
        return

    db.add(
        Usuario(
            correo=correo,
            hash_contrasena=hash_password(password),
            nombres="Administrador",
            apellidos="del Sistema",
            rol_id=roles["ADMINISTRADOR"].id,
        )
    )
    print(f"  + administrador {correo}")


def main() -> None:
    print("Sembrando datos del Ciclo 1...")
    with SessionLocal() as db:
        roles = _sembrar_roles(db)
        _sembrar_ciudades(db)
        _sembrar_administrador(db, roles)
        db.commit()
    print("Listo.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"Error al sembrar: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
