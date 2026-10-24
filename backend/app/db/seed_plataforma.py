"""Crea la cuenta del administrador de la plataforma (CU-01, 2do parcial).

    python -m app.db.seed_plataforma

Lee PLATAFORMA_ADMIN_CORREO y PLATAFORMA_ADMIN_CLAVE del entorno. La cuenta no
pertenece a ninguna empresa (`empresa_id` NULL) y trabaja en modo plataforma.
Es idempotente: si el correo ya existe, no hace nada.

No va en una migracion porque una migracion no puede llevar una contrasena.
"""

import sys

from sqlalchemy import func, null, select

# Importar la aplicacion registra TODOS los modelos: sin eso, SQLAlchemy no
# puede resolver las relaciones de `Usuario` (Cliente -> Categoria, etc.).
import app.main  # noqa: F401,E402
from app.core.config import settings
from app.core.security import hash_password
from app.core.tenencia import ROL_PLATAFORMA, modo_plataforma
from app.db.session import SessionLocal
from app.modules.seguridad.models import Rol, Usuario


def main() -> None:
    correo = settings.PLATAFORMA_ADMIN_CORREO.strip().lower()
    clave = settings.PLATAFORMA_ADMIN_CLAVE
    if not correo or not clave:
        print("Defina PLATAFORMA_ADMIN_CORREO y PLATAFORMA_ADMIN_CLAVE.")
        sys.exit(1)

    with SessionLocal() as db:
        modo_plataforma(db)
        # La cuenta de la plataforma no tiene empresa: su correo es único entre
        # las cuentas sin empresa (CU-06).
        existe = select(Usuario.id).where(
            func.lower(Usuario.correo) == correo, Usuario.empresa_id.is_(None)
        )
        if db.scalar(existe):
            print(f"  = {correo} ya existe, no se toca")
            return
        rol = db.scalar(select(Rol).where(Rol.nombre == ROL_PLATAFORMA))
        if rol is None:
            print("Falta el rol ADMIN_PLATAFORMA: corra antes `alembic upgrade head`.")
            sys.exit(1)
        db.add(
            Usuario(
                correo=correo,
                hash_contrasena=hash_password(clave),
                nombres="Administrador",
                apellidos="Plataforma",
                rol_id=rol.id,
                empresa_id=null(),  # con None, el DEFAULT pondria una empresa
            )
        )
        db.commit()
        print(f"  + administrador de la plataforma {correo}")


if __name__ == "__main__":
    main()
